"""
Class representing a PC-like Device with an IP.
"""
import json
import os
import subprocess
import sys

import aft.devices.common as common
import aft.internal.config as config
import aft.internal.errors as errors
import aft.internal.tools.ssh as ssh
from aft.devices.device import Device
from aft.internal.logger import Logger as logger
from aft.internal.tools.gpio_export import export_gpio, set_gpio


class PCDevice(Device):
    """
    Class representing a PC-like device.

    Attributes:
        _RETRY_ATTEMPTS (integer):
            How many times the device attempts to enter the requested mode
            (testing/service) before givingup
        _BOOT_TIMEOUT (integer):
            The device boot timeout. Used when waiting for responsive ip address
        _POLLING_INTERVAL (integer):
            The polling interval used when waiting for responsive ip address
        _SSH_IMAGE_WRITING_TIMEOUT (integer):
            The timeout for flashing the image.
        _IMG_NFS_MOUNT_POINT (str):
            The location where the service OS mounts the nfs filesystem so that
            it can access the image file etc.
        _ROOT_PARTITION_MOUNT_POINT (str):
            The location where the service OS mounts the image root filesystem
            for SSH key injection.
        _SUPER_ROOT_MOUNT_POINT (str):
            Mount location used when having to mount two layers
    """
    _RETRY_ATTEMPTS = 4
    _BOOT_TIMEOUT = 240
    _POLLING_INTERVAL = 10
    _SSH_IMAGE_WRITING_TIMEOUT = 1440
    _IMG_NFS_MOUNT_POINT = "/mnt/img_data_nfs"
    _ROOT_PARTITION_MOUNT_POINT = "/mnt/target_root/"
    _SUPER_ROOT_MOUNT_POINT = "/mnt/super_target_root/"

    PC_STATIC_IP = "192.168.30.1"
    BBB_STATIC_IP = "192.168.7.1"
    PC_NETWORK = "192.168.30.0/24"

    def __init__(self, parameters, channel, kb_emulator):
        """
        Constructor

        Args:
            parameters (Dictionary): Device configuration parameters
            channel (aft.Cutter): Power cutter object
            kb_emulator (aft.kb_emulators.kb_emulator): Keyboard emulator object
        """
        super().__init__(device_descriptor=parameters, channel=channel, kb_emulator=kb_emulator)

        self.leases_file_name = parameters["leases_file_name"]
        self._service_mode_name = parameters["service_mode"]
        self._boot_internal_keystrokes = parameters["boot_internal_keystrokes"]
        self._boot_usb_keystrokes = parameters["boot_usb_keystrokes"]
        self._target_device = parameters["target_device"]
        self.device_ip = None
        self._uses_hddimg = None

        export_gpio(port="60", value="0")
        export_gpio(port="48", value="0")

    def write_image(self, file_name):
        """
        Method for writing an image to a device.

        Args:
            file_name (str):
                The file name of the image that will be flashed on the device

        Returns:
            None
        """
        # NOTE: it is expected that the image is located somewhere
        # underneath config.NFS_FOLDER (default: /home/tester),
        # therefore symlinks outside of it will not work
        # The config.NFS_FOLDER path is exported as nfs and mounted remotely as
        # _IMG_NFS_MOUNT_POINT

        # Bubblegum fix to support both .hddimg and .hdddirect at the same time
        self._uses_hddimg = os.path.splitext(file_name)[-1] == ".hddimg"

        self._enter_mode("service_mode", self._boot_usb_keystrokes)

        file_on_nfs = os.path.abspath(file_name).replace(config.NFS_FOLDER, self._IMG_NFS_MOUNT_POINT)
        self._flash_image(nfs_file_name=file_on_nfs, filename=file_name)
        self._install_tester_public_key(file_name)

    def _run_tests(self, test_case):
        """
        Boot to test-mode and execute testplan.

        Args:
            test_case (aft.TestCase): Test case object

        Returns:
            The return value of the test_case run()-method
            (implementation class specific)
        """
        return test_case.run(self)

    def get_ip(self):
        """
        Returns device ip address

        Returns:
            (str): The device ip address
        """
        return common.get_ip_for_pc_device(self.parameters["leases_file_name"])

    def boot_internal_test_mode(self):
        self._enter_mode("test_mode", self._boot_internal_keystrokes)

    def boot_usb_test_mode(self):
        self._enter_mode("test_mode", self._boot_usb_keystrokes)

    def boot_usb_service_mode(self):
        self._enter_mode("service_mode", self._boot_usb_keystrokes)

    def _enter_mode(self, target, keystrokes):
        """
        Try to put the device into the specified mode.

        Args:
            keystrokes (string): Path to keystrokes file for booting
            target (string): Boot target: 'test_mode' or 'service_mode'
        Raises:
            aft.errors.AFTDeviceError if device fails to enter the mode or if
            keyboard emulator fails to connect
        """
        if target not in ["test_mode", "service_mode"]:
            raise errors.AFTDeviceError(f"Bad argument: target={target} for pcdevice.py: _enter_mode function")

        # Sometimes booting to a mode fails.
        logger.info(f"Trying to enter {target} up to {str(self._RETRY_ATTEMPTS)} times.")

        for _ in range(self._RETRY_ATTEMPTS):
            try:
                self._set_boot_relay(target)
                self._power_cycle()

                if self.kb_emulator:
                    logger.info("Using " + type(self.kb_emulator).__name__ + " to send keyboard sequence " + keystrokes)
                    self.kb_emulator.send_keystrokes(keystrokes)
                else:
                    logger.warning("No keyboard emulator defined for the device")

                ip_address = self.wait_for_responsive_ip()
                dut_in_service_mode = common.verify_device_mode(self.device_ip, self._service_mode_name)
                booted_in_required_mode = (dut_in_service_mode and target == "service_mode") or \
                                          (not dut_in_service_mode and target == "test_mode")

                if ip_address and booted_in_required_mode:
                    logger.info(f"Correctly booted {target} image - IP: {ip_address}")
                    self._post_boot_hooks(target)

                    return
                else:
                    logger.warning("Failed entering " + target + ".")
            except KeyboardInterrupt:
                raise
            except:
                _err = sys.exc_info()
                logger.error(str(_err[0]).split("'")[1] + ": " + str(_err[1]))

        logger.critical("Unable to get the device in mode " + target)
        raise errors.AFTDeviceError("Could not set the device in mode " + target)

    def wait_for_responsive_ip(self):
        """
        For a limited amount of time, try to assess if the device
        is in the mode requested.

        Returns:
            (str or None):
                The device ip, or None if no active ip address was found
        """
        self.device_ip = common.wait_for_responsive_ip_for_pc_device(self.parameters["leases_file_name"],
                                                                     self._BOOT_TIMEOUT, self._POLLING_INTERVAL)

        return self.device_ip

    def _flash_image(self, nfs_file_name, filename):
        """
        Writes image into the internal storage of the device.

        Args:
            nfs_file_name (str): The image file path on the nfs
            filename (str): The image filename

        Returns:
            None
        """
        used_by_another_process_return_code = 32

        logger.info("Mounting the nfs containing the image to flash.")
        ssh.remote_execute(self.device_ip, ["mount", self._IMG_NFS_MOUNT_POINT],
                           ignore_return_codes=[used_by_another_process_return_code])

        logger.info(f"Writing {nfs_file_name} to internal storage.")
        bmap_args = ["bmaptool", "copy", nfs_file_name, self._target_device]

        if os.path.isfile(filename + ".bmap"):
            logger.info(f"Found {filename} .bmap. Using bmap for flashing.")
        else:
            logger.info(f"Didn't find {filename} .bmap. Flashing without it.")
            bmap_args.insert(2, "--nobmap")

        ssh.remote_execute(self.device_ip, bmap_args, timeout=self._SSH_IMAGE_WRITING_TIMEOUT)

        # Flashing the same file as already on the disk causes non-blocking
        # removal and re-creation of /dev/disk/by-partuuid/ files.
        # This sequence either delays enough or actually settles it.
        logger.info("Partprobing.")
        ssh.remote_execute(self.device_ip, ["partprobe", self._target_device])
        ssh.remote_execute(self.device_ip, ["sync"])
        ssh.remote_execute(self.device_ip, ["udevadm", "trigger"])
        ssh.remote_execute(self.device_ip, ["udevadm", "settle"])
        ssh.remote_execute(self.device_ip, ["udevadm", "control", "-S"])

    def _mount_single_layer(self, image_file_name):
        """
        Mount a hdddirect partition

        Returns:
            None
        """
        logger.info("Mount one layer.")
        ssh.remote_execute(self.device_ip,
                           ["mount", self.get_root_partition_path(image_file_name), self._ROOT_PARTITION_MOUNT_POINT])

    def get_root_partition_path(self, image_file_name):
        """
        Select either the default config value to be the root_partition
        or if the disk layout file exists, use the rootfs from it.

        Args:
            image_file_name (str): The name of the image file. Disk layout file
            name is based on this

        Returns:
            (str): path to the disk pseudo file
        """
        layout_file_name = self.get_layout_file_name(image_file_name)

        if not os.path.isfile(layout_file_name):
            logger.info("Disk layout file " + layout_file_name + " doesn't exist. Finding root partition.")
            return self.find_root_partition()

        layout_file = open(layout_file_name, "r")
        disk_layout = json.load(layout_file)
        rootfs_partition = next(partition for partition in list(disk_layout.values())
                                if isinstance(partition, dict) and partition["name"] == "rootfs")

        return os.path.join("/dev", "disk", "by-partuuid", rootfs_partition["uuid"])

    def get_layout_file_name(self, image_file_name):
        return image_file_name.split(".")[0] + "-disk-layout.json"

    def find_root_partition(self):
        """
        Find _target_device partition that has /home/root
        Find all _target_device partitions
        """
        partitions = []
        target = self._target_device.split("/")[-1]
        lsblk = ssh.remote_execute(self.device_ip, ["lsblk"])
        lsblk = lsblk.split()

        for line in lsblk:
            if (target + "p") in line:
                line = ''.join(x for x in line if x.isalnum())
                partitions.append(line)

        # Check through partitions if it contains '/home/root' directory
        for partition in partitions:
            ssh.remote_execute(self.device_ip, ["mount", "/dev/" + partition, self._ROOT_PARTITION_MOUNT_POINT])
            files = ssh.remote_execute(self.device_ip, ["ls", self._ROOT_PARTITION_MOUNT_POINT])

            if "home" in files:
                files = ssh.remote_execute(self.device_ip, ["ls", self._ROOT_PARTITION_MOUNT_POINT + "home/"])

            ssh.remote_execute(self.device_ip, ["umount", self._ROOT_PARTITION_MOUNT_POINT])

            if "root" in files:
                partition_path = "/dev/" + partition
                return partition_path

        raise errors.AFTDeviceError("Couldn't find root partition")

    def _mount_two_layers(self):
        """
        Mount a hddimg which has 'rootfs' partition

        Returns:
            None
        """
        logger.info("Mounts two layers.")
        ssh.remote_execute(self.device_ip, ["modprobe", "vfat"])

        # mount the first layer of .hddimg
        ssh.remote_execute(self.device_ip, ["mount", self._target_device, self._SUPER_ROOT_MOUNT_POINT])
        ssh.remote_execute(self.device_ip,
                           ["mount", self._SUPER_ROOT_MOUNT_POINT + "rootfs.img", self._ROOT_PARTITION_MOUNT_POINT])

    def _install_tester_public_key(self, image_file_name):
        """
        Copy ssh public key to root user on the target device.
        After the Flash process is done, mount the mmcblk0p1 (rootfs partition) in order to inject the SSH keys allowed
        (*The DUT is booted in service mode during this process)

        Returns:
            None
        """
        # update info about the partition table
        if not self._uses_hddimg:
            self._mount_single_layer(image_file_name)
        else:
            self._mount_two_layers()

        # Identify the home of the root user
        root_user_home_command = ["cat", os.path.join(self._ROOT_PARTITION_MOUNT_POINT, "etc/passwd"),
                                  "|", "grep", "-e", '"^root"', "|", "sed", "-e", '"s/root:.*:root://"', "|",
                                  "sed", "-e", '"s/:.*//"']
        root_user_home = ssh.remote_execute(self.device_ip, root_user_home_command).rstrip().lstrip("/")

        logger.info("Writing ssh-key to device.")
        remote_ssh_dir = os.path.join(self._ROOT_PARTITION_MOUNT_POINT, root_user_home, ".ssh")
        ssh.remote_execute(self.device_ip, ["mkdir", "-p", remote_ssh_dir])
        ssh.remote_execute(self.device_ip, ["chmod", "700", remote_ssh_dir])

        try:
            # Try to copy SSH keys to the authorized_keys file
            authorized_keys_path = os.path.join(remote_ssh_dir, "authorized_keys")
            ssh.remote_execute(self.device_ip, ["cat", "~/.ssh/authorized_keys", ">>", authorized_keys_path])
            ssh.remote_execute(self.device_ip, ["chmod", "600", authorized_keys_path])
        except Exception as e:
            # If the preceding method fails, try to copy them directly to a dropbear authorized_keys files
            # (as the the preceding method fails if the device is running dropbear instead of OpenSSH)
            logger.info("Failed, trying to write the ssh-key in dropbear file instead.")
            ssh.remote_execute(self.device_ip, ["cat", "~/.ssh/authorized_keys", ">>",
                                                os.path.join(self._ROOT_PARTITION_MOUNT_POINT,
                                                             "var/lib/dropbear/authorized_keys")])
            logger.info("Success.")

        logger.info("Flushing.")
        ssh.remote_execute(self.device_ip, ["sync"])
        logger.info("Unmounting.")
        ssh.remote_execute(self.device_ip, ["umount", self._ROOT_PARTITION_MOUNT_POINT])

        if self._uses_hddimg:
            ssh.remote_execute(self.device_ip, ["umount", self._SUPER_ROOT_MOUNT_POINT])

    def execute(self, command, timeout, user="root", verbose=False):
        """
        Runs a command on the device and returns log and error-level.

        Args:
            command (list[str]): The command that will be executed
            timeout (integer): Timeout for the command
            user (str): The user that executes the command
            verbose (boolean): Controls verbosity

        Return:
            Return value of aft.ssh.remote_execute
        """
        return ssh.remote_execute(self.get_ip(), command, timeout=timeout, user=user)

    def push(self, source, destination, user="root"):
        """
        Deploys a file from the local filesystem to the device (remote).

        Args:
            source (str): The source file
            destination (str): The destination file
            user (str): The user who executes the command
        """
        ssh.push(self.get_ip(), source=source, destination=destination, user=user)

    def _set_boot_relay(self, target):
        if target == 'service_mode':
            logger.info('Setting boot relay in service mode')
            set_gpio(port="48", value="1")
        elif target == 'test_mode':
            logger.info('Setting boot relay in test mode')
            set_gpio(port="48", value="0")

    def _post_boot_hooks(self, target):
        if target == 'service_mode':
            self._fix_dut_ip_routing()

    def _fix_dut_ip_routing(self):
        """
        The IP routes tables get flushed every reboot, the routeing table might fail to add the route to the PC on boot
        In that case, add this route manually
        """
        try:
            logger.info(f'Trying to ping {self.PC_STATIC_IP}')
            ping_command = f"ping -c 1 {self.PC_STATIC_IP}".split()
            self.execute(ping_command, timeout=10)
        except subprocess.CalledProcessError:
            logger.info("Ping failed, trying to add an route via BBB to the PC")
            add_ip_route_command = f"ip route add {self.PC_NETWORK} via {self.BBB_STATIC_IP}".split()
            self.execute(add_ip_route_command, timeout=30)
            logger.info("Successfully added route to the PC")
