"""
Factory module for creation of AFT device instances and their cutter objects
"""

import aft.cutters.gpio_cutter
import aft.devices.pcdevice
import aft.kb_emulators.gadgetkeyboard

_DEVICE_CLASSES = {
    "pc": aft.devices.pcdevice.PCDevice,
}

_CUTTER_CLASSES = {
    "gpiocutter": aft.cutters.gpio_cutter.GpioCutter,
}

_KB_EMULATOR_CLASSES = {
    "gadgetkeyboard": aft.kb_emulators.gadgetkeyboard.GadgetKeyboard,
}


def build_kb_emulator(config):
    """
    Construct a keyboard emulator instance of type config["keyboard_emulator"]
    """
    if "keyboard_emulator" in config.keys():
        kb_emulator_class = _KB_EMULATOR_CLASSES[
            config["keyboard_emulator"].lower()]
        return kb_emulator_class(config)
    else:
        return None


def build_cutter(config):
    """
    Construct a (power) cutter instance of type config["cutter_type"].
    """
    cutter_class = _CUTTER_CLASSES[config["cutter_type"].lower()]
    return cutter_class(config)


def build_device(config, cutter, kb_emulator=None):
    """
    Construct a device instance of type config["platform"]
    """
    device_class = _DEVICE_CLASSES[config["platform"].lower()]
    return device_class(config, cutter, kb_emulator)
