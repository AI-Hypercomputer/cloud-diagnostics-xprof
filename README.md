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
NAME                                            ZONE
xprofiler-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef  us-central1-a
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
NAME                                            ZONE
xprofiler-8187640b-e612-4c47-b4df-59a7fc86b253  us-central1-a
xprofiler-ev86r7c5-3d09-xb9b-a8e5-a495f5996eef  us-central1-a
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

