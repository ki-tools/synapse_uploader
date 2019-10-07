import pytest
import tempfile
import os
import json
import shutil
from tests.synapse_test_helper import SynapseTestHelper

# Load Environment variables.
module_dir = os.path.dirname(os.path.abspath(__file__))

test_env_file = os.path.join(module_dir, 'private.test.env.json')

if os.path.isfile(test_env_file):
    with open(test_env_file) as f:
        config = json.load(f).get('test')

        # Validate required properties are present
        for prop in ['SYNAPSE_USERNAME', 'SYNAPSE_PASSWORD']:
            if not prop in config or not config[prop]:
                raise Exception(
                    'Property: "{0}" is missing in {1}'.format(prop, test_env_file))

        for key, value in config.items():
            os.environ[key] = value
else:
    print('WARNING: Test environment file not found at: {0}'.format(test_env_file))


@pytest.fixture(scope='session')
def syn_client(syn_test_helper):
    return syn_test_helper.client()


@pytest.fixture(scope='session')
def syn_test_helper():
    """
    Provides the SynapseTestHelper as a fixture per session.
    """
    helper = SynapseTestHelper()
    yield helper
    helper.dispose()


@pytest.fixture(scope='session')
def syn_project(syn_test_helper):
    return syn_test_helper.create_project()


@pytest.fixture(scope='session')
def temp_file(syn_test_helper):
    """
    Generates a temp file containing the SynapseTestHelper.uniq_name.
    """
    fd, tmp_filename = tempfile.mkstemp()
    with os.fdopen(fd, 'w') as tmp:
        tmp.write(syn_test_helper.uniq_name())
    yield tmp_filename

    if os.path.isfile(tmp_filename):
        os.remove(tmp_filename)


@pytest.fixture()
def new_syn_test_helper():
    """
    Provides the SynapseTestHelper as a fixture per function.
    """
    helper = SynapseTestHelper()
    yield helper
    helper.dispose()


@pytest.fixture()
def new_syn_project(new_syn_test_helper):
    return new_syn_test_helper.create_project()


@pytest.fixture()
def new_temp_dir():
    path = tempfile.mkdtemp()
    yield path
    if os.path.isdir(path):
        shutil.rmtree(path)
