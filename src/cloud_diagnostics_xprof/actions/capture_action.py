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
running job that can be viewed in a xprofiler instance. The intention
is that this can be used to capture a profile from an instance using the
`xprof capture` command.
"""

import argparse
from collections.abc import Mapping, Sequence
import datetime

from cloud_diagnostics_xprof.actions import action


_DOWNLOAD_CAPTURE_PROFILE = (
    'wget https://raw.githubusercontent.com/pytorch/xla/master/scripts/capture_profile.py'
)
_PYTORCH_CAPTURE_COMMAND = (
    'python3 capture_profile.py --service_addr localhost:{port} --duration'
    ' {duration} --logdir {log_directory}'
)
_JAX_CAPTURE_COMMAND = (
    'python3 -m jax.collect_profile {port} {duration} --log_dir={log_directory}'
    ' --no_perfetto_link'
)
_UPLOAD_PROFILE_COMMAND = (
    'gsutil cp $(ls tmp/tensorboard/{session_id}/plugins/profile/*/*xplane.pb|'
    ' tail -1)'
    ' {log_directory}/tensorboard/plugins/profile/session_{session_id}/{host}.xplane.pb'
)

_XPROFZ_ERROR_MESSAGE = (
    'No trace event was collected because there were no responses from clients'
)
_SSH_CONNECTION_TIMED_OUT_MESSAGE = 'Connection timed out'


class Capture(action.Command):
  """A command to capture a profile from a xprofiler instance."""

  def __init__(self):
    super().__init__(
        name='caputre',
        description='Capture a profile from a xprofiler instance.',
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
        help='Capture a profile from a xprofiler instance.',
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
    # framework is optional.
    capture_parser.add_argument(
        '--orchestrator',
        '-o',
        metavar='ORCHESTRATOR',
        choices=['gce', 'gke'],
        default='gce',
        help='The orchestrator where workload is running.',
    )
    # hosts must be specified
    capture_parser.add_argument(
        '--hosts',
        '-n',
        metavar='HOST_NAME',
        nargs='+',
        required=True,
        help=(
            'The host name to capture a profile from.'
            ' List of VM names for GCE and a list of pods for GKE.'
        ),
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
        type=int,
        help='The duration of the profile in milliseconds.',
    )
    # framework is optional.
    capture_parser.add_argument(
        '--framework',
        '-f',
        metavar='FRAMEWORK',
        choices=['pytorch', 'jax', 'tensorflow'],
        required=True,
        help='The framework to capture a profile for.',
    )
    # proxy is optional.
    capture_parser.add_argument(
        '--use-ssh-proxy',
        '-u',
        action='store_true',
        default=False,
        help='Use the SSH proxy to connect to the instance.',
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
      extra_args: Mapping[str, str | None] | None = None,
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
        args.command,
    ]

    if args.use_ssh_proxy:
      command.extend([
          '--',
          '-o ProxyCommand corp-ssh-helper %h %p',
      ])

    return command

  def _build_command_gke(self, args: argparse.Namespace) -> Sequence[str]:
    command = [
        'kubectl',
        'exec',
        args.host,
        '--',
        'bash',
        '-c',
        args.command,
    ]
    return command

  def _profile_single_host_gce(
      self,
      session_id: str,
      host: str,
      local_log_location: str,
      args: argparse.Namespace,
      single_host_args: argparse.Namespace,
      extra_args: Mapping[str, str | None] | None = None,
      verbose: bool = False,
  ) -> list[Sequence[str]]:
    """Runs the profile script on a single host."""
    commands: list[Sequence[str]] = []
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
          log_directory=local_log_location,
      )
      commands.append(
          self._build_command(
              args=single_host_args,
              extra_args=extra_args,
              verbose=verbose,
          )
      )

    # Framework is JAX.
    elif args.framework == 'jax':
      # Local directory on remote host.
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

    # Framework is TensorFlow.
    elif args.framework == 'tensorflow':
      # On-demand capture not supported yet; use UI instead.
      # Raise an error to indicate that on-demand capture is not supported.
      raise ValueError(
          'On-demand capture is not supported for TensorFlow yet.'
          '\n\nPlease use the UI method instead:'
          ' https://github.com/AI-Hypercomputer/cloud-diagnostics-xprof?tab=readme-ov-file#profile-capture-via-tensorboard-ui'
      )

    # Upload the profile to gs bucket.
    # Remove trailing slash from log directory; avoids creating a `/` directory.
    single_host_args.command = _UPLOAD_PROFILE_COMMAND.format(
        log_directory=args.log_directory.rstrip('/'),
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
    return commands

  def _profile_single_host_gke(
      self,
      session_id: str,
      host: str,
      local_log_location: str,
      args: argparse.Namespace,
      single_host_args: argparse.Namespace,
  ) -> list[Sequence[str]]:
    """Runs the profile script on a single host."""
    commands: list[Sequence[str]] = []
    # Framework is PyTorch.
    if args.framework == 'pytorch':
      # Command to download the capture profile script.
      single_host_args.command = _DOWNLOAD_CAPTURE_PROFILE
      commands.append(self._build_command_gke(single_host_args))
      # Capture command (assuming script is already uploaded).
      single_host_args.command = _PYTORCH_CAPTURE_COMMAND.format(
          port=args.port,
          duration=args.duration,
          log_directory=local_log_location,
      )
      commands.append(self._build_command_gke(args=single_host_args))

    # Framework is JAX.
    if args.framework == 'jax':
      # Local directory on remote host.
      # Capture command, generates traces locally.
      single_host_args.command = _JAX_CAPTURE_COMMAND.format(
          port=args.port,
          duration=args.duration,
          log_directory=local_log_location,
      )
      commands.append(self._build_command_gke(args=single_host_args))

    # Upload the profile to gs bucket.
    # Remove trailing slash from log directory; avoids creating a `/` directory.
    single_host_args.command = _UPLOAD_PROFILE_COMMAND.format(
        log_directory=args.log_directory.rstrip('/'),
        session_id=session_id,
        host=host,
    )
    commands.append(self._build_command_gke(args=single_host_args))
    return commands

  def _profile_single_host(
      self,
      session_id: str,
      host: str,
      zone: str,
      args: argparse.Namespace,
      extra_args: Mapping[str, str | None] | None = None,
      verbose: bool = False,
  ) -> str:
    """Runs the profile script on a single host."""
    print(f'Starting profile capture on host {host}.')
    stdout_all = ''

    commands: list[Sequence[str]] = []
    single_host_args = argparse.Namespace(**vars(args))
    single_host_args.host = host
    single_host_args.zone = zone
    single_host_args.use_ssh_proxy = args.use_ssh_proxy
    local_log_location = f'tmp/tensorboard/{session_id}'

    if args.orchestrator == 'gce':
      commands = self._profile_single_host_gce(
          session_id=session_id,
          host=host,
          local_log_location=local_log_location,
          args=args,
          single_host_args=single_host_args,
          extra_args=extra_args,
          verbose=verbose,
      )
    elif args.orchestrator == 'gke':
      commands = self._profile_single_host_gke(
          session_id=session_id,
          host=host,
          local_log_location=local_log_location,
          args=args,
          single_host_args=single_host_args,
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
      # Removes trailing slash from log directory before tensorboard directory.
      print(
          f'Profile saved to {args.log_directory.rstrip("/")}'
          '/tensorboard and session id'
          f' is session_{session_id}.'
      )
    except Exception as e:  # pylint: disable=broad-except
      print(f'Failed to profile host {host}')
      if _XPROFZ_ERROR_MESSAGE in str(e):
        print(
            'This is likely due to the job not being active. Please try again'
            ' after the job is active and profile server is running.'
        )
      elif _SSH_CONNECTION_TIMED_OUT_MESSAGE in str(e):
        print(
            'This is likely due to the SSH connection timing out. Please'
            ' validate the SSH connection to the VM and try again.'
        )
      else:
        print(f'Failed to profile host {host} with error: {e}')

    return stdout_all

  def _validate_run_args(
      self,
      *,
      args: argparse.Namespace,
      verbose: bool = False,
  ) -> None:
    """Validates args for the main command and raises an error if invalid.

    Intended to check arguments passed before the command is run.
    Checks:
      - Log directory (GCS bucket URL) exists.
      - Log directory (GCS bucket URL) has a path part.
      - Hosts exist.

    Args:
      args: The arguments parsed from the command line.
      verbose: Whether to print the command and other output.

    Raises:
      ValueError: If the log directory does not exist.
    """
    if not self._is_valid_bucket(
        bucket_name=args.log_directory,
        verbose=verbose,
    ):
      raise ValueError(f'Log directory {args.log_directory} does not exist.')

    if args.orchestrator == 'gce':
      for host in args.hosts:
        if not self._host_exists(
            host_name=host,
            zone=args.zone,
            verbose=verbose,
        ):
          raise ValueError(f'Host {host} does not exist.')

  def run(
      self,
      args: argparse.Namespace,
      extra_args: Mapping[str, str | None] | None = None,
      verbose: bool = False,
  ) -> str:
    """Runs the profile capture command."""
    self._validate_run_args(
        args=args,
        verbose=verbose,
    )
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
      extra_args: Mapping[str, str | None] | None = None,
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
