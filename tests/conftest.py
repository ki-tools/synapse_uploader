import pytest
import tempfile
import os
import shutil
from synapse_test_helper import SynapseTestHelper
from synapsis import Synapsis
from dotenv import load_dotenv

load_dotenv(override=True)


@pytest.fixture(scope='session')
def test_synapse_auth_token():
    return os.environ.get('SYNAPSE_AUTH_TOKEN')


@pytest.fixture(scope='session', autouse=True)
def syn_client(test_synapse_auth_token):
    Synapsis.configure(authToken=test_synapse_auth_token, synapse_args={'multi_threaded': False})
    SynapseTestHelper.configure(Synapsis.login().Synapse)
    return Synapsis.Synapse


@pytest.fixture(scope='session')
def synapse_test_helper():
    with SynapseTestHelper() as sth:
        yield sth


@pytest.fixture(scope='session')
def syn_project(synapse_test_helper):
    return synapse_test_helper.create_project()


@pytest.fixture()
def new_synapse_test_helper():
    """
    Provides the SynapseTestHelper as a fixture per function.
    """
    with SynapseTestHelper() as sth:
        yield sth


@pytest.fixture()
def new_syn_project(new_synapse_test_helper):
    return new_synapse_test_helper.create_project()


@pytest.fixture()
def new_temp_dir():
    path = tempfile.mkdtemp()
    yield path
    if os.path.isdir(path):
        shutil.rmtree(path)


@pytest.fixture()
def new_temp_file(synapse_test_helper):
    """
    Generates a temp file containing the SynapseTestHelper.uniq_name.
    """
    fd, tmp_filename = tempfile.mkstemp()
    with os.fdopen(fd, 'w') as tmp:
        tmp.write(synapse_test_helper.uniq_name())
    yield tmp_filename

    if os.path.isfile(tmp_filename):
        os.remove(tmp_filename)
