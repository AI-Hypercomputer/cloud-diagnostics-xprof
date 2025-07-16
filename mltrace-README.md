<!--
 Copyright 2023 Google LLC
 
 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at
 
      https://www.apache.org/licenses/LICENSE-2.0
 
 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
 -->
# mltrace

mltrace is a tool to convert your GCP workload logs into a sequence of Perfetto
Traces. The traces are grouped on multiple levels to make the logs easier to
comprehend.

## Introduction

For any workload, you'll see a glut of logs on the console that are hard to
parse through, making it difficult to debug a failure. This is because the logs
are collected from multiple sources involved in running a workload, e.g.,
initialization of components, XLA, GCS, checkpointing, user script logs etc.
Scrolling through these logs is time-consuming and inefficient to find the
real failure point. This tool brings forth a way faster mechanism for a user to
parse the logs visually and ultimately find the root cause of a failure.

## Description

The tool parses the logs, extracts key information for each log, and based on
that information groups the logs and finally converts the logs into traces. Note
that the tool filters out the logs that are irrelevant for debugging failures
e.g., config values.

The traces produced by our tool can be uploaded to
[Perfetto](https://perfetto.dev/), which is an open-source stack for performance
instrumentation and trace analysis.

## Requirements

For using mltrace, you need to clone [Perfetto](https://github.com/google/perfetto)
and compile [perfetto_trace.proto](https://github.com/google/perfetto/protos/perfetto/trace/perfetto_trace.proto).
Instructions for this are in the next section.

- Install [protoc](https://grpc.io/docs/protoc-installation/).
`sudo apt install protobuf-compiler` or `brew install protobuf`

- Install pandas.
`pip install pandas`

- You'll also need to install the google package and make sure it's up-to-date.
`pip install --upgrade google-api-python-client`


## Installation

Clone cloud-diagnostics-xprof and Perfetto.

```
git clone https://github.com/AI-Hypercomputer/cloud-diagnostics-xprof.git
cd cloud-diagnostics-xprof/src
git clone https://github.com/google/perfetto.git
protoc --proto_path=perfetto/protos/perfetto/trace/ --python_out=perfetto/protos/perfetto/trace/ perfetto/protos/perfetto/trace/perfetto_trace.proto
```

## Run mltrace

```
python3 run_mltrace.py -f <json_or_csv_filepath> -j <jobset_name>
```
The output will be a trace file stored under the same directory as your input
file. Upload the output file to [perfetto.dev](https://perfetto.dev/).

See the example use of the tool [here](mltrace-example.md).
