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

"""Base class for defining the interface of actions by xprof via subparsers.

The Command class is used to define the interface to include in the xprof
parser. It is used to create a command line interface (CLI) tool that
allows users to perform various actions through a subparser.
"""

import abc
import argparse
from collections.abc import Mapping, Sequence
import dataclasses
from importlib import metadata
import re
import subprocess
import tabulate


def get_package_version(
    package_name: str,
    version_default: str = 'unknown',
    *,
    verbose: bool = False,
) -> str:
  """Gets the version of the installed package.

  Args:
    package_name: The name of the package to get the version of.
    version_default: The default version to return if the package could not be
      found or the version could not be determined.
    verbose: Whether to print information about package version gathered.

  Returns:
    The version of the package or an error message if the package could not be
    found or the version could not be determined.
  """
  try:
    version = metadata.version(package_name).replace('.', '-')
    if verbose:
      print(f'Version of {package_name} is `{version}`.')
    return version
  except metadata.PackageNotFoundError:
    version = version_default
    if verbose:
      package_not_found_error = (
          f'{package_name} package not found'
          ' or version could not be determined.'
      )
      print(package_not_found_error)
      print(f'Reverting to default version: {version_default}')
    return version


class Command(abc.ABC):
  """A standard implementation of a CLI command."""

  GCLOUD_COMMAND: str = 'gcloud'
  VM_BASE_NAME = 'xprof'
  TABLE_COLUMNS: Sequence[str] = (
      'Log_Directory',
      'URL',
      'Name',
      'Zone',
  )
  LOG_DIRECTORY_LABEL_KEY = 'xprofiler_log_directory'
  XPROFILER_VERSION_LABEL_KEY = 'xprofiler_version'
  XPROFILER_VERSION = get_package_version(
      package_name='cloud-diagnostics-xprof'
  )
  LOG_DIRECTORY_LABEL_KEY_N_SECTIONS = f'{LOG_DIRECTORY_LABEL_KEY}-n_sections'
  DEFAULT_NAMESPACE = 'xprofiler'

  @dataclasses.dataclass(frozen=True)
  class Replacement:
    original: str
    to: str

  # Default replacements for formatting strings
  DEFAULT_STRING_REPLACEMENTS: Sequence[Replacement] = (
      Replacement('gs://', ''),
  )
  LOG_DIRECTORY_STRING_REPLACEMENTS: Mapping[str, Sequence[Replacement]] = {
      '0.0.10': (
          Replacement('gs://', ''),
          Replacement('/', '--slash--'),
      ),
      'default': DEFAULT_STRING_REPLACEMENTS,
      'current': DEFAULT_STRING_REPLACEMENTS,
  }

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
      extra_args: Mapping[str, str | None] | None = None,
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
      extra_args: Mapping[str, str | None] | None = None,
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
      # Only print the full subprocess error if in verbose mode.
      if verbose:
        # Print the simple error stderr from the shell command.
        if e.stderr:
          print('Command failed. Standard Error (stderr):')
          print(e.stderr)
        print(f'Command failed. Subprocess error:\n{e}')
      # For readability, custom error message has stderr from shell command.
      error_message = (
          f'Command failed with return code {e.returncode}.\n'
          f'{e.stderr if e.stderr else ""}'
      )
      raise ValueError(error_message) from e

    return output

  def format_string_with_replacements(
      self,
      original_string: str,
      replacements: Sequence[Replacement],
  ) -> str:
    """Formats the string with the given replacements.

    Used mostly to format the log directory string using string replacements.
    Also removes the trailing forward slash (/) on string.

    Args:
      original_string: The string to format.
      replacements: The replacements to make in the string. Note order is
        important.

    Returns:
      The formatted string.
    """
    # Remove trailing forward slash is present.
    original_string = original_string.rstrip('/')

    # Replace the replacements with the original characters.
    for replacement in replacements:
      original_string = original_string.replace(
          replacement.original,
          replacement.to,
      )

    return original_string

  def format_label_string(
      self,
      labels: dict[str, str],
      replacements: Sequence[Replacement] | None = None,
  ) -> str:
    """Formats the labels as a string.

    This is used to format the labels as a string that can be passed to the
    gcloud command line tool. By default, this will replace the gs:// prefix
    and / with --slash-- to make it easier to read and copy/paste, though a
    custom set of replacements can be provided.

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
      # For consistency, remove trailing forward slash is present.
      if value[-1] == '/':
        value = value[:-1]
      strings.append(f'{key}={value}')
    labels_string = ','.join(strings)

    # Use default replacements if not provided.
    labels_string = self.format_string_with_replacements(
        original_string=labels_string,
        replacements=(
            replacements if replacements else self.DEFAULT_STRING_REPLACEMENTS
        ),
    )

    return labels_string

  def create_data_table(
      self,
      *,
      columns: Sequence[str],
      lines: Sequence[Sequence[str]],
      verbose: bool = False,
  ) -> Mapping[str, Sequence[str]]:
    """Returns a mapping of column headers to values from a table string.

    Args:
      columns: The columns of the table.
      lines: The lines of the table.
      verbose: Whether to print verbose output.

    Returns:
      A mapping of column headers to values from a table string.
    """
    # For referennce of order of columns.
    columns_index: dict[int, str] = dict(enumerate(columns))

    data_table: dict[str, list[str]] = {
        col: [] for col in columns_index.values()
    }

    if verbose:
      print(f'COLUMNS: {columns_index}')
      print('Creating data table...')

    for line_number, line in enumerate(lines):
      # Check that the same number of columns and items in each line.
      # These VMs are either being created or badly configured.
      if len(line) != len(columns_index):
        continue

      for n_item, column_value in enumerate(line):
        # Make sure we use the same order for the columns as the line values.
        data_table[columns_index[n_item]].append(column_value)
      if verbose:
        print(f'line {line_number} added to data table')

    if verbose:
      print(f'DATA TABLE: {data_table}')

    return data_table

  def display_table_string(
      self,
      data_table: Mapping[str, Sequence[str]],
      *,
      verbose: bool = False,
  ) -> str:
    """Returns a formatted table string from data table.

    Args:
      data_table: The data table to display.
      verbose: Whether to print the table.

    Returns:
      The formatted table string.
    """
    if verbose:
      print(f'Print formatted TABLE: {data_table}')

    # Just the first row is the headers.
    header = list(data_table.keys())
    data_rows = [list(row) for row in zip(*data_table.values())]
    lines: list[list[str]] = [header] + data_rows

    formatted_string = tabulate.tabulate(lines, headers='firstrow')

    return formatted_string

  @abc.abstractmethod
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

  def _get_bucket_parts(
      self,
      gcs_bucket_url: str,
  ) -> tuple[str, str | None] | None:
    """Returns the bucket name and path from a GCS bucket URL.

    Args:
      gcs_bucket_url: The GCS bucket URL to parse.

    Returns:
      A tuple of the bucket name (gs://my-bucket) and path part (dir0/dir1/...).
      If the bucket URL format is invalid, returns None. If given just the
      bucket name, returns the bucket name and None.
    """
    # Use regex to extract just the bucket name from the log directory.
    gcs_bucket_pattern = (
        r'^gs://(?P<bucket>[^/]+)(?P<path_part>/(?:[^/\n\r]+/?)*)?$'
    )
    match = re.match(
        pattern=gcs_bucket_pattern,
        string=gcs_bucket_url,
    )
    if match:
      bucket_url: str = f'gs://{match.group("bucket")}'
      path_part: str | None = match.group('path_part')
      # Consider a trailing slash as no path part.
      if path_part == '/':
        path_part = None
      return (bucket_url, path_part)
    else:
      return None

  def _is_valid_bucket(
      self,
      *,
      bucket_name: str,
      verbose: bool,
  ) -> bool:
    """Checks if the bucket exists and the path was part of full GCS bucket URL.

    Note that path part is not necessary for valid bucket URL.

    Args:
      bucket_name: Name of bucket to check. Assumes bucket url (gs://my-bucket)
      verbose: Whether to print the command and other output.

    Returns:
      True if the bucket exists and the path was part of GCS bucket URL, False
      otherwise.
    """
    bucket_name_and_path = self._get_bucket_parts(
        gcs_bucket_url=bucket_name,
    )
    # If can't get the bucket parts, then something is wrong with the format.
    if bucket_name_and_path is None:
      if verbose:
        print(f'Bucket URL {bucket_name} is not valid. Check string format.')
      return False
    else:
      bucket_url, path_part = bucket_name_and_path

    # Check that the path part exists.
    if path_part is None:
      if verbose:
        print(f'Path part from bucket URL {bucket_name} does not exist.')
      return True

    # Check for bucket existence (ignores path part).
    return self._bucket_exists(
        bucket_name=bucket_url,
        verbose=verbose,
    )

  def _bucket_exists(
      self,
      *,
      bucket_name: str | None,
      verbose: bool = False,
  ) -> bool:
    """Checks if the bucket exists.

    Args:
      bucket_name: Name of bucket to check. Assumes bucket url (gs://my-bucket)
      verbose: Whether to print the command and other output.

    Returns:
      True if the bucket exists, False otherwise.
    """
    if bucket_name is None:
      if verbose:
        print('Bucket name not provided.')
      return False
    describe_bucket_command = [
        self.GCLOUD_COMMAND,
        'storage',
        'buckets',
        'describe',
        bucket_name,
    ]
    # Catch errors from the describe bucket command and only return False
    try:
      if verbose:
        print(
            f'Checking if bucket {bucket_name} exists with command:'
            f' {describe_bucket_command}'
        )
      _ = self._run_command(describe_bucket_command, verbose=verbose)
      if verbose:
        print(f'Bucket {bucket_name} exists.')
      return True
    except ValueError as e:
      if verbose:
        print(f'Bucket {bucket_name} does not exist.')
        print(f'Error caught running command to check bucket exists: {e}')
      return False

  def _host_exists(
      self,
      *,
      host_name: str,
      zone: str,
      verbose: bool = False,
  ) -> bool:
    """Checks if a host exists."""
    try:
      host_describe_command = [
          self.GCLOUD_COMMAND,
          'compute',
          'tpus',
          'tpu-vm',
          'describe',
          host_name,
          '--zone',
          zone,
      ]
      _ = self._run_command(host_describe_command, verbose=verbose)
      return True
    except ValueError as e:
      if verbose:
        print(f'Host {host_name} does not exist.')
        print(f'Error caught running command to check bucket exists: {e}')
      return False


def flag_from_string(flag_name: str) -> str:
  """Parses the flag from the string.

  If the flag starts with a dash, it is assumed to be correct with correct
  number of dashes. If the flag is a single character, it is assumed to need a
  dash. Otherwise, it is assumed to be a double dash.

  Args:
    flag_name: The flag name to parse.

  Returns:
    The flag name with dashes if needed.
  """
  # If it starts with a dash (assume correct number of dashes) probably correct.
  if flag_name.startswith('-'):
    return flag_name
  elif len(flag_name) == 1:
    return f'-{flag_name}'
  else:
    return f'--{flag_name}'


def flag_with_value_from_key_value(
    key: str,
    value: str | None,
) -> tuple[str, str | None]:
  """Parses the full flag from the key and value.

  Args:
    key: The key of the flag.
    value: The value of the flag.

  Returns:
    A tuple of the flag name (with dashes if needed) and value.
  """
  flag_name = flag_from_string(key)
  # If the value is an empty string or None, then we want it to be None
  flag_value = value if value else None
  return (flag_name, flag_value)
