"""
A central location for all AFT errors
"""


class AFTConfigurationError(Exception):
    """
    An error caused by incorrect configuration
    """
    pass


class AFTImageNameError(Exception):
    """
    An error caused by non existing image file
    """
    pass


class AFTConnectionError(Exception):
    """
    An error caused by failed (SSH) connection
    """
    pass


class AFTTimeoutError(Exception):
    """
    A timeout error
    """
    pass


class AFTDeviceError(Exception):
    """
    An error caused by device under test
    """
    pass


class AFTNotImplementedError(Exception):
    """
    Feature not implemented
    """
    pass


class AFTPotentiallyBrokenBootloader(Exception):
    """
    Device might have a broken bootloader
    """
    pass
