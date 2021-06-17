from pathlib import Path

GPIO_BASE_PATH = Path("/sys/class/gpio/")


def export_gpio(port, value, direction='out'):
    gpio_pin_path = GPIO_BASE_PATH / f"gpio{port}"

    if not gpio_pin_path.is_dir():
        Path(GPIO_BASE_PATH / "export").write_text(port)

    Path(gpio_pin_path / "direction").write_text(direction)
    Path(gpio_pin_path / "value").write_text(value)


def set_gpio(port, value):
    Path(GPIO_BASE_PATH / f"gpio{port}" / "value").write_text(value)
