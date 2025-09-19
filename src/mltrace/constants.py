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

"""Constants used across multiple files.
"""

TIME_REGEXP = "%Y-%m-%dT%H:%M:%S.%f%z"
WORKER_GROUP_PREFIX = "Slice-Worker "

REGEX_SUBSTR_MATCH_ROW_HEADERS = {
    "[E] Some workers didn't report an error after ": "Node pool error",
    "checkpoint": "Checkpoint",
    "[E] BAD_ICI": "BAD_ICI",
    "last_finished_run_id updated to": "Info",
    "[E] MegaScale Topology Discovery in progress. Missing hosts ": (
        "Missing hosts in Topology discovery"
    ),
    "Enqueueing program \\d+: [a-z0-9]+ to continuation queue": "Info",
    "Failed to call GetSessioInfo for worker": "Failed to call GetSessioInfo",
    "[E] failed to connect to all addresses": "Failed to connect",
    "MegaScale Topology Discovery": "MegaScale Topology Discovery",
}

REDUNDANT_LOGS_SUBSTR_MATCH = [
    (
        r"\\[\\d+\.\\d+\\]"
        r" [anon|file|kernel|kernel_stack|pagetables|sec_pagetables|"
        r"percpu|sock|vmalloc|shmem|file_mapped|file_dirty|file_writeback|"
        r"swapcached|anon_thp|file_thp|shmem_thp|inactive_anon|active_anon|"
        r"inactive_file|active_file|unevictable|slab_reclaimable|"
        r"slab_unreclaimable|slab|workingset_refault_anon|"
        r"workingset_refault_file|workingset_activate_anon|"
        r"workingset_activate_file|workingset_restore_anon|"
        r"workingset_restore_file|workingset_nodereclaim|pgscan|pgsteal|"
        r"pgscan_kswapd|pgscan_direct|pgscan_khugepaged|pgsteal_kswapd|"
        r"pgsteal_direct|pgsteal_khugepaged|pgfault|pgmajfault|pgrefill|"
        r"pgactivate|pgdeactivate|pglazyfree|pglazyfreed|thp_fault_alloc|"
        r"thp_collapse_alloc] \\d+"
    ),
    "stack used: \\d+ KiB of \\d+ KiB",
    "Sending to [0-9.]+:\\d+ on interface",
    "Created \\d+ channels for \\d+ interfaces on slice",
    "^argv\\[\\d+\\]: '",
    "Worker Address: [a-z0-9-_.]+:\\d+",
    "Notifying error handler:",
    "Starting launch_id for device_set_hash",
    "Constructing tf.data.Dataset",
    "Creating directories: ",
    "Driver opened.",
    "No topology specified, using auto-topology",
    "Applying remat on ",
    "All instances are ready for",
    "Dumping Debug Info for",
    "CallbackRegistryLogger dumping to file",
    "Writing to file:",
    "All directories created",
    "Created communicator.",
    "source_endpoint:",
    "Received topology discovery response: go/debugonly",
    "Sending topology discovery request: go/debugonly",
    "gRPC experiments",
    "Load dataset info from",
    "Keeping the one from code.",
    "Debug dumping triggered.",
    "Registering error handler with name",
    "Found \\d+ TPU .* chips.",
    "Starting JAX distributed service on",
    "platforms/xla/megascale/runtime/executor/executor.cc:",
    "Connecting to JAX distributed service on ",
    "Using enhanced global barrier with ",
    "Using \\d+ from .* as SliceBuilder worker service port.",
    "Running on GCE, using service account ",
    "Using MXLA graph seed: ",
    "Creating client for slice \\d+ host \\d+",
    "Created Megascale GrpcTransport.",
    "Done allocating premapped memory of size",
    "HostCommandHandler will auto insert launch_ids ",
    "Created a HostCommandScheduler ",
    "Shapes to compress: ",
    "Prefixes to compress: ",
    "Fiber init: ",
    "Constraining input_batch",
    "feed_read_config=",
    "Starting AllocatorStats Reporter with reporting interval",
    "Done premapping memory of size ",
    "\\(HLO module .*\\): Executable fingerprint",
    "\\(HLO module .*\\): Host transfer fingerprint",
    "LatencyHidingScheduler current memory usage: ",
    "LIBTPU_INIT_ARGS=",
    "DATA_DIR=gs:",
    "dcn_topology_level:",
    "TpuSystemLogger dumping to file",
    "Successful retry compilation of fusion.",
    "Megascale init launch counter for ",
    "bytes for BuildID, using \\d+ syscalls.",
    "Debug logger execution longer than",
    "estimated_start_time_ms:",
    "Error collection latencies",
    "Creating numa aware allocators, number of NUMA nodes ",
    "transfers {$",
    "peers {$",
    "desination {$",
    "Creating a tf.data.Dataset reading ",
    "Successfully started Runtime Metric Service on port",
    "Finished waiting at barrier for process",
    "Successfully started ICI network session with ",
    "Session master notifies the worker in a new session",
    "TPU premapped buffer enabled.",
    "tpu::System initialized",
    "CreateTpuSystemState: TPU initialization is successful",
    "CreateTpuSystemState: using TPU host premapped buffer of size",
    "Megascale Topology Coordinator started for ",
    "Ran \\d+ additional passes of layout assignment to assign all layouts.",
    "Skipping initialization of PA bits on",
    "Creating TpunetdClient with topology go/debugonly",
    "Connecting to vbar control service at ",
    "input_batch=",
    "gpt_trainer process   \\d+ step        0",
    "gpt_trainer process   \\d+ step       -1",
    "Using hybrid mesh shape: HybridMeshShape",
    "Inferred inter-slice/granule mesh shape",
    "param_.* = ",
    "multiply.* = multiply",
    "exponential.* = exponential",
    "FLOPS: ",
    "Temp memory: ",
    "fusion.* = fusion",
    "bitcast.* = bitcast",
    "Branch Divergence (Control Flow Processing)",
    "convolution.* = convolution",
    "tag: \\d+$",
    "core_idx: \\d+$",
    "pc: \\d+$",
    "chip_id: \\d+$",
    "tpu_core_summary {",
    "launch_ids {",
    "key: \\d+$",
    "value: \\d+$",
    "rapid_eye_info {",
    "telemetry {",
    "graph_events {",
    "graph_id: \"",
    "event_type: START",
    "timestamp_ns: \\d+$",
    "File \".*, line \\d+ in",
    "^ *}$",
    "^ *{$",
    "files.* % Done.*Copying",
    "e2e_time_us: \\d+$",
    "launch_id: \\d+$",
    "model.decoder.*: ",
    "mesh_rules.*:",
    "mesh_shape: ",
    "learner.optimizer.args.*:",
    "input\\..*:",
    "address: \"",
    "addresses {",
    "address_mappings {",
    "executable_fingerprint:",
    "pending_graphs {",
    "^ *actions {$",
    "^ *network_receive {$",
    "^ *network_send {$",
    "buffer_size: \\d+$",
    "num_outputs: \\d+$",
    "device_to_host {",
    "pending_actions: \\d+$",
    "host_id: \\d+$",
    "inputs {$",
    "compute {$",
    "destination {$",
    "transfer_info {$",
    "event_type: END",
    "=== Source Location Trace: ===",
    "pad.\\d+ = .*pad",
    "add.\\d+ = .*add",
    "multiply.\\d+ = .*multiply",
    "divide.\\d+ = .*divide",
    "broadcast.\\d+ = .*broadcast",
    "convolution.\\d+ = .*convolution",
    "fusion.\\d+ = .*fusion",
    "exponential.\\d+ = .*exponential",
    "negate.\\d+ = .*negate",
    "bitcast.\\d+ = .*bitcast",
    "all-gather.\\d+ = .*all-gather",
    "constant.\\d+ = .*constant",
    "tuple.\\d+ = .*tuple",
    "Operation completed over ",
    "Register usage: ",
    "Thread .* \\(most recent call first\\):",
    "evalers\\['.*'\\].*: ",
    "enhanced_barrier_enabled:",
    "version: TPU_VERSION_",
    "Output memory: ",
    "=== Cost Analysis ====",
    "Copying file:",
    "Total HBM memory: ",
    "^ *x: \\d+",
    "^ *y: \\d+",
    "^ *z: \\d+",
    "DEBUG_COMPILER_OPTIONS.PY: LIBTPU_LOGS ",
    "host_bounds {",
    "L\\d+ Cache Operations: ",
    "} after \\d+ retries",
    "files.*% Done",
    "Thread joined successfully",
    "DEBUG_LAUNCH.PY: LIBTPU_LOGS in launch.py top level",
    "Input memory: ",
    "Memory Load/Store Units: ",
    "Tensor Cores / MatMul units:",
    "^ *value {",
    "is_training: False",
    "chip_config_name: ",
    "L\\d+ cache access: ",
    "Output data transferred: ",
    " ALU (Arithmetic Logic Unit): \\d+",
    "Special Function Units ",
    "max_steps: \\d+$",
    "learner..*:",
    "mesh_axis_names\\[\\d+\\]:",
    "klass: '",
    "host_name_for_debugging:",
    "Branch Divergence ",
    "source.split: ",
    "Load Balancing / Dispatch",
    "kvlist_attr {",
    "Integer Units ",
    "Texture Units ",
    "source.data_mixture_components\\[\\d+\\]",
    "interface_name:",
    "attributes {",
    "^{ *worker_id = \".*\", hostname =",
    "eval_policy.n: ",
    "ALU \\(Arithmetic Logic Unit\\): ",
    "^ *slice_id: \\d+$",
    "string_attr: \"",
    "source.preprocessor.max_padding_fraction:",
    "source..*: ",
    "@.*\\d+  \\(unknown\\)",
    "start_trace.*\\[\\d+\\]:\\d+$",
    "summary_writer.*:",
    "PjRtCApiClient created.",
    "Connected to distributed JAX controller",
    "batch_axis_names\\[\\d+\\]:",
    "batcher.feed_batch_size: ",
    "train_dtype:",
    "max_step: \\d+$",
    "processor.fn: '",
    "^ *tpu_topology_args {",
    "Error check finished successfully",
    "The total memory traffic:",
    "^ *Launch ID: \\d+",
    "model.batch_axis_names:",
    "model.dtype: ",
    "model.param_init.init_by_param_name",
    "prune_empty_state_updates: ",
    "recorder.fn: ",
    "Summary : go/debugonly ",
    "save_input_iterator: ",
    "start_trace_process_indices\\[\\d+\\]:",
    "start_trace_steps\\[\\d+\\]:",
    "summary_writer.max_queue: ",
    "summary_writer.write_every_n_steps: ",
    "watchdog_timeout_seconds: \\d+$",
    "Module: jit__psum",
    "Load balancing policy: .*max_outstanding_bytes",
    "^ *Fingerprint: ",
    "^ *wrap {",
    "gRPC insecure client credentials are used.",
    "Filling up shuffle buffer",
    "Shuffle buffer filled.",
    "Code memory: ",
    "Dumped gzipped tool data for trace",
    "connected to coordination service",
    "^ *platform_type: ",
    "Finished committing to storage layer by process:",
    "HBM access: ",
    "^ *key:",
    "^ *name:",
    "^ *partition_spec\\[\\d+\\].*:",
    "Max training state size .*:",
    "Profiler session started.",
    "Profiler session initializing.",
    "Profiler session collecting data.",
    "Collecting XSpace to repository",
    "The number of .* ops:",
]

FILE_ONLY_REDUNDANT_LOGS_EXACT = [
    r"*** Check failure stack trace: ***",
]

REDUNDANT_LOGS_EXACT = [
    (
        "All instances are ready for PRE_START_SESSION_BARRIER, broadcasting"
        " notification..."
    ),
    r"\*\*\* Check failure stack trace: \*\*\*",
    "runtime_state {",
    "Hardware utilization scores",
    "CallbackRegistryLogger has log capacity of 0.",
    "## Trainer States:",
    "tpu_topology_args {",
    "Received topology discovery response: go/debugproto",
    "Initializing MegaScale transport.",
    "MegaScale transport initialized.",
    "=== Source Location Trace: ===",
    "TPU backend connection test passed!",
    "UptimeMetric attributes are updated.",
    "Using IP addresses for interface discovery.",
    "Session manager starting a new session...",
    "Creating TpunetdClient with topology go/debugproto",
    "Skipping initialization of PA bits on {type = TensorCore, index = 0}",
    "Using auto-detected TPU version TPU v6 lite",
    "--tpu_use_tfrt not specified. Using default value: true",
    "Running in Cloud, using TpunetdClient",
    "Premapped buffer is using alignment 64",
    "Starting premapped memory manager initialization...",
    "Registered plugin from module: breakpoint_debugger_server",
    "Starting a new ICI network session...",
    "Intentionally not binding to interface since server is client.",
    "Waiting for previous serialization to finish",
    "Not using TPUDecoding because is_decoding=False.",
    "MegaScale transport init succeeded.",
    "RAW: Futex::Swap(): using GFUTEX_SWAP",
    "Skipping MDS query due to true",
    "Starting gRPC Server.",
    "Resetting impairments.",
    "Remote crash gathering hook installed.",
    "Modified Input.config according to input_batcher:",
    "Waiting for previous serialization to finish.",
    "xla_tpu_autofdo_profile_dir updated to ",
    (
        "xla_tpu_autofdo_use_remote_repo is overridden to false because"
        " xla_tpu_autofdo_profile_dir is not set."
    ),
    "No recorder type specified, skipping initialize().",
    "Using TPUSplashAttention.",
    "ReadGlobalTimeCounter returning real data",
    "Session manager started the new session.",
    "Session master starting a new session...",
    "Session master started the new session.",
    "======= Memory Analysis ==================================",
    "TPU backend connection test passed! ",
    "Building device mesh.",
    "Building multi-slice/granule device mesh over axis 1.",
    "Building synchronization state...",
    "Starting synchronization...",
    "slice_info {",
]

REDUNDANT_SEVERITY_IN_FILES = {
    "2a886c8_compiler_base.cc": "INFO",
    "b295d63588a.cc": "INFO",
    "megascale_context.cc": "INFO",
    "param_init.py": "INFO",
    "serialization.py": "INFO",
}

PERFETTO_TEMPLATE_HTML = r"""
<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="Content-Security-Policy" content="script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-src https://ui.perfetto.dev; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; navigate-to 'none';">
  <title>MLTrace: $title</title>
  <style>
    html, body, iframe {
      margin: 0;
      padding: 0;
      width: 100%;
      height: 100%;
      border: none;
    }

    #loader {
      background-color: #fde293;
      width: 100%;
      height: 100%;
      position: absolute;
    }

    .loader {
      width: 40px;
      height: 40px;
      background-color: #3c4043;

      margin: 100px auto;
      -webkit-animation: sk-rotateplane 1.2s infinite ease-in-out;
      animation: sk-rotateplane 1.2s infinite ease-in-out;
    }

    @-webkit-keyframes sk-rotateplane {
      0% { -webkit-transform: perspective(120px) }
      50% { -webkit-transform: perspective(120px) rotateY(180deg) }
      100% { -webkit-transform: perspective(120px) rotateY(180deg)  rotateX(180deg) }
    }

    @keyframes sk-rotateplane {
      0% { 
        transform: perspective(120px) rotateX(0deg) rotateY(0deg);
        -webkit-transform: perspective(120px) rotateX(0deg) rotateY(0deg)
      } 50% { 
        transform: perspective(120px) rotateX(-180.1deg) rotateY(0deg);
        -webkit-transform: perspective(120px) rotateX(-180.1deg) rotateY(0deg)
      } 100% {
        transform: perspective(120px) rotateX(-180deg) rotateY(-179.9deg);
        -webkit-transform: perspective(120px) rotateX(-180deg) rotateY(-179.9deg);
      }
    }

  </style>
</head>
<body>
  <div id="loader">
    <div class="loader"></div>
  </div>

  <iframe id="perfetto_iframe" src="https://ui.perfetto.dev?mode=embedded&hideSidebar=true" onload="iframeLoaded()" allow="usb; fullscreen" hidden></iframe>
  <script>
    function iframeLoaded() {
      fetchAndOpen("$trace_file");
    }
    const ORIGIN = "https://ui.perfetto.dev";

    async function fetchAndOpen(traceUrl) {
      const ds = new DecompressionStream("gzip");
      const resp = await fetch(traceUrl, {mode: 'cors'});
      const blob = await resp.blob();

      const decompressed_stream = blob.stream().pipeThrough(ds);

      const decompressed_blob = await new Response(decompressed_stream).blob();

      const arrayBuffer = await decompressed_blob.arrayBuffer();
      let loader = document.getElementById('loader');
      loader.remove();

      let frame = document.getElementById('perfetto_iframe');
      frame.style.display = "block";
      let win = frame.contentWindow;
      openTrace(win, arrayBuffer);
    }

    function openTrace(win, arrayBuffer) {
      const timer = setInterval(() => win.postMessage('PING', ORIGIN), 50);

      const onMessageHandler = (evt) => {
        if (evt.data !== 'PONG') return;

        // We got a PONG, the UI is ready.
        window.clearInterval(timer);
        window.removeEventListener('message', onMessageHandler);

        const url = new URL(location.href);

        win.postMessage({
          perfetto: {
            buffer: arrayBuffer,
            title: 'MLTrace: $title',
            url: url.toString(),
          }}, ORIGIN);
        };

        window.addEventListener('message', onMessageHandler);
      }
    </script>
  </body>
  </html>
"""
