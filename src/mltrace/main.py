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

"""Main function body for mltrace.
"""
import logging

from mltrace import log_parser
from mltrace import option_parser
from mltrace import perfetto_trace_utils
from mltrace.log_reader import cloud_logging_log_reader, file_log_reader

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def get_logs(args):
  if args.filename:
    return file_log_reader.FileLogReader(args.filename).read_logs()
  else:
    return cloud_logging_log_reader.CloudLoggingLogReader(
        args.project_id, args.jobname, args.start, args.end, args.log_filter
    ).read_logs()


def main():
  """Script main entry."""
  args = option_parser.getopts()
  logs = get_logs(args)
  logger.info("Number of logs read: %d", len(logs))
  if len(logs) == 0:
    raise ValueError("No logs found!")
  data = log_parser.parse_logs(logs, args.jobname)
  logger.info("Number of logs after parsing: %d", len(data))
  if len(data) == 0:
    raise ValueError(
        "We could not parse any logs while the file was not empty."
        " Check the format of the logs."
    )
  traces = perfetto_trace_utils.translate_to_traces(data)
  perfetto_trace_utils.dump_traces(args.output_filename, traces)
