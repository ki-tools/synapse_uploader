# Synapse File Uploader

A utility to upload a directory and all its contents to a [Synapse](https://www.synapse.org/) Project.

## Dependencies

- [Python](https://www.python.org/)
- A [Synapse](https://www.synapse.org/) account with a username/password. Authentication through a 3rd party (.e.g., Google) will not work, you must have a Synapse user/pass for the API to authenticate.
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

```bash
./synapse_uploader.py syn123456 ~/my_study
```

Upload all the folders and files in `~/my_study` to your Project ID `syn123456` in the `drafts/my_study` folder:

```bash
./synapse_uploader.py syn123456 ~/my_study drafts/my_study
```