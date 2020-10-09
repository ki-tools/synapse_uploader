[![Build Status](https://travis-ci.org/ki-tools/synapse_uploader.svg?branch=master)](https://travis-ci.org/ki-tools/synapse_uploader)
[![Coverage Status](https://coveralls.io/repos/github/ki-tools/synapse_uploader/badge.svg?branch=master)](https://coveralls.io/github/ki-tools/synapse_uploader?branch=master)

# Synapse Uploader

Utility to upload a directory and files to [Synapse](https://www.synapse.org/).

## Dependencies

- [Python3](https://www.python.org/)
- A [Synapse](https://www.synapse.org/) account with a username/password. Authentication through a 3rd party (.e.g., Google) will not work, you must have a Synapse user/pass for the [API to authenticate](http://docs.synapse.org/python/#connecting-to-synapse).

## Install

```bash
pip install synapse-uploader
```

## Configuration

Your Synapse credentials can be provided on the command line (`--username`, `--password`) or via environment variables.

```bash
SYNAPSE_USERNAME=your-synapse-username
SYNAPSE_PASSWORD=your-synapse-password
```

## Usage

```text
usage: synapse-uploader [-h] [--version] [-r REMOTE_FOLDER_PATH] [-d DEPTH]
                        [-t THREADS] [-u USERNAME] [-p PASSWORD]
                        [-ll LOG_LEVEL] [-ld LOG_DIR] [-f] [-cd CACHE_DIR]
                        entity-id local-path

positional arguments:
  entity-id             Synapse entity ID to upload to (e.g., syn123456789).
  local-path            Path of the directory or file to upload.

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -r REMOTE_FOLDER_PATH, --remote-folder-path REMOTE_FOLDER_PATH
                        Folder to upload to in Synapse.
  -d DEPTH, --depth DEPTH
                        The maximum number of child folders or files under a
                        Synapse Project/Folder.
  -t THREADS, --threads THREADS
                        The maximum number of threads to use.
  -u USERNAME, --username USERNAME
                        Synapse username.
  -p PASSWORD, --password PASSWORD
                        Synapse password.
  -ll LOG_LEVEL, --log-level LOG_LEVEL
                        Set the logging level.
  -ld LOG_DIR, --log-dir LOG_DIR
                        Set the directory where the log file will be written.
  -f, --force-upload    Force files to be re-uploaded. This will clear the
                        local Synapse cache and increment each file's version.
  -cd CACHE_DIR, --cache-dir CACHE_DIR
                        Set the directory where the Synapse cache will be
                        stored.
```

## Examples

Upload all the folders and files in `~/my_study` to your Project ID `syn123456`:

- Linux: `synapse-uploader syn123456 ~/my_study`
- Windows: `synapse-uploader syn123456 %USERPROFILE%\my_study`

Upload all the folders and files in `~/my_study` to your Project ID `syn123456` in the `drafts/my_study` folder:

- Linux: `synapse-uploader syn123456 ~/my_study -r drafts/my_study`
- Windows: `synapse-uploader syn123456 %USERPROFILE%\my_study -r drafts\my_study`

> Note: The correct path separator (`\` for Windows and `/` for Linux) must be used in both the `local-folder-path` and the `remote-folder-path`.

## Development Setup

```bash
pipenv --three
pipenv shell
make pip_install
make build
make install_local
```
See [Makefile](Makefile) for all commands.

### Testing

- Create and activate a virtual environment:
- Copy [private.test.env.json](tests/templates/private.test.env.json) to the [tests](tests) directory and set each of the variables.
- Run the tests: `make test`
