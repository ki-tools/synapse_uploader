import pytest
import os
import uuid
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
    syn_folders = list(syn_client.getChildren(syn_parent, includeTypes=['folder']))
    syn_folder_names = [s['name'] for s in syn_folders]
    return syn_folders, syn_folder_names


def get_syn_files(syn_client, syn_parent):
    syn_files = list(syn_client.getChildren(syn_parent, includeTypes=['file']))
    syn_file_names = [s['name'] for s in syn_files]
    return syn_files, syn_file_names


def find_by_name(list, name):
    return next((x for x in list if x['name'] == name), None)


def test_synapse_project_value():
    syn_id = 'syn123'
    syn_uploader = SynapseUploader(syn_id, 'None')
    assert syn_uploader._synapse_entity_id == syn_id


def test_local_path_value():
    local_path = os.getcwd()
    syn_uploader = SynapseUploader('None', local_path)
    assert syn_uploader._local_path == local_path


def test_remote_path_value():
    path_segments = ['one', 'two', 'three']
    remote_path = os.sep.join(path_segments)

    syn_uploader = SynapseUploader('None', 'None', remote_path=remote_path)
    assert syn_uploader._remote_path == remote_path

    # Strips spaces and separators
    syn_uploader = SynapseUploader('None', 'None', remote_path='{0} {0}'.format(os.sep))
    assert syn_uploader._remote_path is None

    syn_uploader = SynapseUploader('None', 'None', remote_path='{0} one {0}'.format(os.sep))
    assert syn_uploader._remote_path == 'one'

    syn_uploader = SynapseUploader('None', 'None', remote_path='{0} one {0} two {0} three {0}'.format(os.sep))
    assert syn_uploader._remote_path == remote_path


def test_max_depth_value():
    max_depth = 10
    syn_uploader = SynapseUploader('None', 'None', max_depth=max_depth)
    assert syn_uploader._max_depth == max_depth

    errors = SynapseUploader('None', 'None', max_depth=(SynapseUploader.MAX_SYNAPSE_DEPTH + 1)).execute().errors
    assert 'Maximum depth must be less than or equal to 10000.' in errors


def test_min_depth_value():
    errors = SynapseUploader('None', 'None', max_depth=(SynapseUploader.MIN_SYNAPSE_DEPTH - 1)).execute().errors
    assert 'Maximum depth must be greater than or equal to 2.' in errors


def test_force_upload_value():
    for b_value in [True, False]:
        syn_uploader = SynapseUploader('None', 'None', force_upload=b_value)
        assert syn_uploader._force_upload == b_value


def test_upload_remote_path(syn_client, new_syn_project, new_temp_dir):
    """
            Tests this scenario:

            Remote Path: one/two/three

            file1
            folder1/
                file2
                folder2/
                    file3
            """
    path_segments = ['one', 'two', 'three']
    remote_path = os.path.join(*path_segments)

    mkfile(new_temp_dir, 'file1')
    folder1 = mkdir(new_temp_dir, 'folder1')
    mkfile(folder1, 'file2')
    folder2 = mkdir(folder1, 'folder2')
    mkfile(folder2, 'file3')

    SynapseUploader(new_syn_project.id, new_temp_dir, remote_path=remote_path).execute()

    parent = new_syn_project
    for segment in path_segments:
        syn_files, syn_file_names = get_syn_files(syn_client, parent)
        syn_folders, syn_folder_names = get_syn_folders(syn_client, parent)
        assert len(syn_files) == 0
        assert len(syn_folders) == 1
        folder = find_by_name(syn_folders, segment)
        assert folder
        parent = folder

    syn_files, syn_file_names = get_syn_files(syn_client, parent)
    syn_folders, syn_folder_names = get_syn_folders(syn_client, parent)
    assert len(syn_files) == 1
    assert len(syn_folders) == 1
    syn_folder = find_by_name(syn_folders, 'folder1')
    assert syn_folder
    assert syn_file_names == ['file1']
    assert syn_folder_names == ['folder1']

    syn_files, syn_file_names = get_syn_files(syn_client, syn_folder)
    syn_folders, syn_folder_names = get_syn_folders(syn_client, syn_folder)
    assert len(syn_files) == 1
    assert len(syn_folders) == 1
    syn_folder = find_by_name(syn_folders, 'folder2')
    assert syn_folder
    assert syn_file_names == ['file2']
    assert syn_folder_names == ['folder2']

    syn_files, syn_file_names = get_syn_files(syn_client, syn_folder)
    syn_folders, _ = get_syn_folders(syn_client, syn_folder)
    assert len(syn_files) == 1
    assert len(syn_folders) == 0
    assert syn_file_names == ['file3']


def test_upload(syn_client, synapse_test_helper, new_temp_dir):
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
        mkfile(new_temp_dir, 'file{0}'.format(i))

    folder1 = mkdir(new_temp_dir, 'folder1')
    mkfile(folder1, 'file4')
    folder2 = mkdir(folder1, 'folder2')
    mkfile(folder2, 'file5')
    folder3 = mkdir(folder2, 'folder3')
    mkfile(folder3, 'file6')
    mkfile(folder3, 'file7', content='')  # Empty files should NOT get uploaded.

    project1 = synapse_test_helper.create_project()
    project2 = synapse_test_helper.create_project()

    # Test uploading to a Project and Folder
    upload_targets = [
        project1,
        synapse_test_helper.create_folder(parent=project2)
    ]

    for upload_target in upload_targets:
        SynapseUploader(upload_target.id, new_temp_dir).execute()

        syn_files, syn_file_names = get_syn_files(syn_client, upload_target)
        syn_folders, _ = get_syn_folders(syn_client, upload_target)
        assert len(syn_files) == 3
        assert len(syn_folders) == 1
        syn_folder = find_by_name(syn_folders, 'folder1')
        assert syn_folder
        assert syn_file_names == ['file1', 'file2', 'file3']

        syn_files, _ = get_syn_files(syn_client, syn_folders[-1])
        syn_folders, _ = get_syn_folders(syn_client, syn_folders[-1])
        assert len(syn_files) == 1
        assert len(syn_folders) == 1
        syn_file = find_by_name(syn_files, 'file4')
        syn_folder = find_by_name(syn_folders, 'folder2')
        assert syn_file
        assert syn_folder

        syn_files, _ = get_syn_files(syn_client, syn_folders[-1])
        syn_folders, _ = get_syn_folders(syn_client, syn_folders[-1])
        assert len(syn_files) == 1
        assert len(syn_folders) == 1
        syn_file = find_by_name(syn_files, 'file5')
        syn_folder = find_by_name(syn_folders, 'folder3')
        assert syn_file
        assert syn_folder

        syn_files, _ = get_syn_files(syn_client, syn_folders[-1])
        syn_folders, _ = get_syn_folders(syn_client, syn_folders[-1])
        assert len(syn_files) == 1
        assert len(syn_folders) == 0
        syn_file = find_by_name(syn_files, 'file6')
        assert syn_file


def test_upload_file(syn_client, synapse_test_helper, new_syn_project, new_temp_file, new_temp_dir):
    file_name = os.path.basename(new_temp_file)
    syn_file = synapse_test_helper.create_file(name=file_name, path=new_temp_file, parent=new_syn_project)

    SynapseUploader(syn_file.id, new_temp_file).execute()

    syn_files, syn_file_names = get_syn_files(syn_client, new_syn_project)
    syn_folders, _ = get_syn_folders(syn_client, new_syn_project)
    assert len(syn_files) == 1
    assert len(syn_folders) == 0
    assert file_name in syn_file_names

    # Test validations
    errors = SynapseUploader(syn_file.id, new_temp_dir).execute().errors
    assert 'Local entity must be a file when remote entity is a file: {0}'.format(new_temp_dir) in errors

    errors = SynapseUploader(syn_file.id, new_temp_file, remote_path='/test').execute().errors
    assert 'Cannot specify a remote path when remote entity is a file: {0}'.format(new_temp_file) in errors

    other_temp_file = mkfile(new_temp_dir, synapse_test_helper.uniq_name())
    other_temp_file_name = os.path.basename(other_temp_file)
    errors = SynapseUploader(syn_file.id, other_temp_file).execute().errors
    assert 'Local filename: {0} does not match remote file name: {1}'.format(other_temp_file_name,
                                                                             syn_file.name) in errors


def test_force_upload(syn_client, synapse_test_helper, new_syn_project, new_temp_file):
    annotations = {"one": ["two"]}

    file_name = os.path.basename(new_temp_file)
    syn_file = synapse_test_helper.create_file(name=file_name, path=new_temp_file, parent=new_syn_project,
                                               annotations=annotations)
    assert syn_file.versionNumber == 1
    assert syn_file.annotations == annotations

    SynapseUploader(syn_file.id, new_temp_file).execute()
    syn_file = syn_client.get(syn_file.id)
    assert syn_file.versionNumber == 1
    assert syn_file.annotations == annotations

    SynapseUploader(syn_file.id, new_temp_file, force_upload=True).execute()
    syn_file = syn_client.get(syn_file.id)
    assert syn_file.versionNumber == 2
    assert syn_file.annotations == annotations


def test_upload_max_depth(syn_client, new_syn_project, new_temp_dir):
    """
        Tests this scenario:

        file1
        file2
        file3
        file4
        file5
        folder1/
            file1-1
            file1-2
        folder2
        folder3
        folder4
        folder5

        TO:

        file1
        file2
        more/
            file3
            file4
            more/
                file5
                folder1/
                    file1-1
                    file1-2
                more/
                    folder2
                    folder3
                    more/
                        folder4
                        folder5
        """
    for i in range(1, 6):
        mkfile(new_temp_dir, 'file{0}'.format(i))
        folder_path = mkdir(new_temp_dir, 'folder{0}'.format(i))
        if i == 1:
            mkfile(folder_path, 'file1-1'.format(i))
            mkfile(folder_path, 'file1-2'.format(i))

    SynapseUploader(new_syn_project.id, new_temp_dir, max_depth=3).execute()

    syn_files, syn_file_names = get_syn_files(syn_client, new_syn_project)
    assert len(syn_files) == 2
    assert syn_file_names == ['file1', 'file2']
    syn_folders, syn_folder_names = get_syn_folders(syn_client, new_syn_project)
    assert len(syn_folders) == 1
    assert syn_folder_names == ['more']

    more_folder = find_by_name(syn_folders, 'more')

    syn_files, syn_file_names = get_syn_files(syn_client, more_folder)
    assert len(syn_files) == 2
    assert syn_file_names == ['file3', 'file4']
    syn_folders, syn_folder_names = get_syn_folders(syn_client, more_folder)
    assert len(syn_folders) == 1
    assert syn_folder_names == ['more']

    more_folder = find_by_name(syn_folders, 'more')

    syn_files, syn_file_names = get_syn_files(syn_client, more_folder)
    assert len(syn_files) == 1
    assert syn_file_names == ['file5']
    syn_folders, syn_folder_names = get_syn_folders(syn_client, more_folder)
    assert len(syn_folders) == 2
    assert syn_folder_names == ['folder1', 'more']

    more_folder = find_by_name(syn_folders, 'more')

    syn_folder1 = find_by_name(syn_folders, 'folder1')

    child_syn_files, child_syn_file_names = get_syn_files(syn_client, syn_folder1)
    assert len(child_syn_files) == 2
    assert child_syn_file_names == ['file1-1', 'file1-2']
    child_syn_folders, _ = get_syn_folders(syn_client, syn_folder1)
    assert len(child_syn_folders) == 0

    syn_files, _ = get_syn_files(syn_client, more_folder)
    assert len(syn_files) == 0
    syn_folders, syn_folder_names = get_syn_folders(syn_client, more_folder)
    assert len(syn_folders) == 3
    assert syn_folder_names == ['folder2', 'folder3', 'more']

    more_folder = find_by_name(syn_folders, 'more')

    syn_files, _ = get_syn_files(syn_client, more_folder)
    assert len(syn_files) == 0
    syn_folders, syn_folder_names = get_syn_folders(syn_client, more_folder)
    assert len(syn_folders) == 2
    assert syn_folder_names == ['folder4', 'folder5']


def test_upload_failures():
    # TODO: add tests.
    pass
