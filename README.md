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
# xprofiler

The `xprofiler` SDK and CLI tool provides abstraction over profile session
locations and infrastructure running the analysis.

This includes allowing users to create and manage VM instances for TensorBoard
instances in regards to profiling workloads for GPU and TPU.

## Quickstart

### Install Dependencies

`xprofiler` relies on using [gcloud](https://cloud.google.com/sdk).

The first step is to follow the documentation to [install](https://cloud.google.com/sdk/docs/install).

Running the initial `gcloud` setup will ensure things like your default project
ID are set.

### Create a VM Instance for TensorBoard

To create a TensorBoard instance, you must provide a path to a GCS bucket.
It is also useful to define your specific zone.

```bash
ZONE=us-central1-a
GCS_PATH="gs://example-bucket/my-profile-data"

xprofiler create -z $ZONE -l $GCS_PATH
```

When the command completes, you will see it return information about the
instance created, similar to below:

```
LOG_PATH                            NAME                                            ZONE
gs://example-bucket/my-profile-data xprofiler-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef  us-central1-a
```

This will create a VM instance with TensorBoard installed. Note that this
initial startup for TensorBoard will take up to a few minutes (typically less
than 5 minutes) if you want to connect to the VM's TensorBoard.

### List VM Instances

To list the TensorBoard instances created by `xprofiler`, you can simply run
`xprofiler list`. However, it's recommended to specify the zone (though not
required).

```bash
ZONE=us-central1-a

xprofiler list -z $ZONE
```

This will output something like the following if there are instances matching
the list criteria:

```
LOG_PATH                                   NAME                                            ZONE
gs://example-bucket/my-other-profile-data  xprofiler-8187640b-e612-4c47-b4df-59a7fc86b253  us-central1-a
gs://example-bucket/my-profile-data        xprofiler-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef  us-central1-a
```

Note you can specify the GCS bucket to get just that one associated instance:

```bash
xprofiler list -l $GCS_PATH
```

### Delete VM Instance

To delete an instance, you'll need to specify either the GCS bucket path or the
instance's name. It is not required, but it is recommended to also specify the
zone.

```bash
# Delete by associated GCS path
xprofiler delete -z $ZONE -l $GCS_PATH

# Delete by VM instance name
VM_NAME="xprofiler-8187640b-e612-4c47-b4df-59a7fc86b253"
xprofiler delete -z $ZONE --name $VM_NAME
```

## Details on `xprofiler`

### Main Command: `xprofiler`

The `xprofiler` command has additional subcommands that can be invoked to
[create](#subcommand-xprofiler-create) VM instances,
[list](#subcommand-xprofiler-list) VM instances,
[delete](#subcommand-xprofiler-delete) instances, etc.
However, the main `xprofiler` command has some additional options without
invoking a subcommand.

#### `xprofiler --help`

Gives additional information about using the command including flag options and
available subcommands. Also can be called with `xprofiler -h`.

> Note that each subcommand has a `--help` flag that can give information about
> that specific subcommand. For example: `xprofiler list --help`

#### `xprofiler --abbrev ...`

When invoking a subcommand, typically there is output related to VM instances
involved with the subcommand, usually as a detailed table.

In some cases, a user may only want the relevant information (for example a log
directory GCS path or VM name instance). This can be particularly useful in
scripting with `xprofiler` by chaining with other commands.

To assist with this, the `--abbrev` (or equivalent `-a`) flag will simply print
the relevant item (log directory path or VM instance name).

For example, calling `xprofiler list` might give the following output:

```
LOG_PATH                                   NAME                                            ZONE
gs://example-bucket/my-other-profile-data  xprofiler-8187640b-e612-4c47-b4df-59a7fc86b253  us-central1-a
gs://example-bucket/my-profile-data        xprofiler-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef  us-central1-a
```

But calling with `xprofiler --abbrev list` will instead print out an abbreviated
form of the above output where each item is displayed on a new line:

```
xprofiler-8187640b-e612-4c47-b4df-59a7fc86b253
xprofiler-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef
```
