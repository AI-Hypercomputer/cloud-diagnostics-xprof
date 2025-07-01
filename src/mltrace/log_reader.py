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

"""Reads the logs into a pandas Data Frame.
"""

import pathlib
import pandas as pd


def read_logs_from_csv(filename: str, sep=",") -> pd.DataFrame:
  """Reads the logs into a pandas data frame.

  Args:
      filename (str): The path to the log file
      sep (str): The separator used between columns

  Returns:
      pd.DataFrame: File logs
  """
  logs = pd.read_csv(filename, sep=sep)
  print(f"Found {logs.size} records with columns: {logs.columns}")
  return logs


def read_logs_from_json(filename: str) -> pd.DataFrame:
  """Reads the logs into a pandas data frame.

  Args:
      filename (str): The path to the log file

  Returns:
      pd.DataFrame: File logs
  """
  try:
    # Try to read as a standard JSON array first. This will fail for JSONL.
    logs = pd.read_json(filename)
  except ValueError:
    # If that fails, it might be a JSON Lines file.
    logs = pd.read_json(filename, lines=True)
  print(f"Found {logs.size} records with columns: {logs.columns}")
  return logs


def read_logs_from_file(filename: str) -> pd.DataFrame:
  """Reads the logs into a pandas data frame.

  Args:
      filename (str): The path to the log file

  Returns:
      pd.DataFrame: File logs

  Raises:
      ValueError if the given file is neither CSV nor JSON
  """
  file_ext = pathlib.Path(filename).suffix
  if file_ext == ".csv":
    logs = read_logs_from_csv(filename)
  elif file_ext == ".json":
    logs = read_logs_from_json(filename)
  else:
    raise ValueError(
        f"Invalid file type \"{file_ext}\". Supported: .csv and .json"
    )
  return logs
