# Copyright 2018-present, Bill & Melinda Gates Foundation
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
import uuid
import synapseclient
from synapseclient import Project, Folder, File


class SynapseTestHelper:
    """
    Test helper for working with Synapse.
    """
    _test_id = uuid.uuid4().hex
    _trash = []
    _synapse_client = None

    def client(self):
        if not self._synapse_client:
            syn_user = os.getenv('SYNAPSE_USERNAME')
            syn_pass = os.getenv('SYNAPSE_PASSWORD')

            self._synapse_client = synapseclient.Synapse()
            self._synapse_client.login(syn_user, syn_pass, silent=True)

        return self._synapse_client

    def test_id(self):
        """
        Gets a unique value to use as a test identifier.
        This string can be used to help identify the test instance that created the object.
        """
        return self._test_id

    def uniq_name(self, prefix='', postfix=''):
        return "{0}{1}_{2}{3}".format(prefix, self.test_id(), uuid.uuid4().hex, postfix)

    def dispose_of(self, *syn_objects):
        """
        Adds a Synapse object to the list of objects to be deleted.
        """
        for syn_object in syn_objects:
            if syn_object in self._trash:
                continue
            self._trash.append(syn_object)

    def dispose(self):
        """
        Cleans up any Synapse objects that were created during testing.
        This method needs to be manually called after each or all tests are done.
        """
        projects = []
        folders = []
        files = []
        others = []

        for obj in self._trash:
            if isinstance(obj, Project):
                projects.append(obj)
            elif isinstance(obj, Folder):
                folders.append(obj)
            elif isinstance(obj, File):
                files.append(obj)
            else:
                others.append(obj)

        for syn_obj in files:
            try:
                self.client().delete(syn_obj)
            except:
                pass
            self._trash.remove(syn_obj)

        for syn_obj in folders:
            try:
                self.client().delete(syn_obj)
            except:
                pass
            self._trash.remove(syn_obj)

        for syn_obj in projects:
            try:
                self.client().delete(syn_obj)
            except:
                pass
            self._trash.remove(syn_obj)

        for obj in others:
            print('WARNING: Non-Supported object found: {0}'.format(obj))
            self._trash.remove(obj)

    def create_project(self, **kwargs):
        """
        Creates a new Project and adds it to the trash queue.
        """
        if not 'name' in kwargs:
            kwargs['name'] = self.uniq_name(prefix=kwargs.get('prefix', ''))

        kwargs.pop('prefix', None)

        project = self.client().store(Project(**kwargs))
        self.dispose_of(project)
        return project

    def create_file(self, **kwargs):
        """
        Creates a new File and adds it to the trash queue.
        """
        if not 'name' in kwargs:
            kwargs['name'] = self.uniq_name(prefix=kwargs.get('prefix', ''))

        kwargs.pop('prefix', None)

        file = self.client().store(File(**kwargs))
        self.dispose_of(file)
        return file
