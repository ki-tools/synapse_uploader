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

import src.synapse_uploader.cli as cli
from src.synapse_uploader.synapse_uploader import SynapseUploader


def test_cli(mocker):
    args = ['', 'syn123', '/tmp', '-r', '10', '-d', '20', '-t', '30', '-u', '40', '-p', '50', '-l', 'debug']
    mocker.patch('sys.argv', args)
    mocker.patch('src.synapse_uploader.synapse_uploader.SynapseUploader.upload', return_value=None)
    mock_init = mocker.patch.object(SynapseUploader, '__init__', return_value=None)

    cli.main()

    mock_init.assert_called_once_with(
        'syn123',
        '/tmp',
        remote_path='10',
        max_depth=20,
        max_threads=30,
        username='40',
        password='50'
    )
