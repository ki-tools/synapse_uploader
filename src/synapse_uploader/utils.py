import hashlib
import os
import pathlib


class Utils:
    KB = 1024
    MB = KB * KB
    CHUNK_SIZE = 10 * MB

    @staticmethod
    def app_dir():
        """Gets the application's primary directory for the current user.

        Returns:
            Absolute path to the directory.
        """
        return os.path.join(pathlib.Path.home(), '.syntools')

    @staticmethod
    def app_log_dir():
        """Gets the applications primary log directory for the current user.

        Returns:
            Absolute path to the directory.
        """
        return os.path.join(Utils.app_dir(), 'logs')

    @staticmethod
    def expand_path(local_path):
        var_path = os.path.expandvars(local_path)
        expanded_path = os.path.expanduser(var_path)
        return os.path.abspath(expanded_path)

    @staticmethod
    def ensure_dirs(local_path):
        """Ensures the directories in local_path exist.

        Args:
            local_path: The local path to ensure.

        Returns:
            None
        """
        if not os.path.isdir(local_path):
            os.makedirs(local_path)

    @staticmethod
    def get_md5(local_path):
        md5 = hashlib.md5()
        with open(local_path, mode='rb') as fd:
            while True:
                chunk = fd.read(Utils.CHUNK_SIZE)
                if not chunk:
                    break
                md5.update(chunk)
        return md5.hexdigest()
