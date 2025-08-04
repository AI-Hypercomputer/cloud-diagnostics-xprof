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

from mltrace import log_parser
from mltrace import option_parser
from mltrace import perfetto_trace_utils
from mltrace.log_reader import file_log_reader


def get_logs(args):
  return file_log_reader.FileLogReader(args.filename).read_logs()


def main():
  """Script main entry."""
  args = option_parser.getopts()
  logs = get_logs(args)
  if len(logs) == 0:
    raise ValueError("No logs found!")
  data = log_parser.parse_logs(logs, args.jobname)
  if len(data) == 0:
    raise ValueError(
        "We could not parse any logs while the file was not empty."
        " Check the format of the logs."
    )
  traces = perfetto_trace_utils.translate_to_traces(data)
  html_output_filepath = perfetto_trace_utils.dump_traces(args.filename, traces)
  print(
      f"Saved the traces at {html_output_filepath}.\nNext steps:\n1. Run a"
      " local HTTP server: `python -m http.server --bind 0.0.0.0 9919`.\n2."
      f" Use a browser to connect to http://0.0.0.0:9919/{html_output_filepath}"
      " to see the visualization of job events."
  )
