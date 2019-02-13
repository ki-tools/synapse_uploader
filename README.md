# Synapse Uploader

A utility to upload a directory and all its contents to a [Synapse](https://www.synapse.org/) Project.

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
usage: synapse_uploader.py [-h] [-r REMOTE_FOLDER_PATH] [-d DEPTH]
                           [-u USERNAME] [-p PASSWORD] [-l LOG_LEVEL]
                           project-id local-folder-path

positional arguments:
  project-id            Synapse Project ID to upload to (e.g., syn123456789).
  local-folder-path     Path of the folder to upload.

optional arguments:
  -h, --help            show this help message and exit
  -r REMOTE_FOLDER_PATH, --remote-folder-path REMOTE_FOLDER_PATH
                        Folder to upload to in Synapse.
  -d DEPTH, --depth DEPTH
                        The maximum number of child folders or files under a
                        Synapse Project/Folder.
  -u USERNAME, --username USERNAME
                        Synapse username.
  -p PASSWORD, --password PASSWORD
                        Synapse password.
  -l LOG_LEVEL, --log-level LOG_LEVEL
                        Set the logging level.
```

## Examples

Upload all the folders and files in `~/my_study` to your Project ID `syn123456`:

- Linux: `synapse_uploader syn123456 ~/my_study`
- Windows: `synapse_uploader syn123456 %USERPROFILE%\my_study`

Upload all the folders and files in `~/my_study` to your Project ID `syn123456` in the `drafts/my_study` folder:

- Linux: `synapse_uploader syn123456 ~/my_study -r drafts/my_study`
- Windows: `synapse_uploader syn123456 %USERPROFILE%\my_study -r drafts\my_study`

> Note: The correct path separator (`\` for Windows and `/` for Linux) must be used in both the `local-folder-path` and the `remote-folder-path`.

## Development Setup

```bash
make init_dev
make build
make install_local
```
See [Makefile](Makefile) for all commands.

### Testing

- Create and activate a virtual environment:
  - `python3 -m venv .venv`
  - `source .venv/bin/activate`
- Copy [private.test.env.json](tests/templates/private.test.env.json) to the [tests](tests) directory and set each of the variables.
- Run the tests: `make test`