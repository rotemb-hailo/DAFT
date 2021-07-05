"""
DAFT installation module
"""
import os

from setuptools import setup

DEFAULT_CONFIG = []
if not os.path.isfile("/etc/daft/devices.cfg"):
    DEFAULT_CONFIG.append("default_config/devices.cfg")
if not os.path.isfile("/etc/daft/daft.cfg"):
    DEFAULT_CONFIG.append("default_config/daft.cfg")

setup(
    name="DAFT",
    version="0.5",
    description="Distributed Automatic Flasher Tester",
    author="Simo Kuusela, Topi Kuutela, Igor Stoppa",
    author_email="simo.kuusela@intel.com",
    url="github",

    packages=["daft"],
    package_dir={"daft": "."},
    package_data={"daft": ["modes/*.py"]},

    entry_points={"console_scripts": ["daft=daft.main:main"]},
    data_files=[("/etc/daft/", DEFAULT_CONFIG),
                ("/etc/daft/lockfiles/", [])]
)
