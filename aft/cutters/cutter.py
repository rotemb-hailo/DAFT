"""
Base class for Cutter devices.
"""
import abc


class Cutter(abc.ABC):
    """
    Common abstract base class for all the makes of cutters.
    """
    DEFAULT_TIMEOUT = 5

    @abc.abstractmethod
    def connect(self):
        """
        Method connecting a channel
        """
        pass

    @abc.abstractmethod
    def disconnect(self):
        """
        Method disconnecting a channel
        """
        pass

    @abc.abstractmethod
    def get_cutter_config(self):
        """
        Returns cutter settings as a dictionary.
        """
        pass
