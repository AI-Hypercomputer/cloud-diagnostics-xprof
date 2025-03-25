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

"""Tests for the xprofiler CLI tool."""

import argparse
from collections.abc import Mapping, Sequence
import itertools
from unittest import mock

from xprofiler import xprofiler
from actions import action

from google3.testing.pybase import parameterized


# Define valid test parameters for (main) xprofiler command.
_XPROFILER_VALID_TEST_PARAMS = dict(
    command=(
        None,
        'connect',
        'create',
        'delete',
        'list',
    ),
    abbrev=(
        True,
        False,
    ),
    verbose=(
        True,
        False,
    ),
)

# Define valid test parameters for delete command.
_DELETE_COMMAND_VALID_TEST_PARAMS = dict(
    vm_name=(
        ['test-vm-1'],
        ['test-vm-1', 'test-vm-2'],
        ['test-vm-1', 'test-vm-2', 'test-vm-3', 'test-vm-4', 'test-vm-5'],
    ),
    zone=(
        None,
        'us-central1-a',
    ),
    verbose=(
        True,
        False,
    ),
)


# Create a concrete subclass for testing.
class ConcreteCommand(action.Command):

  def __init__(self, name: str, description: str):
    super().__init__(name=name, description=description)

  def add_subcommand(self, subparser: argparse._SubParsersAction) -> None:
    pass

  def _build_command(
      self,
      args: argparse.Namespace,
      extra_args: Mapping[str, str] | None = None,
      verbose: bool = False,
  ) -> Sequence[str]:
    return ['echo', 'test']  # Simple command to test with.


class XprofilerTest(parameterized.TestCase):

  def test_xprofiler_parser_init_default(self):
    """Test that the parser is initialized correctly."""
    xprofiler_parser = xprofiler.XprofilerParser()

    self.assertIsInstance(xprofiler_parser, xprofiler.XprofilerParser)
    self.assertIsInstance(xprofiler_parser.parser, argparse.ArgumentParser)
    self.assertEmpty(xprofiler_parser.commands)

  def test_xprofiler_parser_init_with_command(self):
    """Test that the parser is initialized correctly."""
    test_command = ConcreteCommand(
        name='test_command',
        description='A test command',
    )
    commands = {
        'test_command': test_command,
    }
    xprofiler_parser = xprofiler.XprofilerParser(
        commands=commands,
    )

    self.assertIsInstance(xprofiler_parser, xprofiler.XprofilerParser)
    self.assertIsInstance(xprofiler_parser.parser, argparse.ArgumentParser)
    self.assertLen(xprofiler_parser.commands, 1)
    # Check command has been included.
    self.assertEqual(
        commands,
        xprofiler_parser.commands,
    )

  def test_xprofiler_run(self):
    """Test xprofiler.run() method calls the command object's run() method."""
    test_command = ConcreteCommand(
        name='test_command',
        description='A test command',
    )
    commands = {
        'test_command': test_command,
    }
    xprofiler_parser = xprofiler.XprofilerParser(
        commands=commands,
    )

    with mock.patch.object(test_command, 'run', autospec=True) as mock_run:
      xprofiler_parser.run(
          command_name='test_command',
          args=mock.MagicMock(),
      )

      mock_run.assert_called_once()

  def test_xprofiler_run_command_not_implemented(self):
    """Test xprofiler.run() raises error if command is not implemented."""
    xprofiler_parser = xprofiler.XprofilerParser()

    with self.assertRaises(ValueError):
      xprofiler_parser.run(
          command_name='test_command',
          args=mock.MagicMock(),
      )

  def test_main_no_command(self):
    """Test that main prints help message if no args/command is provided."""
    # Check print_help is called
    with mock.patch.object(
        argparse.ArgumentParser, 'print_help', autospec=True
    ) as mock_print_help:
      # Note parse_args() will return a Namespace with no values.
      xprofiler.main()

      mock_print_help.assert_called_once()

  @parameterized.named_parameters(
      (
          f'{abbrev=}-{verbose=}',
          abbrev,
          verbose,
      )
      for command, abbrev, verbose in itertools.product(
          *_XPROFILER_VALID_TEST_PARAMS.values()
      )
      if command is None
  )
  def test_main_help_no_command(
      self,
      test_abbrev: bool,
      test_verbose: bool,
  ):
    """Tests that main() prints help message when no command is provided."""
    with mock.patch('argparse.ArgumentParser.print_help') as mock_print_help:
      # Simulate no command-line arguments
      with mock.patch(
          'argparse.ArgumentParser.parse_args',
          return_value=argparse.Namespace(
              command=None,
              abbrev=test_abbrev,
              verbose=test_verbose,
          ),
      ):
        xprofiler.main()

        mock_print_help.assert_called_once()

  @parameterized.named_parameters(
      (f'vms_{len(vm_names)}-{zone=}-{verbose=}', vm_names, zone, verbose)
      for vm_names, zone, verbose in itertools.product(
          *_DELETE_COMMAND_VALID_TEST_PARAMS.values()
      )
  )
  @mock.patch.object(xprofiler.XprofilerParser, 'run')
  def test_main_with_delete_command(
      self,
      test_vm_names: Sequence[str],
      test_zone: str | None,
      test_verbose: bool,
      mock_run,
  ):
    """Test that main calls delete command from subparser w/ args/command.

    This test is parameterized to test all valid combinations of arguments for
    the delete command. It does not check the validity of the delete command
    itself, only that the correct arguments are passed to the xprofiler.run
    method.

    Args:
      test_vm_names: The VM names to pass to the delete command.
      test_zone: The zone to pass to the delete command.
      test_verbose: The verbose flag to pass to the delete command.
      mock_run: The mock object for the xprofiler.run() method.
    """
    # Simulate command-line arguments as if 'delete' command was passed.
    # Patch argparse.ArgumentParser.parse_args to return our test args.
    # Note abbrev flag is not tested here.
    with mock.patch(
        'argparse.ArgumentParser.parse_args',
        return_value=argparse.Namespace(
            command='delete',
            vm_name=test_vm_names,
            zone=test_zone,
            verbose=test_verbose,
            abbrev=False,  # Not tested here; use default value.
        ),
    ):
      xprofiler.main()

    command_name = mock_run.call_args.kwargs['command_name']
    called_args = mock_run.call_args.kwargs['args']
    vm_name_arg = called_args.vm_name
    zone_arg = called_args.zone
    verbose_arg = called_args.verbose

    # Assert that xprofiler.run was in fact called.
    mock_run.assert_called_once()
    # Assert that xprofiler_parser.run was called with the correct arguments.
    self.assertEqual(command_name, 'delete')
    self.assertEqual(vm_name_arg, test_vm_names)
    self.assertEqual(zone_arg, test_zone)
    self.assertEqual(verbose_arg, test_verbose)

  def test_parse_table_no_table(self):
    """Test that _parse_table returns empty dict if no table is provided."""
    xprofiler_parser = xprofiler.XprofilerParser()

    table = xprofiler_parser._parse_table(table=None)

    self.assertEmpty(table)

  def test_parse_table_with_empty_table_string(self):
    """Test that _parse_table returns empty dict if table string is empty."""
    xprofiler_parser = xprofiler.XprofilerParser()

    table = xprofiler_parser._parse_table(table='')

    self.assertEmpty(table)

  def test_parse_table_with_table_string(self):
    """Test that _parse_table returns correct dict if table string is provided."""
    xprofiler_parser = xprofiler.XprofilerParser()
    test_table_string = (
        'NAME       ZONE           MACHINE_TYPE\n'
        'test-vm-1  us-central1-a  e2-medium\n'
        'test-vm-2  us-central1-a  e2-medium\n'
        'test-vm-3  us-central1-a  e2-medium\n'
        'test-vm-4  us-central1-a  e2-medium\n'
    )

    table = xprofiler_parser._parse_table(table=test_table_string)

    self.assertEqual(
        table,
        {
            'NAME': ['test-vm-1', 'test-vm-2', 'test-vm-3', 'test-vm-4'],
            'ZONE': [
                'us-central1-a',
                'us-central1-a',
                'us-central1-a',
                'us-central1-a',
            ],
            'MACHINE_TYPE': [
                'e2-medium',
                'e2-medium',
                'e2-medium',
                'e2-medium',
            ],
        },
    )

  def test_get_table_string_empty_table(self):
    """Test that _get_table_string returns empty string if table is empty."""
    xprofiler_parser = xprofiler.XprofilerParser()

    table_string = xprofiler_parser._get_table_string(table={})

    # The table string should be empty, but may have trailing newline(s).
    self.assertEqual(table_string.strip(), '')

  def test_get_table_string_with_table(self):
    """Test that _get_table_string returns correct string if table is provided."""
    xprofiler_parser = xprofiler.XprofilerParser()
    test_table = {
        'NAME': ['test-vm-1', 'test-vm-2', 'test-vm-3', 'test-vm-4'],
        'ZONE': [
            'us-central1-a',
            'us-central1-a',
            'us-central1-a',
            'us-central1-a',
        ],
        'MACHINE_TYPE': [
            'e2-medium',
            'e2-medium',
            'e2-medium',
            'e2-medium',
        ],
    }

    table_string = xprofiler_parser._get_table_string(
        table=test_table,
    )

    expected_table_string = (
        'NAME       ZONE           MACHINE_TYPE\n'
        'test-vm-1  us-central1-a  e2-medium\n'
        'test-vm-2  us-central1-a  e2-medium\n'
        'test-vm-3  us-central1-a  e2-medium\n'
        'test-vm-4  us-central1-a  e2-medium'
    )
    self.assertEqual(
        table_string,
        expected_table_string,
    )

  def test_display_command_output_with_abbrev(self):
    """Test that display_command_output prints correct string if abbrev."""
    xprofiler_parser = xprofiler.XprofilerParser()
    # Typical output from a gcloud command.
    test_command_output = (
        'NAME       ZONE           MACHINE_TYPE\n'
        'test-vm-1  us-central1-a  e2-medium\n'
        'test-vm-2  us-central1-a  e2-medium\n'
        'test-vm-3  us-central1-a  e2-medium\n'
        'test-vm-4  us-central1-a  e2-medium\n'
    )

    # Method display_command_output() calls print() internally.
    with mock.patch('builtins.print') as mock_print:
      xprofiler_parser.display_command_output(
          command_output=test_command_output,
          abbrev=True,
      )

    # No newline at the end of the string.
    mock_print.assert_called_once_with(
        'test-vm-1\n'
        'test-vm-2\n'
        'test-vm-3\n'
        'test-vm-4'
    )

if __name__ == '__main__':
  parameterized.googletest.main()
