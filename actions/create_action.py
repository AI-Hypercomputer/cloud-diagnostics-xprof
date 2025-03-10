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

"""A create command implementation for the xprofiler CLI.

This command is used as part of the xprofiler CLI to create a hosted TensorBoard
instance. This will include other metadata such as labels to the log directory
that are specific to the the xprofiler instance.
"""

import argparse
from collections.abc import Mapping, Sequence
import uuid

from actions import action


# Used to install dependencies & startup TensorBoard.
# MUST be a raw string otherwise interpreted as file path for startup script.
_STARTUP_SCRIPT_STRING: str = r"""#! /bin/bash
apt-get update
apt-get install -yq git supervisor python3 python3-pip python3-distutils python3-virtualenv
virtualenv -p python3 tensorboardvenv
source tensorboardvenv/bin/activate
tensorboardvenv/bin/pip3 install tensorflow-cpu
tensorboardvenv/bin/pip3 install --upgrade 'cloud-tpu-profiler>=2.3.0'
tensorboardvenv/bin/pip3 install tensorboard_plugin_profile
tensorboardvenv/bin/pip3 install importlib_resources
tensorboardvenv/bin/pip3 install etils
tensorboard --logdir {log_directory} --host 0.0.0.0 --port 6006 &
EOF"""

# Used for creating the VM instance.
_DEFAULT_EXTRA_ARGS: Mapping[str, str] = {
    '--tags': 'default-allow-ssh',
    '--image-family': 'debian-12',
    '--image-project': 'debian-cloud',
    '--machine-type': 'e2-medium',
    '--scopes': 'cloud-platform',
}


class Create(action.Command):
  """A command to delete a hosted TensorBoard instance."""

  def __init__(self):
    super().__init__(
        name='create',
        description='Create a new hosted TensorBoard instance.',
    )

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

    startup_script = _STARTUP_SCRIPT_STRING.format(
        log_directory=args.log_directory
    )

    if verbose:
      print(f'Using startup script:\n{startup_script}')

    extra_args |= {'--metadata': 'startup-script=' + startup_script}

    # Create the VM name if not provided.
    vm_name = (
        args.vm_name if args.vm_name else f'{self.VM_BASE_NAME}-{uuid.uuid4()}'
    )
    if verbose:
      print(f'Will create VM w/ name: {vm_name}')

    create_vm_command = [
        self.GCLOUD_COMMAND,
        'compute',
        'instances',
        'create',
        vm_name,
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
