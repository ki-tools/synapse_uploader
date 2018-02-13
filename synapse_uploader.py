#!/usr/bin/python

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

import sys, os
import synapseclient
from synapseclient import Project, Folder, File

class SynapseUploader:


    def __init__(self, synapse_project, local_path, remote_path=None):
        self._synapse_project = synapse_project
        self._local_path = local_path.rstrip('/')
        self._remote_path = None
        self._synapse_folders = {}
        
        if remote_path != None and len(remote_path.strip()) > 0:
            self._remote_path = remote_path.strip().lstrip('/').rstrip('/')
            if len(self._remote_path) == 0:
                self._remote_path = None



    def get_synapse_folder(self, synapse_path):
        return self._synapse_folders[synapse_path]



    def set_synapse_folder(self, synapse_path, parent):
        self._synapse_folders[synapse_path] = parent



    def login(self):
        print('Logging into Synapse...')
        syn_user = os.environ['SYNAPSE_USER']
        syn_pass = os.environ['SYNAPSE_PASSWORD']
        
        self._synapse_client = synapseclient.Synapse()
        self._synapse_client.login(syn_user, syn_pass, silent=True)


    def get_synapse_path(self, local_path, virtual_path=False):
        if virtual_path:
            return os.path.join(self._synapse_project, local_path)
        else:
            return os.path.join(self._synapse_project
                                ,(self._remote_path if self._remote_path else '')
                                ,local_path.replace(self._local_path + '/', '')
                                )



    def create_directory_in_synapse(self, path, virtual_path=False):
        print('Processing Folder: {0}'.format(path))
        
        full_synapse_path = self.get_synapse_path(path, virtual_path)
        synapse_parent_path = os.path.dirname(full_synapse_path)
        synapse_parent = self.get_synapse_folder(synapse_parent_path)
        folder_name = os.path.basename(full_synapse_path)

        print('  -> {0}'.format(full_synapse_path))
        synapse_folder = self._synapse_client.store(Folder(folder_name, parent=synapse_parent))
    
        self.set_synapse_folder(full_synapse_path, synapse_folder)



    def upload_file_to_synapse(self, local_file):
        print('Processing File: {0}'.format(local_file))

        full_synapse_path = self.get_synapse_path(local_file)
        synapse_parent_path = os.path.dirname(full_synapse_path)
        synapse_parent = self.get_synapse_folder(synapse_parent_path)
        
        print('  -> {0}'.format(full_synapse_path))
        self._synapse_client.store(File(local_file, parent=synapse_parent))



    def start(self):
        print('Uploading to Project: {0}'.format(self._synapse_project))
        print('Uploading Directory: {0}'.format(self._local_path))

        if self._remote_path != None:
            print('Uploading To: {0}'.format(self._remote_path))

        self.login()

        project = self._synapse_client.get(Project(id = self._synapse_project))
        self.set_synapse_folder(self._synapse_project, project)

        # Create the remote_path if specified.
        if self._remote_path != None:
            full_path = ''
            for folder in filter(None, self._remote_path.split('/')):
                full_path = os.path.join(full_path, folder)
                self.create_directory_in_synapse(full_path, virtual_path=True)

        # Create the folders and upload the files.
        for dirpath, dirnames, filenames in os.walk(self._local_path):
            
            if dirpath != self._local_path:
                self.create_directory_in_synapse(dirpath)

            for filename in filenames:
                full_file_name = os.path.join(dirpath, filename)
                self.upload_file_to_synapse(full_file_name)
        print('Upload Completed Successfully.')



def main(argv):
    synapse_project = argv[0]
    local_path = argv[1]
    
    remote_path = None
    if len(argv) == 3:
        remote_path = argv[2]
    
    SynapseUploader(synapse_project, local_path, remote_path).start()



if __name__ == "__main__":
    main(sys.argv[1:])
