import os
import time

from daft.modes.common import reserve_device, remote_execute, time_used
from daft.modes.exceptions import DevicesBlacklistedError, DeviceNameError, ImageNameError, FlashImageError
from daft.modes.mode import Mode


class FlashMode(Mode):
    @classmethod
    def name(cls):
        return 'flash'

    @classmethod
    def add_mode_arguments(cls, parser):
        parser.add_argument("image_file", action="store", nargs="?",
                            help="Image to write: a local file, compatible with the selected device.")

        parser.add_argument("--record", action="store_true", default=False,
                            help="Record serial output from DUT while flashing/testing")
        parser.add_argument("--no-flash",
                            action="store_true",
                            default=False,
                            help="Skip device flashing")
        parser.add_argument("--emulate-usb", action="store_true", default=False,
                            help="Use the image in USB mass storage emulation instead of flashing")
        parser.add_argument("--no-black-listing", action="store_true", default=False,
                            help="Don't blacklist device if flashing/testing fails")
        parser.add_argument("--boot", action="store_true", default=False,
                            help="Flash DUT and reboot it in test mode")
        parser.add_argument("--ip-path", action="store", nargs="?",
                            help="Image to write.")

    def __init__(self, args, config):
        self._args = args
        self._config = config

    def execute(self):
        try:
            start_time = time.time()

            with reserve_device(self._args, self._config) as beaglebone_dut:
                self._flash_cycle(beaglebone_dut, start_time)

        except KeyboardInterrupt:
            print("Keyboard interrupt, stopping DAFT run")
            return 0
        except DevicesBlacklistedError:
            return 5
        except DeviceNameError:
            return 6
        except ImageNameError:
            return 7
        except FlashImageError:
            if beaglebone_dut:
                if self._args.no_black_listing:
                    return
                else:
                    lockfile = "/etc/daft/lockfiles/" + beaglebone_dut["device"]
                    with open(lockfile, "a") as f:
                        f.write("Blacklisted because flashing failed\n")
                        print("Flashing failed, blacklisted " + beaglebone_dut["device"])
            raise

    def _flash_cycle(self, beaglebone_dut, start_time):
        if self._args.emulate_usb:
            self.execute_usb_emulation(beaglebone_dut)
        elif self._args.boot:
            self.dut_flash_and_boot(beaglebone_dut)
        else:
            if not self._args.no_flash:
                self.execute_flashing(beaglebone_dut)

        print("DAFT run duration: " + time_used(start_time))

        return 0

    def execute_flashing(self, bb_dut):
        """
        Execute flashing of the DUT
        """
        if not os.path.isfile(self._args.image_file):
            print(self._args.image_file + " doesn't exist.")
            raise ImageNameError()

        print("Executing flashing of DUT")
        start_time = time.time()
        dut = bb_dut["device_type"].lower()
        current_dir = os.getcwd().replace(self._config["workspace_nfs_path"], "")
        img_path = self._args.image_file.replace(self._config["workspace_nfs_path"],
                                                 "/root/workspace")
        record = ""
        if self._args.record:
            record = "--record"
        try:
            command = ["cd", "/root/workspace" + current_dir, ";aft", dut, img_path, record]
            output = remote_execute(bb_dut["bb_ip"],
                                    command=command,
                                    timeout=1200, config=self._config)

        except KeyboardInterrupt:
            raise
        except:
            raise FlashImageError()
        finally:
            log_files = ["aft.log", "serial.log", "ssh.log", "kb_emulator.log",
                         "serial.log.raw"]
            for log in log_files:
                if os.path.isfile(log):
                    os.rename(log, "flash_" + log)

        print(output, end="")
        print("Flashing took: " + time_used(start_time))

    def dut_flash_and_boot(self, bb_dut):
        """
        Flash DUT and reboot it in test mode
        """
        if not os.path.isfile(self._args.image_file):
            print(self._args.image_file + " doesn't exist.")
            raise ImageNameError()

        print("Executing flashing of DUT")
        start_time = time.time()
        dut = bb_dut["device_type"].lower()
        current_dir = os.getcwd().replace(self._config["workspace_nfs_path"], "")
        img_path = self._args.image_file.replace(self._config["workspace_nfs_path"], "/root/workspace")
        record = "--record" if self._args.record else ""

        try:
            flash_command = ["cd", "/root/workspace" + current_dir, ";aft", dut, img_path, record, "--boot",
                             "test_mode"]

            if self._args.ip_path:
                # Generate file remotely
                flash_command.extend(['--ip-path', self._args.ip_path])

            output = remote_execute(bb_dut["bb_ip"], flash_command, timeout=1200, config=self._config)
        finally:
            log_files = ["aft.log", "serial.log", "ssh.log", "kb_emulator.log",
                         "serial.log.raw"]
            for log in log_files:
                if os.path.isfile(log):
                    os.rename(log, "flash_" + log)

        print(output, end="")
        print("Flashing took: " + time_used(start_time))

    def execute_usb_emulation(self, bb_dut):
        """
        Use testing harness USB emulation to boot the image
        """
        if not os.path.isfile(self._args.image_file):
            print(self._args.image_file + " doesn't exist.")
            raise ImageNameError()

        print("Executing testing of DUT")
        start_time = time.time()
        dut = bb_dut["device_type"].lower()
        current_dir = os.getcwd().replace(self._config["workspace_nfs_path"], "")
        img_path = self._args.image_file.replace(self._config["workspace_nfs_path"], "/root/workspace")
        record = ""

        if self._args.record:
            record = "--record"
        try:
            output = remote_execute(bb_dut["bb_ip"],
                                    ["cd", "/root/workspace" + current_dir, ";aft",
                                     dut, img_path, record, "--emulateusb"],
                                    timeout=1200, config=self._config)
        finally:
            log_files = ["aft.log", "serial.log", "ssh.log", "kb_emulator.log",
                         "serial.log.raw"]
            for log in log_files:
                if os.path.isfile(log):
                    os.rename(log, "test_" + log)

        print(output, end="")
        print("Testing took: " + time_used(start_time))
