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
import os

from mltrace import constants


class IllegalArgumentError(ValueError):
  pass


def validate_time(time_str: str):
  """Validates the given time string against the accepted format.

  Args:
    time_str: The time string to validate.

  Raises:
    IllegalArgumentError: If the given value is incorrect.
  """
  try:
    datetime.datetime.strptime(time_str, constants.TIME_REGEXP)
  except ValueError as exc:
    raise IllegalArgumentError(
        f"The format of start/end time '{time_str}' is incorrect. Use "
        "'{constants.TIME_REGEXP}'"
    ) from exc


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
  if args.filename is None or not os.path.exists(args.filename):
    raise IllegalArgumentError(
        f"ERROR: Provide a valid file path. `{args.filename}` does not exist!"
    )


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
  args = parser.parse_args()

  validate_args(args)
  return args
