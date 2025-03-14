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

"""A connect command implementation for the xprofiler CLI.

This command is used as part of the xprofiler CLI to connect to a hosted
TensorBoard instance. The intention is that this can be used after creation of a
new instance using the `xprofiler create` command.
"""

import argparse
from collections.abc import Mapping, Sequence
from typing_extensions import override
from actions import action
from actions import list_action


class Connect(action.Command):
  """A command to connect to a hosted TensorBoard instance."""

  def __init__(self):
    super().__init__(
        name='connect',
        description='Connect to a hosted TensorBoard instance.',
    )

  @override
  def add_subcommand(
      self,
      subparser: argparse._SubParsersAction,
  ) -> None:
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
        '--verbose',
        '-v',
        action='store_true',
        help='Print the command.',
    )

  def _get_vms_from_log_directory(
      self,
      log_directories: Sequence[str],
      *,
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
    # Use extra args to format list command's output to get just the VM name.
    list_extra_args = {'--format': 'table(name)'}
    # Each VM name is on a separate line after the header.
    command_output = list_command.run(
        args=list_args,
        extra_args=list_extra_args,
        verbose=verbose,
    )
    if verbose:
      print(command_output)

    unused_header, *vm_names = (
        command_output
        .strip()  # Removes the extra new line(s) that tends to be at the end.
        .split('\n')
    )

    return vm_names

  @override
  def _build_command(
      self,
      args: argparse.Namespace,
      extra_args: Mapping[str, str] | None = None,
      verbose: bool = False,
  ) -> Sequence[str]:
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
      raise ValueError('No VM name found.') from IndexError

    if verbose:
      print(f'Using first VM name from the list: {vm_name}')

    connect_command = [
        'gcloud',
        'compute',
        'ssh',
        f'{vm_name}',
        '--ssh-flag="-4 -L 6006:localhost:6006"',
    ]
    if args.zone:
      connect_command.append(f'--zone={args.zone}')

    # Extensions of any other arguments to the main command.
    if extra_args:
      connect_command.extend(
          [f'{arg}={value}' for arg, value in extra_args.items()]
      )

    if verbose:
      print(f'Running command: {connect_command}')

    return connect_command
