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

"""Utils for cloud diagnostics xprof."""
import subprocess


def bucket_exists(bucket_name: str) -> None:
  """Checks if a bucket exists."""
  if not bucket_name.startswith('gs://'):
    raise ValueError(f'Bucket name {bucket_name} does not start with gs://.')

  bucket_name = 'gs://'+ bucket_name.split('/')[2]

  try:
    subprocess.run(
        [
            'gcloud',
            'storage',
            'buckets',
            'describe',
            bucket_name,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
  except subprocess.CalledProcessError as e:
    raise ValueError(f'Bucket {bucket_name} does not exist.') from e


def host_exists(host_name: str, zone: str) -> None:
  """Checks if a host exists."""
  try:
    subprocess.run(
        [
            'gcloud',
            'compute',
            'tpus',
            'tpu-vm',
            'describe',
            host_name,
            '--zone',
            zone,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
  except subprocess.CalledProcessError as e:
    raise ValueError(f'Host {host_name} does not exist.') from e
