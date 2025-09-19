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
from collections.abc import Mapping

from cloud_diagnostics_xprof.actions import action
from cloud_diagnostics_xprof.actions import capture_action
from cloud_diagnostics_xprof.actions import connect_action
from cloud_diagnostics_xprof.actions import create_action
from cloud_diagnostics_xprof.actions import delete_action
from cloud_diagnostics_xprof.actions import list_action
from cloud_diagnostics_xprof.actions import register_action


class KeyValueAction(argparse.Action):
  """Action to parse a key=value pairs."""

  def __call__(self, parser, namespace, values, option_string=None):
    # Get either the value from the namespace or create a new one.
    pairs = getattr(namespace, self.dest, {})
    # Handles if the ddefault is None.
    if pairs is None:
      pairs: dict[str, str | None] = {}

    for raw_param_value in values:
      # Value can be in the format of a key=value or just a key.
      if '=' in raw_param_value:
        try:
          # Assume split only once and the rest is the value.
          key, value = raw_param_value.split('=', maxsplit=1)
          pairs[key] = value
        except ValueError:
          parser.error(
              f'{option_string}: must be in "key=value" format, got'
              f' {raw_param_value}'
          )
      else:
        # Assume the whole param is the key and no value needed.
        pairs[raw_param_value] = None

    setattr(namespace, self.dest, pairs)


class XprofParser:
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
        help=(
            '[EXPERIMENTAL] Abbreviate the output. '
            'This is an experimental feature and may change in the future'
            ' or may be removed completely.'
        ),
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
      extra_args: Mapping[str, str | None] | None = None,
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

  def display_command_output(
      self,
      command_name: str,
      command_output: str,
      *,
      args: argparse.Namespace,
      extra_args: Mapping[str, str] | None = None,
      verbose: bool = False,
  ) -> None:
    """Displays the command output as defined by the subcommand.

    Args:
      command_name: The name of the command to run for subparser.
      command_output: The output of the command.
      args: The arguments parsed from the command line.
      extra_args: Any extra arguments to pass to the command.
      verbose: Whether to print other informational output.
    """
    if command_name not in self.commands:
      raise ValueError(f'Command `{command_name}` not implemented yet.')

    self.commands[command_name].display(
        display_str=command_output,
        args=args,
        extra_args=extra_args,
        verbose=verbose,
    )

  def parse_extra_args(
      self,
      extra_args: list[str] | None,
  ) -> Mapping[str, str | None] | None:
    """Parses the extra arguments to be given to the next CLI command.

    Uses the following format:
      --flag
      -f
      --flag value
      -f value
      --flag=value
      -f=value
      --flag=value0,value1,value2
      -f value0,value1,value2
      --flag value0,value1,value2
      -f value0,value1,value2

    Combinations above are all valid. For example:
      --flag=value --other-flag value -f=value

    Arguements that are not 'flags' (don't start with a dash) are ignored if not
    preceeded by a flag.

    Args:
      extra_args: The extra arguments from the command line.

    Returns:
      A mapping of the parsed extra arguments.
    """
    if extra_args is None:
      return None
    extra_args_map = {}
    # Better to iterate using a while loop since can be arbiratry values.
    i = 0
    while i < len(extra_args):
      arg = extra_args[i]
      # Arg starts with a dash, so it's a flag.
      if arg.startswith('-'):
        flag_name = arg
        # Look ahead for a value, as long as it's not another flag
        # Accept multiple values after a flag.
        all_values: list[str] = []
        while i + 1 < len(extra_args) and not extra_args[i+1].startswith('-'):
          value = extra_args[i+1]
          i += 1  # Skip the value as a flag.
          all_values.append(value)

        # value will be passed to the next command so it can be either None or a
        # string of multiple values separated by spaces.
        # Note: no value could be a boolean or assignment (e.g. -f=value).
        value = ' '.join(all_values) if all_values else None
        # Don't need to format the string since it should already be formatted.
        extra_args_map[flag_name] = value
      else:  # Hits if not a 'flag'. (Or if multiple values for a flag.)
        print(f'Warning: Unexpected argument instead of flag: {arg}')
      i += 1
    return extra_args_map if extra_args_map else None


def main():
  xprof_parser: XprofParser = XprofParser(
      commands={
          'capture': capture_action.Capture(),
          'connect': connect_action.Connect(),
          'create': create_action.Create(),
          'delete': delete_action.Delete(),
          'list': list_action.List(),
          'register': register_action.Register(),
      },
  )

  # Parse args from CLI.
  args, extra_args = xprof_parser.parser.parse_known_args()

  # Run command (prints output as necessary).
  if args.command is None:
    xprof_parser.parser.print_help()
  else:
    if args.verbose:
      print(f'xprofiler args:\n{args}')
      print(f'xprofiler extra_args:\n{extra_args}')
    try:
      extra_command_args = xprof_parser.parse_extra_args(extra_args)

      command_output = xprof_parser.run(
          command_name=args.command,
          args=args,
          extra_args=extra_command_args,
          verbose=args.verbose,
      )

      xprof_parser.display_command_output(
          command_name=args.command,
          command_output=command_output,
          args=args,
          verbose=args.verbose,
      )
    except ValueError as e:
      print(f'{e}')
    except RuntimeError as e:
      print(f'{e}')


if __name__ == '__main__':
  main()
