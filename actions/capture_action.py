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
from actions import action


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

    # Build the profile command
    profile_log_location = (
        f'{args.log_directory}/{args.experiment_name}/{args.run_name}'
    )
    profile_script_command = (
        'python3 capture_profile.py'
        f' --service_addr "localhost:{args.port}"'
        f' --logdir {profile_log_location}'
        f' --duration_ms {args.duration}'
    )
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
        f'{profile_script_command}',
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

    upload_script_command = (
        'wget https://raw.githubusercontent.com/pytorch/xla/master/'
        'scripts/capture_profile.py'
    )

    if verbose:
      print(f'Running profile capture on {host} host...')

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

    # Run the profile script on host.
    if verbose:
      print(f'Running profile script on single host {host}...')

    # Include a host-specific argument for the host name.
    single_host_args = argparse.Namespace(**vars(args))
    single_host_args.host = host
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
      try:
        single_host_stdout = self._profile_single_host(
            host=host,
            zone=args.zone,
            args=args,
            extra_args=extra_args,
            verbose=verbose,
        )
        stdout_all_hosts.append(single_host_stdout)
      # Catch issues with profiling the host.
      except Exception as e:  # pylint: disable=broad-except
        print(f'Failed to profile host {host}: {e}')

    return '\n'.join(stdout_all_hosts)
