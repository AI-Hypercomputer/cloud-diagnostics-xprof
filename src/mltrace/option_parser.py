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

"""Option Parser for the ML Trace tool.
"""

import argparse
import datetime
import logging
import os

from mltrace import constants


class IllegalArgumentError(ValueError):
  pass


def set_logging_level(loglevel: str):
  """Sets the logging level for the MLTrace module.

  Args:
    loglevel: The logging level to set.
  Raises:
    ValueError: If the logging level is invalid.
  """
  # Set the logging level based on the command-line argument
  numeric_level = getattr(logging, loglevel.upper(), None)
  if not isinstance(numeric_level, int):
    raise ValueError(f"Invalid log level: {loglevel}")
  logging.getLogger().setLevel(numeric_level)


def get_default_time_range(start: str, end: str) -> tuple[str, str]:
  """Returns the default time range for the logs.

  Args:
    start: The start time string.
    end: The end time string.
  Returns:
    A tuple of start and end time strings.
  """
  if end is None:
    end = datetime.datetime.now(datetime.timezone.utc).strftime(
        constants.TIME_REGEXP
    )
  if start is None:
    start = (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(hours=1)
    ).strftime(constants.TIME_REGEXP)
  return (start, end)


def validate_time(start: str, end: str):
  """Validates the given time string against the accepted format.

  Args:
    start: The start time string to validate.
    end: The end time string to validate.

  Raises:
    IllegalArgumentError: If the given value is incorrect.
  """
  try:
    start = datetime.datetime.strptime(start, constants.TIME_REGEXP)
    end = datetime.datetime.strptime(end, constants.TIME_REGEXP)
  except ValueError as exc:
    raise IllegalArgumentError(
        f"The format of start/end time is incorrect. Use "
        f"'{constants.TIME_REGEXP}'"
    ) from exc
  if start > end:
    raise IllegalArgumentError(
        "ERROR: Start time must be before end time. "
        f"Got {start} > {end}"
    )


def validate_args(args: argparse.Namespace):
  """Validates the command-line args.

  Args:
    args: The command-line arguments.

  Raises:
    IllegalArgumentError: If the args are not supported.
  """
  if not args.jobname:
    raise IllegalArgumentError(
        "Jobname cannot be empty. Provide a valid jobset/job name"
    )
  if args.filename is not None:
    # Reading from a file.
    if not os.path.exists(args.filename):
      raise IllegalArgumentError(
          f"ERROR: Provide a valid file path. `{args.filename}` does not exist!"
      )
  else:
    # Reading from Cloud Logging.
    if args.output_filename is None:
      raise IllegalArgumentError(
          "ERROR: If you're reading logs from a file, provide "
          " --filename.\nOtherwise if you're reading logs from Cloud Logging,"
          " provide --output_filename where the traces will be stored."
      )
  validate_time(args.start, args.end)


def getopts() -> argparse.Namespace:
  """Parses and returns the command line options.

  Returns:
    argparse.Namespace: The parsed command line arguments
  """
  parser = argparse.ArgumentParser(
      prog="MLTrace", description="Build traces for the GCP workload logs"
  )
  parser.add_argument(
      "-f", "--filename", help="Path to the CSV/JSON file that contains logs"
  )
  parser.add_argument("-j", "--jobname", help="Name of the job/jobset")
  parser.add_argument(
      "-p", "--project_id", required=True, help="GCP project name"
  )
  parser.add_argument(
      "-e", "--end", default=None, help="End time of logs, defaults to now"
  )
  parser.add_argument(
      "-s",
      "--start",
      default=None,
      help="Start time of logs, defaults to 1 hour before end time",
  )
  parser.add_argument(
      "-l",
      "--log_filter",
      help=(
          "Space-separated log filters in single quotes, see examples in the"
          " README"
      ),
  )
  parser.add_argument(
      "-o",
      "--output_filename",
      help="Name of the output file when reading directly from Cloud Logging",
  )
  parser.add_argument("--loglevel", default="INFO",
                      choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                      help="Set the logging level (e.g., DEBUG, INFO, WARNING)")
  args = parser.parse_args()

  set_logging_level(args.loglevel)

  # Set start and end times if missing, so that the tool doesn't run without
  # bounds.
  args.start, args.end = get_default_time_range(args.start, args.end)

  if args.output_filename is None and args.filename is not None:
    args.output_filename = args.filename

  validate_args(args)
  return args
