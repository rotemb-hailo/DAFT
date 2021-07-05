"""
Base class for keyboard emulators.
"""
from abc import ABC, abstractmethod


class KeyboardEmulator(ABC):
    """
    Common abstract base class for keyboard emulators.
    """
    @abstractmethod
    def send_keystrokes(self, keystrokes):
        """
        Method to send keystrokes
        """
        pass
