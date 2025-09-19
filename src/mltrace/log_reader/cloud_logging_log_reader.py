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

"""Reads logs from Cloud Logging."""

import datetime
import logging
import more_itertools
import pandas as pd
import urllib.parse

from google.cloud import logging_v2
from . import log_reader
from .. import constants

PAGE_SIZE = 10000
logger = logging.getLogger(__name__)

class CloudLoggingLogReader(log_reader.LogReader):
  """Reads logs from Cloud Logging."""

  def __init__(
      self, project_id: str, jobname: str, start: str, end: str, log_filter: str
  ):
    self._project_id = project_id
    self._jobname = jobname
    self._start = start
    self._end = end
    self._log_filter = log_filter

  def _validate_log_structure(self, log: logging_v2.LogEntry) -> bool:
    """Validates the log structure.
    """
    if (
        log.resource is None
        or len(log.resource.ListFields()) < 2
        or not isinstance(log.resource.ListFields()[1][1], dict)
        or not all(
            k in log.resource.ListFields()[1][1]
            for k in [
                "project_id",
                "cluster_name",
                "location",
                "container_name",
                "pod_name",
            ]
        )
    ):
      logger.error(
          "Log structure has changed. Resource either not found in the log or"
          " the structure has changed. Expected structure:"
          " log.resource.ListFields()[1][1] is a dictionary with `project_id`,"
          " `cluster_name`, `location`, `container_name` and `pod_name` as"
          " keys. Got: %s",
          log,
      )
      return False
    return True


  def read_logs(self) -> pd.DataFrame:
    """Reads the logs into a pandas data frame.

    Returns:
        pd.DataFrame: Cloud logs
    """
    client = logging_v2.services.logging_service_v2.LoggingServiceV2Client()
    self._log_filter += f' timestamp>="{self._start}" timestamp<="{self._end}" '
    for regexp in constants.REDUNDANT_LOGS_SUBSTR_MATCH:
      # Per Cloud Logging docs, regex patterns must be in double quotes.
      # We must escape backslashes and double quotes inside the pattern.
      r = regexp.replace('\\', '\\\\').replace('"', '\\"')
      self._log_filter += f'textPayload!~"{r}" '

    for regexp in constants.REDUNDANT_LOGS_EXACT:
      r = regexp.replace('\\', '\\\\').replace('"', '\\"')
      self._log_filter += f'textPayload!~"{r}" '

    self._log_filter += " AND ".join([
        f"sourceLocation.file!={filename} OR severity!={severity}"
        for filename, severity in constants.REDUNDANT_SEVERITY_IN_FILES.items()
    ])

    request = logging_v2.types.ListLogEntriesRequest(
        resource_names=[f"projects/{self._project_id}"],
        filter=self._log_filter,
        page_size=PAGE_SIZE,
    )
    logger.debug("Starting the log reader with page-size=%d", PAGE_SIZE)
    log_pages = client.list_log_entries(request=request).pages
    p = more_itertools.peekable(log_pages)
    plog = p.peek().entries[0]
    if not self._validate_log_structure(plog):
      return pd.DataFrame()

    l = []  # List to store the logs
    for i, page in enumerate(log_pages):
      logger.debug("Reading log page#%d", i)
      for log in page.entries:
        json_payload = log.json_payload
        if json_payload is not None:
          json_payload = json_payload.get("message")
        start_t = log.timestamp - datetime.timedelta(microseconds=1)
        start_str = start_t.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        end_t = log.timestamp + datetime.timedelta(microseconds=1)
        end_str = end_t.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # Safely build the query string parts.
        query_parts = []
        if log.text_payload:
          query_parts.append(f'textPayload="{log.text_payload}"')
        if json_payload:
          query_parts.append(f'jsonPayload.message="{json_payload}"')
        query_parts.append(f'timestamp>="{start_str}"')
        query_parts.append(f'timestamp<="{end_str}"')

        log_query = "\n".join(query_parts)
        encoded_query = urllib.parse.quote(log_query)

        l.append({
            "resource.labels.pod_name": log.resource.ListFields()[1][1][
                "pod_name"
            ],
            "resource.labels.container_name": log.resource.ListFields()[1][1][
                "container_name"
            ],
            "project": log.resource.ListFields()[1][1]["project_id"],
            "cluster_name": log.resource.ListFields()[1][1]["cluster_name"],
            "location": log.resource.ListFields()[1][1]["location"],
            "timestamp": log.timestamp,
            "textPayload": log.text_payload,
            "jsonPayload.message": json_payload,
            "severity": log.severity,
            "sourceLocation.file": log.source_location.file,
            "sourceLocation.line": log.source_location.line,
            "labels": log.labels,
            "logLink": (
                "https://pantheon.corp.google.com/logs/query;query="
                f"{encoded_query}?project={self._project_id}"
            ),
        })
    logger.debug("Log reader completed.")
    return pd.DataFrame(l)
