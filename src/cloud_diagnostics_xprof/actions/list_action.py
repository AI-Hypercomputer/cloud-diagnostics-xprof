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
        '--zone',
        '-z',
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
    if args.zone:
      # Note we still filter by zone since this is **significantly** faster than
      # filtering with the `--filter` in gcloud
      list_vms_command.append(f'--zones={args.zone}')

    list_vms_command.append(
        '--format=table('
        f'labels.{self.LOG_DIRECTORY_LABEL_KEY}'
        ',labels.tb_backend_id'
        ',name'
        ',zone'
        ')'
    )

    # Always filter by VM base name.
    base_filter_values: Mapping[str, list[str]] = dict(
        name=[
            self.VM_BASE_NAME,
        ],
    )
    # Allow this full filter string to be built up.
    full_filter_string = self._format_filter_string(
        base_filter_values,
        match_operator='~',
        join_operator='AND',
    )

    main_filter_values: Mapping[str, list[str]] = {}
    # If log directory is specified, we will also filter in addition to others.
    if args.log_directory:
      log_directory_strings = [
          self._format_string_with_replacements(
              original_string=log_directory,
              replacements=self._DEFAULT_STRING_REPLACEMENTS,
          )
          for log_directory in args.log_directory
      ]
      main_filter_values |= {
          f'labels.{self.LOG_DIRECTORY_LABEL_KEY}': log_directory_strings,
      }
    # True if any matches exactly.
    main_filter_string = self._format_filter_string(
        main_filter_values,
        match_operator='=',
        join_operator='OR',
    )

    # Allow this full filter string to be built up.
    if main_filter_string:
      full_filter_string += f' AND {main_filter_string}'

    # Allow user provided filters as additional filters.
    if args.filter:
      if verbose:
        print(f'Filters from parser: {args.filter}')

      # Simply use the user provided filter strings to define match criteria.
      filter_string = ' AND '.join(args.filter)

      # AND the main filter string with the filter string.
      # Paranetheses are needed if the filter string from user uses OR.
      full_filter_string += f' AND ({filter_string})'

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
      # Define the columns using the defaults values.

      lines = []
      for line in display_str.splitlines()[1:]:  # Ignores header line.
        split_line = line.split()
        # Skips line if the number of columns to be displayed is not correct.
        if len(split_line) != len(self.TABLE_COLUMNS):
          if verbose:
            print(
                f'Skip line `{line}` since it has missing column values.'
            )
          continue
        log_directory, backend_id, name, zone = split_line

        # Make sure the log directory is starts with gs://
        log_directory_formatted = (
            'gs://'
            + self._format_string_with_replacements(
                log_directory,
                self._DEFAULT_STRING_REVERSE_REPLACEMENTS,
            )
        )
        # Just the region from the zone. (e.g. us-central1-a -> us-central1)
        region = '-'.join(zone.split('-')[:-1])
        backend_id_formatted = self._PROXY_URL.format(
            backend_id=backend_id,
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
