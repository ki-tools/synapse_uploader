# Synapse File Uploader

A utility to upload a directory to [Synapse](https://www.synapse.org/)

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