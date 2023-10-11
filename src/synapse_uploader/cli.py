import os
import sys
import logging
import argparse
from datetime import datetime
from ._version import __version__
from .synapse_uploader import SynapseUploader
from .utils import Utils
from synapsis import cli as synapsis_cli


class LogFilter(logging.Filter):
    FILTERS = [
        '##################################################',
        'Uploading file to Synapse storage',
        'Connection pool is full, discarding connection:'
    ]

    def filter(self, record):
        for filter in self.FILTERS:
            if filter in record.msg:
                return False
        return True


def main():
    parser = argparse.ArgumentParser()
    synapsis_cli.inject(parser)
    parser.add_argument('--version', action='version', version='%(prog)s {0}'.format(__version__))
    parser.add_argument('entity_id',
                        metavar='entity-id',
                        help='Synapse entity ID to upload to (e.g., syn123456789).')

    parser.add_argument('local_path',
                        metavar='local-path',
                        help='Path of the directory or file to upload.')

    parser.add_argument('-r', '--remote-folder-path',
                        help='Folder to upload to in Synapse.',
                        default=None)

    parser.add_argument('-d', '--depth',
                        help='The maximum number of child folders or files under a Synapse Project/Folder.',
                        type=int,
                        default=SynapseUploader.MAX_SYNAPSE_DEPTH)

    parser.add_argument('-t', '--threads',
                        help='The maximum number of threads to use.',
                        type=int,
                        default=None)

    parser.add_argument('-ll', '--log-level',
                        help='Set the logging level.',
                        default='INFO')

    parser.add_argument('-ld', '--log-dir',
                        help='Set the directory where the log file will be written.')

    parser.add_argument('-f', '--force-upload',
                        help='Force files to be re-uploaded. This will clear the local Synapse cache and increment each file\'s version.',
                        default=False,
                        action='store_true')
    parser.add_argument('-cd', '--cache-dir',
                        help='Set the directory where the Synapse cache will be stored.')

    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper())

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    log_filename = '{0}.log'.format(timestamp)

    if args.log_dir:
        log_filename = os.path.join(Utils.expand_path(args.log_dir), log_filename)
    else:
        log_filename = os.path.join(Utils.app_log_dir(), log_filename)

    Utils.ensure_dirs(os.path.dirname(log_filename))

    logging.basicConfig(
        filename=log_filename,
        filemode='w',
        format='%(asctime)s %(levelname)s: %(message)s',
        level=log_level
    )

    # Add console logging.
    console = logging.StreamHandler()
    console.setLevel(log_level)
    console.setFormatter(logging.Formatter('%(message)s'))
    logging.getLogger().addHandler(console)

    # Filter logs
    log_filter = LogFilter()
    for logger in [logging.getLogger(name) for name in logging.root.manager.loggerDict]:
        logger.addFilter(log_filter)

    print('Logging output to: {0}'.format(log_filename))

    try:
        cache_dir = args.cache_dir
        if cache_dir:
            cache_dir = os.path.join(cache_dir, '.synapseCache')

        synapsis_cli.configure(args, synapse_args={'cache_root_dir': cache_dir, 'multi_threaded': False}, login=True)
        cmd = SynapseUploader(
            args.entity_id,
            args.local_path,
            remote_path=args.remote_folder_path,
            max_depth=args.depth,
            max_threads=args.threads,
            force_upload=args.force_upload
        )
        cmd.execute()
        if cmd.errors:
            logging.error('Finished with errors.')
            for error in cmd.errors:
                print(error)
            print('Output logged to: {0}'.format(log_filename))
            sys.exit(1)
        else:
            logging.info('Finished successfully.')
            print('Output logged to: {0}'.format(log_filename))
            sys.exit(0)
    except Exception as ex:
        logging.error(ex)
        print('Output logged to: {0}'.format(log_filename))
        sys.exit(1)


if __name__ == "__main__":
    main()
