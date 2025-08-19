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

"""Data generator for xprofiler"""

from collections.abc import Sequence
import subprocess
import time


def _run_command(
    command: Sequence[str],
    *,
    verbose: bool = False,
) -> str:
  """Run the command.

  Args:
    command: The command to run.
    verbose: Whether to print the command and other output.

  Returns:
    The output of the command.
  """
  output = ''
  try:
    diag = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    if verbose:
      print(f'Command {command} succeeded.')
    if diag.stdout:
      output = diag.stdout
      if verbose:
        print(f'Output: {diag.stdout}')
  except subprocess.CalledProcessError as e:
    # Only print the full subprocess error if in verbose mode.
    if verbose:
      # Print the simple error stderr from the shell command.
      if e.stderr:
        print('Command failed. Standard Error (stderr):')
        print(e.stderr)
      print(f'Command failed. Subprocess error:\n{e}')
    # For readability, custom error message has stderr from shell command.
    error_message = (
        f'Command failed with return code {e.returncode}.\n'
        f'{e.stderr if e.stderr else ""}'
    )
    raise ValueError(error_message) from e

  return output


def current_millis() -> int:
  return time.perf_counter_ns() // 1000000


#
def _create(
    verbose: bool, hierarchical_namespace: bool, folder_count, folder_nesting
):
  bucket_name = f'terma-test-hierarchical-{str(hierarchical_namespace).lower()}-folders-{folder_count}-deep-{folder_nesting}'
  print(f'Setup {bucket_name}...')

  _run_command(
      [
          'gcloud',
          'storage',
          'buckets',
          'create',
          f'gs://{bucket_name}',
          '--location=US',
          '--enable-hierarchical-namespace',
          '--uniform-bucket-level-access',
      ],
      verbose=verbose,
  )

  for i in range(0, folder_count):
    path = ''
    for j in range(0, folder_nesting):
      path += f'/folder-{i}-{j}'

    path += f'/tensorboard/plugins/profile/data-{i}'

    if hierarchical_namespace:
      _run_command(
          [
              'gcloud',
              'storage',
              'folders',
              'create',
              '--recursive',
              f'gs://{bucket_name}{path}',
          ],
          verbose=verbose,
      )
      _run_command(
          [
              'gcloud',
              'storage',
              'cp',
              'gs://tyagiva-test/test-job/tensorboard/plugins/profile/2025_04_14_17_39_23/t1v-n-78126f6c-w-0.xplane.pb',
              f'gs://{bucket_name}{path}/data-{i}.xplane.pb',
          ],
          verbose=verbose,
      )
    else:
      _run_command(
          [
              'gcloud',
              'storage',
              'cp',
              'gs://tyagiva-test/test-job/tensorboard/plugins/profile/2025_04_14_17_39_23/t1v-n-78126f6c-w-0.xplane.pb',
              f'gs://{bucket_name}{path}/data-{i}.xplane.pb',
          ],
          verbose=verbose,
      )


def main():
  verbose = True

  """ _create(verbose, False, 1, 1)
  _create(verbose, True, 1, 1)

  _create(verbose, False, 10, 1)
  _create(verbose, True, 10, 1)

  _create(verbose, False, 10, 10)
  _create(verbose, True, 10, 10)

  _create(verbose, False, 100, 1)
  _create(verbose, True, 100, 1)

  _create(verbose, False, 100, 10)
  _create(verbose, True, 100, 10)

  _create(verbose, False, 200, 2)
  _create(verbose, True, 200, 2)
  """


if __name__ == '__main__':
  main()
