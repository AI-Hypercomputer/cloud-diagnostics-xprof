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

"""Base class for defining the interface of actions by xprofiler via subparsers.

The Command class is used to define the interface to include in the xprofiler
parser. It is used to create a command line interface (CLI) tool that
allows users to perform various actions through a subparser.
"""

import abc
import argparse
from collections.abc import Mapping, Sequence
import dataclasses
import subprocess


class Command(abc.ABC):
  """A standard implementation of a CLI command."""

  GCLOUD_COMMAND: str = 'gcloud'
  VM_BASE_NAME = 'xprofiler'

  @dataclasses.dataclass(frozen=True)
  class Replacement:
    original: str
    to: str

  # Default replacements for formatting strings
  _DEFAULT_STRING_REPLACEMENTS: Sequence[Replacement] = (
      Replacement('gs://', ''),
      Replacement('/', '--slash--'),
  )

  # Default string reverse replacements
  _DEFAULT_STRING_REVERSE_REPLACEMENTS: Sequence[Replacement] = (
      Replacement('--slash--', '/'),
  )

  def __init__(
      self,
      name: str,
      description: str,
  ):
    """Initialize a command.

    Args:
      name: The name of the command.
      description: The description of the command used for help messages.
    """
    self.name = name
    self.description = description

  @abc.abstractmethod
  def add_subcommand(
      self,
      subparser: argparse._SubParsersAction,
  ) -> None:
    """Add arguments to the parser.

    Args:
      subparser: The subparser to add the arguments to.
    """

  @abc.abstractmethod
  def _build_command(
      self,
      args: argparse.Namespace,
      extra_args: Mapping[str, str] | None = None,
      verbose: bool = False,
  ) -> Sequence[str]:
    """Build the command.

    Args:
      args: The arguments parsed from the command line.
      extra_args: Any extra arguments to pass to the command.
      verbose: Whether to print the command and other output.

    Returns:
      The command to run.
    """

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
    command = self._build_command(args, extra_args, verbose)
    if verbose:
      print(f'Command to run: {command}')

    stdout: str = self._run_command(command, verbose=verbose)
    return stdout

  def _run_command(
      self,
      command: Sequence[str],
      *,
      verbose: bool = False,
  ) -> str:
    """Run the command.

    Args:
      command: The command to run.
      verbose: Whether to print the command and other output.

    Returns:
      The output of the command.
    """
    output = ''
    try:
      diag = subprocess.run(
          command,
          check=True,
          capture_output=True,
          text=True,
      )
      if verbose:
        print(f'Command {command} succeeded.')
      if diag.stdout:
        output = diag.stdout
        if verbose:
          print(f'Output: {diag.stdout}')

    except subprocess.CalledProcessError as e:
      raise ValueError(f'Command failed with following error: {e}') from e

    return output

  def _format_string_with_replacements(
      self,
      original_string: str,
      replacements: Sequence[Replacement],
  ) -> str:
    """Formats the string with the given replacements.

    Args:
      original_string: The string to format.
      replacements: The replacements to make in the string. Note order is
        important.

    Returns:
      The formatted string.
    """
    # Replace the replacements with the original characters.
    for replacement in replacements:
      original_string = original_string.replace(
          replacement.original,
          replacement.to,
      )

    return original_string

  def _format_label_string(
      self,
      labels: dict[str, str],
      replacements: Sequence[Replacement] | None = None,
  ) -> str:
    """Formats the labels as a string.

    This is used to format the labels as a string that can be passed to the
    gcloud command line tool. By default, this will replace the gs:// prefix
    and / with --slash-- to make it easier to read and copy/paste, though a
    custom set of replacements can be provided. It will also remove the trailing
    slash on a label if present if no replacements are provided.

    Args:
        labels: The labels to format.
        replacements: The replacements to make in the labels. Note order is
          important.

    Returns:
        The formatted labels as a string.
    """

    # Create one string before using replacements.
    strings = []
    for key, value in labels.items():
      if replacements is None and value[-1] == '/':
        value = value[:-1]
      strings.append(f'{key}={value}')
    labels_string = ','.join(strings)

    # Use default replacements if not provided.
    labels_string = self._format_string_with_replacements(
        original_string=labels_string,
        replacements=(
            replacements if replacements else self._DEFAULT_STRING_REPLACEMENTS
        ),
    )

    return labels_string
