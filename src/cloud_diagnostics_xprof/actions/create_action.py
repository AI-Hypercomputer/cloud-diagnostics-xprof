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

This command is used as part of the xprof CLI to create a hosted TensorBoard
instance. This will include other metadata such as labels to the log directory
that are specific to the the xprof instance.
"""

import argparse
from collections.abc import Mapping, Sequence
import json
import re
import time
import uuid

from cloud_diagnostics_xprof.actions import action
from cloud_diagnostics_xprof.actions import delete_action
from cloud_diagnostics_xprof.actions import list_action


_WAIT_TIME_IN_SECONDS = 20
_MAX_WAIT_TIME_IN_SECONDS = 300

_OUTPUT_MESSAGE = r"""
Instance for {LOG_DIRECTORY} has been created.
You can access it at https://{BACKEND_ID}-dot-{REGION}.notebooks.googleusercontent.com
Instance is hosted at {VM_NAME} VM.
"""

_TB_LAUNCHED_LABEL = 'tb_launched_ts'
_TB_BACKEND_LABEL = 'tb_backend_id'

_STARTUP_SCRIPT_STRING = r"""#! /bin/bash
echo \"Starting setup.\"
apt-get update
apt-get install -yq git supervisor python3 python3-pip python3-distutils python3-virtualenv
# Setup tensorboard webserver
echo \"Setup tensorboard webserver.\"
virtualenv -p python3 tensorboardvenv
source tensorboardvenv/bin/activate
tensorboardvenv/bin/pip3 install tensorflow-cpu
tensorboardvenv/bin/pip3 install --upgrade 'cloud-tpu-profiler>=2.19.0'
tensorboardvenv/bin/pip3 install tensorboard_plugin_profile
tensorboardvenv/bin/pip3 install importlib_resources
tensorboardvenv/bin/pip3 install etils
tensorboard --logdir {LOG_DIRECTORY} --host 0.0.0.0 --port 6006 &
# Label VM with the current timestamp if TB has launched successfully.
sleep 12  # Buffer time for TB to launch (just in case).
if ps -ef | grep tensorboard > /dev/null; then
    echo \"$(date): TensorBoard running.\"
    TB_LAUNCHED_TS=$(date +%s)
    gcloud compute instances add-labels {MY_INSTANCE_NAME} --zone={ZONE} --labels {TB_LAUNCHED_LABEL}=\"\$TB_LAUNCHED_TS\"
else
    echo \"$(date): TensorBoard failed to launch. Exiting...\"
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
# Get VM ID for this proxy url
echo \"Get VM ID for this proxy url.\"
VM_ID=\$(curl -H 'Metadata-Flavor: Google' \"http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?format=full&audience=${PROXY_URL}/request-endpoint\"  2>/dev/null)
# Generate backend and host id
echo \"Generate backend and host id.\"
RESULT_JSON=\$(curl -H \"Authorization: Bearer \$(gcloud auth print-access-token)\" -H \"X-Inverting-Proxy-VM-ID: \${VM_ID}\" -d \"\" \"\${PROXY_URL}/request-endpoint\" 2>/dev/null)
echo -e \"\${RESULT_JSON}\"
# Extract backend id from response
echo \"Extract backend id from response.\"
BACKEND_ID=\$(python3 -c \"import json; import sys; data=json.loads(sys.argv[1]); print(data['backendID'])\" \"\${RESULT_JSON}\")
echo -e \"\${BACKEND_ID}\"
# Extract hostname from response
echo \"Extract hostname from response.\"
HOSTNAME=\$(python3 -c \"import json; import sys; data=json.loads(sys.argv[1]); print(data['hostname'])\" \"\${RESULT_JSON}\")
echo -e \"\${HOSTNAME}\"
# Set container name
CONTAINER_NAME='proxy-agent'
# Set URL for agent container
CONTAINER_URL='gcr.io/inverting-proxy/agent:latest'
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
gcloud compute instances add-labels {MY_INSTANCE_NAME} --zone={ZONE} --labels {TB_BACKEND_LABEL}=\"\${BACKEND_ID}\"
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
  """A command to delete a hosted TensorBoard instance."""

  def __init__(self):
    super().__init__(
        name='create',
        description='Create a new hosted TensorBoard instance.',
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
        help='Create a hosted TensorBoard instance.',
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
        'log_directory': args.log_directory,
    }
    extra_args |= {'--labels': self._format_label_string(labels)}

    if verbose:
      print(f'Will create VM w/ name: {self.vm_name}')

    # Create the startup entry script.
    startup_entry_script = startup_script_string(
        args.log_directory, self.vm_name, args.zone
    )

    if verbose:
      print(f'Using startup script:\n{startup_entry_script}')

    extra_args |= {'--metadata': 'startup-script=' + startup_entry_script}

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
        zone=args.zone,
        log_directory=[
            args.log_directory,  # Ensure this is treated as one item.
        ],
        filter=None,
        verbose=verbose,
    )
    list_command_output = list_command.run(list_args, verbose=verbose)
    if verbose:
      print(list_command_output)

    # Extract the VM name from the list command output.
    all_lines = list_command_output.strip().split('\n')
    columns: list[str] = all_lines.pop(0).split()
    lines = [line.split() for line in all_lines]
    data_table = self.create_data_table(
        columns=columns,
        lines=lines,
        verbose=verbose,
    )
    # Make sure we can compare with what we expect the output to looks like.
    log_directory_formatted = self._format_string_with_replacements(
        original_string=args.log_directory,
        replacements=self._DEFAULT_STRING_REPLACEMENTS,
    )

    # Ask user if they want to create another instance or quit.
    if log_directory_formatted in data_table.get('LOG_DIRECTORY', []):
      print(
          f'Instance for {args.log_directory} already exists.\n'
      )
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
      has_tb_backend_id = (
          vm_labels
          and (_TB_LAUNCHED_LABEL in vm_labels.keys())
          and (_TB_BACKEND_LABEL in vm_labels.keys())
      )
      if verbose:
        print(f'{has_tb_backend_id=}')
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
          )
      )
    else:  # Setup failed so delete the VM (if created).
      print(
          'Timed out waiting for instance to be set up.\n'
          f'Attempting to delete created VM {self.vm_name} since setup failed.'
      )
      # Delete the VM that was created.
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
      )
  )
