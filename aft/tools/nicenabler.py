"""
Script to keep a Linux network interface attached to a USB-path available even
if it disappears momentarily.
"""

import subprocess
import os
import netifaces
import time
import argparse


def _get_nth_parent_dir(path, parent):
    """
    Return the 'parent'h parent directory of 'path'
    """
    if parent == 0:
        return path
    return _get_nth_parent_dir(os.path.dirname(path), parent - 1)


def find_nic_with_usb_path(usb_path):
    """
    Search and return the name of a network interface attached to 'usb_path' USB-path
    """
    _NIC_FILESYSTEM_LOCATION = "/sys/class/net"
    interfaces = netifaces.interfaces()
    for interface in interfaces:
        nic_path = os.path.realpath(os.path.join(_NIC_FILESYSTEM_LOCATION, interface))
        nic_usb_path = _get_nth_parent_dir(nic_path, 3)

        if os.path.basename(nic_usb_path) == usb_path:
            return interface
    return None


def wait_and_enable_nic(usb_path, ip_address):
    """
    Wait until a network interface appears in USB-path 'usb_path' and once it does,
    assign ip address and subnet size <*.*.*.*/x> 'ip_address' to it.
    """
    while True:
        nic = find_nic_with_usb_path(usb_path)
        if not nic:
            time.sleep(1)
            continue

        # assumes the script is present in the same directory
        interface_script = os.path.join(os.path.dirname(__file__), "interface_script.sh")

        subprocess.check_call(["sudo", interface_script, nic, ip_address])
        return


def main():
    """
    Start point.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=str, help="USB-tree path of the NIC")
    parser.add_argument("ip", type=str, help="IP-address/subnet to be assigned " +
                                             "to the NIC <*.*.*.*/x>")
    args = parser.parse_args()

    while True:
        nic = find_nic_with_usb_path(args.path)
        if not nic:
            wait_and_enable_nic(args.path, args.ip)
        time.sleep(1)


if __name__ == '__main__':
    main()
