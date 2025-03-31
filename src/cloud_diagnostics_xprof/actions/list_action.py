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

This command is used as part of the xprof CLI to list hosted TensorBoard
instances. The intention is that this can be used after creation of instances
using the `xprof create` command.
"""

import argparse
from collections.abc import Mapping, Sequence
from cloud_diagnostics_xprof.actions import action


class List(action.Command):
  """A command to list a hosted TensorBoard instance."""

  _PROXY_URL = (
      'https://{backend_id}-dot-{region}.notebooks.googleusercontent.com'
  )

  def __init__(self):
    super().__init__(
        name='list',
        description='List all hosted TensorBoard instances.',
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
        help='List all hosted TensorBoard instances.',
        formatter_class=argparse.RawTextHelpFormatter,  # Keeps format in help.
    )
    list_parser.add_argument(
        '--zone',
        '-z',
        metavar='ZONE_NAME',
        required=True,
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
        help='Filter the list of instances by property.',
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
  ) -> str:
    """Formats the filter string for gcloud as single string.

    Args:
      filter_values: The filter values to format.

    Returns:
      The formatted filter string.
    """
    all_filter_strings = [
        ' OR '.join(f'{key}~"{value}"' for value in list_of_values)
        for key, list_of_values in filter_values.items()
    ]
    # Must contain these properties across all key values
    filter_string = '(' + ') AND ('.join(all_filter_strings) + ')'
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
    # Note we still filter by zone since this is **significantly** faster than
    # filtering with the `--filter` in gcloud
    if args.zone:
      list_vms_command.append(f'--zones={args.zone}')

    list_vms_command.append(
        '--format=table(labels.log_directory, labels.tb_backend_id, name)'
    )

    # Process filter flag into filter_values
    filter_values: Mapping[str, list[str]] = {}
    if args.filter:
      if verbose:
        print(f'Filters from parser: {args.filter}')
      for filter_name in args.filter:
        key, value = filter_name.split('=', 1)
        if key not in filter_values:
          filter_values |= {f'{key}': []}
        filter_values[key].append(value)
    else:  # Default to filtering by VM name
      filter_values |= dict(
          name=[
              self.VM_BASE_NAME,
          ],
      )

    # If log directory is specified, we will also filter in addition to others.
    if args.log_directory:
      log_directory_strings = [
          self._format_string_with_replacements(
              original_string=log_directory,
              replacements=self._DEFAULT_STRING_REPLACEMENTS,
          )
          for log_directory in args.log_directory
      ]
      filter_values |= {
          'labels.log_directory': log_directory_strings,
      }

    filter_string = self._format_filter_string(filter_values)
    list_vms_command.append(f'--filter={filter_string}')

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
      columns = self.TABLE_COLUMNS
      # Just the region from the zone. (e.g. us-central1-a -> us-central1)
      region = '-'.join(args.zone.split('-')[:-1])

      lines = []
      for line in display_str.splitlines()[1:]:  # Ignores header line.
        split_line = line.split()
        if len(split_line) != len(columns):
          continue
        log_directory, backend_id, name = split_line
        # Make sure the log directory is starts with gs://
        log_directory_formatted = (
            'gs://'
            + self._format_string_with_replacements(
                log_directory,
                self._DEFAULT_STRING_REVERSE_REPLACEMENTS,
            )
        )
        backend_id_formatted = self._PROXY_URL.format(
            backend_id=backend_id,
            region=region,
        )
        lines.append([
            log_directory_formatted,
            backend_id_formatted,
            name,
        ])

      # Display the table string.
      data_table = self.create_data_table(
          columns=columns,
          lines=lines,
          verbose=verbose,
      )

      formatted_data_table_string = self.display_table_string(
          data_table=data_table,
          verbose=verbose,
      )

      print(formatted_data_table_string)
