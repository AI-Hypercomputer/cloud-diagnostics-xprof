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

"""A list command implementation for the xprof CLI.

This command is used as part of the xprof CLI to list xprofiler
instances. The intention is that this can be used after creation of instances
using the `xprof create` command.
"""

import argparse
from collections.abc import Mapping, Sequence
import json
from typing import Any

from cloud_diagnostics_xprof.actions import action


class List(action.Command):
  """A command to list a xprofiler instance."""

  _PROXY_URL = (
      'https://{backend_id}-dot-{region}.notebooks.googleusercontent.com'
  )

  def __init__(self):
    super().__init__(
        name='list',
        description='List all xprofiler instances.',
    )

  def add_subcommand(
      self,
      subparser: argparse._SubParsersAction,
  ) -> None:
    """Creates a subcommand for `list`.

    Args:
        subparser: The subparser to add the list subcommand to.
    """
    list_parser = subparser.add_parser(
        name='list',
        help='List all xprofiler instances.',
        formatter_class=argparse.RawTextHelpFormatter,  # Keeps format in help.
    )
    list_parser.add_argument(
        '--zones',
        '-z',
        nargs='+',  # Allow multiple zones
        metavar='ZONE_NAME',
        help='The GCP zone to list the instances in.',
    )
    list_parser.add_argument(
        '--log-directory',
        '-l',
        nargs='+',  # Allow multiple log directories
        metavar='GS_PATH',
        help='The GCS path to the log directory associated with the instance.',
    )
    # Uses key=value format to allow for multiple values
    # e.g. --filter=name=vm1 --filter=name=vm2
    # Same keys will be ORed together; different keys will be ANDed together
    list_parser.add_argument(
        '--filter',
        '-f',
        metavar='FILTER_NAME',
        nargs='+',
        help=(
            '[EXPERIMENTAL] Filter the list of instances by property. '
            'This is an experimental feature and may change in the future'
            ' or may be removed completely.'
        ),
    )
    list_parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Print the command.',
    )

  def _format_filter_string(
      self,
      filter_values: Mapping[str, Sequence[str]],
      match_operator: str = '~',
      join_operator: str = 'AND',
      verbose: bool = False,
  ) -> str:
    """Formats the filter string for gcloud as single string.

    Args:
      filter_values: The filter values to format.
      match_operator: The operator used for matching (only ~, =, !=).
      join_operator: The opeartor used to join the filter strings (AND / OR).
      verbose: Whether to print the command and other output.

    Returns:
      The formatted filter string.
    """
    if not filter_values:
      if verbose:
        print('No filter values provided.')
      return ''

    # Check valid join operators.
    if join_operator.upper() not in ['AND', 'OR']:
      raise ValueError(
          f'Invalid join operator: {join_operator}. Must be one of AND, OR.'
      )

    # Check valid match operators. For now, only support ~, =, !=.
    is_negation = False
    match match_operator:
      case '~':
        key_joiner_str = ':'
      case '=':
        key_joiner_str = '='
      case '!=':
        key_joiner_str = '='
        is_negation = True
      case _:
        raise ValueError(
            f'Invalid match operator: {match_operator}. Must be one of ~, =, !='
        )

    if verbose:
      print(f'Creating filter striing for {filter_values}')
      print(f'Given match operator: {match_operator}')
      print(f'Given join operator: {join_operator}')

    # Since can have multiple values for each key, we need to OR–join them.
    negation_str = '-' if is_negation else ''
    all_filter_strings = [
        (
            f'{negation_str}{key}{key_joiner_str}({",".join(list_of_values)})'
        )
        for key, list_of_values in filter_values.items()
    ]
    if verbose:
      print(f'All filter strings: {all_filter_strings}')
    # Must contain these properties across all key values
    filter_string = (
        '(' +
        f') {join_operator} ('.join(all_filter_strings) +
        ')'
    )
    if verbose:
      print(f'Final filter string: {filter_string}')
    return filter_string

  def get_log_directory_from_vm(
      self,
      vm: Mapping[str, Any],
      verbose: bool = False,
  ) -> str | None:
    """Gets the log directory from the VM.

    Args:
      vm: The VM to get the log directory from (dictionary).
      verbose: Whether to print the command and other output.

    Returns:
      The log directory from the VM formatted as URL.
    """
    log_directory_from_metadata = (
        vm
        .get('metadata', {})
        .get('items', [])
    )
    # Assume the items is a list and the first item is the log directory.
    # This if given by the gcloud's `--format` flag; specifically from
    # `metadata.items.extract({self.LOG_DIRECTORY_LABEL_KEY})`
    if log_directory_from_metadata:
      log_directory_formatted = log_directory_from_metadata[0]
      if verbose:
        print(f'Log directory from metadata: {log_directory_formatted}')
    else:  # Old method if not in metadata.
      log_directory_formatted = self.format_string_with_replacements(
          vm.get('labels', {}).get(self.LOG_DIRECTORY_LABEL_KEY, ''),
          self._DEFAULT_STRING_REVERSE_REPLACEMENTS,
      )
      if log_directory_formatted:
        log_directory_formatted = 'gs://' + log_directory_formatted
        if verbose:
          print(f'Log directory from labels: {log_directory_formatted}')
      else:  # No log directory found with either method.
        if verbose:
          print('No log directory found via any method.')
        log_directory_formatted = None

    return log_directory_formatted

  def _build_command(
      self,
      args: argparse.Namespace,
      extra_args: Mapping[str, str] | None = None,
      verbose: bool = False,
  ) -> Sequence[str]:
    """Builds the list command.

    Note this should not be called directly by the user and should be called
    by the run() method in the action module (using the subparser).

    Args:
      args: The arguments parsed from the command line.
      extra_args: Any extra arguments to pass to the command.
      verbose: Whether to print the command and other output.

    Returns:
      The command to list the VM(s).
    """
    # Note: Gives all since filtering with not fully supported yet
    list_vms_command = [
        self.GCLOUD_COMMAND,
        'compute',
        'instances',
        'list',
    ]
    if args.zones:
      # Note we still filter by zone since this is **significantly** faster than
      # filtering with the `--filter` in gcloud
      zones_string = ','.join(args.zones)
      list_vms_command.append(f'--zones={zones_string}')

    # Getting output format to later be parsed into a data table.
    list_vms_command.append(
        '--format=json('
        f'metadata.items.extract({self.LOG_DIRECTORY_LABEL_KEY})'
        f',labels.{self.LOG_DIRECTORY_LABEL_KEY}'
        ',labels.tb_backend_id'
        ',name'
        ',zone'
        ')'
    )

    # Filter by VM base name (old method) or has version label (new method).
    base_filter_values: Mapping[str, list[str]] = {
        'name': [
            self.VM_BASE_NAME,
        ],
        f'labels.{self.XPROFILER_VERSION_LABEL_KEY}': ['*'],
    }

    # Filter log directoy or other user-provided filters after runing command.
    full_filter_string = self._format_filter_string(
        base_filter_values,
        match_operator='~',
        join_operator='OR',
    )

    # Allow user provided filters as additional filters.
    if args.filter:
      if verbose:
        print(f'Filters from parser: {args.filter}')

      # Simply use the user provided filter strings to define match criteria.
      filter_string = ' AND '.join(args.filter)

      # AND the main filter string with the filter string.
      # Paranetheses are needed if the filter string from user uses OR.
      full_filter_string = (
          f'({full_filter_string})'
          f' AND ({filter_string})'
      )

    if verbose:
      print(f'Full filter string: {full_filter_string}')
    list_vms_command.append(f'--filter={full_filter_string}')

    # Extensions of any other arguments to the main command.
    if extra_args:
      list_vms_command.extend(
          [f'{arg}={value}' for arg, value in extra_args.items()]
      )

    if verbose:
      print(list_vms_command)

    return list_vms_command

  def run(
      self,
      args: argparse.Namespace,
      extra_args: Mapping[str, str] | None = None,
      verbose: bool = False,
  ) -> str:
    """Run the command.

    Args:
      args: The arguments parsed from the command line.
      extra_args: Any extra arguments to pass to the command.
      verbose: Whether to print the command and other output.

    Returns:
      The output of the command.
    """

    # Run the command and get the output.
    command = self._build_command(args, extra_args, verbose)
    if verbose:
      print(f'Command to run: {command}')

    stdout: str = self._run_command(command, verbose=verbose)
    output_data = json.loads(stdout)

    vm_matches = []

    # Filter the output based on user provided filters.
    # This is an alternative to using gcloud's `--filter` flag to allow for
    # filtering on multiple keys. (Appears to be a bug in gcloud.)
    if args.log_directory:
      # Assume the old version is 0.0.10.
      old_version_replacements = self.LOG_DIRECTORY_STRING_REPLACEMENTS.get(
          '0.0.10',
          self.DEFAULT_STRING_REPLACEMENTS,
      )
      # Assume thecurrent version is default (can be confirm xprofiler version).
      current_version_replacements = self.DEFAULT_STRING_REPLACEMENTS

      for log_directory in args.log_directory:
        if verbose:
          print(f'Checking for {log_directory=}')
        # Format the log directory string for the old version labeling.
        log_dir_str_old_version = self.format_string_with_replacements(
            log_directory,
            old_version_replacements,
        )
        if verbose:
          print(
              f'Log directory string (old version): {log_dir_str_old_version=}'
          )
        # Format the log directory string for the new version labeling.
        # Add gs:// prefix back to search with.
        log_dir_str = 'gs://' + self.format_string_with_replacements(
            original_string=log_directory,
            replacements=current_version_replacements,
        )
        if verbose:
          print(f'Log directory string: {log_dir_str=}')
        # Remove VM from list but use for final output if matches.
        found_vm: bool = False
        for vm in output_data:
          # New method: log directory found in metadata.
          vm_log_dir_metadata = (
              vm
              .get('metadata', {})
              .get('items', [])
          )
          # Old method: log directory formatted string matches label.
          vm_log_dir_label = (
              vm
              .get('labels', {})
              .get(self.LOG_DIRECTORY_LABEL_KEY)
          )
          # Check if string within the list
          if log_dir_str in vm_log_dir_metadata:
            found_vm = True
            if verbose:
              print(
                  f'Found VM match via metadata for {log_directory}'
                  f': {vm.get("name")}'
              )
          elif log_dir_str_old_version == vm_log_dir_label:
            found_vm = True
            if verbose:
              print(
                  f'Found VM match via labels for {log_directory}'
                  f': {vm.get("name")}'
              )
          if found_vm:
            vm_matches.append(vm)
            # Keep checking in case there are other VMs with same log directory.
            found_vm = False
    else:  # No log directory provided, so just use the output as is.
      vm_matches = output_data

    # Creates a string of JSON for the display method to handle.
    result_str = json.dumps(vm_matches)
    return result_str

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

    if display_str:
      data = json.loads(display_str)
      # Define the columns
      # Define the columns using the defaults values.

      lines = []
      for vm in data:
        name = vm.get('name', '')

        # Get the log directory from the VM.
        log_directory_formatted = self.get_log_directory_from_vm(
            vm,
            verbose=verbose,
        )
        # Skip VM if no log directory found.
        if not log_directory_formatted:
          if verbose:
            print(
                'Skip displaying since no log directory found'
                f' for {name} ({vm}).'
            )
          continue
        # Usually apears in URL format: https://.../zones/us-central1-a
        zone = (
            vm
            .get('zone', '')
            .split('/')[-1]
        )
        # Just the region from the zone. (e.g. us-central1-a -> us-central1)
        region = '-'.join(
            zone
            .split('-')[:-1]
        )
        backend_id_formatted = self._PROXY_URL.format(
            backend_id=(
                vm
                .get('labels', {})
                .get('tb_backend_id')
            ),
            region=region,
        )

        lines.append([
            log_directory_formatted,
            backend_id_formatted,
            name,
            zone,
        ])

      # Display the table string.
      data_table = self.create_data_table(
          columns=self.TABLE_COLUMNS,
          lines=lines,
          verbose=verbose,
      )

      formatted_data_table_string = self.display_table_string(
          data_table=data_table,
          verbose=verbose,
      )

      print(formatted_data_table_string)
