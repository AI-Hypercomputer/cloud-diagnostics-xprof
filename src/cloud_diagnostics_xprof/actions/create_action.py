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

"""A create command implementation for the xprof CLI.

This command is used as part of the xprof CLI to create a xprofiler
instance. This will include other metadata such as labels to the log directory
that are specific to the the xprof instance.
"""

import argparse
from collections.abc import Mapping, Sequence
import json
import time
import uuid

from cloud_diagnostics_xprof.actions import action
from cloud_diagnostics_xprof.actions import delete_action
from cloud_diagnostics_xprof.actions import list_action


_WAIT_TIME_IN_SECONDS = 20
_MAX_WAIT_TIME_IN_SECONDS = 300

# Note that this string will replace multiple variables so string is not
# necessarily valid bash.
_OUTPUT_MESSAGE = r"""
Instance for {LOG_DIRECTORY} has been created.
You can access it via the following,
1. xprofiler connect -z {ZONE} -l {LOG_DIRECTORY} -m ssh
2. [Experimental (supports small captures, < 200 mb)] https://{BACKEND_ID}-dot-{REGION}.notebooks.googleusercontent.com
Instance is hosted at {VM_NAME} VM.
"""

_TB_LAUNCHED_LABEL = 'tb_launched_ts'
_TB_BACKEND_LABEL = 'tb_backend_id'
_TB_ATTEMPTS_LABEL = 'tb_attempts_count'
_MAX_TB_ATTEMPTS = 19

_STARTUP_SCRIPT_STRING = r"""#! /bin/bash
STARTUP_SCRIPT_BEGIN_TS=$(date +%s)
gcloud compute instances add-labels {MY_INSTANCE_NAME} --zone={ZONE} --labels startup_script_begin=\"\$STARTUP_SCRIPT_BEGIN_TS\"

echo \"Starting setup.\"
apt-get update
apt-get install -yq git supervisor python3 python3-pip python3-distutils python3-virtualenv
# Setup tensorboard webserver
echo \"Setup tensorboard webserver.\"
virtualenv -p python3 tensorboardvenv
source tensorboardvenv/bin/activate
tensorboardvenv/bin/pip3 install tensorflow-cpu
tensorboardvenv/bin/pip3 install --upgrade 'cloud-tpu-profiler'
tensorboardvenv/bin/pip3 install tensorboard_plugin_profile
tensorboardvenv/bin/pip3 install importlib_resources
tensorboardvenv/bin/pip3 install etils
tensorboard --logdir {LOG_DIRECTORY} --host 0.0.0.0 --port 6006 &
# Label VM with the current timestamp if TB has launched successfully.
for (( attempt=1; attempt < {MAX_TB_ATTEMPTS}; attempt++ )); do
    p_out=\$(ps -ef| grep tensorboard)
    if [[ \"\$p_out\" == *\"tensorboardvenv\"* ]]; then
        echo \"\$(date): TensorBoard running.\"
        TB_LAUNCHED_TS=\$(date +%s)
        gcloud compute instances add-labels {MY_INSTANCE_NAME} --zone={ZONE} --labels {TB_LAUNCHED_LABEL}=\"\$TB_LAUNCHED_TS\"
        break
    else
        sleep 3
    fi
done
# Label VM with the total number of attempts to launch TB.
gcloud compute instances add-labels {MY_INSTANCE_NAME} --zone={ZONE} --labels {TB_ATTEMPTS_LABEL}=\"\$attempt\"
if [[ \"\$attempt\" -ge {MAX_TB_ATTEMPTS} ]]; then
    echo \"TensorBoard failed to launch after multiple attempts.\"
    exit 1
fi
# Setup forwarding agent and proxy
echo \"Setup forwarding agent and proxy.\"
# Remove existing docker packages
echo \"Remove existing docker packages.\"
for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do sudo apt-get remove $pkg; done
# Install docker
echo \"Install docker.\"
sudo apt install docker.io --yes
# Get inverse proxy mapping file.
echo \"Get inverse proxy mapping file.\"
gcloud storage cp gs://dl-platform-public-configs/proxy-agent-config.json .
# Get proxy URL for this region
echo \"Get proxy URL for this region.\"
PROXY_URL=\$(python3 -c \"import json; import sys; data=json.load(sys.stdin); print(data['agent-docker-containers']['latest']['proxy-urls']['{REGION}'][0])\" < proxy-agent-config.json)
echo -e \"PROXY_URL:\"
echo -e \"PROXY_URL: \${PROXY_URL}\"
# Get VM ID for this proxy url
echo \"Get VM ID for this proxy url.\"
VM_ID=\$(curl -H 'Metadata-Flavor: Google' \"http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?format=full&audience=${PROXY_URL}/request-endpoint\"  2>/dev/null)
echo -e \"VM_ID:\"
echo -e \"\${VM_ID}\"
# Generate backend and host id
echo \"Generate backend and host id.\"
RESULT_JSON=\$(curl -H \"Authorization: Bearer \$(gcloud auth print-access-token)\" -H \"X-Inverting-Proxy-VM-ID: \${VM_ID}\" -d \"\" \"\${PROXY_URL}/request-endpoint\" 2>/dev/null)
echo -e \"RESULT_JSON:\"
echo -e \"\${RESULT_JSON}\"
# Extract backend id from response
echo \"Extract backend id from response.\"
BACKEND_ID=\$(python3 -c \"import json; import sys; data=json.loads(sys.argv[1]); print(data['backendID'])\" \"\${RESULT_JSON}\")
echo -e \"BACKEND_ID:\"
echo -e \"\${BACKEND_ID}\"
# Extract hostname from response
echo \"Extract hostname from response.\"
HOSTNAME=\$(python3 -c \"import json; import sys; data=json.loads(sys.argv[1]); print(data['hostname'])\" \"\${RESULT_JSON}\")
echo -e \"HOSTNAME:\"
echo -e \"\${HOSTNAME}\"
# Set container name
CONTAINER_NAME='proxy-agent'
echo -e \"CONTAINER_NAME:\"
echo -e \"\${CONTAINER_NAME}\"
# Set URL for agent container
CONTAINER_URL='gcr.io/inverting-proxy/agent:latest'
echo -e \"CONTAINER_URL:\"
echo -e \"\${CONTAINER_URL}\"
# Start agent container
docker run -d \
--env \"BACKEND=\${BACKEND_ID}\" \
--env \"PROXY=\${PROXY_URL}/\" \
--env \"SHIM_WEBSOCKETS=true\" \
--env \"SHIM_PATH=websocket-shim\" \
--env \"PORT=6006\" \
--net=host \
--restart always \
--name \"\${CONTAINER_NAME}\" \
\"\${CONTAINER_URL}\" &
echo \"Setting endpoint info in metadata.\"
# Show command to user.
# Label set regardless of BACKEND_ID value.
gcloud compute instances add-labels {MY_INSTANCE_NAME} --zone={ZONE} --labels {TB_BACKEND_LABEL}=\"\${BACKEND_ID}\"
echo \"Labeled VM with key: `{TB_BACKEND_LABEL}`.\"
echo \"Startup Finished\"
"""

# Used to install dependencies & startup TensorBoard.
# MUST be a raw string otherwise interpreted as file path for startup script.
_STARTUP_ENTRY_STRING: str = r"""#! /bin/bash
python3 -c "print(r'''{STARTUP_SCRIPT_STRING}''')" > startup.sh
chmod 775 startup.sh
. ./startup.sh > startup.log
"""

# Used for creating the VM instance.
_DEFAULT_EXTRA_ARGS: Mapping[str, str] = {
    '--tags': 'default-allow-ssh',
    '--image-family': 'debian-12',
    '--image-project': 'debian-cloud',
    '--scopes': 'cloud-platform',
}

_DEFAULT_EXTRA_ARGS_DESCRIBE: Mapping[str, str] = {
    '--format': 'json',
}


class Create(action.Command):
  """A command to delete a xprofiler instance."""

  def __init__(self):
    super().__init__(
        name='create',
        description='Create a new xprofiler instance.',
    )
    self.vm_name = f'{self.VM_BASE_NAME}-{uuid.uuid4()}'

  def add_subcommand(
      self,
      subparser: argparse._SubParsersAction,
  ) -> None:
    """Creates a subcommand for `create`.

    Args:
        subparser: The subparser to add the create subcommand to.
    """
    create_parser = subparser.add_parser(
        name='create',
        help='Create a xprofiler instance.',
        formatter_class=argparse.RawTextHelpFormatter,  # Keeps format in help.
    )
    create_parser.add_argument(
        '--log-directory',
        '-l',
        metavar='GS_PATH',
        required=True,
        help='The GCS path to the log directory.',
    )
    create_parser.add_argument(
        '--zone',
        '-z',
        metavar='ZONE_NAME',
        required=True,
        help='The GCP zone to create the instance in.',
    )
    create_parser.add_argument(
        '--vm-name',
        '-n',
        metavar='VM_NAME',
        help=(
            'The name of the VM to create. '
            'If not specified, a default name will be used.'
        ),
    )
    create_parser.add_argument(
        '--machine-type',
        '-m',
        metavar='MACHINE_TYPE',
        help='The machine type to use for the VM.',
        default='c4-highmem-8',
    )
    create_parser.add_argument(
        '--auto-delete-on-failure-off',
        action='store_true',
        help=(
            'Will not delete the VM if failure occurs.'
        ),
    )
    create_parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Print the command.',
    )

  def _build_command(
      self,
      args: argparse.Namespace,
      extra_args: Mapping[str, str] | None = None,
      verbose: bool = False,
  ) -> Sequence[str]:
    """Builds the create command.

    Note this should not be called directly by the user and should be called
    by the run() method in the action module (using the subparser).

    Args:
      args: The arguments parsed from the command line.
      extra_args: Any extra arguments to pass to the command.
      verbose: Whether to print the command and other output.

    Returns:
      The command to create the VM.
    """
    # Make sure we define this if not already since we'll build from it.
    if extra_args is None:
      extra_args = {}

    # Include our extra args for creation (overwriting any user provided).
    extra_args |= _DEFAULT_EXTRA_ARGS

    labels = {
        self.XPROFILER_VERSION_LABEL_KEY: self.XPROFILER_VERSION,
    }
    extra_args |= {'--labels': self.format_label_string(labels)}

    if verbose:
      print(f'Will create VM w/ name: {self.vm_name}')

    # Create the startup entry script.
    startup_entry_script = startup_script_string(
        args.log_directory, self.vm_name, args.zone
    )

    if verbose:
      print(f'Using startup script:\n{startup_entry_script}')

    log_directory_formatted_string = (
        'gs://'
        + self.format_string_with_replacements(
            original_string=args.log_directory,
            replacements=self.DEFAULT_STRING_REPLACEMENTS,
        )
    )

    # Include version, log directory, and startup script in metadata.
    extra_args |= {
        '--metadata': (
            f'{self.XPROFILER_VERSION_LABEL_KEY}={self.XPROFILER_VERSION}'
            f',{self.LOG_DIRECTORY_LABEL_KEY}={log_directory_formatted_string}'
            f',startup-script={startup_entry_script}'
        )
    }

    create_vm_command = [
        self.GCLOUD_COMMAND,
        'compute',
        'instances',
        'create',
        self.vm_name,
        '--machine-type',
        args.machine_type,
    ]
    if args.zone:
      create_vm_command.append(f'--zone={args.zone}')

    # Extensions of any other arguments to the main command.
    if extra_args:
      create_vm_command.extend(
          [f'{arg}={value}' for arg, value in extra_args.items()]
      )

    if verbose:
      print(create_vm_command)

    return create_vm_command

  def _build_describe_command(
      self,
      args: argparse.Namespace,
      extra_args: Mapping[str, str] | None = None,
      verbose: bool = False,
  ) -> Sequence[str]:
    """Builds the describe command.

    Note this should not be called directly by the user and should be called
    by the run() method in the action module (using the subparser).

    Args:
      args: The arguments parsed from the command line.
      extra_args: Any extra arguments to pass to the command.
      verbose: Whether to print the command and other output.

    Returns:
      The command to describe the VM.
    """
    # Make sure we define this if not already since we'll build from it.
    if extra_args is None:
      extra_args = {}

    # Include our extra args for creation (overwriting any user provided).
    extra_args |= _DEFAULT_EXTRA_ARGS_DESCRIBE

    describe_vm_command = [
        self.GCLOUD_COMMAND,
        'compute',
        'instances',
        'describe',
        self.vm_name,
    ]
    if args.zone:
      describe_vm_command.append(f'--zone={args.zone}')

    # Extensions of any other arguments to the main command.
    if extra_args:
      describe_vm_command.extend(
          [f'{arg}={value}' for arg, value in extra_args.items()]
      )

    if verbose:
      print(describe_vm_command)

    return describe_vm_command

  def _delete_vm(
      self,
      *,
      vm_name: str,
      zone: str,
      verbose: bool = False,
  ) -> str:
    """Deletes the VM that was created."""
    delete_command = delete_action.Delete()
    delete_args = argparse.Namespace(
        vm_name=[vm_name],
        log_directory=None,
        zone=zone,
        quiet=True,
    )
    delete_command_output = delete_command.run(delete_args, verbose=verbose)
    return delete_command_output

  def _validate_run_args(
      self,
      *,
      args: argparse.Namespace,
      verbose: bool = False,
    ) -> None:
    """Validates args for the main command and raises an error if invalid.

    Intended to check arguments passed before the command is run.
    Checks:
      - Log directory (GCS bucket URL) exists.
      - Log directory (GCS bucket URL) has a path part.

    Args:
      args: The arguments parsed from the command line.
      verbose: Whether to print the command and other output.

    Raises:
      ValueError: If the log directory does not exist.
    """
    if not self._is_valid_bucket(
        bucket_name=args.log_directory,
        verbose=verbose,
    ):
      raise ValueError(
          f'Log directory {args.log_directory} does not exist.'
      )

  def run(
      self,
      args: argparse.Namespace,
      extra_args: Mapping[str, str] | None = None,
      verbose: bool = False,
  ) -> str:
    """Run the command.

    Args:
      args: The arguments parsed from the command line.
      extra_args: Any extra arguments to pass to the command.
      verbose: Whether to print the command and other output.

    Returns:
      The output of the command.

    Raises:
      RuntimeError: If the backend server cannot be started.
    """
    # Will raise an error if args are determined to be invalid.
    self._validate_run_args(args=args, verbose=verbose)

    if args.vm_name:
      self.vm_name = args.vm_name

    # Check if the VM already exists.
    if verbose:
      print('Checking if VM already exists.')
    list_command = list_action.List()
    list_args = argparse.Namespace(
        zones=[args.zone],
        log_directory=[
            args.log_directory,  # Ensure this is treated as one item.
        ],
        filter=None,
        verbose=verbose,
    )
    list_command_output = list_command.run(list_args, verbose=verbose)
    if verbose:
      print(list_command_output)
    vm_data = json.loads(list_command_output)

    # Make sure we can compare with what we expect the output to looks like.
    log_directory_formatted = 'gs://' + self.format_string_with_replacements(
        original_string=args.log_directory,
        replacements=self.DEFAULT_STRING_REPLACEMENTS,
    )
    # Get all the log directories from the VMs.
    all_vm_log_dirs = (
        list_command.get_log_directory_from_vm(vm=vm, verbose=verbose)
        for vm in vm_data
    )

    # Ask user if they want to create another instance or quit.
    if log_directory_formatted in all_vm_log_dirs:
      print(f'Instance for {args.log_directory} already exists.\n')
      # Display the instances & information to the user.
      list_command.display(
          display_str=list_command_output,
          args=list_args,
          verbose=verbose,
      )
      print('\n')  # Just to make it visually clearer for the user.

      # Prompt user if they want to continue or quit.
      message_to_user = (
          'Do you want to continue to create another instance with the same '
          'log directory? (y/n)\n'
      )
      # Don't proceed is user does not say 'Y'/'y'
      user_input = input(message_to_user).lower()
      if user_input != 'y':
        print('Exiting...')
        stdout = list_command_output
        return stdout

    if verbose:
      print('Creating VM...')

    command = self._build_command(args, extra_args, verbose)
    if verbose:
      print(f'Command to run: {command}')

    stdout: str = self._run_command(command, verbose=verbose)

    timer = 0
    print('Waiting for instance to be created. It can take a few minutes.')
    has_tb_backend_id = False
    backend_id: str | None = None
    vm_labels_final_values: dict[str, str | None] = {}
    while timer < _MAX_WAIT_TIME_IN_SECONDS:
      time.sleep(_WAIT_TIME_IN_SECONDS)
      timer += _WAIT_TIME_IN_SECONDS
      command = self._build_describe_command(args, extra_args, verbose)
      if verbose:
        print(f'{timer} seconds have passed of {_MAX_WAIT_TIME_IN_SECONDS}.')
        print(f'Command to run: {command}')
      stdout_describe = self._run_command(command, verbose=verbose)
      json_output = json.loads(stdout_describe)
      vm_labels = json_output.get('labels', {})
      if verbose:
        print(f'JSON labels: \n{vm_labels}')

      # Store the latest values of the labels.
      vm_labels_final_values[_TB_LAUNCHED_LABEL] = vm_labels.get(
          _TB_LAUNCHED_LABEL
      )
      vm_labels_final_values[_TB_BACKEND_LABEL] = vm_labels.get(
          _TB_BACKEND_LABEL
      )

      # Must have both labels & backend id must have a value.
      has_tb_backend_id = (
          vm_labels
          and vm_labels_final_values[_TB_LAUNCHED_LABEL]
          and vm_labels_final_values[_TB_BACKEND_LABEL]
      )

      if verbose:
        print(f'{has_tb_backend_id=}')

      # Exit if we've reached the max number of attempts for TensorBoard server.
      if (
          _TB_ATTEMPTS_LABEL in vm_labels
          and int(vm_labels[_TB_ATTEMPTS_LABEL]) >= _MAX_TB_ATTEMPTS
      ):
        raise RuntimeError('Unable to start backend server.')

      if has_tb_backend_id:
        backend_id = json_output['labels']['tb_backend_id']
        break

    # Print out information since creation was successful.
    if has_tb_backend_id:
      if verbose:
        print(f'Backend id: {backend_id}')
      print(
          _OUTPUT_MESSAGE.format(
              LOG_DIRECTORY=args.log_directory,
              BACKEND_ID=backend_id,
              REGION='-'.join(args.zone.split('-')[:-1]),
              VM_NAME=self.vm_name,
              ZONE=args.zone,
          )
      )
    else:  # Setup failed; perform any cleanup.
      print(
          'Timed out waiting for instance to be set up.\n'
      )

      # Print out specific failure (if any that can be enumerated).
      if verbose:
        print('Final label values:')
        for label, value in vm_labels_final_values.items():
          print(f'{label}={value}')
        # Specifically check if the backend id is not set.
        backend_id_value = vm_labels_final_values.get(_TB_BACKEND_LABEL)
        if backend_id_value:
          print(f'TensorBoard backend ID was set to `{backend_id_value=}`')
        else:
          print(f'TensorBoard backend ID was not set. `{backend_id_value=}`')

      # Delete the VM that was created unless user specified otherwise.
      if args.auto_delete_on_failure_off:
        if verbose:
          print('Not deleting VM since user specified to not delete.')
        # Warn the user regardless of verbose setting.
        print(
            'Failure in setting up VM.\n'
            'Note that the VM was NOT deleted and may be in a bad state'
            ' and/or unstable.\n'
        )
        print(
            _OUTPUT_MESSAGE.format(
                LOG_DIRECTORY=args.log_directory,
                BACKEND_ID=backend_id,
                REGION='-'.join(args.zone.split('-')[:-1]),
                VM_NAME=self.vm_name,
                ZONE=args.zone,
            )
        )
      else:
        if verbose:
          print('Deleting VM that was created.')
        _ = self._delete_vm(
            vm_name=self.vm_name,
            zone=args.zone,
            verbose=verbose,
        )

    return stdout

  def display(
      self,
      display_str: str | None,
      *,
      args: argparse.Namespace,
      extra_args: Mapping[str, str] | None = None,
      verbose: bool = False,
  ) -> None:
    """Display provided string after potential formatting.

    Args:
      display_str: The string to display.
      args: The arguments parsed from the command line.
      extra_args: Any extra arguments to pass to the command.
      verbose: Whether to print the command and other output.
    """
    # No display string is needed for the create command.
    return None


def startup_script_string(log_directory: str, vm_name: str, zone: str) -> str:
  """Returns the startup script string."""
  return _STARTUP_ENTRY_STRING.format(
      STARTUP_SCRIPT_STRING=_STARTUP_SCRIPT_STRING.format(
          LOG_DIRECTORY=log_directory,
          MY_INSTANCE_NAME=vm_name,
          ZONE=zone,
          REGION='-'.join(zone.split('-')[:-1]),
          PROXY_URL='{PROXY_URL}',
          VM_ID='{VM_ID}',
          BACKEND_ID='{BACKEND_ID}',
          HOSTNAME='{HOSTNAME}',
          CONTAINER_NAME='{CONTAINER_NAME}',
          CONTAINER_URL='{CONTAINER_URL}',
          RESULT_JSON='{RESULT_JSON}',
          TB_LAUNCHED_LABEL=_TB_LAUNCHED_LABEL,
          TB_BACKEND_LABEL=_TB_BACKEND_LABEL,
          TB_ATTEMPTS_LABEL=_TB_ATTEMPTS_LABEL,
          MAX_TB_ATTEMPTS=_MAX_TB_ATTEMPTS,
      )
  )
