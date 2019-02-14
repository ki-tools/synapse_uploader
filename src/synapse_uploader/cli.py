#!/usr/bin/env python

# Copyright 2017-present, Bill & Melinda Gates Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import argparse
from .synapse_uploader import SynapseUploader


class LogFilter(logging.Filter):
    FILTERS = [
        '##################################################',
        'Uploading file to Synapse storage',
        'Connection pool is full, discarding connection:'
    ]

    def filter(self, record):
        for filter in self.FILTERS:
            if filter in record.msg:
                return False
        return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project_id', metavar='project-id',
                        help='Synapse Project ID to upload to (e.g., syn123456789).')
    parser.add_argument('local_folder_path', metavar='local-folder-path',
                        help='Path of the folder to upload.')
    parser.add_argument('-r', '--remote-folder-path',
                        help='Folder to upload to in Synapse.', default=None)
    parser.add_argument('-d', '--depth',
                        help='The maximum number of child folders or files under a Synapse Project/Folder.',
                        type=int, default=SynapseUploader.MAX_SYNAPSE_DEPTH)
    parser.add_argument('-t', '--threads',
                        help='The maximum number of threads to use.', type=int, default=None)
    parser.add_argument('-u', '--username',
                        help='Synapse username.', default=None)
    parser.add_argument('-p', '--password',
                        help='Synapse password.', default=None)
    parser.add_argument('-l', '--log-level',
                        help='Set the logging level.', default='INFO')

    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper())
    log_file_name = 'log.txt'

    logging.basicConfig(
        filename=log_file_name,
        filemode='w',
        format='%(asctime)s %(levelname)s: %(message)s',
        level=log_level
    )

    # Add console logging.
    console = logging.StreamHandler()
    console.setLevel(log_level)
    console.setFormatter(logging.Formatter('%(message)s'))
    logging.getLogger().addHandler(console)

    # Filter logs
    log_filter = LogFilter()
    for logger in [logging.getLogger(name) for name in logging.root.manager.loggerDict]:
        logger.addFilter(log_filter)

    SynapseUploader(
        args.project_id,
        args.local_folder_path,
        remote_path=args.remote_folder_path,
        max_depth=args.depth,
        max_threads=args.threads,
        username=args.username,
        password=args.password
    ).upload()


if __name__ == "__main__":
    main()
