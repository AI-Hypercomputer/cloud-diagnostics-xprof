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

The `xprofiler` tool aims to simplify profiling experience for XLA workloads.
It provides an abstraction over profile sessions and manages
[`xprof` hosting](https://github.com/openxla/xprof) experience.
This includes allowing users to create and manage VM instances that
are preprovisioned with TensorBoard and latest profiling tools.

For more information about profiling with `xprof`, please see the `xprof`
[documentation](https://github.com/openxla/xprof/blob/master/docs/).

## Quickstart

These steps can be setup on user's workstation/cloudtop.

### Install Dependencies

`xprofiler` relies on using [gcloud](https://cloud.google.com/sdk).

The first step is to follow the documentation to [install](https://cloud.google.com/sdk/docs/install).

Running the initial `gcloud` setup will ensure things like your default project
ID are set.

```bash
gcloud init
gcloud auth login
```

### Setup cloud-diagnostic-xprof Package

Use a virtual environment (as best practice).

```bash
python3 -m venv venv
source venv/bin/activate

# Install package
pip install cloud-diagnostics-xprof

# Confirm installed with pip
pip show cloud-diagnostics-xprof

Name: cloud-diagnostics-xprof
Version: 0.0.9
Summary: Abstraction over profile session locations and infrastructure running the analysis.
Home-page: https://github.com/AI-Hypercomputer/cloud-diagnostics-xprof
Author: Author-email: Hypercompute Diagon <hypercompute-diagon@google.com>
```

### Permissions

`xprofiler` relies on project level IAM permissions.

* Users must have Compute User or Editor permissions on the project.
* `xprofiler` uses default compute user service account to access trace files
from GCS bucket. `<project-number>`-compute@developer.gserviceaccount.com should
have Storage Object User access on the target bucket.

### GCS Path Recommendations

`xprofiler` follows a path pattern to identify different profile sessions stored
in a bucket. This allows visualization of multiple profiling sessions using the
same `xprofiler` instance.

* For xprofiler capture command, use `gs://<bucket-name>/<run-name>` pattern.
* All files will be stored in `gs://<bucket-name>/<run-name>/tensorboard/plugin/profile/<session_id>`.
* For `xprofiler create` command, use `gs://<bucket-name>/<run-name>/tensorboard`
  pattern.

#### Examples of proper and improper GCS paths:

```bash
# Proper path (note forward slash at end is optional)
gs://my-bucket/main_directory/sub-a/sub-b/

# Proper path
gs://my_other_bucket/main_directory/sub-1/sub-2

# Improper path: does not start with gs://
my_other_bucket/main_directory/sub-1/sub-2
```

### Create `xprofiler` Instance

To create a `xprofiler` instance, you must provide a path to a GCS bucket and
zone. Project information will be retrieved from gcloud config.

```bash
ZONE="<some zone>"
GCS_PATH="gs://<some-bucket>/<some-run>/tensorboard"

xprofiler create -z $ZONE -l $GCS_PATH
```

When the command completes, you will see it return information about the
instance created, similar to below:

```
Waiting for instance to be created. It can take a few minutes.

Instance for gs://<some-bucket>/<some-run> has been created.
You can access it via following,
1. xprofiler connect -z <some zone> -l gs://<some-bucket>/<some-run> -m ssh
2. [Experimental (supports smaller files, < 200mb)] https://<id>-dot-us-<region>.notebooks.googleusercontent.com.
Instance is hosted at xprof-97db0ee6-93f6-46d4-b4c4-6d024b34a99f VM.
```

This will create a VM instance with xprofiler packages installed. The setup can
take up to a few minutes. The link above is shareable with anyone with IAM \
permissions.

By default, xprofiler instances will be hosted on a c4-highmem machine. Users
can also specify a machine type of their choice using the -m flag.

During `create`, Users will be prompted if they would like to create a second
instance for the same gcs path. Pressing anything but Y/y will exit the program.

```
$ xprofiler create -z <zone> -l gs://<some-bucket>/<some-run>/tensorboard

Instance for gs://<some-bucket>/<some-run>/tensorboard already exists.

Log_Directory                              URL                                                                  Name                                        Zone
-----------------------------------------  -------------------------------------------------------------------  ------------------------------------------  -------
gs://<some-bucket>/<some-run>/tensorboard  https://<id>-dot-us-<region>.notebooks.googleusercontent.com         xprof-97db0ee6-93f6-46d4-b4c4-6d024b34a99f  <zone>


Do you want to continue to create another instance with the same log directory? (y/n)
y
Waiting for instance to be created. It can take a few minutes.

Instance for gs://<some-bucket>/<some-run>/tensorboard has been created.
You can access it via following,
1. xprofiler connect -z <zone> -l gs://<some-bucket>/<some-run>/tensorboard -m ssh
2. [Experimental (supports smaller files, < 200mb)] https://<id>-dot-us-<region>.notebooks.googleusercontent.com.
Instance is hosted at xprof-<uuid> VM.
```

### Open `xprofiler` Instance

##### Using Proxy (Only supports small captures, less than 10sec)
Users can open created instances using the link from create output. This path
relies on a reverse proxy to expose the xprofiler backend. Users must have
valid IAM permissions.

> Note: Currently, This path can only support smaller trace files (<200 mb).

##### Using SSH Tunnel (Preferred for larger captures)

Users can connect to an instance by specifying a log_directory.

* Connect uses an SSH tunnel and users can open a localhost url from their
browsers.

>Note: `-z (--zone)` and `-l (--log_directory)` are mandatory arguments.

```
xprofiler connect -z $ZONE -l $GCS_PATH -m ssh

xprofiler instance can be accessed at http://localhost:6006.

```

### List `xprofiler` Instances

To list the `xprofiler` instances, you will need to specify a zone. Users can
optionally provide bucket information.

```bash
ZONE=us-central1-a

xprofiler list -z $ZONE
```
> Note: The `-z (--zones)` flag is not required but is highly recommended.
> If a zone is not provided, the command can take longer to search for all
> relevant VM instances.

This will output something like the following if there are instances matching
the list criteria:

```bash
Log_Directory                              URL                                                                  Name                                        Zone
-----------------------------------------  -------------------------------------------------------------------  ------------------------------------------  -------
gs://<some-bucket>/<some-run>/tensorboard  https://<id>-dot-us-<region>.notebooks.googleusercontent.com         xprof-97db0ee6-93f6-46d4-b4c4-6d024b34a99f  <zone>
gs://<some-bucket>/<some-run>/tensorboard  https://<id>-dot-us-<region>.notebooks.googleusercontent.com         xprof-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef  <zone>
```

Note you can specify the GCS bucket to get just that one associated instance:

```bash
xprofiler list -z $ZONE -l $GCS_PATH
```

### Delete `xprofiler` Instance

To delete an instance, you'll need to specify either the GCS bucket paths or the
VM instances' names. Specifying the zone is required.

```bash
# Delete by associated GCS path
xprofiler delete -z us-central1-b -l gs://<some-bucket>/<some-run>/tensorboard

Found 1 VM(s) to delete.
Log_Directory                              URL                                                                  Name                                        Zone
-----------------------------------------  -------------------------------------------------------------------  ------------------------------------------  -------
gs://<some-bucket>/<some-run>/tensorboard  https://<id>-dot-us-<region>.notebooks.googleusercontent.com         xprof-8187640b-e612-4c47-b4df-59a7fc86b253  <zone>

Do you want to continue to delete the VM `xprof-8187640b-e612-4c47-b4df-59a7fc86b253`?
Enter y/n: y
Will delete VM `xprof-8187640b-e612-4c47-b4df-59a7fc86b253`


# Delete by VM instance name
VM_NAME="xprof-8187640b-e612-4c47-b4df-59a7fc86b253"
xprofiler delete -z $ZONE --vm-name $VM_NAME
```

### Capture Profile

Users can capture profiles programmatically or manually.

##### Prerequisite - Enable collector
Users are required to enable the collector from their workloads following below
steps.
> Note: This is needed for both Programmatic and Manual captures.

```
# To enable from a jax workload
import jax
jax.profiler.start_server(9012)

# To enable from a pytorch workload
import torch_xla.debug.profiler as xp
server = xp.start_server(9012)

# To enable for tensorflow
import tensorflow.compat.v2 as tf2
tf2.profiler.experimental.server.start(9012)
```

Below links have some more information about the individual frameworks.

* [jax](https://docs.jax.dev/en/latest/profiling.html#manual-capture)
* [pytorch](https://cloud.google.com/tpu/docs/pytorch-xla-performance-profiling-tpu-vm#starting_the_profile_server)

##### Programmatic profile capture
Users can capture traces from their workloads by marking their code paths.
programmatic capture is more deterministic and gives more control to users.

```python
# jax
jax.profiler.start_trace("gs://<some_bucket>/<some_run>")
# Code to profile
#……….
jax.profiler.stop_trace()

# pytorch
xp.trace_detached(f"localhost:{9012}", "gs://<some_bucket>/<some_run>", duration_ms=2000)
# Using StepTrace
for step, (input, label) in enumerate(loader):
    with xp.StepTrace('train_step', step_num=step):
         # code to trace

# Using Trace
with xp.Trace('fwd_context'):
    # code to trace

# TensorFlow
tf.profiler.experimental.start("gs://<some_bucket>/<some_run>")
for step in range(num_steps):
  # Creates a trace event for each training step with the
  # step number.
  with tf.profiler.experimental.Trace("Train", step_num=step):
    train_fn()
tf.profiler.experimental.stop()
```

##### Manual profile capture
Users can trigger profile capture on target hosts using capture command.

###### GCE

* For jax, SDK requires tensorboard_plugin_profile package and the same must be
available on target VMs.
> Note: xprofiler uses gsutil to move files to GCS bucket from target VM. VMs
must have gcloud pre-installed.

```bash
# Trigger capture profile
xprofiler capture \
-z <zone> \
-l gs://<some-bucket>/<some-run> \
-f jax \ # jax or pytorch
-n vm_name1 vm_name2 vm_name3 \
-d 2000 # duration in ms

Starting profile capture on host vm_name1.
Profile saved to gs://<some-bucket>/<some-run>/tensorboard and session id is session_2025_04_03_18_13_49.

Starting profile capture on host vm_name2.
Profile saved to gs://<some-bucket>/<some-run>/tensorboard and session id is session_2025_04_03_18_13_49.
```

###### GKE

For GKE, Users are required to setup kubectl and cluster context on their
machines.

* Setup [kubectl](https://cloud.google.com/kubernetes-engine/docs/how-to/cluster-access-for-kubectl).

* Set current cluster context.

```bash
gcloud container clusters get-credentials <cluster_name> --region=<region>
```

subsequently, users can validate if current context is setup properly.

```bash
kubectl config current-context
gke_<project_id>_<region>_<cluster_name>
```

* Users can get a mapping between pods and nodes using `kubectl get pods`
command. For GKE, We can pass a list of pods to `xprofiler capture` command to
initiate profile capture.

```bash
$ kubectl get pods -o wide| awk '{print $1"\t\t"$7}'
```

> Note:For jax, SDK requires tensorboard_plugin_profile package and the same
must be available on target Pods.

> Note: Xprofiler uses gsutil to move files to GCS bucket from pod. Container
image must have gcloud pre-installed.

```bash
# Trigger capture profile
xprofiler capture \
-z <zone> \
-o gke \
-l gs://<some-bucket>/<some-run> \
-f jax \ # jax or pytorch \
-n pod_1 pod_2 pod_3 \
-d 2000 # duration in ms

Starting profile capture on pod_1.
Profile saved to gs://<some-bucket>/<some-run>/tensorboard and session id is session_2025_04_03_18_13_49.

Starting profile capture on pod_2.
Profile saved to gs://<some-bucket>/<some-run>/tensorboard and session id is session_2025_04_03_18_13_49.
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

> Note: that each subcommand has a `-h (--help)` flag that can give information
about that specific subcommand. For example: `xprofiler list -h`

### Subcommand: `xprofiler create`

This command is used to create a new VM instance for `xprofiler` to run with a
given profile log directory GCS path.

Usage details:

```
xprofiler create
  [--help]
  --log-directory GS_PATH
  --zone ZONE_NAME
  [--vm-name VM_NAME]
  [--machine-type MACHINE_TYPE]
  [--verbose]
```

#### `xprofiler create --help`

This provides the basic usage guide for the `xprofiler create` subcommand.

### Subcommand: `xprofiler list`

This command is used to list a VM instances created by the `xprofiler` tool.

Usage details:

```
xprofiler list
  [--help]
  [--zones ZONE_NAME [ZONE_NAME ...]]
  [--log-directory GS_PATH [GS_PATH ...]]
  [--filter FILTER_NAME [FILTER_NAME ...]]
  [--verbose]
```

#### `xprofiler list --help`

This provides the basic usage guide for the `xprofiler list` subcommand.

### Subcommand: `xprofiler delete`

This command is used to delete VM instances, focused on those created by the
`xprofiler` tool.

Usage details:

```
xprofiler delete
  [--help]
  --zone ZONE_NAME
  [--log-directory GS_PATH [GS_PATH ...]]
  [--vm-name VM_NAME [VM_NAME ...]]
  [--verbose]
```

#### `xprofiler delete --help`

This provides the basic usage guide for the `xprofiler delete` subcommand.

### Subcommand: `xprofiler capture`

Usage details:

```
xprofiler capture
  [--help]
  --log-directory GS_PATH
  --zone ZONE_NAME
  --hosts HOST_NAME [HOST_NAME ...]
  --framework FRAMEWORK
  [--orchestrator ORCHESTRATOR]
  [--duration DURATION]
  [--port LOCAL_PORT]
  [--verbose]
```

#### `xprofiler capture --help`

This provides the basic usage guide for the `xprofiler capture` subcommand.

#### `xprofiler connect --help`
```
xprofiler connect
  [--help]
  --log-directory GS_PATH
  --zone ZONE_NAME
  [--mode MODE]
  [--port LOCAL_PORT]
  [--host-port HOST_PORT]
  [--disconnect]
  [--verbose]
```

#### `xprofiler connect --help`

This provides the basic usage guide for the `xprofiler connect` subcommand.
