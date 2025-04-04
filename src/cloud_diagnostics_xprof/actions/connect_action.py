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

"""A connect command implementation for the xprof CLI.

This command is used as part of the xprof CLI to connect to a hosted
TensorBoard instance. The intention is that this can be used after creation of a
new instance using the `xprof create` command.
"""

import argparse
from collections.abc import Mapping, Sequence
from cloud_diagnostics_xprof.actions import action
from cloud_diagnostics_xprof.actions import list_action


class Connect(action.Command):
  """A command to connect to a hosted TensorBoard instance."""

  def __init__(self):
    super().__init__(
        name='connect',
        description='Connect to a hosted TensorBoard instance.',
    )

  def add_subcommand(
      self,
      subparser: argparse._SubParsersAction,
  ) -> None:
    """Creates a subcommand for `connect`.

    Args:
        subparser: The subparser to add the connect subcommand to.
    """
    connect_parser = subparser.add_parser(
        name='connect',
        help='Connect to a hosted TensorBoard instance.',
        formatter_class=argparse.RawTextHelpFormatter,  # Keeps format in help.
    )
    connect_parser.add_argument(
        '--log-directory',
        '-l',
        metavar='GS_PATH',
        required=True,
        help='The GCS path to the log directory associated with the instance.',
    )
    connect_parser.add_argument(
        '--zone',
        '-z',
        required=True,
        metavar='ZONE_NAME',
        help='The GCP zone to connect to the instance in.',
    )
    # Options for mode are ssh or proxy.
    connect_parser.add_argument(
        '--mode',
        '-m',
        metavar='MODE',
        choices=['ssh', 'proxy'],
        default='ssh',
        help='The mode to connect to the instance.',
    )
    connect_parser.add_argument(
        '--port',
        '-p',
        metavar='LOCAL_PORT',
        default='6006',
        help='The port to connect to the instance.',
    )
    connect_parser.add_argument(
        '--host-port',
        metavar='HOST_PORT',
        default='6006',
        help='The port from the host to connect to the instance.',
    )
    connect_parser.add_argument(
        '--disconnect',
        '-d',
        action='store_true',
        help='Disconnect from the instance (assuming connection was made).',
    )
    # proxy is optional.
    connect_parser.add_argument(
        '--use-ssh-proxy',
        '-u',
        action='store_true',
        default=False,
        help='Use the SSH proxy to connect to the instance.',
    )
    connect_parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Print the command.',
    )

  def _get_vms_from_log_directory(
      self,
      log_directories: Sequence[str],
      zone: str | None,
      verbose: bool = False,
  ) -> Sequence[str]:
    """Gets the VM name(s) from the log directory(s).

    Args:
      log_directories: The log directory(s) associated with VM(s) to connect.
      zone: The GCP zone to connect the instance in.
      verbose: Whether to print verbose output.

    Returns:
      The VM name(s) from the log directory(s).
    """
    # Use the list action to get the VM name(s).
    list_command = list_action.List()
    list_args = argparse.Namespace(
        zone=zone,
        log_directory=log_directories,
        filter=None,
        verbose=verbose,
    )

    # Each VM name is on a separate line after the header.
    command_output = list_command.run(
        args=list_args,
        verbose=verbose,
    )
    if verbose:
      print(command_output)

    vm_names = (
        command_output
        .strip()  # Removes the extra new line(s) that tends to be at the end.
        .split('\n')[1:]  # Ignores header line.
    )

    vm_names = [vm_name.split()[2] for vm_name in vm_names]

    return vm_names

  def _initial_ssh_add_keys(self, verbose: bool = False) -> str:
    """Adds the SSH keys to the VM.

    Args:
      verbose: Whether to print verbose output.

    Returns:
      The output of the command.
    """

    command = [
        'gcloud',
        'compute',
        'os-login',
        'ssh-keys',
        'add',
        '--key',
        '$(ssh-add -L | grep publickey)',
    ]

    if verbose:
      print(f'Command to run: {command}')

    stdout = self._run_command(command)

    return stdout

  def _build_command(
      self,
      args: argparse.Namespace,
      extra_args: Mapping[str, str] | None = None,
      verbose: bool = False,
  ) -> Sequence[str]:
    """Builds the command to connect to a hosted TensorBoard instance.

    Args:
      args: The arguments parsed from the command line.
      extra_args: Any extra arguments to pass to the command.
      verbose: Whether to print the command and other output.

    Returns:
      The command to connect to a hosted TensorBoard instance.
    """
    # Check that log directory is specified.
    if not args.log_directory:
      raise ValueError('--log-directory must be specified.')

    # Get the VM name from the log directory.
    vm_names_from_log_directory = self._get_vms_from_log_directory(
        log_directories=[args.log_directory],
        zone=args.zone,
        verbose=verbose,
    )

    vm_names = vm_names_from_log_directory

    if verbose:
      print(f'VM name(s) from log directory: {vm_names}')

    # If there are multiple VM names, use the first one.
    try:
      vm_name = vm_names[0]
    except IndexError:
      raise ValueError(
          'No VM name found associated with the log directory.'
      ) from IndexError

    if verbose:
      print(f'Using first VM name from the list: {vm_name}')

    # Establish a master control connection to the VM.
    socket_path = f'/tmp/ssh_mux_socket_{vm_name}'
    # Disconnect from the VM if specified.
    if args.disconnect:
      ssh_flags = f'-o ControlPath={socket_path} -O exit'
    # If not disconnecting, connect to the VM.
    else:
      ssh_flags = (
          f'-f -N -M -S {socket_path}'  # Create socket file & keep it alive.
          f' -L {args.port}:localhost:{args.host_port}'  # Forward port.
      )

    # Command will either create & connect to a socket file or disconnect.
    connect_command = [
        'gcloud',
        'compute',
        'ssh',
        f'{vm_name}',
        f'--ssh-flag={ssh_flags}',
    ]
    if args.zone:
      connect_command.append(f'--zone={args.zone}')

    # Extensions of any other arguments to the main command.
    if extra_args:
      connect_command.extend(
          [f'{arg}={value}' for arg, value in extra_args.items()]
      )

    if args.use_ssh_proxy:
      connect_command.extend([
          '--',
          '-o ProxyCommand corp-ssh-helper %h %p',
      ])

    return connect_command

  def run(
      self,
      args: argparse.Namespace,
      extra_args: Mapping[str, str] | None = None,
      verbose: bool = False,
  ) ->  str:
    # If the user wants to disconnect, print a message.
    if args.disconnect:
      print('DISCONNECTING FROM VM...')
    # Warn user that initial SSH connection can take a while.
    else:
      print(
          'CONNECTING TO VM...\n'
          'Note: The initial SSH connection can take a while when connecting to'
          ' a VM on a new project for the first time.'
      )
      # Add the SSH keys to the VM.
      print('Adding SSH keys to the VM...')
      stdout_ssh_add_keys = self._initial_ssh_add_keys(verbose=verbose)
      print('SSH keys added to the VM')
      if verbose:
        print(stdout_ssh_add_keys)

    stdout = super().run(
        args=args,
        extra_args=extra_args,
        verbose=verbose,
    )

    # Print the URL if connected successfully.
    if not args.disconnect and args.mode == 'ssh':
      print(
          'Connected successfully!\n'
          f'URL: https://localhost:{args.port}'
      )

    return stdout

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
    # No display string is needed for the connect command.
    return None
