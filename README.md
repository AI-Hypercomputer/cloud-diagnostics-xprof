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
Waiting for instance to be created. It can take a few minutes.

Instance for gs://example-bucket/my-profile-data has been created.
You can access it at https://42rc2772e3vg2276-dot-us-central1.notebooks.googleusercontent.com
Instance is hosted at xprof-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef VM.
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
Log_Directory                                 URL                                                                       Name
-----------------------------------------  ------------------------------------------------------------------------  ------------------------------------------
gs://example-bucket/my-other-profile-data  https://27ac8347d8af0142-dot-us-central1.notebooks.googleusercontent.com  xprof-8187640b-e612-4c47-b4df-59a7fc86b253
gs://example-bucket/my-profile-data        https://42rc2772e3vg2276-dot-us-central1.notebooks.googleusercontent.com  xprof-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef
```

Note you can specify the GCS bucket to get just that one associated instance:

```bash
xprofiler list -l $GCS_PATH
```

### Delete VM Instance

To delete an instance, you'll need to specify either the GCS bucket paths or the
VM instances' names. Specifying the zone is required.

```bash
# Delete by associated GCS path
xprofiler delete -z $ZONE -l $GCS_PATH

# Delete by VM instance name
VM_NAME="xprof-8187640b-e612-4c47-b4df-59a7fc86b253"
xprofiler delete -z $ZONE --vm-name $VM_NAME
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
gs://example-bucket/my-other-profile-data  xprof-8187640b-e612-4c47-b4df-59a7fc86b253  us-central1-a
gs://example-bucket/my-profile-data        xprof-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef  us-central1-a
```

But calling with `xprofiler --abbrev list` will instead print out an abbreviated
form of the above output where each item is displayed on a new line:

```
xprof-8187640b-e612-4c47-b4df-59a7fc86b253
xprof-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef
```

### Subcommand: `xprofiler create`

This command is used to create a new VM instance for TensorBoard to run with a
given profile log directory GCS path.

Usage details:

```
xprofiler create
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
gs://example-bucket/my-profile-data xprof-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef  us-central1-a
```

If the [xprofiler abbreviation flag](#xprofiler-abbrev-) is used, then an
abbreviated output is given like so:

```
xprof-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef
```

#### `xprofiler create --help`

This provides the basic usage guide for the `xprofiler create` subcommand.

#### Creating a VM Instance

To create a new VM instance, a user _must_ specify a profile log directory path
(a GCS path) as in `xprofiler create -l gs://example-bucket/my-profile-data`.
This will create a VM instance associated with the log directory. The instance
will also have TensorBoard installed and setup ready for use.

> Note that after the VM creation, it might take a few minutes for the VM
> instance to fully be ready (installing dependencies, launching TensorBoard,
> etc.)

It is recommended to also provide a zone with `--zone` or `-z` but it is
optional.

By default, the VM instance's name will be uniquely created prepended with
`xprof-`. However, this can be specified with the `--vm-name` or `-n` flag
to give a specific name to the newly created VM.

Lastly, there is a `--verbose` or `-v` flag that will provide information as the
`xprofiler create` subcommand runs.

### Subcommand: `xprofiler list`

This command is used to list a VM instances created by the `xprofiler` tool.

Usage details:

```
xprofiler list
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
gs://example-bucket/my-other-profile-data  xprof-8187640b-e612-4c47-b4df-59a7fc86b253  us-central1-a
gs://example-bucket/my-profile-data        xprof-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef  us-central1-a
```

If the [xprofiler abbreviation flag](#xprofiler-abbrev-) is used, then an
abbreviated output is given like so:

```
xprof-8187640b-e612-4c47-b4df-59a7fc86b253
xprof-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef
```

#### `xprofiler list --help`

This provides the basic usage guide for the `xprofiler list` subcommand.

#### Listing Specific Subsets

Note that the `xprofiler list` command will default to listing all VM instances
that have the prefix `xprof`.

However, a specific subset of VM instances can be returned using different
options.

##### Providing Zone

`xprofiler list -z $ZONE`

Providing the zone is highly recommended since otherwise the command can take a
while to search for all relevant VM instances.

##### Providing GCS Path (Profile Log Directory)

Since `xprofiler list` is meant to look for VM instances created with
`xprofiler`, it is likely the VM instance of interest is associated with a
profile log directory.

To filter for a specific VM instance with an associated log directory, simply
use the command like so:

```bash
xprofiler list -l $GS_PATH
```

You can even use multiple log directory paths to find any VMs associated with
any of these paths:

```bash
xprofiler list -l $GS_PATH_0 $GS_PATH_1 $GS_PATH_2
```

### Subcommand: `xprofiler delete`

This command is used to delete VM instances, focused on those created by the
`xprofiler` tool.

Usage details:

```
xprofiler list
  [--help]
  [--log-directory GS_PATH [GS_PATH ...]]
  [--vm-name VM_NAME [VM_NAME ...]]
  [--zone ZONE_NAME]
  [--verbose]
```

During execution of the delete command, it will prompt the user to confirm each
VM to be deleted. (Note the VMs _will not_ be deleted until after confirming or
rejecting deletion for each VM.) Output looks similar to the example below:

```
Found 2 VM(s) to delete.

Log_Directory                              URL                                                                       Name
-----------------------------------------  ------------------------------------------------------------------------  ----------------------------------------------
gs://example-bucket/my-data               https://78700cq71a7f967e-dot-us-central1.notebooks.googleusercontent.com  xprof-8187640b-e612-4c47-b4df-59a7fc86b253
gs://example-bucket/my-data/sub-directory https://7q639a14v4278d50-dot-us-central1.notebooks.googleusercontent.com  xprof-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef

Do you want to continue to delete the VM `xprof-8187640b-e612-4c47-b4df-59a7fc86b253`?
Enter y/n: y

Do you want to continue to delete the VM `xprof-8187640b-e612-4c47-b4df-59a7fc86b253`?
Enter y/n: y

Do you want to continue to delete the VM `xprof-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef`?
Enter y/n: n
Will NOT delete VM `xprof-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef`
```

#### `xprofiler delete --help`

This provides the basic usage guide for the `xprofiler delete` subcommand.

##### Providing Zone

`xprofiler delete -z $ZONE`

Providing the zone is required since otherwise the command can take a
while to search for all relevant VM instances that are to be deleted.

##### Providing GCS Path (Profile Log Directory)

Since `xprofiler delete` is meant to delete VM instances created with
`xprofiler`, it is likely the VM instance of interest is associated with a
profile log directory.

To filter for a specific VM instance with an associated log directory, simply
use the command like so:

```bash
xprofiler delete -z $ZONE -l $GS_PATH
```

You can even use multiple log directory paths to find any VMs associated with
any of these paths:

```bash
xprofiler delete -z $ZONE -l $GS_PATH_0 $GS_PATH_1 $GS_PATH_2
```

> NOTE: The [log directory](#providing-gcs-path-profile-log-directory-2) and/or
> [VM name](#providing-vm-instance-names) must be specified.

##### Providing VM Instance Names

Thought the primary method of deletion will likely center around VM instances
created with `xprofiler`, it is sometimes convenient to delete VM instances by
their name instead of an associated log directory.

```bash
xprofiler delete -z $ZONE --vm-name $VM_NAME $VM_NAME_1
```

This can also take in multiple VM instances to be deleted:

```bash
xprofiler delete -z $ZONE --vm-name $VM_NAME_0 $VM_NAME_1 $VM_NAME_2
```

Finally, this option can also be used with specifying log directories:

```bash
xprofiler delete -z $ZONE -l $GS_PATH --vm-name $VM_NAME_0 $VM_NAME_1 $VM_NAME_2
```

> NOTE: The [log directory](#providing-gcs-path-profile-log-directory-2) and/or
> [VM name](#providing-vm-instance-names) must be specified.