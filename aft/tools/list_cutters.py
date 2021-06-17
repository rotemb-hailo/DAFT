"""
Script to list attached USB-powercutters/usbrelays
"""

import fnmatch
import os

try:
    import subprocess32
except ImportError:
    import subprocess as subprocess32

ACCEPTED_DEVICES = [("0b00", "3070"), ("10c4", "ea60")]


def vidpid_filter(device):
    """
    Filter function which tests if a 'device' is a USB-powercutter
    """
    try:
        device_info = subprocess32.check_output(["udevadm", "info", device])
        device_lines = device_info.split("\n")
        vid_line = [line for line in device_lines if "ID_VENDOR_ID" in line][0]
        pid_line = [line for line in device_lines if "ID_MODEL_ID" in line][0]
        device_vid = vid_line.split("=")[-1]
        device_pid = pid_line.split("=")[-1]

        if (device_vid, device_pid) in ACCEPTED_DEVICES:
            return True
        return False
    except subprocess32.CalledProcessError:
        return False


def main():
    """
    Entry point. Prints all usb device under /dev which are assigned to USB-powercutter devices
    """
    devices = os.listdir("/dev")
    devices_full_paths = ["/dev/" + device for device in devices]
    tty_devices = [dev for dev in devices_full_paths if fnmatch.fnmatch(dev, "/dev/ttyUSB*")]
    cutter_devices = [dev for dev in tty_devices if vidpid_filter(dev)]
    for device in enumerate(cutter_devices, start=1):
        print(str(1) + " " + str(device[1]))
    return 0


if __name__ == '__main__':
    main()
