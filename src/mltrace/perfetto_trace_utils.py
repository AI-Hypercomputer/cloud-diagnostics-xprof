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

"""Translates logs to Perfetto trace events and dumps the traces to a .gz file.
"""

import datetime
import gzip
import logging
import os
import pathlib
import re
import string

from mltrace import constants
import pandas as pd
from perfetto.protos.perfetto.trace import perfetto_trace_pb2

logger = logging.getLogger(__name__)


class Counter:
  """A simple counter that returns the next counter value."""

  def __init__(self):
    self._counter = 0

  def next_counter(self):
    self._counter += 1
    return self._counter


def translate_to_traces(df: pd.DataFrame) -> bytes:
  """Translates the logs to trace events.

  The conversion logic builds a hierarchy of traces using the unique values of
  certain data frame columns.
  For example, the "parent" column determines the parent group. Within each
  parent, the "section" column defines the sub-groups within the parent.
  Here's an example hierarchy:

  |__ Coordinator
      |
      |__ Checkpoint
      |__ Training
      |__ Failed to connect
      |__ Other logs
  |
  |__ Workers
      |
      |__ Checkpoint
      |__ Training
      |__ Failed to connect
      |__ Other logs

  Args:
    df (pd.DataFrame): Logs data

  Returns:
    bytes: Trace events serialized into string format
  """
  logger.debug("Starting the log->trace translation.")
  counter = Counter()
  clock_is_set = False

  def next_counter():
    return counter.next_counter()

  def add_packet(t):
    p = t.packet.add()
    p.trusted_packet_sequence_id = 1
    p.sequence_flags = p.SEQ_NEEDS_INCREMENTAL_STATE
    p.timestamp_clock_id = 1
    return p

  def maybe_add_clock(timestamp):
    nonlocal clock_is_set
    if not clock_is_set:
      p = add_packet(t)
      p.clock_snapshot.primary_trace_clock = 1
      clock = p.clock_snapshot.clocks.add()
      clock.timestamp = timestamp
      clock.clock_id = 1
      clock_is_set = True

  def add_instant_event(track_id, name, start, metadata=None):
    maybe_add_clock(start)
    p = add_packet(t)
    p.track_event.type = p.track_event.TYPE_INSTANT
    p.track_event.timestamp_absolute_us = start
    p.track_event.track_uuid = track_id
    p.track_event.name = name
    if metadata:
      for key, value in metadata.items():
        d = p.track_event.debug_annotations.add()
        d.name = key
        d.string_value = str(value)

  def add_section(uuid, name, parent=None, process_name=None):
    p = add_packet(t)
    p.track_descriptor.name = name
    p.track_descriptor.uuid = uuid
    if parent:
      p.track_descriptor.parent_uuid = parent

    if process_name:
      p.track_descriptor.process.pid = uuid
      p.track_descriptor.process.process_name = process_name

  t = perfetto_trace_pb2.Trace()
  p = add_packet(t)
  p.sequence_flags = p.SEQ_INCREMENTAL_STATE_CLEARED

  for key in df["parent"].unique():
    value = df[df["parent"] == key]
    w_uuid = next_counter()
    add_section(w_uuid, key, process_name=key)
    logger.debug("Adding events for parent: %s", key)
    for section in value.section.unique():
      uuid = next_counter()
      add_section(uuid, section, parent=w_uuid)
      logger.debug("Adding events for section: %s", section)

      def add_events(event, uuid=uuid):
        name = event.textPayload  # Marker color

        try:
          # This block handles string timestamps, assuming ISO 8601 format.
          # The original code had a dangerous eval and broken strptime here.
          ts_str = event.timestamp
          if not isinstance(ts_str, str):
            raise TypeError("Not a string, try parsing as datetime object.")

          # Truncate to microseconds if there are nanoseconds.
          t_micro = re.sub(r"(\.\d{6})\d*(Z?)$", r"\1\2", ts_str)
          # fromisoformat before Python 3.11 doesn't like 'Z'
          if t_micro.endswith("Z"):
            t_micro = t_micro[:-1] + "+00:00"
          dt = datetime.datetime.fromisoformat(t_micro)
          timestamp_us = int(dt.timestamp() * 1_000_000)
        except (TypeError, ValueError):
          # This block handles datetime objects
          timestamp_us = int(event.timestamp.timestamp() * 1_000_000)

        metadata = {
            k: v for k, v in event.dropna().to_dict().items() if not pd.isna(v)
        }
        add_instant_event(uuid, name, timestamp_us, metadata)

      value[value["section"] == section].apply(add_events, axis=1)

  logger.debug("Log->trace translation completed")
  return t.SerializeToString()


def dump_traces(input_filepath: str, traces: bytes):
  """Dumps traces to the gives filepath.

  Args:
    input_filepath (str): The path to the input file
    traces (bytes): The traces to dump
  """
  p = pathlib.Path(input_filepath)
  gz_output_filepath = os.path.join(str(p.parent), p.stem + ".gz")
  logger.debug("Saving the traces at %s", gz_output_filepath)
  with open(gz_output_filepath, "wb") as fp:
    fp.write(gzip.compress(traces))

  html_output_filepath = os.path.join(str(p.parent), p.stem + ".html")
  logger.debug("Building the HTML at %s", html_output_filepath)
  with open(html_output_filepath, "w") as fp:
    html_template = string.Template(constants.PERFETTO_TEMPLATE_HTML)
    fp.write(
        html_template.substitute(
            dict(
                trace_file=f"./{p.stem}.gz",
                title=p.stem,
            )
        )
    )

  logger.info(
      "Saved the HTML at %s and traces at %s. You can either host the HTML for"
      " visualization by running `python3 -m http.server --bind 0.0.0.0 9919`"
      " from the output directory OR upload the trace file to"
      " https://perfetto.dev.",
      html_output_filepath,
      gz_output_filepath,
  )
