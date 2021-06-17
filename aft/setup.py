"""
AFT installation module
"""
import os
from setuptools import setup

DEVICE_FILES = ["default_config/devices/platform.cfg",
                "default_config/devices/catalog.cfg"]
TEST_PLANS = ["default_config/test_plan/iot_qatest.cfg"]
CONFIG_FILES = ["default_config/aft.cfg"]


def config_filter(filename):
    return not os.path.isfile(os.path.join("/etc/aft", filename[len("default_config/"):]))


DEVICE_FILES = [filename for filename in DEVICE_FILES if config_filter(filename)]
TEST_PLANS = [filename for filename in TEST_PLANS if config_filter(filename)]
CONFIG_FILES = [filename for filename in CONFIG_FILES if config_filter(filename)]

dependencies = ["netifaces", "unittest-xml-reporting", "pyserial>=3", "fabric"]

setup(name="aft",
      version="1.0.0",
      description="Automated Flasher Tester",
      author="Igor Stoppa, Topi Kuutela, Erkka Kääriä, Simo Kuusela",
      author_email="igor.stoppa@intel.com, topi.kuutela@intel.com, erkka.kaaria@intel.com, simo.kuusela@intel.com",
      url="github",
      packages=["aft"],
      package_dir={"aft": "."},
      package_data={"aft": ["cutters/*.py",
                            "kb_emulators/*.py",
                            "devices/*.py",
                            "testcases/*.py",
                            "internal/*.py",
                            "internal/tools/*.py"]},
      install_requires=dependencies,
      entry_points={"console_scripts": ["aft=aft.main:main"]},
      data_files=[("/etc/aft/devices/", DEVICE_FILES),
                  ("/etc/aft/test_plan/", TEST_PLANS),
                  ("/etc/aft/", CONFIG_FILES)])
