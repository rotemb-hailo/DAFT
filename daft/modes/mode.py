from abc import ABC, abstractmethod


class Mode(ABC):
    @abstractmethod
    def execute(self):
        pass

    @classmethod
    @abstractmethod
    def name(cls):
        pass

    @classmethod
    @abstractmethod
    def add_mode_arguments(cls, parser):
        """
        Receives an argument parser, and adds the arguments that are required for the flow's function to it
        Args:
            parser (): 
        """
        pass
