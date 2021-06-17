"""
Base class for keyboard emulators.
"""
from abc import ABCMeta, abstractmethod


class KeyboardEmulator(ABCMeta):
    """
    Common abstract base class for keyboard emulators.
    """

    @abstractmethod
    def send_keystrokes(self, keystrokes):
        """
        Method to send keystrokes
        """
        pass
