import os

from fabric import Property, Service, Signal
from fabric.utils import exec_shell_command_async, monitor_file
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.scale import Scale
from gi.repository import GLib

import modules.icons as icons
from modules.settings import SettingsBroker
from services.logger import logger

# Discover screen backlight device
try:
    screen_device = os.listdir("/sys/class/backlight")
    screen_device = screen_device[0] if screen_device else ""
except FileNotFoundError:
    screen_device = ""


class Brightness(Service):
    """Service to manage screen brightness levels."""

    instance = None

    @staticmethod
    def get_initial():
        if Brightness.instance is None:
            Brightness.instance = Brightness()

        return Brightness.instance

    @Signal
    def screen(self, value: int) -> None:
        """Signal emitted when screen brightness changes."""
        # Implement as needed for your application

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Path for screen backlight control
        self.screen_backlight_path = f"/sys/class/backlight/{screen_device}"

        # Initialize maximum brightness level
        self.max_screen = self.do_read_max_brightness(
            self.screen_backlight_path)

        if screen_device == "":
            return

        # Monitor screen brightness file
        self.screen_monitor = monitor_file(
            f"{self.screen_backlight_path}/brightness")

        self.screen_monitor.connect(
            "changed",
            lambda _, file, *args: self.emit(
                "screen",
                round(int(file.load_bytes()[0].get_data())),
            ),
        )

    def do_read_max_brightness(self, path: str) -> int:
        # Reads the maximum brightness value from the specified path.
        max_brightness_path = os.path.join(path, "max_brightness")
        if os.path.exists(max_brightness_path):
            with open(max_brightness_path) as f:
                return int(f.readline())
        return -1  # Return -1 if file doesn't exist, indicating an error.

    @Property(int, "read-write")
    def screen_brightness(self) -> int:
        # Property to get or set the screen brightness.
        brightness_path = os.path.join(self.screen_backlight_path, "brightness")
        if os.path.exists(brightness_path):
            with open(brightness_path) as f:
                return int(f.readline())
        return -1  # Return -1 if file doesn't exist, indicating error.

    @screen_brightness.setter
    def screen_brightness(self, value: int):
        # Setter for screen brightness property.
        if not (0 <= value <= self.max_screen):
            value = max(0, min(value, self.max_screen))

        try:
            exec_shell_command_async(
                f"brightnessctl --device '{screen_device}' set {value}",
                lambda _: None)
            self.emit("screen", int((value / self.max_screen) * 100))
        except GLib.Error as e:
            logger.error(f"Error setting screen brightness: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected error setting screen brightness: {e}")


class BrightnessSlider(Scale):

    def __init__(self, client, **kwargs):
        super().__init__(
            name="control-slider",
            orientation="h",
            h_expand=True,
            has_origin=True,
            increments=(5, 10),
            **kwargs,
        )

        self.client = client

        self.set_range(0, self.client.max_screen)
        self.set_value(self.client.screen_brightness)
        self.add_style_class("brightness")

        self._pending_value = None
        self._update_source_id = None
        self.settings_notifier = SettingsBroker()

        self.connect("change-value", self.on_scale_move)
        self.client.connect("screen", self.on_brightness_changed)

    def on_brightness_changed(self, client, _):
        self.settings_notifier.notify_listeners(
            "brightness-changed",
            round(
                (self.client.screen_brightness / self.client.max_screen) * 100))
        self.set_value(self.client.screen_brightness)

    def on_scale_move(self, widget, scroll, moved_pos):
        self._pending_value = moved_pos
        if self._update_source_id is None:
            self._update_source_id = GLib.idle_add(
                self._update_brightness_callback)
        return False

    def _update_brightness_callback(self):
        if self._pending_value is not None:
            value_to_set = self._pending_value
            self._pending_value = None
            if value_to_set != self.client.screen_brightness:
                self.client.screen_brightness = value_to_set
            return True
        else:
            self._update_source_id = None
            return False


class BrightnessRow(Box):

    def __init__(self, **kwargs):
        super().__init__(
            name="brightness-row",
            orientation="h",
            spacing=12,
            **kwargs,
        )

        self.client = Brightness.get_initial()
        if self.client.screen_brightness == -1:
            self.destroy()
            return

        self._pending_value = None
        self._update_source_id = None

        self.client.connect("screen", self.set_icon)

        self.brightness_icons = [icons.brightness_low, icons.brightness_high]

        self.brightness_icon = Label(name="brightness-icon",
                                     markup=self.brightness_icons[0])
        self.add(self.brightness_icon)

        self.brightness_slider = BrightnessSlider(client=self.client)
        self.add(self.brightness_slider)

        self.set_icon()

    def set_icon(self, *args):
        current = int(
            (self.client.screen_brightness / self.client.max_screen) * 100)
        num_icons = len(self.brightness_icons)
        range_per_icon = 100 // num_icons

        icon_index = min(current // range_per_icon, num_icons - 1)
        icon = self.brightness_icons[icon_index]

        self.brightness_icon.set_markup(icon)

    def destroy(self):
        if self._update_source_id is not None:
            GLib.source_remove(self._update_source_id)
        super().destroy()
