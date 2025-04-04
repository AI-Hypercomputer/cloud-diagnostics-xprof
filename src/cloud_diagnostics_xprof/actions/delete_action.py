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

"""A delete command implementation for the xprof CLI.

This command is used as part of the xprof CLI to delete a hosted TensorBoard
instance. The intention is that this can be used after creation of a new
instance using the `xprof create` command (versus using for general instance
deletion).
"""

import argparse
from collections.abc import Mapping, Sequence
from cloud_diagnostics_xprof.actions import action
from cloud_diagnostics_xprof.actions import list_action


class Delete(action.Command):
  """A command to delete a hosted TensorBoard instance."""

  def __init__(self):
    super().__init__(
        name='delete',
        description='Delete a hosted TensorBoard instance.',
    )

  def add_subcommand(
      self,
      subparser: argparse._SubParsersAction,
  ) -> None:
    """Creates a subcommand for `delete`.

    Args:
        subparser: The subparser to add the delete subcommand to.
    """
    delete_parser = subparser.add_parser(
        name='delete',
        help='Delete a hosted TensorBoard instance.',
        formatter_class=argparse.RawTextHelpFormatter,  # Keeps format in help.
    )
    # log-directory is optional.
    delete_parser.add_argument(
        '--log-directory',
        '-l',
        metavar='GS_PATH',
        nargs='+',  # Allow multiple log directories to delete multiple VMs.
        help=(
            'The log directory(s) associated with the VM(s) to delete. '
            'Specify multiple names to delete multiple VMs.'
        ),
    )
    delete_parser.add_argument(
        '--vm-name',
        '-n',
        metavar='VM_NAME',
        nargs='+',  # Allow multiple VM names.
        help=(
            'The name of the VM(s) to delete. '
            'Specify multiple names to delete multiple VMs.'
        ),
    )
    delete_parser.add_argument(
        '--zone',
        '-z',
        metavar='ZONE_NAME',
        required=True,
        help='The GCP zone to delete the instance in.',
    )
    delete_parser.add_argument(
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
      log_directories: The log directory(s) associated with the VM(s) to delete.
      zone: The GCP zone to delete the instance in.
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

  def _display_vm_names(
      self,
      vm_names: Sequence[str],
      zone: str,
      verbose: bool = False,
  ) -> None:
    """Displays the VM name(s) to the user.

    Args:
      vm_names: The VM name(s) to display.
      verbose: Whether to print verbose output.
    """
    if verbose:
      print(f'Calling list subcommand to get info on VM(s): {vm_names}')

    list_command = list_action.List()

    # Build filter args to get the VM(s) to display.
    filter_args = []
    for vm_name in vm_names:
      filter_args.append(f'name={vm_name}')
    list_args = argparse.Namespace(
        log_directory=None,
        zone=zone,
        filter=filter_args,
        verbose=verbose,
    )

    # Each VM name is on a separate line after the header.
    command_output = list_command.run(
        args=list_args,
        verbose=verbose,
    )

    list_command.display(
        display_str=command_output,
        args=list_args,
        verbose=verbose,
    )

  def _confirm_vm_deletions(
      self,
      vm_candidates: Sequence[str],
  ) -> Sequence[str]:
    """Confirms with user that they want to delete the VM(s).

    Args:
      vm_candidates: The VM name(s) to delete.

    Returns:
      The VM name(s) to delete.
    """
    # Confirm with user that they want to delete each VM(s).
    message_to_user = (
        '\nDo you want to continue to delete the VM `{VM_NAME}`?\n'
        'Enter y/n: '
    )

    # Don't proceed if user does not say 'Y'/'y'.
    vm_names: list[str] = []
    for vm_name in vm_candidates:
      user_input = input(message_to_user.format(VM_NAME=vm_name)).lower()
      if user_input != 'y':
        print(f'Will NOT delete VM `{vm_name}`')
      else:
        print(f'Will delete VM `{vm_name}`')
        vm_names.append(vm_name)
    print()  # Add a new line for clarity.

    return vm_names

  def _build_command(
      self,
      args: argparse.Namespace,
      extra_args: Mapping[str, str] | None = None,
      verbose: bool = False,
  ) -> Sequence[str]:
    """Builds the delete command.

    Note this should not be called directly by the user and should be called
    by the run() method in the action module (using the subparser).

    Args:
      args: The arguments parsed from the command line.
      extra_args: Any extra arguments to pass to the command.
      verbose: Whether to print the command and other output.

    Returns:
      The command to delete the VM(s).
    """
    # Check that either VM name or log directory is specified.
    if not args.vm_name and not args.log_directory:
      raise ValueError(
          'Either --vm-name or --log-directory must be specified.'
      )

    # List of VM names to (potentially) delete.
    vm_candidates = []

    # Include the VM name(s) from the command line if specified.
    if args.vm_name:
      if verbose:
        print(f'VM name(s) from command line: {args.vm_name}')
      vm_candidates.extend(args.vm_name)

    # If log directory is specified, use that to get the VM name(s).
    if args.log_directory:
      vm_names_from_log_directory = self._get_vms_from_log_directory(
          log_directories=args.log_directory,
          zone=args.zone,
          verbose=verbose,
      )

      if verbose:
        print(f'VM name(s) from log directory: {vm_names_from_log_directory}')

      vm_candidates.extend(vm_names_from_log_directory)

    print(f'Found {len(vm_candidates)} VM(s) to delete.\n')
    self._display_vm_names(vm_candidates, args.zone, verbose)

    vm_names = self._confirm_vm_deletions(vm_candidates)

    if verbose:
      print(f'Will delete VM(s) w/ name: {vm_names}')

    delete_vm_command = [
        self.GCLOUD_COMMAND,
        'compute',
        'instances',
        'delete',
        '--quiet',  # Don't ask for confirmation or give extra details.
        f'--zone={args.zone}'
    ]

    # Extensions of any other arguments to the main command.
    if extra_args:
      delete_vm_command.extend(
          [f'{arg}={value}' for arg, value in extra_args.items()]
      )

    if not vm_names:
      raise ValueError('No VM(s) to delete.')

    delete_vm_command.extend(vm_names)

    if verbose:
      print(delete_vm_command)

    return delete_vm_command

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
    # No display string is needed for the delete command.
    return None
