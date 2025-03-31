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
# xprof

The `xprof` SDK and CLI tool provides abstraction over profile session
locations and infrastructure running the analysis.

This includes allowing users to create and manage VM instances for TensorBoard
instances in regards to profiling workloads for GPU and TPU.

## Quickstart

### Install Dependencies

`xprof` relies on using [gcloud](https://cloud.google.com/sdk).

The first step is to follow the documentation to [install](https://cloud.google.com/sdk/docs/install).

Running the initial `gcloud` setup will ensure things like your default project
ID are set.

### Create a VM Instance for TensorBoard

To create a TensorBoard instance, you must provide a path to a GCS bucket.
It is also useful to define your specific zone.

```bash
ZONE=us-central1-a
GCS_PATH="gs://example-bucket/my-profile-data"

xprof create -z $ZONE -l $GCS_PATH
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

To list the TensorBoard instances created by `xprof`, you can simply run
`xprof list`. However, it's recommended to specify the zone (though not
required).

```bash
ZONE=us-central1-a

xprof list -z $ZONE
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
xprof list -l $GCS_PATH
```

### Delete VM Instance

To delete an instance, you'll need to specify either the GCS bucket paths or the
VM instances' names. Specifying the zone is required.

```bash
# Delete by associated GCS path
xprof delete -z $ZONE -l $GCS_PATH

# Delete by VM instance name
VM_NAME="xprofiler-8187640b-e612-4c47-b4df-59a7fc86b253"
xprof delete -z $ZONE --vm-name $VM_NAME
```

## Details on `xprof`

### Main Command: `xprof`

The `xprof` command has additional subcommands that can be invoked to
[create](#subcommand-xprof-create) VM instances,
[list](#subcommand-xprof-list) VM instances,
[delete](#subcommand-xprof-delete) instances, etc.
However, the main `xprof` command has some additional options without
invoking a subcommand.

#### `xprof --help`

Gives additional information about using the command including flag options and
available subcommands. Also can be called with `xprof -h`.

> Note that each subcommand has a `--help` flag that can give information about
> that specific subcommand. For example: `xprof list --help`

#### `xprof --abbrev ...`

When invoking a subcommand, typically there is output related to VM instances
involved with the subcommand, usually as a detailed table.

In some cases, a user may only want the relevant information (for example a log
directory GCS path or VM name instance). This can be particularly useful in
scripting with `xprof` by chaining with other commands.

To assist with this, the `--abbrev` (or equivalent `-a`) flag will simply print
the relevant item (log directory path or VM instance name).

For example, calling `xprof list` might give the following output:

```
LOG_PATH                                   NAME                                            ZONE
gs://example-bucket/my-other-profile-data  xprofiler-8187640b-e612-4c47-b4df-59a7fc86b253  us-central1-a
gs://example-bucket/my-profile-data        xprofiler-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef  us-central1-a
```

But calling with `xprof --abbrev list` will instead print out an abbreviated
form of the above output where each item is displayed on a new line:

```
xprofiler-8187640b-e612-4c47-b4df-59a7fc86b253
xprofiler-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef
```

### Subcommand: `xprof create`

This command is used to create a new VM instance for TensorBoard to run with a
given profile log directory GCS path.

Usage details:

```
xprof create
  [--help]
  --log-directory GS_PATH
  [--zone ZONE_NAME]
  [--vm-name VM_NAME]
  [--verbose]
```

At the successful completion of this command, the information regarding the
newly created VM instances is printed out like the example below:

```
LOG_PATH                            NAME                                            ZONE
gs://example-bucket/my-profile-data xprofiler-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef  us-central1-a
```

If the [xprof abbreviation flag](#xprof-abbrev) is used, then an
abbreviated output is given like so:

```
xprofiler-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef
```

#### `xprof create --help`

This provides the basic usage guide for the `xprof create` subcommand.

#### Creating a VM Instance

To create a new VM instance, a user _must_ specify a profile log directory path
(a GCS path) as in `xprof create -l gs://example-bucket/my-profile-data`.
This will create a VM instance associated with the log directory. The instance
will also have TensorBoard installed and setup ready for use.

> Note that after the VM creation, it might take a few minutes for the VM
> instance to fully be ready (installing dependencies, launching TensorBoard,
> etc.)

It is recommended to also provide a zone with `--zone` or `-z` but it is
optional.

By default, the VM instance's name will be uniquely created prepended with
`xprofiler-`. However, this can be specified with the `--vm-name` or `-n` flag
to give a specific name to the newly created VM.

Lastly, there is a `--verbose` or `-v` flag that will provide information as the
`xprof create` subcommand runs.

### Subcommand: `xprof list`

This command is used to list a VM instances created by the xprof tool.

Usage details:

```
xprof list
  [--help]
  [--zone ZONE_NAME]
  [--log-directory GS_PATH [GS_PATH ...]]
  [--filter FILTER_NAME [FILTER_NAME ...]]
  [--verbose]
```

At the successful completion of this command, the information of matching VM
instances is printed out like the example below:

```
LOG_PATH                                   NAME                                            ZONE
gs://example-bucket/my-other-profile-data  xprofiler-8187640b-e612-4c47-b4df-59a7fc86b253  us-central1-a
gs://example-bucket/my-profile-data        xprofiler-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef  us-central1-a
```

If the [xprof abbreviation flag](#xprof-abbrev-) is used, then an
abbreviated output is given like so:

```
xprofiler-8187640b-e612-4c47-b4df-59a7fc86b253
xprofiler-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef
```

#### `xprof list --help`

This provides the basic usage guide for the `xprof list` subcommand.

#### Listing Specific Subsets

Note that the `xprof list` command will default to listing all VM instances
that have the prefix `xprof`.

However, a specific subset of VM instances can be returned using different
options.

##### Providing Zone

`xprof list -z $ZONE`

Providing the zone is highly recommended since otherwise the command can take a
while to search for all relevant VM instances.

##### Providing GCS Path (Profile Log Directory)

Since `xprof list` is meant to look for VM instances created with
`xprof`, it is likely the VM instance of interest is associated with a
profile log directory.

To filter for a specific VM instance with an associated log directory, simply
use the command like so:

```bash
xprof list -l $GS_PATH
```

You can even use multiple log directory paths to find any VMs associated with
any of these paths:

```bash
xprof list -l $GS_PATH_0 $GS_PATH_1 $GS_PATH_2
```
