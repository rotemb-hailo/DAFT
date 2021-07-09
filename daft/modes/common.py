import configparser
from enum import Enum

import os
import subprocess
import time
from contextlib import contextmanager

from daft.modes.exceptions import DevicesBlacklistedError, DeviceNameError


@contextmanager
def reserve_device(args, config):
    device = None

    try:
        device = _reserve_device(args)
        yield device
    finally:
        if device:
            release_device(device)
            remote_execute(device["bb_ip"], 'ps aux | grep "[a]ft" | xargs -r kill -s SIGINT'.split(), timeout=10,
                           config=config)


def _reserve_device(args):
    """
    Reserve Beaglebone/DUT for flashing and testing
    """
    start_time = time.time()
    dut = args.dut.lower()
    config = get_bbb_config()
    dut_found = False

    while True:
        duts_blacklisted = 1
        for device in config:
            if device["device_type"].lower() == dut or device["device"].lower() == dut:
                dut_found = True
                lockfile = "/etc/daft/lockfiles/" + device["device"]
                write_mode = "w+"
                if os.path.isfile(lockfile):
                    write_mode = "r+"
                with open(lockfile, write_mode) as f:
                    lockfile_contents = f.read()

                    if not lockfile_contents:
                        f.write("Locked\n")
                        print("Reserved " + device["device"])
                        print("Waiting took: " + time_used(start_time))

                        return device
                    if "Locked\n" == lockfile_contents:
                        duts_blacklisted = 0

        if not dut_found:
            print("Device name '" + dut + "', was not found in "
                                          "/etc/daft/devices.cfg")
            raise DeviceNameError()

        if duts_blacklisted:
            print("All devices named '" + dut + "' are blacklisted in "
                                                "/etc/daft/lockfiles.")
            raise DevicesBlacklistedError()

        time.sleep(10)


def get_bbb_config():
    """
    Read and parse BBB configuration file and return result as dictionary
    """
    config = configparser.SafeConfigParser()
    config.read("/etc/daft/devices.cfg")
    configurations = []
    for device in config.sections():
        device_config = dict(config.items(device))
        device_config["device"] = device
        device_config["device_type"] = device.rstrip('1234567890_')
        configurations.append(device_config)

    return configurations


def release_device(beaglebone_dut):
    """
    Release Beaglebone/DUT lock
    """
    if beaglebone_dut:
        lockfile = "/etc/daft/lockfiles/" + beaglebone_dut["device"]
        with open(lockfile, "w") as f:
            f.write("")
            print("Released " + beaglebone_dut["device"])


def remote_execute(remote_ip, command, timeout=60, ignore_return_codes=None,
                   user="root", connect_timeout=15, config=None):
    """
    Execute a Bash command over ssh on a remote device with IP 'remote_ip'.
    Returns combines stdout and stderr if there are no errors. On error raises
    subprocess errors.
    """
    ssh_args = ["ssh",
                "-i", config["bbb_fs_path"] + "/root/.ssh/id_rsa_testing_harness",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "StrictHostKeyChecking=no",
                "-o", "BatchMode=yes",
                "-o", "LogLevel=ERROR",
                "-o", "ConnectTimeout=" + str(connect_timeout),
                user + "@" + str(remote_ip)]

    connection_retries = 3

    for i in range(1, connection_retries + 1):
        try:
            output = local_execute(ssh_args + command, timeout, ignore_return_codes)
        except subprocess.CalledProcessError as err:
            if "Connection refused" in err.output and i < connection_retries:
                time.sleep(2)
                continue
            raise err

        return output


def local_execute(command, timeout=60, ignore_return_codes=None, cwd=None):
    """
    Execute a command on local machine. Returns combined stdout and stderr if
    return code is 0 or included in the list 'ignore_return_codes'. Otherwise
    raises a subprocess error.
    """
    process = subprocess.Popen(command, universal_newlines=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               cwd=cwd)
    start = time.time()
    output = ""
    return_code = None
    while time.time() < start + timeout and return_code is None:
        return_code = process.poll()
        if return_code is None:
            try:
                output += process.communicate(timeout=1)[0]
            except subprocess.TimeoutExpired:
                pass
    if return_code is None:
        # Time ran out but the process didn't end.
        raise subprocess.TimeoutExpired(cmd=command, output=output,
                                        timeout=timeout)
    if ignore_return_codes is None:
        ignore_return_codes = []
    if return_code in ignore_return_codes or return_code == 0:
        return output
    else:
        print(output, end="")
        raise subprocess.CalledProcessError(returncode=return_code,
                                            cmd=command, output=output)


def time_used(start_time):
    """
    Calculate and return time taken from start time
    """
    minutes, seconds = divmod((time.time() - start_time), 60)
    minutes = int(round(minutes))
    seconds = int(round(seconds))
    time_taken = str(minutes) + "min " + str(seconds) + "s"

    return time_taken
