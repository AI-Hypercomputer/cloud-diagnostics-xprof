# Copyright 2023 Google LLC
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#      https://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A profile capture command implementation for the xprofiler CLI.

This command is used as part of the xprofiler CLI to capture a profile from a
running job that can be viewed in a hosted TensorBoard instance. The intention
is that this can be used to capture a profile from an instance using the
`xprofiler capture` command.
"""

import argparse
from collections.abc import Mapping, Sequence
from xprofiler.src.cloud_diagnostics_xprof.actions import action


class Capture(action.Command):
  """A command to capture a profile from a hosted TensorBoard instance."""

  def __init__(self):
    super().__init__(
        name='caputre',
        description='Capture a profile from a hosted TensorBoard instance.',
    )

  def add_subcommand(
      self,
      subparser: argparse._SubParsersAction,
  ) -> None:
    """Creates a subcommand for `capture`.

    Args:
        subparser: The subparser to add the capture subcommand to.
    """
    capture_parser = subparser.add_parser(
        name='capture',
        help='Capture a profile from a hosted TensorBoard instance.',
        formatter_class=argparse.RawTextHelpFormatter,  # Keeps format in help.
    )
    # log-directory is required.
    capture_parser.add_argument(
        '--log-directory',
        '-l',
        metavar='GS_PATH',
        required=True,
        help='The log directory to capture a profile to.',
    )
    # zone is required.
    capture_parser.add_argument(
        '--zone',
        '-z',
        metavar='ZONE_NAME',
        required=True,
        help='The GCP zone to the instance in for the profile capture.',
    )
    # hosts must be specified
    capture_parser.add_argument(
        '--hosts',
        '-n',
        metavar='HOST_NAME',
        nargs='+',
        required=True,
        help='The host name to capture a profile from.',
    )
    # port is optional.
    capture_parser.add_argument(
        '--port',
        '-p',
        metavar='LOCAL_PORT',
        default='9012',
        help='The local port to capture a profile from.',
    )
    # experiment name is optional.
    capture_parser.add_argument(
        '--experiment-name',
        '-e',
        metavar='EXPERIMENT_NAME',
        default='experiment',
        help='The experiment name to capture a profile for.',
    )
    # run name is optional.
    capture_parser.add_argument(
        '--run-name',
        '-r',
        metavar='RUN_NAME',
        default='run',
        help='The run name to capture a profile for.',
    )
    # Duration is optional.
    capture_parser.add_argument(
        '--duration',
        '-d',
        metavar='DURATION',
        default='2000',
        help='The duration of the profile in milliseconds.',
    )
    # framework is optional.
    capture_parser.add_argument(
        '--framework',
        '-f',
        metavar='FRAMEWORK',
        choices=['pytorch', 'jax', 'unknown'],
        default='unknown',
        help='The framework to capture a profile for.',
    )
    # verbose is optional.
    capture_parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Print the command.',
    )

  def _build_command(
      self,
      args: argparse.Namespace,
      extra_args: Mapping[str, str] | None = None,
      verbose: bool = False,
  ) -> Sequence[str]:

    command = []

    profile_command = [
        self.GCLOUD_COMMAND,
        'compute',
        'tpus',
        'tpu-vm',
        'ssh',
        args.host,
        '--zone',
        args.zone,
        '--worker=all',
        '--command',
        f'{args.profile_script}',
    ]
    command.extend(profile_command)

    return command

  def _profile_single_host(
      self,
      host: str,
      zone: str,
      args: argparse.Namespace,
      extra_args: Mapping[str, str] | None = None,
      verbose: bool = False,
  ) -> str:
    """Runs the profile script on a single host."""
    stdout_all = ''

    profile_log_location = (
        f'{args.log_directory}/{args.experiment_name}/{args.run_name}'
    )

    # Include a host-specific argument for the host name.
    single_host_args = argparse.Namespace(**vars(args))
    single_host_args.host = host
    # Allow for multiple profile commands to run for unknown framework.
    profile_commands: dict[str, str] = {}

    # Does PyTorch support if unknown
    if (args.framework == 'pytorch') or (args.framework == 'unknown'):
      # Upload the capture profile script to host.
      try:
        upload_script_command = (
            'wget https://raw.githubusercontent.com/pytorch/xla/master/'
            'scripts/capture_profile.py'
        )

        # Upload the capture profile script to host.
        if verbose:
          print('Uploading profile script to host...')
        upload_profile_script_command = [
            self.GCLOUD_COMMAND,
            'compute',
            'tpus',
            'tpu-vm',
            'ssh',
            host,
            '--zone',
            zone,
            '--worker=all',
            '--command',
            f'{upload_script_command}',
        ]
        upload_profile_script_stdout = self._run_command(
            command=upload_profile_script_command,
            verbose=verbose,
        )
        stdout_all += upload_profile_script_stdout
      except Exception as e:  # pylint: disable=broad-except
        print(f'Failed to upload profile script to host {host}: {e}')
        # Skip the pytorch profile capture if the script fails to upload.

      # Capture command (assuming script is already uploaded).
      profile_commands['pytorch'] = (
          'python3 capture_profile.py'
          f' --service_addr "localhost:{args.port}"'
          f' --logdir {profile_log_location}'
          f' --duration_ms {args.duration}'
      )
    # Does JAX support if unknown
    if (args.framework == 'jax') or (args.framework == 'unknown'):
      profile_commands['jax'] = (
          'python -m jax.collect_profile'
          f' {args.port}'
          f' {args.duration}'
          f' --log_dir={profile_log_location}'
          ' --no_perfetto_link'  # No UI link appears.
      )

    # Run the profile script for each framework specified.
    for command_name, command in profile_commands.items():
      try:
        # Run the profile script on host.
        if verbose:
          print(f'Running profile capture on {host} host for {command_name}...')
        # Pass the relevant framework command to profile.
        single_host_args.profile_script = command
        single_host_profile_command = self._build_command(
            args=single_host_args,
            extra_args=extra_args,
            verbose=verbose,
        )
        stdout_single_host_profile = self._run_command(
            command=single_host_profile_command,
            verbose=verbose,
        )

        stdout_all += stdout_single_host_profile
      except Exception as e:  # pylint: disable=broad-except
        error_message = (
            f'Failed to profile host {host} with {command_name} framework: {e}'
        )
        print(error_message)

    return stdout_all

  def run(
      self,
      args: argparse.Namespace,
      extra_args: Mapping[str, str] | None = None,
      verbose: bool = False,
  ) -> str:

    stdout_all_hosts: list[str] = []

    if verbose:
      print(f'Running profile capture on {len(args.hosts)} hosts...')

    for host in args.hosts:
      # Run the profile script on a single host.
      single_host_stdout = self._profile_single_host(
          host=host,
          zone=args.zone,
          args=args,
          extra_args=extra_args,
          verbose=verbose,
      )
      stdout_all_hosts.append(single_host_stdout)

    return '\n'.join(stdout_all_hosts)
