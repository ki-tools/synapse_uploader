import os
import getpass
import time
import random
import concurrent.futures
import threading
import logging
from datetime import datetime, timedelta
import synapseclient as syn
from .utils import Utils


class SynapseUploader:
    # Maximum number of files per Project/Folder in Synapse.
    MAX_SYNAPSE_DEPTH = 10000

    # Minimum depth for Projects/Folders in Synapse.
    MIN_SYNAPSE_DEPTH = 2

    def __init__(self,
                 synapse_entity_id,
                 local_path,
                 remote_path=None,
                 max_depth=MAX_SYNAPSE_DEPTH,
                 max_threads=None,
                 username=None,
                 password=None,
                 synapse_client=None,
                 force_upload=False):

        self._synapse_entity_id = synapse_entity_id
        self._local_path = Utils.expand_path(local_path)
        self._remote_path = remote_path
        self._max_depth = max_depth
        self._max_threads = max_threads
        self._username = username
        self._password = password
        self._synapse_client = synapse_client
        self._force_upload = force_upload

        self.start_time = None
        self.end_time = None

        self._thread_lock = threading.Lock()
        self._synapse_parents = {}
        self.has_errors = False

        if max_depth > self.MAX_SYNAPSE_DEPTH:
            raise Exception('Maximum depth must be less than or equal to {0}.'.format(self.MAX_SYNAPSE_DEPTH))

        if max_depth < self.MIN_SYNAPSE_DEPTH:
            raise Exception('Maximum depth must be greater than or equal to {0}.'.format(self.MIN_SYNAPSE_DEPTH))

        if remote_path:
            self._remote_path = remote_path.replace(' ', '').lstrip(os.sep).rstrip(os.sep)
            if len(self._remote_path) == 0:
                self._remote_path = None

    def execute(self):
        self.start_time = datetime.now()

        if not self._synapse_login():
            self.has_errors = True
            logging.error('Could not log into Synapse. Aborting.')
            return

        if self._force_upload:
            # NOTE: The cache must be purged in order to force the file to re-upload.
            print('Forcing upload. Cache will be purged. Entity versions will be incremented.')
            # Set the purge date way in the future to account for local time slop.
            purge_count = self._synapse_client.cache.purge(datetime.today() + timedelta(weeks=52))
            print('{0} files purged from cache.'.format(purge_count))

        remote_entity = self._synapse_client.get(self._synapse_entity_id, downloadFile=False)
        remote_entity_is_file = False

        if isinstance(remote_entity, syn.Project):
            remote_type = 'Project'
            self._set_synapse_parent(remote_entity)
        elif isinstance(remote_entity, syn.Folder):
            remote_type = 'Folder'
            self._set_synapse_parent(remote_entity)
        elif isinstance(remote_entity, syn.File):
            remote_type = 'File'
            remote_entity_is_file = True
        else:
            raise Exception('Remote entity must be a project, folder, or file. Found {0}'.format(type(remote_entity)))

        local_entity_is_file = False

        if os.path.isfile(self._local_path):
            local_type = 'File'
            local_entity_is_file = True
        elif os.path.isdir(self._local_path):
            local_type = 'Directory'
        else:
            raise Exception('Local entity must be a directory or file: {0}'.format(self._local_path))

        if remote_entity_is_file and not local_entity_is_file:
            raise Exception('Local entity must be a file when remote entity is a file: {0}'.format(self._local_path))

        if remote_entity_is_file and self._remote_path:
            raise Exception(
                'Cannot specify a remote path when remote entity is a file: {0}'.format(self._local_path))

        logging.info('Uploading to {0}: {1} ({2})'.format(remote_type, remote_entity.name, remote_entity.id))
        logging.info('Uploading {0}: {1}'.format(local_type, self._local_path))

        if remote_entity_is_file:
            remote_file_name = remote_entity['_file_handle']['fileName']
            local_file_name = os.path.basename(self._local_path)
            if local_file_name != remote_file_name:
                raise Exception('Local filename: {0} does not match remote file name: {1}'.format(local_file_name,
                                                                                                  remote_file_name))

            remote_parent = self._synapse_client.get(remote_entity.get('parentId'))
            self._set_synapse_parent(remote_parent)
            self._upload_file_to_synapse(self._local_path, remote_parent)
        else:
            if self._remote_path:
                logging.info('Uploading to: {0}'.format(self._remote_path))

            remote_parent = remote_entity

            # Create the remote_path if specified.
            if self._remote_path:
                full_path = ''
                for folder in filter(None, self._remote_path.split(os.sep)):
                    full_path = os.path.join(full_path, folder)
                    remote_parent = self._create_folder_in_synapse(full_path, remote_parent)

            with concurrent.futures.ThreadPoolExecutor(max_workers=self._max_threads) as executor:
                self._upload_folder(executor, self._local_path, remote_parent)

        self.end_time = datetime.now()
        logging.info('')
        logging.info('Run time: {0}'.format(self.end_time - self.start_time))

        if self.has_errors:
            logging.error('Finished with errors. Please see log file.')
        else:
            logging.info('Finished successfully.')

    def _synapse_login(self):
        if self._synapse_client and self._synapse_client.credentials:
            logging.info('Already logged into Synapse.')
        else:
            self._username = self._username or os.getenv('SYNAPSE_USERNAME')
            self._password = self._password or os.getenv('SYNAPSE_PASSWORD')

            if not self._username:
                self._username = input('Synapse username: ')

            if not self._password:
                self._password = getpass.getpass(prompt='Synapse password: ')

            logging.info('Logging into Synapse as: {0}'.format(self._username))
            try:
                self._synapse_client = syn.Synapse(skip_checks=True)
                self._synapse_client.login(self._username, self._password, silent=True)
            except Exception as ex:
                self._synapse_client = None
                self.has_errors = True
                logging.error('Synapse login failed: {0}'.format(str(ex)))

        return self._synapse_client is not None

    def _upload_folder(self, executor, local_path, synapse_parent):
        if not synapse_parent:
            self.has_errors = True
            logging.error('Parent not found, cannot execute folder: {0}'.format(local_path))
            return

        parent = synapse_parent

        dirs, files = self._get_dirs_and_files(local_path)

        child_count = 0

        # Upload the files
        for file_entry in files:
            if (child_count + 1) >= self._max_depth:
                parent = self._create_folder_in_synapse('more', parent)
                child_count = 0

            executor.submit(self._upload_file_to_synapse, file_entry.path, parent)
            child_count += 1

        # Upload the directories.
        for dir_entry in dirs:
            if (child_count + 1) >= self._max_depth:
                parent = self._create_folder_in_synapse('more', parent)
                child_count = 0

            syn_dir = self._create_folder_in_synapse(dir_entry.path, parent)
            self._upload_folder(executor, dir_entry.path, syn_dir)
            child_count += 1

    def _create_folder_in_synapse(self, path, synapse_parent):
        synapse_folder = None

        if not synapse_parent:
            self.has_errors = True
            logging.error('Parent not found, cannot create folder: {0}'.format(path))
            return synapse_folder

        folder_name = os.path.basename(path)
        full_synapse_path = self._get_synapse_path(folder_name, synapse_parent)

        max_attempts = 5
        attempt_number = 0
        exception = None

        while attempt_number < max_attempts and not synapse_folder:
            try:
                attempt_number += 1
                exception = None
                synapse_folder = self._synapse_client.store(syn.Folder(name=folder_name, parent=synapse_parent),
                                                            forceVersion=self._force_upload)
            except Exception as ex:
                exception = ex
                logging.error('[Folder ERROR] {0} -> {1} : {2}'.format(path, full_synapse_path, str(ex)))
                if attempt_number < max_attempts:
                    sleep_time = random.randint(1, 5)
                    logging.info('[Folder RETRY in {0}s] {1} -> {2}'.format(sleep_time, path, full_synapse_path))
                    time.sleep(sleep_time)

        if exception:
            self.has_errors = True
            logging.error('[Folder FAILED] {0} -> {1} : {2}'.format(path, full_synapse_path, str(exception)))
        else:
            logging.info('[Folder] {0} -> {1}'.format(path, full_synapse_path))
            self._set_synapse_parent(synapse_folder)

        return synapse_folder

    def _upload_file_to_synapse(self, local_file, synapse_parent):
        synapse_file = None

        if not synapse_parent:
            self.has_errors = True
            logging.error('Parent not found, cannot execute file: {0}'.format(local_file))
            return synapse_file

        # Skip empty files since these will error when uploading via the synapseclient.
        if os.path.getsize(local_file) < 1:
            logging.info('Skipping empty file: {0}'.format(local_file))
            return synapse_file

        file_name = os.path.basename(local_file)
        full_synapse_path = self._get_synapse_path(file_name, synapse_parent)

        max_attempts = 5
        attempt_number = 0
        exception = None

        while attempt_number < max_attempts and not synapse_file:
            try:
                attempt_number += 1
                exception = None
                synapse_file = self._synapse_client.store(
                    syn.File(path=local_file, name=file_name, parent=synapse_parent),
                    forceVersion=self._force_upload)
            except Exception as ex:
                exception = ex
                logging.error('[File ERROR] {0} -> {1} : {2}'.format(local_file, full_synapse_path, str(ex)))
                if attempt_number < max_attempts:
                    sleep_time = random.randint(1, 5)
                    logging.info('[File RETRY in {0}s] {1} -> {2}'.format(sleep_time, local_file, full_synapse_path))
                    time.sleep(sleep_time)

        if exception:
            self.has_errors = True
            logging.error('[File FAILED] {0} -> {1} : {2}'.format(local_file, full_synapse_path, str(exception)))
        else:
            logging.info('[File] {0} -> {1}'.format(local_file, full_synapse_path))

        return synapse_file

    def _set_synapse_parent(self, parent):
        with self._thread_lock:
            self._synapse_parents[parent.id] = parent

    def _get_synapse_parent(self, parent_id):
        with self._thread_lock:
            return self._synapse_parents.get(parent_id, None)

    def _get_synapse_path(self, folder_or_file_name, parent):
        segments = []

        if isinstance(parent, syn.Project):
            segments.insert(0, parent.name)
        else:
            next_parent = parent
            while next_parent:
                segments.insert(0, next_parent.name)
                next_parent = self._get_synapse_parent(next_parent.parentId)

        segments.append(folder_or_file_name)

        return os.path.join(*segments)

    def _get_dirs_and_files(self, local_path):
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
