"""
Class for handling threads.
"""


class ThreadHandler(object):
    """
    Flags: Dictionary with aĺl flags added with set_flag()
    Threads: List with all thread objects
    """
    RECORDERS_STOP = "recorders_stop"

    FLAGS = {}
    THREADS = []

    @staticmethod
    def add_thread(thread):
        """
        Add thread object to THREADS list
        """
        ThreadHandler.THREADS.append(thread)

    @staticmethod
    def get_threads():
        """
        Return THREADS list
        """
        return ThreadHandler.THREADS

    @staticmethod
    def set_flag(flag):
        """
        Add/change flag in FLAGS dictionary
        """
        ThreadHandler.FLAGS[flag] = True

    @staticmethod
    def unset_flag(flag):
        """
        Add/change flag in FLAGS dictionary
        """
        ThreadHandler.FLAGS[flag] = False

    @staticmethod
    def get_flag(flag):
        """
        Return flags value from FLAGS dictionary, if one isn't found return None
        """
        try:
            return ThreadHandler.FLAGS[flag]
        except KeyError:
            return None
