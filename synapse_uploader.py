#!/usr/bin/env python3

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

import sys
import os
import argparse
import getpass
import time
import random
import synapseclient
from synapseclient import Project, Folder, File


class SynapseUploader:

    def __init__(self, synapse_project, local_path, remote_path=None, dry_run=False, username=None, password=None):
        self._dry_run = dry_run
        self._synapse_project = synapse_project
        self._local_path = local_path.rstrip(os.sep)
        self._remote_path = None
        self._synapse_folders = {}
        self._username = username
        self._password = password
        self._hasErrors = False

        if remote_path != None and len(remote_path.strip()) > 0:
            self._remote_path = remote_path.strip().lstrip(os.sep).rstrip(os.sep)
            if len(self._remote_path) == 0:
                self._remote_path = None

    def start(self):
        if self._dry_run:
            print('~~ Dry Run ~~')
        print('Uploading to Project: {0}'.format(self._synapse_project))
        print('Uploading Directory: {0}'.format(self._local_path))

        if self._remote_path != None:
            print('Uploading To: {0}'.format(self._remote_path))

        self.login()

        project = self._synapse_client.get(Project(id=self._synapse_project))
        self.set_synapse_folder(self._synapse_project, project)

        # Create the remote_path if specified.
        if self._remote_path:
            full_path = ''
            for folder in filter(None, self._remote_path.split(os.sep)):
                full_path = os.path.join(full_path, folder)
                self.create_directory_in_synapse(full_path, virtual_path=True)

        # Create the folders and upload the files.
        for dirpath, dirnames, filenames in os.walk(self._local_path):

            if dirpath != self._local_path:
                self.create_directory_in_synapse(dirpath)

            for filename in filenames:
                full_file_name = os.path.join(dirpath, filename)
                self.upload_file_to_synapse(full_file_name)

        completion_status = 'With Errors' if self._hasErrors else 'Successfully'

        if self._dry_run:
            print('Dry Run Completed {0}'.format(completion_status))
        else:
            print('Upload Completed {0}'.format(completion_status))

    def get_synapse_folder(self, synapse_path):
        return self._synapse_folders.get(synapse_path, None)

    def set_synapse_folder(self, synapse_path, parent):
        self._synapse_folders[synapse_path] = parent

    def login(self):
        print('Logging into Synapse...')
        syn_user = os.getenv('SYNAPSE_USER') or self._username
        syn_pass = os.getenv('SYNAPSE_PASSWORD') or self._password

        if syn_user == None:
            syn_user = input('Synapse username: ')

        if syn_pass == None:
            syn_pass = getpass.getpass(prompt='Synapse password: ')

        self._synapse_client = synapseclient.Synapse()
        self._synapse_client.login(syn_user, syn_pass, silent=True)

    def get_synapse_path(self, local_path, virtual_path=False):
        if virtual_path:
            return os.path.join(self._synapse_project, local_path)
        else:
            return os.path.join(
                self._synapse_project,
                (self._remote_path if self._remote_path else ''),
                local_path.replace(self._local_path + os.sep, '')
            )

    def create_directory_in_synapse(self, path, virtual_path=False):
        print('Processing Folder: {0}'.format(path))

        full_synapse_path = self.get_synapse_path(path, virtual_path)
        synapse_parent_path = os.path.dirname(full_synapse_path)
        synapse_parent = self.get_synapse_folder(synapse_parent_path)

        if not synapse_parent:
            self._hasErrors = True
            print('  -! Cannot create folder, parent not found.')
            return

        folder_name = os.path.basename(full_synapse_path)

        print('  -> {0}'.format(full_synapse_path))

        synapse_folder = Folder(name=folder_name, parent=synapse_parent)

        if self._dry_run:
            # Give the folder a fake id so it doesn't blow up when this folder is used as a parent.
            synapse_folder.id = 'syn0'
        else:
            max_attempts = 5
            attempt_number = 0

            while attempt_number < max_attempts and not synapse_folder.get('id', None):
                try:
                    attempt_number += 1
                    synapse_folder = self._synapse_client.store(
                        synapse_folder, forceVersion=False)
                except Exception as ex:
                    print('  -! Error creating folder: {0}'.format(str(ex)))
                    if attempt_number < max_attempts:
                        sleep_time = random.randint(1, 5)
                        print(
                            '  -! Retrying in {0} seconds'.format(sleep_time))
                        time.sleep(sleep_time)

        if not synapse_folder.get('id', None):
            self._hasErrors = True
            print('  -! Failed to create folder')
        else:
            if attempt_number > 1:
                print('  -> Folder created')
            self.set_synapse_folder(full_synapse_path, synapse_folder)

    def upload_file_to_synapse(self, local_file):
        # Skip empty files since these will error when uploading via the synapseclient.
        if (os.path.getsize(local_file) < 1):
            print('Skipping Empty File: {0}'.format(local_file))
            return
        else:
            print('Processing File: {0}'.format(local_file))

        full_synapse_path = self.get_synapse_path(local_file)
        synapse_parent_path = os.path.dirname(full_synapse_path)
        synapse_parent = self.get_synapse_folder(synapse_parent_path)

        if not synapse_parent:
            self._hasErrors = True
            print('  -! Cannot upload file, parent not found.')
            return

        print('  -> {0}'.format(full_synapse_path))

        synapse_file = File(path=local_file, parent=synapse_parent)

        if not self._dry_run:
            max_attempts = 5
            attempt_number = 0

            while attempt_number < max_attempts and not synapse_file.get('id', None):
                try:
                    attempt_number += 1
                    synapse_file = self._synapse_client.store(
                        synapse_file, forceVersion=False)
                except Exception as ex:
                    print('  -! Error uploading file: {0}'.format(str(ex)))
                    if attempt_number < max_attempts:
                        sleep_time = random.randint(1, 5)
                        print(
                            '  -! Retrying in {0} seconds'.format(sleep_time))
                        time.sleep(sleep_time)

            if not synapse_file.get('id', None):
                self._hasErrors = True
                print('  -! Failed to upload file')
            else:
                if attempt_number > 1:
                    print('  -> File uploaded')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project_id', metavar='project-id',
                        help='Synapse Project ID to upload to (e.g., syn123456789).')
    parser.add_argument('local_folder_path', metavar='local-folder-path',
                        help='Path of the folder to upload.')
    parser.add_argument('-r', '--remote-folder-path',
                        help='Folder to upload to in Synapse.', default=None)
    parser.add_argument('-u', '--username',
                        help='Synapse username.', default=None)
    parser.add_argument('-p', '--password',
                        help='Synapse password.', default=None)
    parser.add_argument('-d', '--dry-run', help='Dry run only. Do not upload any folders or files.',
                        default=False, action='store_true')

    args = parser.parse_args()

    SynapseUploader(
        args.project_id,
        args.local_folder_path,
        remote_path=args.remote_folder_path,
        dry_run=args.dry_run,
        username=args.username,
        password=args.password
    ).start()


if __name__ == "__main__":
    main()
