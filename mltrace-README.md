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

- Install [protoc](https://grpc.io/docs/protoc-installation/):
`sudo apt install protobuf-compiler` or `brew install protobuf` or

```
PB_REL="https://github.com/protocolbuffers/protobuf/releases"
curl -LO $PB_REL/download/v29.3/protoc-29.3-linux-x86_64.zip
unzip protoc-29.3-linux-x86_64.zip -d $HOME/.local
export PATH="$PATH:$HOME/.local/bin"
```

- Install pandas:
`pip install pandas`

- You'll also need to install the google package and make sure it's up-to-date:
`pip install --upgrade google-api-python-client`


## Installation

Clone `cloud-diagnostics-xprof` and `Perfetto`:

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
The output will be a trace file and an HTML file stored under the same directory
as your input file.

## View the traces

Either host a local HTTP server or manually upload the output file to
[perfetto.dev](https://perfetto.dev/) for visualizing the traces.

#### Option a: Host a local HTTP server

Follow the instructions from the output of the tool:

1. Run a local HTTP server: `python -m http.server --bind 0.0.0.0 9919`.
2. Use a browser to connect to http://0.0.0.0:9919/<output_filename>.html.

#### Option b: Upload to perfetto.dev manually

The tool has created a ".gz" file of the same name as the HTML file. You can
upload this file manually.

Got to https://perfetto.dev/ > Click on `Trace Viewer` > Upload the ".gz" trace
file.


## Example usage

### Step 1: Download the logs

The script reads logs from a JSON file. The first step is to copy logs to JSON.

#### Option a: Download from GCP console

You can download your workload logs from the GCP console directly. See the
screenshot below.

Note that this option has a max limit of 10k on the number of logs to download.
If you're looking to download more logs. See
[Option (b)](#option-b-export-the-logs-from-sink).

<img src="docs/images/ex1-download-1.png" width="700">
<img src="docs/images/ex1-download-2.png" width="500">

#### Option b: Export the logs from sink

You can create a sink and export your logs as mentioned on the second screenshot
above. If you do not have a custom sink for your project, all logs are stored in
the _Default sink by default.

```
# 1. Copy logs to GCS
LOG_SINK="_Default"  # Modify if using a custom sink
BUCKET={YOUR_BUCKET_NAME}
LOG_FILTER={YOUR_LOG_FILTER}  # e.g., 'resource.type="k8s_container" resource.labels.location="us-west1" resource.labels.pod_name="test1" timestamp > "2025-07-17T01:00:00.0Z"'
PROJECT={YOUR_PROJECT_ID}

gcloud logging copy ${LOG_SINK} storage.googleapis.com/${BUCKET} --location=global --log-filter=${LOG_FILTER} --project=${PROJECT}

# 2. Download logs from GCS.
mkdir logs
PATH= ..  # Find the GCS path to the log files.
gsutil -m cp -r "gs://${BUCKET}/{$PATH}" logs/

# 3. Merge the log files with the below python commands, if multiple files are created.
import pandas as pd
read_files = glob.glob("logs/*.json")
output_list = []
for f in read_files:
  output_list.append(pd.read_json(f))
r = pd.concat(output_list)
r.to_json("merged.json", orient='records', lines=True)
```

### Step 2: Run the mltrace tool

```
python3 run_mltrace.py -f <filepath> -j <jobset_name>
```

### Step 3: Visualize the traces with Perfetto

![Visualize with Perfetto](docs/images/ex1-perfetto.png "Visualize with Perfetto")

