import os
import shutil

from daft.modes.common import local_execute
from daft.modes.mode import Mode


class UpdateMode(Mode):
    @classmethod
    def name(cls):
        return 'update'

    def __init__(self, args, config):
        self._args = args
        self._config = config

    def execute(self):
        """
        Update Beaglebone AFT
        """
        if os.path.isdir("testing_harness") and os.path.isdir("daft"):
            if os.path.isdir(self._config["bbb_fs_path"] + self._config["bbb_aft_path"]):
                try:
                    shutil.rmtree(self._config["bbb_fs_path"] + self._config["bbb_aft_path"])
                except FileNotFoundError:
                    pass
                shutil.copytree("testing_harness", self._config["bbb_fs_path"] +
                                self._config["bbb_aft_path"])
                print("Updated AFT successfully")
            else:
                print("Can't update AFT, didn't find " + self._config["bbb_fs_path"] +
                      self._config["bbb_aft_path"])
                return 3

            local_execute("python3 setup.py install".split(), cwd="daft/")
            local_execute("rm -r DAFT.egg-info build dist".split(), cwd="daft/")
            print("Updated DAFT successfully")

            return 0

        else:
            print("Can't update, didn't find 'daft' and 'testing_harness' directory")
            return 2

    @classmethod
    def add_mode_arguments(cls, parser):
        pass
