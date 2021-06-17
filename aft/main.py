"""
Main entry point for aft.
"""

import argparse
import logging
import sys

import aft.internal.config as config
from aft.internal.devices_manager import DevicesManager
from aft.internal.logger import Logger as logger
from aft.internal.tools.thread_handler import ThreadHandler

SUCCESS_EXIT_CODE = 0


def main():
    """
    Entry point for library-like use.
    """
    try:
        main_logic()

        return SUCCESS_EXIT_CODE
    except KeyboardInterrupt:
        print("Keyboard interrupt, stopping aft")
        logger.error("Keyboard interrupt, stopping aft.")

        return SUCCESS_EXIT_CODE
    except:
        _err = sys.exc_info()
        logger.error(str(_err[0]).split("'")[1] + ": " + str(_err[1]))

        raise
    finally:
        ThreadHandler.set_flag(ThreadHandler.RECORDERS_STOP)

        for thread in ThreadHandler.get_threads():
            thread.join(5)


def main_logic():
    logger.set_process_prefix()
    config.parse()
    args = parse_args()

    if args.debug:
        logger.level(logging.DEBUG)

    device_manager = DevicesManager(args)
    device = device_manager.try_flash_model(args)

    if args.emulateusb:
        device.boot_usb_test_mode()
    else:
        if args.boot == "test_mode":
            device.boot_internal_test_mode()
        elif args.boot == "service_mode":
            device.boot_usb_service_mode()

    device_manager.release(device)


def parse_args():
    """
    Argument parsing
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("machine",
                        action="store",
                        nargs="?",
                        help="Model type")

    parser.add_argument("file_name",
                        action="store",
                        nargs="?",
                        help="Image to write: a local file, compatible with the selected machine.")

    parser.add_argument("--flash_retries",
                        type=int,
                        nargs="?",
                        action="store",
                        default="2",
                        help="Specify how many times flashing one machine will be tried.")

    parser.add_argument("--record",
                        action="store_true",
                        default=False,
                        help="Record the serial output during testing to a file " +
                             "from the serial_port and serial_bauds defined in configuration.")

    parser.add_argument("--noflash",
                        action="store_true",
                        default=False,
                        help="Skip device flashing")

    parser.add_argument("--nopoweroff",
                        action="store_true",
                        default=False,
                        help="Do not power off the DUT after testing")

    parser.add_argument("--emulateusb",
                        action="store_true",
                        default=False,
                        help="Use the image in USB mass storage emulation instead of flashing")

    parser.add_argument("--boot",
                        type=str,
                        nargs="?",
                        action="store",
                        choices=["test_mode", "service_mode"],
                        help="Boot device to specific mode")

    parser.add_argument("--catalog",
                        action="store",
                        help="Configuration file describing the supported device types",
                        default="/etc/aft/devices/catalog.cfg")

    parser.add_argument("--verbose",
                        action="store_true",
                        help="Prints additional information on various operations")

    parser.add_argument("--debug",
                        action="store_true",
                        help="Increases logging level")

    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main())
