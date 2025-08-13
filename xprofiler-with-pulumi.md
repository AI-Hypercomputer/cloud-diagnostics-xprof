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
Below sample snipped to setup Xprofiler on Kubernetes by Pulumi:

```python

"""Xprofiler GKE Pulumi Snippet

This is sample code, adjust before usage.

This snipped provision Kubernetes components to run Self-Service Xprofiler
(Tensorboard Web UI) in auto scale mode by Pulumi. Snippet will create all
required components, properly wait setup and output URL to access Tensorboard
Web UI. Kubernetes cluster and log diretory for Tensorboard must created
outside.

Kubernets components:
- Tensorboard Deployment
- Tensorboard Service (to balance traffic)
- Proxy Deployment (entry point for Tensorboard Web UI)
- Proxy Service
- HorizontalPodAutoscaler (auto scale Tensorboard from 1 to 36 pods)
"""

import pulumi
from pulumi_kubernetes.apps.v1 import Deployment
from pulumi_kubernetes.autoscaling.v1 import HorizontalPodAutoscaler
from pulumi_kubernetes.core.v1 import ContainerPortArgs
from pulumi_kubernetes.core.v1 import Service


# User settings ----------------------------------------------------------------

# Path to log directory.
log_directory = (
    "gs://yujunzou-dev-supercomputer-testing/terma-self-service-gke-testing"
)
# Region where kubernetes cluster will be deployed.
region = "us-central1"
# Kubernetes namespace where all resources will be provisioned.
namespace = "xprofiler"
# Service account name to be used for Pods to access log directory.
service_account_name = "xprofiler"

# Dependencies -----------------------------------------------------------------

# Tensorboard image.
tensorboard_image = "us-central1-docker.pkg.dev/deeplearning-images/reproducibility/xprofiler:tb-plugin-2.20.4"

# Internal configuration -------------------------------------------------------

app_label = "xprofiler"
pod_port = 9001

# Components -------------------------------------------------------------------

tb_deployment = Deployment(
    "tb",
    metadata={"namespace": namespace, "labels": {"app": app_label}},
    spec={
        "selector": {
            "match_labels": {"role": "xprofiler-tb", "app": app_label}
        },
        "template": {
            "metadata": {"labels": {"role": "xprofiler-tb", "app": app_label}},
            "spec": {
                "service_account_name": service_account_name,
                "containers": [{
                    "name": "tensorboard",
                    "image": tensorboard_image,
                    "args": [
                        "tensorboard",
                        "--logdir=" + log_directory,
                        "--bind_all",
                        "--port=" + str(pod_port),
                        "--verbosity=0",  # INFO level
                    ],
                    "ports": [ContainerPortArgs(container_port=pod_port)],
                    "resources": {"limits": {"cpu": "1000m"}},
                }],
            },
        },
    },
)

tb_service = Service(
    "tb-service",
    metadata={"namespace": namespace, "labels": {"app": app_label}},
    spec={
        "selector": {"role": "xprofiler-tb", "app": app_label},
        "ports": [{"protocol": "TCP", "port": 80, "target_port": pod_port}],
    },
)

proxy_init_container_script = [
    "/bin/bash",
    "-c",
    f"""
        echo "INFO: Getting kubectl..."
        apt-get install -y kubectl

        # TODO replace with variable
        REGION="us-east5"
        CONFIG_DIR="/tmp/configs"
        CONFIG_FILE="${{CONFIG_DIR}}/proxy-agent-config.json"
        ENV_FILE="${{CONFIG_DIR}}/proxy.txt"
        echo "Creating config directory."
        mkdir -p ${{CONFIG_DIR}}

        echo "INFO: Copying proxy agent config from GCS..."
        gcloud storage cp gs://dl-platform-public-configs/proxy-agent-config.json ${{CONFIG_FILE}}

        echo "INFO: Extracting proxy URL for region: ${{REGION}}"
        PROXY_URL=$(python3 -c "import json; print(json.load(open('${{CONFIG_FILE}}'))['agent-docker-containers']['latest']['proxy-urls']['${{REGION}}'][0])")
        if [ -z "${{PROXY_URL}}" ]; then
          echo "ERROR: Could not find proxy URL for region ${{REGION}}." >&2
          exit 1
        fi
        echo "INFO: Proxy URL: ${{PROXY_URL}}"

        VM_ID=$(curl --fail -s -H 'Metadata-Flavor: Google' "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?format=full&audience=${{PROXY_URL}}/request-endpoint")
        echo "VM_ID: ${{VM_ID}}"

        ACCESS_TOKEN=$(gcloud auth print-access-token)
        RESULT_JSON=$(curl --fail -s -H "Authorization: Bearer ${{ACCESS_TOKEN}}" -H "X-Inverting-Proxy-VM-ID: ${{VM_ID}}" -d "" "${{PROXY_URL}}/request-endpoint")
        echo "RESULT_JSON: ${{RESULT_JSON}}"

        BACKEND_ID=$(echo "${{RESULT_JSON}}" | python3 -c "import json, sys; print(json.load(sys.stdin)['backendID'])")
        echo "BACKEND_ID: ${{BACKEND_ID}}"
        HOSTNAME=$(echo "${{RESULT_JSON}}" | python3 -c "import json, sys; print(json.load(sys.stdin)['hostname'])")
        echo "HOSTNAME: ${{HOSTNAME}}"

        EXTERNAL_PROXY_URL="https://${{HOSTNAME}}"
        echo "INFO: Applying annotation 'proxy-url=${{EXTERNAL_PROXY_URL}}'..."
        kubectl annotate service "<tb_service_name>" --namespace "{namespace}" "proxy-url=${{EXTERNAL_PROXY_URL}}" --overwrite

        echo "Proxy will be available at: ${{EXTERNAL_PROXY_URL}}"
        echo "SUCCESS: Init container finished."

        echo "TB service host <tb_service_host_var>=${{<tb_service_host_var>}}"

        {{
         echo "export PROXY='${{PROXY_URL}}/'"
         echo "export BACKEND_ID='${{BACKEND_ID}}'"
         echo "export HOSTNAME='${{<tb_service_host_var>}}:80'"
         echo "export SHIM_WEBSOCKETS='true'"
         echo "export SHIM_PATH='websocket-shim'"
        }} > ${{ENV_FILE}}
""",
]

proxy_agent_container_script = [
    "/bin/bash",
    "-c",
    """source /tmp/configs/proxy.txt

        exec /opt/bin/proxy-forwarding-agent \
         "--backend=${BACKEND_ID}" \
         "--proxy=${PROXY}" \
         "--host=${HOSTNAME}" \
         "--shim-websockets=${SHIM_WEBSOCKETS}" \
         "--shim-path=${SHIM_PATH}"
""",
]


def tb_service_env(args):
  generated_name = args[0].upper().replace("-", "_") + "_SERVICE_HOST"
  array = proxy_init_container_script
  array[2] = (
      array[2]
      .replace("<tb_service_host_var>", generated_name)
      .replace("<tb_service_name>", args[0])
  )
  return array


proxy_deployment = Deployment(
    "proxy",
    api_version="apps/v1",
    metadata={"namespace": namespace, "labels": {"app": app_label}},
    spec={
        "selector": {"match_labels": {"role": "xprofiler-proxy"}},
        "template": {
            "metadata": {
                "labels": {"role": "xprofiler-proxy", "app": app_label}
            },
            "spec": {
                "service_account_name": service_account_name,
                "init_containers": [{
                    "name": "proxy-init",
                    "image": "google/cloud-sdk:slim",
                    "command": (
                        pulumi.Output.all(tb_service.metadata["name"]).apply(
                            tb_service_env
                        )
                    ),
                    "volume_mounts": [
                        {"name": "proxy-volume", "mount_path": "/tmp/configs"}
                    ],
                }],
                "containers": [{
                    "name": "proxy-agent",
                    "image": "gcr.io/inverting-proxy/agent:latest",
                    "command": proxy_agent_container_script,
                    "volume_mounts": [{
                        "name": "proxy-volume",
                        "mount_path": "/tmp/configs",
                        "read_only": True,
                    }],
                }],
                "volumes": [{"name": "proxy-volume", "empty_dir": {}}],
            },
        },
    },
)

proxy_service = Service(
    "proxy-service",
    metadata={"namespace": namespace, "labels": {"app": app_label}},
    spec={
        "selector": {"role": "xprofiler-proxy", "app": app_label},
        "cluster_ip": "None",
        "ports": [{"protocol": "TCP", "port": 8083, "targetPort": 8083}],
    },
)

hpa = HorizontalPodAutoscaler(
    "hpa",
    api_version="autoscaling/v2",
    kind="HorizontalPodAutoscaler",
    metadata={"namespace": namespace, "labels": {"app": app_label}},
    spec={
        "scale_target_ref": {
            "api_version": "apps/v1",
            "kind": "Deployment",
            "name": (
                pulumi.Output.all(tb_deployment.metadata["name"]).apply(
                    lambda args: args[0]
                )
            ),
        },
        "min_replicas": 1,
        "max_replicas": 36,
        "metrics": [{
            "type": "Resource",
            "resource": {
                "name": "cpu",
                "target": {"type": "Utilization", "average_utilization": 60},
            },
        }],
    },
)

# Output proxy url -------------------------------------------------------------


def get_proxy_url_from_annotations(args):
  s = Service.get("test", f"{namespace}/{args[1]["name"]}")
  return s.metadata.annotations["proxy-url"]


# Tensorboard Web UI URL
pulumi.export(
    "proxy-url",
    pulumi.Output.all(proxy_deployment.status, tb_service.metadata).apply(
        get_proxy_url_from_annotations
    ),
)

```