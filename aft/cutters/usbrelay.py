"""
Tool for handling USB-relay USB Cutter devices.
"""

try:
    import subprocess32
except ImportError:
    import subprocess as subprocess32
import os

from aft.cutters.cutter import Cutter


class Usbrelay(Cutter):
    """
    Wrapper for controlling cutters from Usbrelay.
    """
    cutter_controller = os.path.join(os.path.dirname(__file__), os.path.pardir,
                                     "tools", "cutter_on_off.py")

    def __init__(self, config):
        self._cutter_dev_path = config["cutter"]

    def connect(self):
        subprocess32.check_call(["python", self.cutter_controller,
                                 self._cutter_dev_path, "1"],
                                stdout=open(os.devnull, "w"),
                                stderr=open(os.devnull, "w"))

    def disconnect(self):
        subprocess32.check_call(["python", self.cutter_controller,
                                 self._cutter_dev_path, "0"],
                                stdout=open(os.devnull, "w"),
                                stderr=open(os.devnull, "w"))

    def get_cutter_config(self):
        """
        Returns the cutter configurations

        Returns:
            Cutter configuration as a dictionary with the following format:
            {
                "type": "usbrelay",
                "cutter": "/dev/ttyUSBx"
            }

        """
        return {"type": "usbrelay", "cutter": self._cutter_dev_path}
