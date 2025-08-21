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

"""File log reader.
"""

import logging
import pathlib

import pandas as pd

from . import log_reader

logger = logging.getLogger(__name__)


class FileLogReader(log_reader.LogReader):
  """Reads logs from a file into a pandas data frame."""

  def __init__(self, filename: str):
    self._filename = filename

  def _read_logs_from_csv(self) -> pd.DataFrame:
    """Reads the logs into a pandas data frame.

    Returns:
        pd.DataFrame: File logs
    """
    logs = pd.read_csv(self._filename, sep=",")
    logger.info("Found %d records with columns: %s", logs.size, logs.columns)
    return logs

  def _read_logs_from_json(self) -> pd.DataFrame:
    """Reads the logs into a pandas data frame.

    Returns:
        pd.DataFrame: File logs
    """
    try:
      # Try to read as a standard JSON array first. This will fail for JSONL.
      logs = pd.read_json(self._filename)
    except ValueError:
      # If that fails, it might be a JSON Lines file.
      logs = pd.read_json(self._filename, lines=True)
    logger.info("Found %d records with columns: %s", logs.size, logs.columns)
    return logs

  def read_logs(self) -> pd.DataFrame:
    """Reads the logs into a pandas data frame.

    Returns:
        pd.DataFrame: File logs

    Raises:
        ValueError if the given file is neither CSV nor JSON
    """
    file_ext = pathlib.Path(self._filename).suffix
    logger.info("Starting the log reader for file: %s", self._filename)
    if file_ext == ".csv":
      logs = self._read_logs_from_csv()
    elif file_ext in [".json", ".jsonl"]:
      logs = self._read_logs_from_json()
    else:
      raise ValueError(
          f"Invalid file type \"{file_ext}\". Supported: .csv and .json[l]"
      )
    logger.debug("Log reader completed.")
    return logs
