import argparse
import configparser
import os
import sys

from daft.modes.flash_mode import FlashMode
from daft.modes.update_mode import UpdateMode


def get_daft_config():
    """
    Read and parse DAFT configuration file and return result as dictionary
    """
    config = configparser.ConfigParser()
    config.read("/etc/daft/daft.cfg")
    section = config.sections()[0]
    config = dict(config.items(section))
    config["workspace_nfs_path"] = os.path.normpath(config["workspace_nfs_path"])
    config["bbb_fs_path"] = os.path.normpath(config["bbb_fs_path"])

    return config


def parse_args():
    """
    Argument parsing
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("dut", action="store", nargs="?", help="Device type or specific device to test")
    subparsers = parser.add_subparsers(dest='mode', help='Desired mode')

    update_parser = subparsers.add_parser(UpdateMode.name(),
                                          help="Update AFT to Beaglebone filesystem and DAFT to PC host")
    flash_parser = subparsers.add_parser(FlashMode.name(), help="Flash and boot images")

    UpdateMode.add_mode_arguments(update_parser)
    FlashMode.add_mode_arguments(flash_parser)

    return parser.parse_args()


def main():
    args = parse_args()
    config = get_daft_config()
    modes = {FlashMode.name(): FlashMode(args, config),
             UpdateMode.name(): UpdateMode(args, config)}

    return modes[args.mode].execute()


if __name__ == "__main__":
    main_return_code = main()
    sys.exit(main_return_code)
