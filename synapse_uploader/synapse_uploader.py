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

import os
import getpass
import time
import random
import concurrent.futures
import threading
import logging
import synapseclient
from synapseclient import Project, Folder, File


class SynapseUploader:
    # Maximum number of files per Project/Folder in Synapse.
    MAX_SYNAPSE_DEPTH = 10000

    # Minimum depth for Projects/Folders in Synapse.
    MIN_SYNAPSE_DEPTH = 2

    def __init__(self,
                 synapse_project_id,
                 local_path,
                 remote_path=None,
                 max_depth=MAX_SYNAPSE_DEPTH,
                 max_threads=None,
                 username=None,
                 password=None,
                 synapse_client=None):

        self._synapse_project_id = synapse_project_id
        self._local_path = local_path.rstrip(os.sep)
        self._remote_path = remote_path
        self._max_depth = max_depth
        self._max_threads = max_threads
        self._username = username
        self._password = password
        self._synapse_client = synapse_client

        self._thread_lock = threading.Lock()
        self._synapse_parents = {}
        self._hasErrors = False

        if max_depth > self.MAX_SYNAPSE_DEPTH:
            raise Exception('Maximum depth must be less than or equal to {0}.'.format(self.MAX_SYNAPSE_DEPTH))

        if max_depth < self.MIN_SYNAPSE_DEPTH:
            raise Exception('Maximum depth must be greater than or equal to {0}.'.format(self.MIN_SYNAPSE_DEPTH))

        if remote_path:
            self._remote_path = remote_path.replace(' ', '').lstrip(os.sep).rstrip(os.sep)
            if len(self._remote_path) == 0:
                self._remote_path = None

    def upload(self):
        logging.info('Uploading to Project: {0}'.format(self._synapse_project_id))
        logging.info('Uploading Directory: {0}'.format(self._local_path))

        if self._remote_path:
            logging.info('Uploading To: {0}'.format(self._remote_path))

        if not self.login():
            logging.error('Could not log into Synapse. Aborting.')
            return

        project = self._synapse_client.get(Project(id=self._synapse_project_id))
        self.set_synapse_parent(project)

        parent = project

        # Create the remote_path if specified.
        if self._remote_path:
            full_path = ''
            for folder in filter(None, self._remote_path.split(os.sep)):
                full_path = os.path.join(full_path, folder)
                parent = self.create_directory_in_synapse(full_path, parent)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self._max_threads) as executor:
            self.upload_folder(executor, self._local_path, parent)

        completion_status = 'With Errors' if self._hasErrors else 'Successfully'

        logging.info('Upload Completed {0}'.format(completion_status))

    def login(self):
        if self._synapse_client and self._synapse_client.credentials:
            logging.info('Already logged into Synapse.')
        else:
            logging.info('Logging into Synapse...')
            self._username = self._username or os.getenv('SYNAPSE_USERNAME')
            self._password = self._password or os.getenv('SYNAPSE_PASSWORD')

            if not self._username:
                self._username = input('Synapse username: ')

            if not self._password:
                self._password = getpass.getpass(prompt='Synapse password: ')

            try:
                self._synapse_client = synapseclient.Synapse()
                self._synapse_client.login(self._username, self._password, silent=True)
            except Exception as ex:
                self._synapse_client = None
                logging.error('Synapse login failed: {0}'.format(str(ex)))

        return self._synapse_client is not None

    def set_synapse_parent(self, parent):
        with self._thread_lock:
            self._synapse_parents[parent.id] = parent

    def get_synapse_parent(self, parent_id):
        with self._thread_lock:
            return self._synapse_parents.get(parent_id, None)

    def get_synapse_path(self, folder_or_file_name, parent):
        segments = []

        if isinstance(parent, Project):
            segments.insert(0, parent.name)
        else:
            next_parent = parent
            while next_parent:
                segments.insert(0, next_parent.name)
                next_parent = self.get_synapse_parent(next_parent.parentId)

        segments.append(folder_or_file_name)

        return os.path.join(*segments)

    def get_dirs_and_files(self, local_path):
        dirs = []
        files = []

        with os.scandir(local_path) as iter:
            for entry in iter:
                if entry.is_dir(follow_symlinks=False):
                    dirs.append(entry)
                else:
                    files.append(entry)

        dirs.sort(key=lambda f: f.name)
        files.sort(key=lambda f: f.name)

        return dirs, files

    def upload_folder(self, executor, local_path, synapse_parent):
        parent = synapse_parent

        dirs, files = self.get_dirs_and_files(local_path)

        child_count = 0

        # Upload the files
        for file_entry in files:
            if (child_count + 1) >= self._max_depth:
                parent = self.create_directory_in_synapse('more', parent)
                child_count = 0

            executor.submit(self.upload_file_to_synapse, file_entry.path, parent)
            child_count += 1

        # Upload the directories.
        for dir_entry in dirs:
            if (child_count + 1) >= self._max_depth:
                parent = self.create_directory_in_synapse('more', parent)
                child_count = 0

            syn_dir = self.create_directory_in_synapse(dir_entry.path, parent)
            self.upload_folder(executor, dir_entry.path, syn_dir)
            child_count += 1

    def create_directory_in_synapse(self, path, synapse_parent):
        if not synapse_parent:
            self._hasErrors = True
            logging.error('  -! Parent not found, cannot create folder: {0}'.format(path))
            return

        folder_name = os.path.basename(path)
        full_synapse_path = self.get_synapse_path(folder_name, synapse_parent)

        logging.info('Processing Folder: {0}{1}  -> {2}'.format(path, os.linesep, full_synapse_path))

        synapse_folder = Folder(name=folder_name, parent=synapse_parent)

        max_attempts = 5
        attempt_number = 0

        while attempt_number < max_attempts and not synapse_folder.get('id', None):
            try:
                attempt_number += 1
                synapse_folder = self._synapse_client.store(synapse_folder, forceVersion=False)
            except Exception as ex:
                logging.error('  -! Error creating folder: {0}'.format(str(ex)))
                if attempt_number < max_attempts:
                    sleep_time = random.randint(1, 5)
                    logging.info('  -! Retrying in {0} seconds'.format(sleep_time))
                    time.sleep(sleep_time)

        if not synapse_folder.get('id', None):
            self._hasErrors = True
            logging.error('  -! Failed to create folder: {0}'.format(path))
        else:
            if attempt_number > 1:
                logging.info('  -> Folder created')
            self.set_synapse_parent(synapse_folder)

        return synapse_folder

    def upload_file_to_synapse(self, local_file, synapse_parent):
        if not synapse_parent:
            self._hasErrors = True
            logging.error('  -! Parent not found, cannot upload file: {0}'.format(local_file))
            return None

        # Skip empty files since these will error when uploading via the synapseclient.
        if (os.path.getsize(local_file) < 1):
            logging.info('Skipping Empty File: {0}'.format(local_file))
            return None

        file_name = os.path.basename(local_file)
        full_synapse_path = self.get_synapse_path(file_name, synapse_parent)

        logging.info('Processing File: {0}{1}  -> {2}'.format(local_file, os.linesep, full_synapse_path))

        synapse_file = File(path=local_file, parent=synapse_parent)

        max_attempts = 5
        attempt_number = 0

        while attempt_number < max_attempts and not synapse_file.get('id', None):
            try:
                attempt_number += 1
                synapse_file = self._synapse_client.store(synapse_file, forceVersion=False)
            except Exception as ex:
                logging.error('  -! Error uploading file: {0}'.format(str(ex)))
                if attempt_number < max_attempts:
                    sleep_time = random.randint(1, 5)
                    logging.info('  -! Retrying in {0} seconds'.format(sleep_time))
                    time.sleep(sleep_time)

        if not synapse_file.get('id', None):
            self._hasErrors = True
            logging.error('  -! Failed to upload file: {0}'.format(local_file))
        else:
            if attempt_number > 1:
                logging.info('  -> File uploaded')

        return synapse_file
