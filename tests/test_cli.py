import pytest
import synapse_uploader.cli as cli
from synapse_uploader.synapse_uploader import SynapseUploader


def test_cli(mocker, test_synapse_auth_token):
    args = ['', 'syn123', '/tmp', '-r', '10', '-d', '20', '-t', '30',
            '--auth-token', test_synapse_auth_token, '-ll', 'debug', '-f', '-cd', '/tmp/cache']
    mocker.patch('sys.argv', args)
    mocker.patch('src.synapse_uploader.synapse_uploader.SynapseUploader.execute')
    mock_init = mocker.spy(SynapseUploader, '__init__')

    with pytest.raises(SystemExit):
        cli.main()

    mock_init.assert_called_once_with(mocker.ANY,
                                      'syn123',
                                      '/tmp',
                                      remote_path='10',
                                      max_depth=20,
                                      max_threads=30,
                                      force_upload=True
                                      )
