import ipaddress

import os
import time
from pathlib import Path

from daft.modes import networking
from daft.modes.common import reserve_device, remote_execute, time_used, local_execute
from daft.modes.exceptions import DevicesBlacklistedError, DeviceNameError, ImageNameError, FlashImageError
from daft.modes.mode import Mode


class FlashMode(Mode):
    GENERATED_LOG_FILES = ["aft.log", "serial.log", "ssh.log", "kb_emulator.log", "serial.log.raw"]

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
        parser.add_argument("--save-ip", action="store_true", default=False,
                            help="Save the deployed ip into a file.")

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

    def execute_flashing(self, bb_dut, additional_flags=None):
        """
        Execute flashing of the DUT
        """
        if not os.path.isfile(self._args.image_file):
            raise ImageNameError(self._args.image_file + " doesn't exist.")

        print("Executing flashing of DUT")

        record = "--record" if self._args.record else ""
        dut = bb_dut["device_type"].lower()
        current_dir = os.getcwd().replace(self._config["workspace_nfs_path"], "")
        img_path = self._args.image_file.replace(self._config["workspace_nfs_path"], "/root/workspace")

        try:
            command = ["cd", "/root/workspace" + current_dir, ";aft", dut, img_path, record]

            if self._args.save_ip:
                # Delete the file if already exists
                expected_ip_path = Path(self._config["workspace_nfs_path"]) / self._args.dut.lower()
                expected_ip_path.unlink(missing_ok=True)

                command.extend(['--save-ip'])
            if additional_flags:
                command.extend(additional_flags)

            start_time = time.time()
            output = remote_execute(bb_dut["bb_ip"], command=command, timeout=1200, config=self._config)

            print(output, end="")
            print("Flashing took: " + time_used(start_time))
        except KeyboardInterrupt:
            raise
        except Exception:
            raise FlashImageError()
        finally:
            self._rename_logs()

    def dut_flash_and_boot(self, bb_dut):
        """
        Flash DUT and reboot it in test mode
        """
        flash_results = self.execute_flashing(bb_dut, additional_flags=['--boot', 'test_mode'])
        dut_ip_file = Path(self._config["workspace_nfs_path"]) / self._args.dut.lower()

        if dut_ip_file.exists():
            dut_ip = dut_ip_file.read_text()
            bbb_ip = bb_dut["bb_ip"]

            networking.fix_dut_routing(dut_ip, bbb_ip)
            networking.rewrite_ssh_keys(dut_ip)

        return flash_results

    def execute_usb_emulation(self, bb_dut):
        """
        Use testing harness USB emulation to boot the image
        """
        return self.execute_flashing(bb_dut, additional_flags=["--emulateusb"])

    def _rename_logs(self):
        for log in self.GENERATED_LOG_FILES:
            if os.path.isfile(log):
                os.rename(log, "flash_" + log)
