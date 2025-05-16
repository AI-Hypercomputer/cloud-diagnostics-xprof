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
    # Allow for extra arguments to be passed to the command.
    self.parser.add_argument(
        '--extra-args',
        '-e',
        metavar='EXTRA_ARGS',
        nargs='*',
        action=KeyValueAction,
        default={},
        help=(
            '[EXPERIMENTAL] '
            'Extra arguments to pass to the command in key=value format.'
            'This is an experimental feature and may change in the future.\n'
            ' Note that commands will prepend with `--` (or `-` with single'
            ' characters) before adding to the main internal command.'
        ),
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


def main():
  xprof_parser: XprofParser = XprofParser(
      commands={
          'capture': capture_action.Capture(),
          'connect': connect_action.Connect(),
          'create': create_action.Create(),
          'delete': delete_action.Delete(),
          'list': list_action.List(),
      },
  )

  # Parse args from CLI.
  args = xprof_parser.parser.parse_args()

  # Run command (prints output as necessary).
  if args.command is None:
    xprof_parser.parser.print_help()
  else:
    try:
      # Delete extra_args from args before passing to run() to prevent conflict.
      if hasattr(args, 'extra_args'):
        # Format the command using dashes.
        extra_command_args = {}
        for key, value in args.extra_args.items():
          new_flag, new_value = action.flag_with_value_from_key_value(
              key=key,
              value=value,
          )
          extra_command_args[new_flag] = new_value
        del args.extra_args
      else:
        extra_command_args = None

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
