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

"""This command is part of the xprof CLI and is used to register an ML run that

includes a captured profile.
"""

import argparse
from collections.abc import Mapping, Sequence
import json
from typing import Any, Dict

import google.auth
from google.auth.transport.requests import Request
import requests
from cloud_diagnostics_xprof.actions import action


class Register(action.Command):
  """[EXPERIMENTAL] register command.

  This command is part of the xprof CLI and is used to register an
  MLrun that includes a captured profile.
  This command is experimental and may be changed or removed at any point.
  """

  BASE_URL: str = 'https://hypercomputecluster.googleapis.com/v1alpha'

  OPERATION_PREFIX: str = 'operation-'

  def __init__(self):
    super().__init__(
        name='register',
        description='Create an ML run with the register command.',
    )

  def add_subcommand(
      self,
      subparser: argparse._SubParsersAction,
  ) -> None:
    """Creates a subcommand for `register`.

    Args:
        subparser: The subparser to add the register subcommand to.
    """
    register_parser = subparser.add_parser(
        name='register',
        help='[EXPERIMENTAL] Register command.',
        description=(
            'This command is part of the xprof CLI and is used to register an'
            ' MLrun that includes a captured profile. This command is'
            ' experimental and may be changed or removed at any point.'
        ),
        formatter_class=argparse.RawTextHelpFormatter,  # Keeps format in help.
    )
    register_parser.add_argument(
        '--log-directory',
        '-l',
        metavar='GS_PATH',
        required=True,
        help='The GCS path to the log directory.',
    )
    # verbose is optional.
    register_parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Print the command.',
    )
    register_parser.add_argument(
        '--region',
        '-r',
        required=True,
        help='The name of the region to create the ML run in.',
    )
    register_parser.add_argument(
        '--ml-run-name',
        '-m',
        required=True,
        help='The name of the ML run to be registered.',
    )
    register_parser.add_argument(
        '--run-set',
        '-s',
        required=True,
        help='The name of the run set to be registered.',
    )
    register_parser.add_argument(
        '--project-id',
        '-p',
        required=True,
        help='The project id of this ML run.',
    )
    register_parser.add_argument(
        '--display-name',
        '-d',
        required=True,
        help='The display name of the ML run to be registered.',
    )

  def run(
      self,
      args: argparse.Namespace,
      extra_args: Mapping[str, str | None] | None = None,
      verbose: bool = False,
  ) -> str:
    """Runs the register ML run command."""

    ml_run = self._create_ml_run(args)

    return self._get_ml_run_id(args, ml_run)

  def _get_ml_run_id(
      self, args: argparse.Namespace, ml_run: Dict[str, Any]
  ) -> str:
    """Returns the URL to the ML run."""

    if 'name' not in ml_run:
      if 'error' in ml_run and 'message' in ml_run['error']:
        return ml_run['error']['message']
      return f'ML run registration failed. Failed {ml_run}'

    # Extract the run ID from the name.
    # The name is in the format of
    # projects/{project_id}/locations/{region}/operations/{operation-id}
    name_list = ml_run['name'].split('/')

    operations_url = f'{self.BASE_URL}/projects/{args.project_id}/locations/{args.region}/operations/{name_list[-1]}'
    # TODO b/443783268: Put this in a loop with timeout to check if done is
    # true.
    response = requests.get(
        url=operations_url,
        headers=self._get_headers(),
    )
    response_json = response.json()
    if (
        'metadata' not in response_json
        or 'target' not in response_json['metadata']
    ):
      return f'ML run registration failed. Failed {ml_run}, {response_json}'

    # Extract the run ID from the target.
    # The target is in the format of
    # projects/{project_id}/locations/{region}/machineLearningRuns/{run_id}
    target_list = response_json['metadata']['target'].split('/')
    return f'ML run registered: {target_list[-1]}'

  def _get_access_token(self) -> str:
    """Returns the access token for the current user."""
    credentials, _ = google.auth.default()
    if not credentials.valid:
      credentials.refresh(Request())
    return credentials.token

  def _get_headers(self) -> Dict[str, Any]:
    """Get HTTP headers with authentication."""
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {self._get_access_token()}',
    }

  def _create_ml_run(
      self,
      args: argparse.Namespace,
  ) -> Dict[str, Any]:
    """Creates a new machine learning run.

    Args:
      args: The arguments parsed from the command line.

    Returns:
      Response from the API as a dictionary

    Raises:
        requests.exceptions.RequestException: If the HTTP request fails
    """

    # TODO(b/443783268): Remove when the metrics and configs are optional.
    json_string = """
    {
      "configs": {
        "userConfigs": {
          "a": "b"
        }
      },
      "tools": [{
        "xprof": {
        }
      }],
      "metrics": {
        "avgStep": "1s",
        "avgMfu": 1.0,
        "avgThroughput": 1.0,
        "avgLatency": "1s"
      },
      "state": "STATE_COMPLETED"
    }
    """
    payload = json.loads(json_string)
    payload['displayName'] = args.display_name
    payload['name'] = args.ml_run_name
    payload['runSet'] = args.run_set
    payload['artifacts'] = {'gcs_path': args.log_directory}

    ml_runs_url = f'{self.BASE_URL}/projects/{args.project_id}/locations/{args.region}/machineLearningRuns'

    response = requests.post(
        url=ml_runs_url,
        headers=self._get_headers(),
        data=json.dumps(payload),
    )

    return response.json()

  def _build_command(
      self,
      args: argparse.Namespace,
      extra_args: Mapping[str, str | None] | None = None,
      verbose: bool = False,
  ) -> Sequence[str]:
    """Builds the command to create a new machine learning run."""
    # There is no need to build the command for register.
    return []

  def display(
      self,
      display_str: str | None,
      *,
      args: argparse.Namespace,
      extra_args: Mapping[str, str | None] | None = None,
      verbose: bool = False,
  ) -> None:
    """Displays the output of the command."""
    print(display_str)
