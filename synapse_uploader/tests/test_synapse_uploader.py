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
import getpass
import pytest
from synapse_uploader.synapse_uploader import SynapseUploader


def mkdir(*path_segments):
    path = os.path.join(*path_segments)
    if not os.path.isdir(path):
        os.mkdir(path)
    return path


def mkfile(*path_segments, content=str(uuid.uuid4())):
    path = os.path.join(*path_segments)
    with open(path, 'w') as file:
        file.write(content)
    return path


def get_syn_folders(syn_client, syn_parent):
    syn_folders = list(syn_client.getChildren(
        syn_parent, includeTypes=['folder']))
    syn_folder_names = [s['name'] for s in syn_folders]
    return syn_folders, syn_folder_names


def get_syn_files(syn_client, syn_parent):
    syn_files = list(syn_client.getChildren(syn_parent, includeTypes=['file']))
    syn_file_names = [s['name'] for s in syn_files]
    return syn_files, syn_file_names


def test_synapse_project_value():
    syn_id = 'syn123'
    syn_uploader = SynapseUploader(syn_id, 'None')
    assert syn_uploader._synapse_project == syn_id


def test_local_path_value():
    local_path = '/one/two/three'
    syn_uploader = SynapseUploader('None', local_path)
    assert syn_uploader._local_path == local_path


def test_remote_path_value():
    path_segments = ['one', 'two', 'three']
    remote_path = os.path.join(*path_segments)

    syn_uploader = SynapseUploader('None', 'None', remote_path=remote_path)
    assert syn_uploader._remote_path == remote_path

    # Strips spaces and separators
    syn_uploader = SynapseUploader('None', 'None', remote_path='{0} {0}'.format(os.sep))
    assert syn_uploader._remote_path is None

    syn_uploader = SynapseUploader('None', 'None', remote_path='{0} one {0}'.format(os.sep))
    assert syn_uploader._remote_path == 'one'

    syn_uploader = SynapseUploader('None', 'None', remote_path='{0} one {0} two {0} three {0}'.format(os.sep))
    assert syn_uploader._remote_path == 'one/two/three'


def test_max_depth_value():
    max_depth = 10
    syn_uploader = SynapseUploader('None', 'None', max_depth=max_depth)
    assert syn_uploader._max_depth == max_depth

    with pytest.raises(Exception) as ex:
        SynapseUploader('None', 'None', max_depth=(SynapseUploader.MAX_SYNAPSE_DEPTH + 1))
    assert str(ex.value) == 'Maximum depth must be less than or equal to 10000.'


def test_min_depth_value():
    with pytest.raises(Exception) as ex:
        SynapseUploader('None', 'None', max_depth=(SynapseUploader.MIN_SYNAPSE_DEPTH - 1))
    assert str(ex.value) == 'Maximum depth must be greater than or equal to 2.'


def test_username_value():
    username = 'test_user'
    syn_uploader = SynapseUploader('None', 'None', username=username)
    assert syn_uploader._username == username


def test_password_value():
    password = 'test_password'
    syn_uploader = SynapseUploader('None', 'None', password=password)
    assert syn_uploader._password == password


def test_synapse_client_value():
    client = object()
    syn_uploader = SynapseUploader('None', 'None', synapse_client=client)
    assert syn_uploader._synapse_client == client


def test_login(syn_client, monkeypatch, mocker):
    # Uses ENV
    syn_uploader = SynapseUploader('None', 'None')
    syn_uploader.login() is True
    assert syn_uploader._synapse_client is not None

    # Uses the passed in params
    syn_uploader = SynapseUploader('None', 'None',
                                   username=os.environ['SYNAPSE_USERNAME'], password=os.environ['SYNAPSE_PASSWORD'])
    assert syn_uploader.login() is True
    assert syn_uploader._synapse_client is not None

    # Uses the passed in client
    syn_uploader = SynapseUploader('None', 'None', synapse_client=syn_client)
    syn_uploader.login() is True
    assert syn_uploader._synapse_client == syn_client

    # Fails to login
    syn_uploader = SynapseUploader('None', 'None', username=uuid.uuid4(), password=uuid.uuid4())
    assert syn_uploader.login() is False
    assert syn_uploader._synapse_client is None

    # Prompts for the username and password
    with monkeypatch.context() as mp:
        mp.delenv('SYNAPSE_USERNAME')
        mp.delenv('SYNAPSE_PASSWORD')

        mock_username = uuid.uuid4()
        mock_password = uuid.uuid4()

        mocker.patch('builtins.input', return_value=mock_username)
        mocker.patch('getpass.getpass', return_value=mock_password)
        syn_uploader = SynapseUploader('None', 'None')
        syn_uploader.login()
        assert syn_uploader._username == mock_username
        assert syn_uploader._password == mock_password
        input.assert_called_once()
        getpass.getpass.assert_called_once()



def test_upload_bad_credentials(mocker):
    syn_uploader = SynapseUploader('None', 'None', username=uuid.uuid4(), password=uuid.uuid4())
    syn_uploader.upload()
    assert syn_uploader._synapse_client is None


def test_upload_remote_path(syn_client, new_syn_project, temp_dir):
    path_segments = ['one', 'two', 'three']
    remote_path = os.path.join(*path_segments)

    SynapseUploader(new_syn_project.id, temp_dir, remote_path=remote_path, synapse_client=syn_client).upload()

    parent = new_syn_project
    for segment in path_segments:
        folder = next(syn_client.getChildren(parent, includeTypes=['folder']))
        assert folder['name'] == segment
        parent = folder


def test_upload(syn_client, new_syn_project, temp_dir):
    """
        Tests this scenario:

        file1
        file2
        file3
        folder1/
            file4
            folder2/
                file5
                folder3/
                    file6
        """
    for i in range(1, 4):
        mkfile(temp_dir, 'file{0}'.format(i))

    folder1 = mkdir(temp_dir, 'folder1')
    mkfile(folder1, 'file4')
    folder2 = mkdir(folder1, 'folder2')
    mkfile(folder2, 'file5')
    folder3 = mkdir(folder2, 'folder3')
    mkfile(folder3, 'file6')
    mkfile(folder3, 'file7', content='')  # Empty files should NOT get uploaded.

    SynapseUploader(new_syn_project.id, temp_dir, synapse_client=syn_client).upload()

    syn_files, _ = get_syn_files(syn_client, new_syn_project)
    syn_folders, _ = get_syn_folders(syn_client, new_syn_project)
    assert len(syn_files) == 3
    assert len(syn_folders) == 1
    syn_folder = next((x for x in syn_folders if x['name'] == 'folder1'), None)
    assert syn_folder
    assert [x['name'] for x in syn_files] == ['file1', 'file2', 'file3']

    syn_files, _ = get_syn_files(syn_client, syn_folders[-1])
    syn_folders, _ = get_syn_folders(syn_client, syn_folders[-1])
    assert len(syn_files) == 1
    assert len(syn_folders) == 1
    syn_file = next((x for x in syn_files if x['name'] == 'file4'), None)
    syn_folder = next((x for x in syn_folders if x['name'] == 'folder2'), None)
    assert syn_file
    assert syn_folder

    syn_files, _ = get_syn_files(syn_client, syn_folders[-1])
    syn_folders, _ = get_syn_folders(syn_client, syn_folders[-1])
    assert len(syn_files) == 1
    assert len(syn_folders) == 1
    syn_file = next((x for x in syn_files if x['name'] == 'file5'), None)
    syn_folder = next((x for x in syn_folders if x['name'] == 'folder3'), None)
    assert syn_file
    assert syn_folder

    syn_files, _ = get_syn_files(syn_client, syn_folders[-1])
    syn_folders, _ = get_syn_folders(syn_client, syn_folders[-1])
    assert len(syn_files) == 1
    assert len(syn_folders) == 0
    syn_file = next((x for x in syn_files if x['name'] == 'file6'), None)
    assert syn_file


def test_upload_max_depth(syn_client, new_syn_project, temp_dir):
    """
        Tests this scenario:

        folder1
        folder2
        more/
            folder3
            folder4
            more/
                folder5
                file1
                more/
                    file2
                    file3
                    more/
                        file4
                        file5
        """
    for i in range(1, 6):
        mkfile(temp_dir, 'file{0}'.format(i))
        mkdir(temp_dir, 'folder{0}'.format(i))

    SynapseUploader(new_syn_project.id, temp_dir, max_depth=3, synapse_client=syn_client).upload()

    syn_files, _ = get_syn_files(syn_client, new_syn_project)
    assert len(syn_files) == 0
    syn_folders, _ = get_syn_folders(syn_client, new_syn_project)
    assert len(syn_folders) == 3

    syn_files, _ = get_syn_files(syn_client, syn_folders[-1])
    assert len(syn_files) == 0
    syn_folders, _ = get_syn_folders(syn_client, syn_folders[-1])
    assert len(syn_folders) == 3

    syn_files, _ = get_syn_files(syn_client, syn_folders[-1])
    assert len(syn_files) == 1
    syn_folders, _ = get_syn_folders(syn_client, syn_folders[-1])
    assert len(syn_folders) == 2

    syn_files, _ = get_syn_files(syn_client, syn_folders[-1])
    assert len(syn_files) == 2
    syn_folders, _ = get_syn_folders(syn_client, syn_folders[-1])
    assert len(syn_folders) == 1

    syn_files, _ = get_syn_files(syn_client, syn_folders[-1])
    assert len(syn_files) == 2
    syn_folders, _ = get_syn_folders(syn_client, syn_folders[-1])
    assert len(syn_folders) == 0
