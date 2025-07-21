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

"""A delete command implementation for the xprofiler CLI.

This command is used as part of the xprofiler CLI to delete a xprofiler
instance. The intention is that this can be used after creation of a new
instance using the `xprofiler create` command (versus using for general instance
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
        '--gke',
        action='store_true',
        help=(
            '[EXPERIMENTAL] Delete Pod(s) on GKE instead of a VM. '
            'This is an experimental feature and may change in the future'
            ' or may be removed completely.'
        ),
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

  def _get_vm_names(
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
        gke=False,
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
    vm_names = [vm['name'] for vm in json.loads(command_output)]

    return vm_names

  def _get_pod_names(
      self,
      log_directories: Sequence[str] | None,
      pod_names: Sequence[str] | None,
      zone: str | None = None,
      verbose: bool = False,
  ) -> Sequence[str]:
    """Gets the Pod name(s) from the log directory(s) and/or Pod name(s).

    Args:
      log_directories: The log directory(s) associated with the Pod(s).
      pod_names: The Pod name(s).
      zone: The GCP zone to check for Pod names. Can be None.
      verbose: Whether to print verbose output.

    Returns:
      The Pod name(s) that were actually found.
    """
    # Use the list action to get the Pod name(s).
    list_command = list_action.List()
    list_args = argparse.Namespace(
        zones=[zone] if zone else None,
        log_directory=log_directories,
        vm_name=pod_names,
        filter=None,
        gke=True,
        verbose=verbose,
    )

    # Each Pod name is on a separate line after the header.
    command_output = list_command.run(
        args=list_args,
        verbose=verbose,
    )
    if verbose:
      print(command_output)

    # Get VM names from the list output.
    pod_names = [
        pod_name
        for pod in json.loads(command_output)
        if (
            # TODO: b/? -- hide parsing metadata for vm/gke behind api to reuse logic
            pod_name := pod.get('metadata', {})
            .get('labels', {})
            .get('instance', '')
        )
    ]

    return pod_names

  def _display_instance_names(
      self,
      names: Sequence[str],
      zone: str,
      gke: bool = False,
      *,
      verbose: bool = False,
  ) -> None:
    """Displays the VM or Pod name(s) to the user.

    Args:
      names: The VM or Pod name(s) to display.
      zone: The GCP zone the instance can be found in.
      gke: Whether the instance is a GKE Pod. If False, it is a VM.
      verbose: Whether to print verbose output.
    """
    if not names:
      if verbose:
        print('Empty names list so nothing to display.')
      return

    if verbose:
      print(f'Calling list subcommand to get info on VM(s)/Pod(s): {names}')

    list_command = list_action.List()

    if gke:
      filter_args = None
      names_param = names
    else:
      # Build filter args to get the VM(s) to display.
      # True if any exactly matches a VM name (based on gcloud's filter syntax).
      # This tends to be faster than using the VM name(s) directly.
      filter_args = [f'name=({",".join(names)})']
      names_param = None
    list_args = argparse.Namespace(
        log_directory=None,
        zones=[zone],  # Must be a list, even if only one zone.
        vm_name=names_param,  # Confusing name but can be the Pod or VM name(s).
        filter=filter_args,  # Can be None.
        gke=gke,
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

  def _confirm_instance_deletions(
      self,
      candidates: Sequence[str],
  ) -> Sequence[str]:
    """Confirms with user that they want to delete the VM(s)/Pod(s).

    Args:
      candidates: The VM or Pod name(s) to delete.

    Returns:
      The VM or Pod name(s) to delete.
    """
    # Confirm with user that they want to delete each VM(s).
    message_to_user = (
        '\nDo you want to continue to delete the VM `{INSTANCE_NAME}`?\n'
        'Enter y/n: '
    )

    # Don't proceed if user does not say 'Y'/'y'.
    instance_names: list[str] = []
    for instance_name in candidates:
      user_input = input(
          message_to_user.format(INSTANCE_NAME=instance_name)
      ).lower()
      if user_input != 'y':
        print(f'Keep VM `{instance_name}`')
      else:
        print(f'Deleting VM `{instance_name}`')
        instance_names.append(instance_name)
    print()  # Add a new line for clarity.

    return instance_names

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
      raise ValueError('Either --vm-name or --log-directory must be specified.')

    if args.gke:
      candidates = self._get_pod_names(
          log_directories=args.log_directory,
          pod_names=args.vm_name,
          zone=args.zone,
          verbose=verbose,
      )
    else:
      # List of VM names to (potentially) delete, confirmed by checking project.
      candidates = self._get_vm_names(
          log_directories=args.log_directory,
          vm_names=args.vm_name,
          zone=args.zone,
          verbose=verbose,
      )

    if verbose:
      print(f'Confirmed VM/Pod candidates to delete: {candidates}')

    if not candidates:
      raise ValueError('No VM(s)/Pod(s) to delete.')

    # Skip confirmation if user specified --quiet.
    # Only need to display VM(s) if the user is confiming deletion or verbose.
    if verbose or not args.quiet:
      print(f'Found {len(candidates)} VM(s)/Pod(s) to delete.\n')
      self._display_instance_names(
          names=candidates,
          zone=args.zone,
          gke=args.gke,
          verbose=verbose,
      )

    # Skip confirmation if user specified --quiet.
    if args.quiet:
      vm_names = candidates
      if verbose:
        print(f'Skipping confirmation for VM(s)/Pod(s): {vm_names}')
    else:
      vm_names = self._confirm_instance_deletions(candidates)

    if not vm_names:
      raise ValueError('No VM(s) to delete.')

    if verbose:
      print(f'Will delete VM(s)/Pod(s) w/ name: {vm_names}')

    if args.gke:
      if len(args.vm_name) != 1:
        raise ValueError('Please specify only one vm name!')

      delete_command = [
          'kubectl',
          'delete',
          'all',
          f'--namespace={self.DEFAULT_NAMESPACE}',
          '-l',
          f'instance={args.vm_name[0]}',
      ]
    else:
      delete_command = [
          self.GCLOUD_COMMAND,
          'compute',
          'instances',
          'delete',
          '--quiet',  # Don't ask for confirmation or give extra details.
          f'--zone={args.zone}',
      ]

      # Extensions of any other arguments to the main command.
      if extra_args:
        delete_command.extend([
            f'{arg}={value}' if value else f'{arg}'
            for arg, value in extra_args.items()
        ])

      delete_command.extend(vm_names)

    if verbose:
      print(delete_command)

    return delete_command

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
