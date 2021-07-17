"""Tool for managing collection of devices from the same host PC"""

import atexit
import errno

import configparser
import fcntl
import os
import sys
import time
from contextlib import contextmanager

import aft.internal.config as config
import aft.internal.device_factory as device_factory
import aft.internal.errors as errors
from aft.internal.logger import Logger
from aft.internal.tools.misc import local_execute, inject_ssh_keys_to_image


class DevicesManager:
    """Class handling devices connected to the same host PC"""
    __PLATFORM_FILE_NAME = "/etc/aft/devices/platform.cfg"

    # Construct the device object of the correct machine type based on the
    # catalog config file.
    def __init__(self, args):
        """
        Constructor

        Based on command-line arguments and configuration files, construct
        configurations

        Args:
            args (argparse namespace argument object):
                Command line arguments, as parsed by argparse
        """
        self._args = args
        self._lock_files = []
        self._logger = Logger
        self.device_configs = self._construct_configs()

    def _construct_configs(self):
        """
        Find and merge the device configurations into single data structure.

        Returns:
            List of dictionaries, where dictionaries have the following format:
            {
                "name": "device_name",
                "model": "device_model",
                "settings": {
                                "device_specific_setting1": "value1",
                                "device_specific_setting2": "value2",
                                "platform_setting1": "value3",
                                "catalog_setting1": "value4",
                            }
            }

        Note:
            catalog\platform entries are not device specific, but these are
            duplicated for each device for ease of access.
        """
        platform_config_file = self.__PLATFORM_FILE_NAME
        catalog_config_file = self._args.catalog

        platform_config = configparser.SafeConfigParser()
        platform_config.read(platform_config_file)
        catalog_config = configparser.SafeConfigParser()
        catalog_config.read(catalog_config_file)

        configs = list()

        for device_title in catalog_config.sections():
            model = device_title
            catalog_entry = dict(catalog_config.items(model))

            platform = catalog_entry["platform"]
            platform_entry = dict(platform_config.items(platform))

            settings = dict()

            # note the order: more specific file overrides changes from
            # more generic. This should be maintained
            settings.update(platform_entry)
            settings.update(catalog_entry)

            settings["model"] = device_title.lower()
            settings["name"] = device_title.lower()
            settings["serial_log_name"] = config.SERIAL_LOG_NAME

            device_param = dict()
            device_param["name"] = device_title.lower()
            device_param["model"] = model.lower()
            device_param["settings"] = settings
            configs.append(device_param)

        if len(configs) == 0:
            raise errors.AFTConfigurationError("Zero device configurations built - is this really correct? " +
                                               "Check that paths for catalog and platform files "
                                               "are correct and that the files have some settings inside")

        self._logger.info("Built configuration sets for " + str(len(configs)) + " devices")

        return configs

    @contextmanager
    def reserve(self, timeout=3600):
        device = None

        try:
            device = self._reserve(timeout)
            yield device
        finally:
            if device:
                self._release(device)

    def _reserve(self, timeout=3600):
        """
        Reserve and lock a device and return it
        """
        devices = []

        for device_config in self.device_configs:
            if device_config["model"].lower() == self._args.machine.lower():
                cutter = device_factory.build_cutter(device_config["settings"])
                kb_emulator = device_factory.build_kb_emulator(device_config["settings"])
                device = device_factory.build_device(device_config["settings"], cutter, kb_emulator)
                devices.append(device)

        return self._do_reserve(devices, self._args.machine, timeout)

    def reserve_specific(self, machine_name, timeout=3600, model=None):
        """
        Reserve and lock a specific device. If model is given, check if
        the device is the given model
        """

        # Basically very similar to a reserve-method
        # we just populate they devices array with a single device
        devices = []

        for device_config in self.device_configs:
            if device_config["name"].lower() == machine_name.lower():
                cutter = device_factory.build_cutter(device_config["settings"])
                kb_emulator = device_factory.build_kb_emulator(
                    device_config["settings"])
                device = device_factory.build_device(device_config["settings"],
                                                     cutter,
                                                     kb_emulator)
                devices.append(device)
                break

        # Check if device is a given model
        if model and len(devices):
            if not devices[0].model.lower() == model.lower():
                raise errors.AFTConfigurationError(
                    "Device and machine doesn't match")

        return self._do_reserve(devices, machine_name, timeout)

    def _do_reserve(self, devices, name, timeout):
        """d
        Try to reserve and lock a device from devices list.
        """
        if len(devices) == 0:
            raise errors.AFTConfigurationError("No device configurations when reserving " + name +
                                               " - check that given machine type or name is correct ")

        start = time.time()

        while time.time() - start < timeout:
            for device in devices:
                self._logger.info("Attempting to acquire " + device.name)
                try:
                    # This is a non-atomic operation which may cause trouble
                    # Using a locking database system could be a viable fix.
                    lockfile = os.fdopen(os.open(os.path.join(config.LOCK_FILE, "daft_dut_lock"),
                                                 os.O_WRONLY | os.O_CREAT, 0o660), "w")
                    fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)

                    self._logger.info("Device acquired.")
                    self._lock_files.append(("daft_dut_lock", lockfile))
                    atexit.register(self._release, device)

                    return device
                except IOError as err:
                    if err.errno in {errno.EACCES, errno.EAGAIN}:
                        self._logger.info("Device busy.")
                    else:
                        self._logger.critical("Cannot obtain lock file.")
                        sys.exit(-1)
            self._logger.info("All devices busy ... waiting 10 seconds and trying again.")
            time.sleep(10)
        raise errors.AFTTimeoutError("Could not reserve " + name + " in " + str(timeout) + " seconds.")

    def _release(self, reserved_device):
        """
        Put the reserved device back to the pool. It will happen anyway when
        the process dies, but this removes the stale lockfile.
        """
        for i in self._lock_files:
            if i[0] == "daft_dut_lock":
                i[1].close()
                self._lock_files.remove(i)
                break

        if reserved_device:
            path = os.path.join(config.LOCK_FILE, "daft_dut_lock")

            if os.path.isfile(path):
                os.unlink(path)

    def prepare_device(self, device, args):
        """
        Reserve and flash a machine. By default it tries to flash 2 times,

        Args:
            args: AFT arguments
        Returns:
            device: Reserved machine.
        """
        if args.record:
            device.record_serial()

        if not self.check_libcomposite_service_running():
            self.stop_image_usb_emulation(device.leases_file_name)

        if args.emulateusb:
            self.start_image_usb_emulation(args, device.leases_file_name)
            inject_ssh_keys_to_image(args.file_name)

        return device

    def try_flash_device(self, args, device):
        if args.noflash:
            return device

        return self._flash(args, device)

    def _flash(self, args, device):
        flash_attempt = 0
        flash_retries = args.flash_retries

        while flash_attempt < flash_retries:
            flash_attempt += 1
            try:
                print(f"Flashing {device.name}, attempt {flash_attempt} of {flash_retries}.")
                device.write_image(args.file_name)
                print("Flashing successful.")

                return device
            except KeyboardInterrupt:
                raise
            except Exception as e:
                self._logger.error(str(e))

                if (flash_retries - flash_attempt) == 0:
                    self._logger.info("Flashing failed " + str(flash_attempt) + " times")
                    self._release(device)
                    raise
                elif (flash_retries - flash_attempt) == 1:
                    self._logger.info("Flashing failed, trying again one more time")
                elif (flash_retries - flash_attempt) > 1:
                    self._logger.info(
                        "Flashing failed, trying again " + str(flash_retries - flash_attempt) + " more times")

    def check_libcomposite_service_running(self):
        """
        Check if lib-composite.service is running. Return 1 if running, else 0
        """
        found_msg = "OK"
        check_if_service_running = f'systemctl is-active --quiet libcomposite.service && echo "{found_msg}" || "NO"'
        self._logger.info(f'Checking if lib-composite is running {check_if_service_running}')
        stdout = local_execute(check_if_service_running, shell=True)

        return stdout.strip() == found_msg

    def start_image_usb_emulation(self, args, leases_file):
        """
        Start using the image with USB mass storage emulation
        """
        if self.check_libcomposite_service_running():
            local_execute("systemctl stop libcomposite.service".split())

        self.free_dnsmasq_leases(leases_file)
        image_file = os.path.abspath(args.file_name)

        if not os.path.isfile(image_file):
            print("Image file doesn't exist")
            raise errors.AFTImageNameError("Image file doesn't exist")

        local_execute(("start_libcomposite " + image_file).split())
        self._logger.info("Started USB mass storage emulation using " + image_file)

    def stop_image_usb_emulation(self, leases_file):
        """
        Stop using the image with USB mass storage emulation
        """
        self.free_dnsmasq_leases(leases_file)
        local_execute("stop_libcomposite".split())
        local_execute("systemctl start libcomposite.service".split())
        self._logger.info("Stopped USB mass storage emulation with an image")

    def free_dnsmasq_leases(self, leases_file):
        """
        dnsmasq.leases file needs to be cleared and dnsmasq.service restarted
        or there will be no IP address to give for DUT if same
        image is used in quick succession with and without --emulateusb
        """
        local_execute("systemctl stop dnsmasq.service".split())

        with open(leases_file, "w") as f:
            f.write("")
            f.flush()

        local_execute("systemctl start dnsmasq.service".split())
        self._logger.info("Freed dnsmasq leases")

    def get_configs(self):
        return self.device_configs
