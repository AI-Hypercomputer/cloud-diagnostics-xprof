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

This command is used as part of the xprof CLI to delete a xprofiler
instance. The intention is that this can be used after creation of a new
instance using the `xprof create` command (versus using for general instance
deletion).
"""

import argparse
from collections.abc import Mapping, Sequence
import json
from cloud_diagnostics_xprof.actions import action
from cloud_diagnostics_xprof.actions import list_action


class Delete(action.Command):
  """A command to delete a xprofiler instance."""

  def __init__(self):
    super().__init__(
        name='delete',
        description='Delete a xprofiler instance.',
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
        help='Delete a xprofiler instance.',
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
        '--quiet',
        '-q',
        action='store_true',
        help='Skip user confirmation to delete the instance(s).',
    )
    delete_parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Print the command.',
    )

  def _get_vms_names(
      self,
      log_directories: Sequence[str] | None,
      vm_names: Sequence[str] | None,
      zone: str | None = None,
      verbose: bool = False,
  ) -> Sequence[str]:
    """Gets the VM name(s) from the log directory(s) and/or VM name(s).

    Args:
      log_directories: The log directory(s) associated with the VM(s).
      vm_names: The VM name(s).
      zone: The GCP zone to check for VM names. Can be None.
      verbose: Whether to print verbose output.

    Returns:
      The VM name(s) that were actually found.
    """
    # Use the list action to get the VM name(s).
    list_command = list_action.List()
    list_args = argparse.Namespace(
        zones=[zone] if zone else None,
        log_directory=log_directories,
        vm_name=vm_names,
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

    # Get VM names from the list output.
    vm_names = [
        vm['name']
        for vm in json.loads(command_output)
    ]

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
      zone: The GCP zone to delete the instance in.
      verbose: Whether to print verbose output.
    """
    if not vm_names:
      if verbose:
        print('Empty VM names list so nothing to display.')
      return

    if verbose:
      print(f'Calling list subcommand to get info on VM(s): {vm_names}')

    list_command = list_action.List()

    # Build filter args to get the VM(s) to display.
    # True if any exactly matches a VM name (based on gcloud's filter syntax).
    filter_args = [
        f'name=({",".join(vm_names)})'
    ]
    list_args = argparse.Namespace(
        log_directory=None,
        zones=[zone],
        vm_name=None,
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
      extra_args: Mapping[str, str | None] | None = None,
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

    # List of VM names to (potentially) delete, confirmed by checking project.
    vm_candidates = self._get_vms_names(
        log_directories=args.log_directory,
        vm_names=args.vm_name,
        zone=args.zone,
        verbose=verbose,
    )

    if verbose:
      print(f'ConfirmedVM candidates to delete: {vm_candidates}')

    if not vm_candidates:
      raise ValueError('No VM(s) to delete.')

    # Skip confirmation if user specified --quiet.
    # Only need to display VM(s) if the user is confiming deletion or verbose.
    if verbose or not args.quiet:
      print(f'Found {len(vm_candidates)} VM(s) to delete.\n')
      self._display_vm_names(
          vm_names=vm_candidates,
          zone=args.zone,
          verbose=verbose,
      )

    # Skip confirmation if user specified --quiet.
    if args.quiet:
      vm_names = vm_candidates
      if verbose:
        print(f'Skipping confirmation for VM(s): {vm_names}')
    else:
      vm_names = self._confirm_vm_deletions(vm_candidates)

    if not vm_names:
      raise ValueError('No VM(s) to delete.')

    if verbose:
      print(f'Will delete VM(s) w/ name: {vm_names}')

    delete_vm_command = [
        self.GCLOUD_COMMAND,
        'compute',
        'instances',
        'delete',
        '--quiet',  # Don't ask for confirmation or give extra details.
        f'--zone={args.zone}',
    ]

    # Extensions of any other arguments to the main command.
    if extra_args:
      delete_vm_command.extend([
          f'{arg}={value}' if value else f'{arg}'
          for arg, value in extra_args.items()
      ])

    delete_vm_command.extend(vm_names)

    if verbose:
      print(delete_vm_command)

    return delete_vm_command

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
    # No display string is needed for the delete command.
    return None
