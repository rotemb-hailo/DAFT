"""
Common helper functions for the device classes

In general, these are functions used by more than one, but not all, device
classes. In case all the device classes share a feature, it should be part of
the Device base class.
"""
import os
import sys
import time
from pathlib import Path

try:
    import subprocess32
except ImportError:
    import subprocess as subprocess32

from aft.logger import Logger as logger
import aft.tools.ssh as ssh


def wait_for_responsive_ip_for_pc_device(leases_file_path, timeout, polling_interval):
    """
    Attempt to acquire active ip address for the device with the given mac
    address up to timeout seconds.

    Args:
        leases_file_path (str): Path to dnsmasq leases file
        timeout (integer): Timeout in seconds
        polling_interval (integer): Time between retries in seconds.

    Returns:
        Ip address as a string, or None if ip address was not responsive.
    """
    logger.info("Waiting for the device to become responsive")
    logger.debug("Timeout: " + str(timeout))
    logger.debug("Polling interval: " + str(polling_interval))

    for _ in range(timeout // polling_interval):
        responsive_ip = get_ip_for_pc_device(leases_file_path)

        if not responsive_ip:
            time.sleep(polling_interval)
            continue

        logger.info("Got a response from " + responsive_ip)
        return responsive_ip

    logger.info("No responsive ip was found")


def get_ip_for_pc_device(leases_file_path):
    """
    Return active ip address for PC like device that leases it through dnsmasq.

    Address is considered to be active if ssh connection can be made
    successfully

    Args:
        leases_file_path (str): Path to dnsmasq leases file

    Returns:
        Device ip address as string or None if device does not have active
        ip address
    """
    ip_addresses = get_leased_ip_addresses_for_mac(leases_file_path)

    for ip_address in ip_addresses:
        if ssh.test_ssh_connectivity(ip_address):
            return ip_address

    return None


def get_leased_ip_addresses_for_mac(leases_file_path):
    """
    Return list of ip addresses that have been leased for the device with the
    given mac address.

    Args:
        leases_file_path (str): Path to dnsmasq leases file.

    Returns:
        List of ip addresses. Each ip address is a string.
    """
    leases = get_mac_leases_from_dnsmasq(leases_file_path)

    # If the testing setup has only one device return the first leases ip
    # address (there should be only one)
    if len(leases):
        return [leases[0]["ip"]]
    else:
        return []


def get_mac_leases_from_dnsmasq(leases_file_path):
    """
    Read the active leases from dnsmasq leases file and return a list of
    active leases as dictionaries.

    Args:
        leases_file_path (str): Path to leases file, e.g. /path/to/file/dnsmasq.leases

    Returns:
        List of dictionaries containing the active leases.
        The dictionaries have the following format:

        {
            "mac": "device_mac_address",
            "ip": "device_ip_address",
            "hostname": "device_host_name",
            "client_id": "client_id_or_*_if_unset"
        }
    """
    with open(leases_file_path) as lease_file:
        leases = lease_file.readlines()

    leases_list = []
    # dnsmasq.leases contains rows with the following format:
    # <lease_expiry_time_as_epoch_format> <mac> <ip> <hostname> <domain>
    # See:
    # http://lists.thekelleys.org.uk/pipermail/dnsmasq-discuss/2005q1/000143.html

    for lease in leases:
        lease = lease.split()
        leases_list.append({"mac": lease[1], "ip": lease[2], "hostname": lease[3], "client_id": lease[4]})

    return leases_list


def log_subprocess32_error_and_abort(err):
    """
    Log subprocess32 error cleanly and abort

    Args:
        err (subprocess32.CalledProcessError): The exception
    """
    logger.critical(str(err.cmd) + " failed with error code: " +
                    str(err.returncode) + " and output: " + str(err.output))
    logger.critical("Aborting")
    sys.exit(1)


def make_directory(directory):
    """
    Make directory safely

    Args:
        directory (str): The directory that will be created
    """
    try:
        os.makedirs(directory)
    except OSError:
        if not os.path.isdir(directory):
            raise


def verify_device_mode(ip, mode_name):
    """
    Check that the device with given ip is responsive to ssh and is in the
    specified mode.

    The mode is checked by checking that the mode_name arg is present in the
    /proc/version file

    Args:
        ip (str): The device ip address
        mode_name (str): Word to check for in /proc/version

    Returns:
        True if the device is in the desired mode, False otherwise
    """
    device_in_desired_mode = False

    try:
        ssh_stdout = ssh.remote_execute(ip, ["cat", "/proc/version"])

        if mode_name in ssh_stdout:
            logger.info("Found " + mode_name + " in DUT /proc/version")
            device_in_desired_mode = True
        else:
            logger.info("Didn't find " + mode_name + " in DUT /proc/version")
            logger.debug("/cat/proc/version: " + str(ssh_stdout))
    except subprocess32.CalledProcessError as err:
        logger.warning("Failed verifying the device mode with command: '" +
                       str(err.cmd) + "' failed with error code: '" +
                       str(err.returncode) + "' and output: '" +
                       str(err.output) + "'.")

    return device_in_desired_mode
