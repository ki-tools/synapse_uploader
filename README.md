# Synapse File Uploader

A utility to upload a directory and all its contents to a [Synapse](https://www.synapse.org/) Project.

## Dependencies

- [Python](https://www.python.org/)
- A [Synapse](https://www.synapse.org/) account with a username/password. Authentication through a 3rd party (.e.g., Google) will not work, you must have a Synapse user/pass for the [API to authenticate](http://docs.synapse.org/python/#connecting-to-synapse).
- synapseclient - Follow install instructions [here](http://docs.synapse.org/python/)

## Install

Copy the Python file to your local system or clone the GIT repository.

```bash
$ git clone git@github.com:pcstout/synapse_uploader.git
$ cd synapse_uploader
$ chmod u+x *.py
```

## Usage

```bash
./synapse_uploader.py <project-id> <local-folder-path> [remote-folder-path]
```

## Examples

Upload all the folders and files in `~/my_study` to your Project ID `syn123456`:

- Linux: `./synapse_uploader.py syn123456 ~/my_study`
- Windows: `synapse_uploader.py syn123456 C:\my_study`

Upload all the folders and files in `~/my_study` to your Project ID `syn123456` in the `drafts/my_study` folder:

- Linux: `./synapse_uploader.py syn123456 ~/my_study drafts/my_study`
- Windows: `synapse_uploader.py syn123456 C:\my_study drafts\my_study`

> Note: The correct path separator (`\` for Windows and `/` for Linux) must be used in both the `local-folder-path` and the `remote-folder-path`.