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
    py_modules=["main"],
    entry_points={"console_scripts": ["daft=main:main"]},
    data_files=[("/etc/daft/", DEFAULT_CONFIG),
                ("/etc/daft/lockfiles/", [])]
)
