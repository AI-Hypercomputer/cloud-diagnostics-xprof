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

"""CLI tool to manage hosted TensorBoard instances.

xprofiler wraps existing tools and commands to provide a more user friendly
interface for managing hosted TensorBoard instances. Specifically, it provides
a CLI interface to create, list, and delete hosted TensorBoard instances
centered around a log directory as the 'primary key'.
"""

import argparse
import collections
from collections.abc import Mapping, Sequence
import itertools

from actions import action
from actions import capture_action
from actions import connect_action
from actions import create_action
from actions import delete_action
from actions import list_action


class XprofilerParser:
  """Parser for the xprofiler CLI."""

  _END_OF_LINE: int = -1

  def __init__(
      self,
      description: str | None = None,
      commands: Mapping[str, action.Command] | None = None,
  ):
    """Initializes the parser with relevant options.

    Args:
      description: The description of the parser.
      commands: The commands to add to the parser.
    """
    self.description = (
        description or 'CLI tool to manage hosted TensorBoard instances.'
    )
    self.commands = commands or {}
    self._setup_parser()

  def _setup_parser(self) -> None:
    """Sets up the parser."""
    self.parser = argparse.ArgumentParser(
        description=self.description,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    # Only display abbereviated outputs (does not affect verbose).
    self.parser.add_argument(
        '--abbrev',
        '-a',
        action='store_true',
        help='Abbreviate the output.',
    )

    # Allow for future commands.
    subparsers = self.parser.add_subparsers(
        title='commands',
        dest='command',
        help='Available commands',
    )

    for cli_command in self.commands.values():
      cli_command.add_subcommand(subparsers)

  def run(
      self,
      command_name: str,
      args: argparse.Namespace,
      extra_args: Mapping[str, str] | None = None,
      verbose: bool = False,
  ) -> str:
    """Runs the command.

    Args:
      command_name: The name of the command to run for subparser.
      args: The arguments parsed from the command line.
      extra_args: Any extra arguments to pass to the command.
      verbose: Whether to print other informational output.

    Returns:
      The output of the command.
    """
    if command_name not in self.commands:
      raise ValueError(f'Command `{command_name}` not implemented yet.')

    command_output = self.commands[command_name].run(
        args=args,
        extra_args=extra_args,
        verbose=verbose,
    )
    return command_output

  @staticmethod
  def _parse_table(
      table: str | None = None,
      verbose: bool = False,
  ) -> Mapping[str, Sequence[str]]:
    """Parses the table from the output of the create VM command.

    Args:
      table: The table to parse.
      verbose: Whether to print verbose output.

    Returns:
      A mapping of header to list of values.
    """

    # If no string to parse, return empty dict.
    if not table:
      return {}

    # Remove any excess whitespace & new lines before splitting lines.
    table = table.strip()

    table_lines = table.split('\n')
    header_str = table_lines[0]
    headers = header_str.split()

    # Find where the next column in the header starts.
    header_locations: dict[str, tuple[int, int]] = {}
    for header, next_header in itertools.zip_longest(headers, headers[1:]):
      start = header_str.index(header)
      # End is either where the next header starts or the end of the string.
      # Assume no next header means go to the end.
      end = (
          # Ensure we start looking from the value of interests starts.
          header_str.index(next_header, start) if next_header
          else XprofilerParser._END_OF_LINE
      )
      header_locations[header] = (start, end)
    if verbose:
      print(f'HEADERS: {headers}')

    # Find all other info from next lines
    table_values = collections.defaultdict(list)
    for line in table_lines[1:]:
      line_values = line.split()
      if verbose:
        print(f'LINE VALUES:\n{line_values}')
      for header, (start, end) in header_locations.items():
        if end == XprofilerParser._END_OF_LINE:
          value = line[start:]
        else:
          value = line[start:end]
        table_values[header].append(value.strip())

    if verbose:
      print('------------------table results-------------------')
      print(table_values)

    return table_values

  @staticmethod
  def _get_table_string(
      table: Mapping[str, Sequence[str]],
      display_header: bool = True,
      separator: str = '  ',
      column_filter: Sequence[str] | None = None,
      verbose: bool = False,
  ) -> str:
    """Returns string of table in a human readable format from a mapping.

    Args:
      table: A mapping where keys are column headers and values are sequences of
        single strings.
      display_header: Whether to include the header row.
      separator: The string to use as a separator between columns.
      column_filter: Column headers to include in the output. If None, all
        columns are included.
      verbose: Whether to print verbose output.

    Returns:
        A string representing the formatted table.
    """
    headers = table.keys()
    # If no filter is provided, show all columns.
    filter_columns = column_filter if column_filter else headers
    if verbose:
      print(f'HEADERS: {headers}')
    values = [table[header] for header in headers if header in filter_columns]
    if verbose:
      print(f'VALUES: {values}')

    # Calculate column widths based on header and value lengths.
    column_widths = {
        header: max(len(header), max(len(val) for val in values))
        for header, values in zip(headers, values)
        if header in filter_columns
    }
    if verbose:
      print(f'COLUMN WIDTHS: {column_widths}')

    # Create header row.
    header_row = separator.join(
        header.ljust(width)
        for header, width in column_widths.items()
    )
    if verbose:
      print(f'HEADER ROW: {header_row}')

    # Create value rows.
    value_rows = []
    if values:
      for row_values in zip(*values):
        row_values = separator.join(
            val.ljust(width) if val else ''.ljust(width)
            for val, width in zip(row_values, column_widths.values())
        )
        # Remove any trailing whitespace after joining.
        value_rows.append(row_values.strip())

    if verbose:
      print(f'VALUE ROWS: {value_rows}')
      print(f'{display_header=}')

    # Combine header and value rows.
    header_string = f'{header_row}\n' if display_header else ''
    table_string = header_string + '\n'.join(value_rows)

    return table_string

  @staticmethod
  def display_command_output(
      command_output: str,
      abbrev: bool = False,
      verbose: bool = False,
  ) -> None:
    """Displays the command output.

    Args:
      command_output: The output of the command.
      abbrev: Whether to abbreviate the output.
      verbose: Whether to print the output.
    """
    if verbose:
      print(f'{abbrev=}')
      print(command_output)

    table_mapping = XprofilerParser._parse_table(
        table=command_output,
        verbose=verbose,
    )
    # Only display the VM name if abbreviated is requested
    table_string = XprofilerParser._get_table_string(
        table=table_mapping,
        display_header=(not abbrev),
        column_filter=(
            ['NAME'] if abbrev else None
        ),
        verbose=verbose,
    )

    print(table_string)


def main():
  xprofiler_parser: XprofilerParser = XprofilerParser(
      commands={
          'capture': capture_action.Capture(),
          'connect': connect_action.Connect(),
          'create': create_action.Create(),
          'delete': delete_action.Delete(),
          'list': list_action.List(),
      },
  )
  # Parse args from CLI.
  args = xprofiler_parser.parser.parse_args()

  # Run command (prints output as necessary).
  if args.command is None:
    xprofiler_parser.parser.print_help()
  else:
    command_output = xprofiler_parser.run(
        command_name=args.command,
        args=args,
        verbose=args.verbose,
    )
    xprofiler_parser.display_command_output(
        command_output,
        abbrev=args.abbrev,
        verbose=args.verbose,
    )


if __name__ == '__main__':
  main()
