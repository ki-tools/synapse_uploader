import os
import time
import random
import concurrent.futures
import threading
import logging
import functools
from datetime import datetime
import synapseclient as syn
from .utils import Utils
from synapsis import Synapsis


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
                 force_upload=False):

        self._synapse_entity_id = synapse_entity_id
        self._local_path = Utils.expand_path(local_path)
        self._remote_path = remote_path
        self._max_depth = max_depth
        self._max_threads = max_threads
        self._force_upload = force_upload

        self.start_time = None
        self.end_time = None

        self._thread_lock = threading.Lock()
        self._synapse_parents = {}
        self.errors = []

        if remote_path:
            self._remote_path = remote_path.replace(' ', '').lstrip(os.sep).rstrip(os.sep)
            if len(self._remote_path) == 0:
                self._remote_path = None

    def execute(self):
        self.start_time = datetime.now()

        if self._max_depth > self.MAX_SYNAPSE_DEPTH:
            self._show_error('Maximum depth must be less than or equal to {0}.'.format(self.MAX_SYNAPSE_DEPTH))
            return self

        if self._max_depth < self.MIN_SYNAPSE_DEPTH:
            self._show_error('Maximum depth must be greater than or equal to {0}.'.format(self.MIN_SYNAPSE_DEPTH))
            return self

        if self._force_upload:
            logging.info('Forcing upload. Entity versions will be incremented.')

        remote_entity = Synapsis.get(self._synapse_entity_id, downloadFile=False)
        remote_entity_type = Synapsis.ConcreteTypes.get(remote_entity)
        if not (remote_entity_type.is_project or remote_entity_type.is_folder or remote_entity_type.is_file):
            self._show_error('Remote entity must be a project, folder, or file. Found {0}'.format(type(remote_entity)))
            return self

        if remote_entity_type.is_project or remote_entity_type.is_folder:
            self._set_synapse_parent(remote_entity)

        local_entity_is_file = False

        if os.path.isfile(self._local_path):
            local_type = 'File'
            local_entity_is_file = True
        elif os.path.isdir(self._local_path):
            local_type = 'Directory'
        else:
            self._show_error('Local entity must be a directory or file: {0}'.format(self._local_path))
            return self

        if remote_entity_type.is_file and not local_entity_is_file:
            self._show_error('Local entity must be a file when remote entity is a file: {0}'.format(self._local_path))
            return self

        if remote_entity_type.is_file and self._remote_path:
            self._show_error('Cannot specify a remote path when remote entity is a file: {0}'.format(self._local_path))
            return self

        logging.info(
            'Uploading to {0}: {1} ({2})'.format(remote_entity_type.name, remote_entity.name, remote_entity.id))
        logging.info('Uploading {0}: {1}'.format(local_type, self._local_path))

        if remote_entity_type.is_file:
            remote_file_name = remote_entity['_file_handle']['fileName']
            local_file_name = os.path.basename(self._local_path)
            if local_file_name != remote_file_name:
                self._show_error('Local filename: {0} does not match remote file name: {1}'.format(local_file_name,
                                                                                                   remote_file_name))
                return self

            remote_parent = Synapsis.get(remote_entity.get('parentId'))
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
        return self

    def _upload_folder(self, executor, local_path, synapse_parent):
        if not synapse_parent:
            self._show_error('Parent not found, cannot execute folder: {0}'.format(local_path))
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
            self._show_error('Parent not found, cannot create folder: {0}'.format(path))
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
                synapse_folder = Synapsis.store(syn.Folder(name=folder_name, parent=synapse_parent),
                                                forceVersion=self._force_upload)
            except Exception as ex:
                exception = ex
                logging.error('[Folder ERROR] {0} -> {1} : {2}'.format(path, full_synapse_path, str(ex)))
                if attempt_number < max_attempts:
                    sleep_time = random.randint(1, 5)
                    logging.info('[Folder RETRY in {0}s] {1} -> {2}'.format(sleep_time, path, full_synapse_path))
                    time.sleep(sleep_time)

        if exception:
            self._show_error('[Folder FAILED] {0} -> {1} : {2}'.format(path, full_synapse_path, str(exception)))
        else:
            logging.info('[Folder] {0} -> {1}'.format(path, full_synapse_path))
            self._set_synapse_parent(synapse_folder)

        return synapse_folder

    def _upload_file_to_synapse(self, local_file, synapse_parent):
        synapse_file = None

        if not synapse_parent:
            self._show_error('Parent not found, cannot execute file: {0}'.format(local_file))
            return synapse_file

        # Skip empty files since these will error when uploading via the synapseclient.
        local_file_size = os.path.getsize(local_file)
        if local_file_size < 1:
            logging.info('Skipping empty file: {0}'.format(local_file))
            return synapse_file

        file_name = os.path.basename(local_file)
        full_synapse_path = self._get_synapse_path(file_name, synapse_parent)

        max_attempts = 5
        attempt_number = 0
        exception = None
        log_success_prefix = 'File'

        while attempt_number < max_attempts and not synapse_file:
            try:
                attempt_number += 1
                exception = None
                needs_upload = True

                file_obj = self._find_synapse_file(synapse_parent['id'], local_file)
                if file_obj:
                    file_obj.path = local_file
                    if self._force_upload:
                        Synapsis.cache.remove(file_obj)
                    else:
                        if file_obj['_file_handle']['contentSize'] == local_file_size and \
                                file_obj['_file_handle']['contentMd5'] == Utils.get_md5(local_file):
                            needs_upload = False
                            log_success_prefix = 'File is Current'
                else:
                    file_obj = syn.File(path=local_file, name=file_name, parent=synapse_parent)

                if needs_upload or self._force_upload:
                    synapse_file = Synapsis.store(file_obj, forceVersion=self._force_upload)
            except Exception as ex:
                exception = ex
                logging.error('[File ERROR] {0} -> {1} : {2}'.format(local_file, full_synapse_path, str(ex)))
                if attempt_number < max_attempts:
                    sleep_time = random.randint(1, 5)
                    logging.info('[File RETRY in {0}s] {1} -> {2}'.format(sleep_time, local_file, full_synapse_path))
                    time.sleep(sleep_time)

        if exception:
            self._show_error('[File FAILED] {0} -> {1} : {2}'.format(local_file, full_synapse_path, str(exception)))
        else:
            logging.info('[{0}] {1} -> {2}'.format(log_success_prefix, local_file, full_synapse_path))

        return synapse_file

    def _find_synapse_file(self, synapse_parent_id, local_file_path):
        """Finds a Synapse file by its parent and local_file name."""
        children = self._get_synapse_children(synapse_parent_id)

        for child in children:
            if child['name'] == os.path.basename(local_file_path):
                syn_file = Synapsis.get(child['id'], downloadFile=False)
                # Synapse can store a file with two names: 1) The entity name 2) the actual filename.
                # Check that the actual filename matches the local file name to ensure we have the same file.
                if syn_file['_file_handle']['fileName'] != os.path.basename(local_file_path):
                    for find_child in children:
                        if find_child == child:
                            continue
                        syn_child = Synapsis.get(find_child['id'], downloadFile=False)
                        if syn_child['_file_handle']['fileName'] == os.path.basename(local_file_path):
                            return syn_child
                return syn_file

        return None

    LRU_MAXSIZE = (os.cpu_count() or 1) * 5

    @functools.lru_cache(maxsize=LRU_MAXSIZE, typed=True)
    def _get_synapse_children(self, synapse_parent_id):
        """Gets the child files metadata for a parent Synapse container."""
        return list(Synapsis.getChildren(synapse_parent_id, includeTypes=["file"]))

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

    def _show_error(self, msg):
        self.errors.append(msg)
        logging.error(msg)
