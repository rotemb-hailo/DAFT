import os
from contextlib import contextmanager

from aft.cutters.cutter import Cutter
from aft.internal.logger import Logger as logger


class GpioCutterError(Exception):
    def __init__(self, message=None):
        self.message = message

    def __str__(self):
        return self.message


class GpioCutter(Cutter):
    """
    Class for controlling a relay with Beaglebone Black GPIO pin
    """

    def __init__(self, config):
        super().__init__()
        self._GPIOS_BASE_DIR = '/sys/class/gpio'
        self._GPIO_PIN = config["gpio_pin"]
        self._GPIO_CUTTER_ON = int(config["gpio_cutter_on"])
        self._GPIO_CUTTER_OFF = int(config["gpio_cutter_off"])

    def connect(self):
        """
        Turns power on
        """
        try:
            self._set_gpio_pin(self._GPIO_CUTTER_ON)
        except GpioCutterError as e:
            logger.error(e)
            logger.error("Unable to set GPIO controlled cutter on")
            raise e

    def disconnect(self):
        """
        Turns power off
        """
        try:
            self._set_gpio_pin(self._GPIO_CUTTER_OFF)
        except GpioCutterError as e:
            logger.error(e)
            logger.error("Unable to set GPIO controlled cutter off")
            raise e

    def get_cutter_config(self):
        """
        Returns cutter settings.
        """
        return 0

    def _set_gpio_pin(self, state):
        """
        Set GPIO pin to state
        """
        if state < 0:
            raise GpioCutterError("There is not any negative gpio state")

        with self._open_virt_file() as fd:
            fd.write(str(state))

    @contextmanager
    def _open_virt_file(self):
        gpio_abs_path = os.path.join(self._GPIOS_BASE_DIR, self._GPIO_PIN, 'value')

        if not os.path.isfile(gpio_abs_path):
            error_msg = "GPIO file {0} is not found".format(gpio_abs_path)
            logger.error(error_msg)
            raise GpioCutterError(error_msg)

        try:
            fd = open(gpio_abs_path, 'w')
        except (OSError, IOError) as e:
            logger.error(e)
            error_msg = "GPIO file {0} can not be opened".format(gpio_abs_path)
            logger.error(error_msg)
            raise GpioCutterError("GPIO file can not be loaded")

        yield fd
        fd.close()
