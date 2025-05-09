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

### Recommendations

#### GCS Paths

`xprofiler` follows a path pattern to identify different profile sessions stored
in a bucket. This allows visualization of multiple profiling sessions using the
same `xprofiler` instance.

* For xprofiler capture command, use `gs://<bucket-name>/<run-name>` pattern.
* All files will be stored in
  `gs://<bucket-name>/<run-name>/tensorboard/plugin/profile/<session_id>`.
* For `xprofiler create` command, use
  `gs://<bucket-name>/<run-name>/tensorboard` pattern.

##### Examples of proper and improper GCS paths:

```bash
# Proper path (note forward slash at end is optional)
gs://my-bucket/main_directory/sub-a/sub-b/

# Proper path
gs://my_other_bucket/main_directory/sub-1/sub-2

# Improper path: does not start with gs://
my_other_bucket/main_directory/sub-1/sub-2
```

#### Machine Types

During creation, the VM machine type can be specified. By default the machine
type is `c4-highmem-8` which should be sufficient for most profile sizes.

However, users may choose a smaller or larger performance machine based on their
profile sizes and/or cost. For relatively small profiles (<100MB), users may
wish to go down to an `e2-highmem-4` machine. For larger profiles, users may
want to use a more powerful machine type like a `c4-highmem-32`.

Overall, we recommend a
[general purpose machine type](https://cloud.google.com/compute/docs/general-purpose-machines)
though users are welcome to specify other machine types. A list of machine types
are listed here: https://cloud.google.com/compute/docs/machine-resource

For more information about `xprofiler create` and machine types, see more
details in the [section below](#xprofiler-create-machine-type) on
`xprofiler create --machine-type`.

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
take up to a few minutes. The link above is shareable with anyone with IAM
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

> Note: `-z (--zone)` and `-l (--log_directory)` are mandatory arguments.

```
xprofiler connect -z $ZONE -l $GCS_PATH -m ssh

xprofiler instance can be accessed at http://localhost:6006.

```

### List `xprofiler` Instances

To list the `xprofiler` instances, you will need to specify a zone. Users can
optionally provide bucket information and/or VM instance names.

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

Note you can specify one or more GCS bucket paths and/or VM instance names to
get any VMs associated with the criteria provided. This will list any VMs
associated with the log directories or VM names specified.
(See [section](#optionally-specifying-log-directories-andor-vm-names) below for
more details.)

```bash
# Specifying one GCS path
xprofiler list -z $ZONE -l $GCS_PATH

# Specifying one VM instance name
xprofiler list -z $ZONE --vm-name $VM_NAME
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

##### Prerequisite: Enable Collector

Users are required to enable the collector from their workloads following below
steps.
> Note: This is needed for both Programmatic and Manual captures.

```python
# To enable for a jax workload
import jax
jax.profiler.start_server(9012)

# To enable for a pytorch workload
import torch_xla.debug.profiler as xp
server = xp.start_server(9012)

# To enable for tensorflow workload
import tensorflow.compat.v2 as tf2
tf2.profiler.experimental.server.start(9012)
```

Below links have some more information about the individual frameworks:

* [JAX](https://docs.jax.dev/en/latest/profiling.html#manual-capture)
* [PyTorch](https://cloud.google.com/tpu/docs/pytorch-xla-performance-profiling-tpu-vm#starting_the_profile_server)

##### Programmatic Profile Capture

Users can capture traces from their workloads by marking their code paths.
Programmatic capture is more deterministic and gives more control to users.

> Note: The code snippets below assume that code in the earlier
> [prerequisite section](#prerequisite-enable-collector)

###### JAX Profile Capture

```python
jax.profiler.start_trace("gs://<some_bucket>/<some_run>")
# Code to profile
...
jax.profiler.stop_trace()
```

###### PyTorch Profile Capture

```python
xp.trace_detached(f"localhost:{9012}", "gs://<some_bucket>/<some_run>", duration_ms=2000)

# Using StepTrace
for step, (input, label) in enumerate(loader):
  with xp.StepTrace('train_step', step_num=step):
    # code to trace
    ...
```

Alternatively, wrap individual parts of the code with `xp.Trace`:

```python
# Using Trace
with xp.Trace('fwd_context'):
    # code to trace
    ...
```

###### TensorFlow Profile Capture

```python
tf.profiler.experimental.start("gs://<some_bucket>/<some_run>")
for step in range(num_steps):
  # Creates a trace event for each training step with the step number
  with tf.profiler.experimental.Trace("Train", step_num=step):
    train_fn()
tf.profiler.experimental.stop()
```

##### Manual Profile Capture

Users can also trigger profile capture on target hosts. There are two methods to
do this:

* Using the `xprofiler capture` command
  - For [GCE](#profile-capture-via-xprofiler-gce) workloads
  - For [GKE](#profile-capture-via-xprofiler-gke) workloads
* Using [TensorBoard's UI](#profile-capture-via-tensorboard-ui)

###### Profile Capture via TensorBoard UI

Users have the option to trigger a profile capture using TensorBoard's UI.

First, visit the proxy URL for a VM instance (created via `xprofiler`) to visit
the TensorBoard UI. Which will bring you to one of two pages.

**Scenario 1: GCS Has Profile Data**

If the GCS log directory associated with the VM instance has profile data
already available, you'll likely see a page similar to this with profile runs
ready to view:

![TensorBoard UI on profile tab](https://raw.githubusercontent.com/AI-Hypercomputer/cloud-diagnostics-xprof/refs/heads/main/docs/images/tensorboard-ui-profile-tab-with-profiles.png)

Notice the "CAPTURE PROFILE" button on the dashboard. You'll want to click that
& proceed with the next section on completing this form to capture profile data.

**Scenario 2: GCS Has No Profile Data**

You may see a similar page to this one with no dashboards if the GCS log
directory does not yet have any profile data:

![TensorBoard UI that is blank with message on dashboards](https://raw.githubusercontent.com/AI-Hypercomputer/cloud-diagnostics-xprof/refs/heads/main/docs/images/tensorboard-ui-with-no-profiles.png)

You will then need to select the profile tab:

![TensorBoard UI with upper-right dropdown menu selecting "Profile"](https://raw.githubusercontent.com/AI-Hypercomputer/cloud-diagnostics-xprof/refs/heads/main/docs/images/tensorboard-ui-with-no-profiles-dropdown-on-profile.png)

You'll then see a page similar to this one with a "CAPTURE PROFILE" button:

![TensorBoard UI that is blank with message on profiling](https://raw.githubusercontent.com/AI-Hypercomputer/cloud-diagnostics-xprof/refs/heads/main/docs/images/tensorboard-ui-profile-tab-with-profiles.png)

You want to click the "CAPTURE PROFILE" button which will bring up a form to
fill. Proceed to the next section for details in completing this form to capture
profile data.

**Completing Form for Profile Capture**

In either case from above, you should see a similar form to fill to capture
profile data:

![Incomplete form for TensorBoard UI profile capture](https://raw.githubusercontent.com/AI-Hypercomputer/cloud-diagnostics-xprof/refs/heads/main/docs/images/tensorboard-ui-capture-profile-form-incomplete.png)

You will need to minimally provide the "Profile Service URL(s)" for the TPU VM
instance.

> Note:
> The instructions refer to the TPU VM that is _running_ the workload to
> profile and ***NOT*** the `xprofiler` VM instance.

You will need the full hostname for the TPU & port number
with the following format:

```
<TPU_VM_HOSTNAME>.<ZONE>.c.<GCP_PROJECT_NAME>.internal:<PORT_NUMBER>
```

* `TPU_VM_HOSTNAME`: This is different from the TPU name and refers to the host
  that the workload is running on.
  You can retrieve the hostname using `gcloud` by providing the TPU VM name and
  TPU's the zone:
  `gcloud compute tpus tpu-vm ssh $TPU_NAME  --zone=$ZONE --command="hostname"`
* `ZONE`: This is the zone of the TPU VM. Note that it is ***NOT** necessarily
  the same as the `xprofiler` VM instance that is displaying TensorBoard.
* `GCP_PROJECT_NAME`: This is the project name for the TPU VM.
  Note that it is ***NOT** necessarily the same as the `xprofiler` VM instance
  that is displaying TensorBoard. However, it likely will need to be since
  having the TPU in a different project will likely lead to permission issues,
  preventing profile capture.
* `PORT_NUMBER`: This is the port that was set when starting the profile server
  in the relevant code.
  See earlier [prerequisite section](#prerequisite-enable-collector).

For example, your string will look similar to this:

```
t1v-n-g8675e3i-w-0.us-east5-b.c.my-project.internal:9012
```

You can then adjust any of the other settings you care to modify and click
"CAPTURE".

![Complete form for TensorBoard UI profile capture](https://raw.githubusercontent.com/AI-Hypercomputer/cloud-diagnostics-xprof/refs/heads/main/docs/images/tensorboard-ui-capture-profile-form-complete.png)

You will see a loading animation and then a message at the bottom of the screen.

If successful, you will see a message similar to this:

![Successful capture for TensorBoard UI profile capture](https://raw.githubusercontent.com/AI-Hypercomputer/cloud-diagnostics-xprof/refs/heads/main/docs/images/tensorboard-ui-capture-profile-message-success.png)

If something went wrong you might see something similar to this:

![Failed capture for TensorBoard UI profile capture](https://raw.githubusercontent.com/AI-Hypercomputer/cloud-diagnostics-xprof/refs/heads/main/docs/images/tensorboard-ui-capture-profile-message-failure.png)

You can attempt the capture again, ensuring your settings in the form are
correct. You may also need to confirm the TPU workload is running and properly
configured for profiling.

> Note:
> After a successful capture, you might need to refresh the dashboard.
> You can hit the refresh icon for a single refresh or go to the settings menu
> (the gear icon) and set "Reload data" automatically.

###### Profile Capture via `xprofiler`: GCE

For JAX, `xprofiler` requires the
[tensorboard-plugin-profile](https://pypi.org/project/tensorboard-plugin-profile)
package and must also be available on target VMs.

> Note: `xprofiler` uses `gsutil` to move files to GCS bucket from target VM.
> VMs must have `gcloud` pre-installed.

```bash
# Trigger capture profile
# Framework can be jax or pytorch
xprofiler capture \
  -z <zone> \
  -l gs://<some-bucket>/<some-run> \
  -f jax \
  -n vm_name1 vm_name2 vm_name3 \
  -d 2000 # duration in ms

Starting profile capture on host vm_name1.
Profile saved to gs://<some-bucket>/<some-run>/tensorboard and session id is session_2025_04_03_18_13_49.

Starting profile capture on host vm_name2.
Profile saved to gs://<some-bucket>/<some-run>/tensorboard and session id is session_2025_04_03_18_13_49.
```

###### Profile Capture via `xprofiler`: GKE

For GKE, users are required to setup `kubectl` and cluster context on their
machines. (See details on setting up
[kubectl](https://cloud.google.com/kubernetes-engine/docs/how-to/cluster-access-for-kubectl).)

```bash
gcloud container clusters get-credentials <cluster_name> --region=<region>
```

After setting up credentials, users can verify the current context:

```bash
kubectl config current-context
gke_<project_id>_<region>_<cluster_name>
```

Users can then get a mapping between pods and nodes using the `kubectl get pods`
command:

```bash
$ kubectl get pods -o wide| awk '{print $1"\t\t"$7}'
```

For GKE, users can then pass a list of pods to `xprofiler capture` command to
initiate profile capture.

```bash
# Trigger capture profile
# Framework can be jax or pytorch
xprofiler capture \
  -z <zone> \
  -o gke \
  -l gs://<some-bucket>/<some-run> \
  -f jax
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

> Note: Each subcommand has a `-h (--help)` flag that can give information
about that specific subcommand. For example: `xprofiler list -h`

### Subcommand: `xprofiler create`

This command is used to create a new VM instance for `xprofiler` to run with a
given profile log directory GCS path.

`xprofiler create` will return an error if the machine type given is not found
in the provided zone. Note that the error message will include a `gcloud`
command that can be used to determine a zone with the given machine type.

Usage details:

```
xprofiler create
  [--help]
  --log-directory GS_PATH
  --zone ZONE_NAME
  [--vm-name VM_NAME]
  [--machine-type MACHINE_TYPE]
  [--auto-delete-on-failure-off]
  [--verbose]
```

#### `xprofiler create --help`

This provides the basic usage guide for the `xprofiler create` subcommand.

#### `xprofiler create --machine-type`

The `create` command defaults to using `c4-highmem-8` for the VM instance.
However, users can specify a different machine type using the flag
`--machine-type` followed by a machine type such as `e2-highmem-8`. Information
on machine types can be found
[here](https://cloud.google.com/compute/docs/machine-resource). Also see
our [recommendations for `xprofiler`](#machine-types)

Note that if a machine type is not found for the given zone, an error will occur
with a suggestion for running a `gcloud` command as well as some available zones
for that machine type.

The output will look similar to this:

```bash
Please check the machine type w/ us-east5-c and try again. You can investigate zones with the machine type victors-discount-vm available:
gcloud compute machine-types list --filter="name=victors-discount-vm" --format="value(zone)"
The machine type and zone do not match.
Suggested zones with machine type victors-discount-vm available:
['us-central1-a', 'us-central1-b', 'us-central1-c', 'us-central1-f', 'europe-west1-b', 'europe-west1-c', 'europe-west1-d', 'us-west1-a', 'us-west1-b', 'us-west1-c']
```

#### `xprofiler create --auto-delete-on-failure-off`

The `create` command will automatically delete failed VM instances created by
the `xprofiler` tool. This is to ensure that a malformed VM does not persist if
it can't be fully utilized by `xprofiler`.

However, it can optionally turn off automatic deletion using the
`--auto-delete-on-failure-off` flag. This can be particularly useful in
debugging issues when creating VMs.

### Subcommand: `xprofiler list`

This command is used to list a VM instances created by the `xprofiler` tool.

Usage details:

```
xprofiler list
  [--help]
  [--zones ZONE_NAME [ZONE_NAME ...]]
  [--log-directory GS_PATH [GS_PATH ...]]
  [--vm-name VM_NAME [VM_NAME ...]]
  [--filter FILTER_NAME [FILTER_NAME ...]]
  [--verbose]
```

#### `xprofiler list --help`

This provides the basic usage guide for the `xprofiler list` subcommand.

#### `xprofiler list --zones`

The `list` subcommand can optionally take a `-z (--zones)` flag to specify which
zones to consider for listing VMs.

```bash
# Listing all xprofiler VMs in us-central1-a
xprofiler list -z us-central1-a

# Listing all xprofiler VMs in us-east5-a and us-central1-a
xprofiler list -z us-east5-a us-central1-a
```

If no value for the zones is provided, then `xprofiler list` will search across
all zones with any other matching criteria in mind. This however, can
potentially take significantly more time so it is recommended to specify the
zone(s) explicitly.

#### Optionally specifying log directories and/or VM names

Users optionally can specify one or more log directories (GCS paths) and/or VM
names. This can be done with the `-l (--log-directory)` flag for log directories
and with the `-n (--vm-name)` flag for VM instance names.

When specifying multiple criteria, any matching VM will be listed.

Examples:

```bash
# List VMs that match either GCS path
xprofiler list -l gs://bucket0/top-dir gs://bucket1/top-dir


# List VMs that match either VM name
xprofiler list -n my-vm-one my-vm-two


# List VMs that match any of the GCS paths or VM names
xprofiler list \
  -l gs://bucket0/top-dir gs://bucket1/top-dir \
  -n my-vm-one my-vm-two
```

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
