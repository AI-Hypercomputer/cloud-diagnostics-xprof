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

"""A profile capture command implementation for the xprof CLI.

This command is used as part of the xprof CLI to capture a profile from a
running job that can be viewed in a hosted TensorBoard instance. The intention
is that this can be used to capture a profile from an instance using the
`xprof capture` command.
"""

import argparse
from collections.abc import Mapping, Sequence
import datetime
import socket
from cloud_diagnostics_xprof.actions import action

_DOWNLOAD_CAPTURE_PROFILE = (
    'wget https://raw.githubusercontent.com/pytorch/xla/master/scripts/capture_profile.py'
)
_PYTORCH_CAPTURE_COMMAND = (
    'python3 capture_profile.py --service_addr localhost:{port} --duration'
    ' {duration} --log_dir {log_directory}'
)
_JAX_CAPTURE_COMMAND = (
    'python3 -m jax.collect_profile {port} {duration} --log_dir={log_directory}'
    ' --no_perfetto_link'
)
_UPLOAD_PROFILE_COMMAND = (
    'gsutil cp $(ls /tmp/tensorboard/{session_id}/plugins/profile/*/*xplane.pb|'
    ' tail -1)'
    ' {log_directory}/tensorboard/plugins/profile/session_{session_id}/{host}.xplane.pb'
)
_CLOUDTOP_DOMAIN = '.c.googlers.com'


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
        choices=['pytorch', 'jax'],
        required=True,
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
    command = [
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
        f'{args.command}',
    ]

    if self._running_on_cloudtop():
      command.extend([
          '--',
          '-o ProxyCommand corp-ssh-helper %h %p',
      ])

    return command

  def _profile_single_host(
      self,
      session_id: str,
      host: str,
      zone: str,
      args: argparse.Namespace,
      extra_args: Mapping[str, str] | None = None,
      verbose: bool = False,
  ) -> str:
    """Runs the profile script on a single host."""
    print(f'Starting profile capture on host {host}.')
    stdout_all = ''

    profile_log_location = f'{args.log_directory}/tensorboard'

    commands: list[Sequence[str]] = []
    single_host_args = argparse.Namespace(**vars(args))
    single_host_args.host = host
    single_host_args.zone = zone
    # Framework is PyTorch.
    if args.framework == 'pytorch':
      # Command to download the capture profile script.
      single_host_args.command = _DOWNLOAD_CAPTURE_PROFILE
      commands.append(
          self._build_command(single_host_args, extra_args, verbose)
      )
      # Capture command (assuming script is already uploaded).
      single_host_args.command = _PYTORCH_CAPTURE_COMMAND.format(
          port=args.port,
          duration=args.duration,
          log_directory=profile_log_location,
      )
      commands.append(
          self._build_command(
              args=single_host_args,
              extra_args=extra_args,
              verbose=verbose,
          )
      )

    # Framework is JAX.
    if args.framework == 'jax':
      # Local directory on remote host.
      local_log_location = f'/tmp/tensorboard/{session_id}'
      # Capture command, generates traces locally.
      single_host_args.command = _JAX_CAPTURE_COMMAND.format(
          port=args.port,
          duration=args.duration,
          log_directory=local_log_location,
      )
      commands.append(
          self._build_command(
              args=single_host_args,
              extra_args=extra_args,
              verbose=verbose,
          )
      )

      # Upload the profile to gs bucket.
      single_host_args.command = _UPLOAD_PROFILE_COMMAND.format(
          log_directory=args.log_directory,
          session_id=session_id,
          host=host,
      )
      commands.append(
          self._build_command(
              args=single_host_args,
              extra_args=extra_args,
              verbose=verbose,
          )
      )

    # Run all commands.
    try:
      for command in commands:
        # Run the profile script on host.
        if verbose:
          print(f'Running command {command} on {host} host.')
        stdout = self._run_command(
            command=command,
            verbose=verbose,
        )

        stdout_all += stdout
      print(
          f'Profile saved to {args.log_directory}/tensorboard and session id'
          f' is session_{session_id}.'
      )
    except Exception as e:  # pylint: disable=broad-except
      print(f'Failed to profile host {host} with error: {e}')

    return stdout_all

  def run(
      self,
      args: argparse.Namespace,
      extra_args: Mapping[str, str] | None = None,
      verbose: bool = False,
  ) -> str:

    stdout_all_hosts: list[str] = []
    session_id = datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
    if verbose:
      print(f'Running profile capture on {len(args.hosts)} hosts...')

    for host in args.hosts:
      # Run the profile script on a single host.
      single_host_stdout = self._profile_single_host(
          session_id=session_id,
          host=host,
          zone=args.zone,
          args=args,
          extra_args=extra_args,
          verbose=verbose,
      )
      stdout_all_hosts.append(single_host_stdout)

    return '\n'.join(stdout_all_hosts)

  def display(
      self,
      display_str: str | None,
      *,
      args: argparse.Namespace,
      extra_args: Mapping[str, str] | None = None,
      verbose: bool = False,
  ) -> None:
    """Display provided string after potential formatting.

    Args:
      display_str: The string to display.
      args: The arguments parsed from the command line.
      extra_args: Any extra arguments to pass to the command.
      verbose: Whether to print the command and other output.
    """
    return None

  def _running_on_cloudtop(self):
    """Check if the current machine is a cloudtop.

    Returns:
      True if the machine is a cloudtop.
    """
    # TODO(b/407869734): Improve this check to be more robust.
    return _CLOUDTOP_DOMAIN in socket.getfqdn()
