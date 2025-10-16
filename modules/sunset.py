import subprocess

from fabric.utils.helpers import exec_shell_command_async
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from gi.repository import GLib  # type: ignore

import modules.icons as icons
from services.config import config


class Sunset(Button):
    """Widget to manage hyrsunset"""

    def __init__(self):
        super().__init__(
            name="sunset-button",
            on_clicked=self.toggle_hyprsunset,
        )
        self.enabled = False
        self.sunset_icon = Label(name="sunset-icon",
                                  markup=icons.night)
        self.sunset_name = Label(
            name="sunset-status",
            label="",
            h_align="start",
        )

        self.add(Box(
                spacing=12,
                children=[
                    self.sunset_icon,
                    Box(
                        orientation="v",
                        h_align="start",
                        v_align="center",
                        children=[
                            Label(
                                label="Nigh Mode",
                                name="sunset-button-label",
                                h_align="start",
                            ),
                            self.sunset_name,
                        ],
                    ),
                ],
                orientation="h",
            ))
        self.check_hyprsunset()

    def toggle_hyprsunset(self, *args):
        """
        Toggle the 'hyprsunset' process:
          - If running, kill it and mark as 'Disabled'.
          - If not running, start it and mark as 'Enabled'.
        """
        GLib.Thread.new("hyprsunset-toggle", self._toggle_hyprsunset_thread, None)

    def _toggle_hyprsunset_thread(self, user_data):
        """Background thread to check and toggle hyprsunset without blocking UI."""
        try:
            subprocess.check_output(["pgrep", "hyprsunset"])
            exec_shell_command_async("pkill hyprsunset")
            self.enabled = False
        except subprocess.CalledProcessError:
            exec_shell_command_async(f"hyprsunset -t {config['NOTCH']['MODULES']['SUNSET']['TEMPERATURE']} -g {config['NOTCH']['MODULES']['SUNSET']['GAMMA']}")
            self.enabled = True
        GLib.idle_add(self._set_status)

    def _set_status(self):
        if self.enabled:
            self.add_style_class("up")
            self.remove_style_class("down")
            self.sunset_name.set_label("Enabled")
        else:
            self.add_style_class("down")
            self.remove_style_class("up")
            self.sunset_name.set_label("Disabled")

    def check_hyprsunset(self, *args):
        """
        Update the button state based on whether hyprsunset is running.
        """
        GLib.Thread.new("hyprsunset-check", self._check_hyprsunset_thread, None)

    def _check_hyprsunset_thread(self, user_data):
        """Background thread to check hyprsunset status without blocking UI."""
        try:
            subprocess.check_output(["pgrep", "hyprsunset"])
            self.enabled = True
        except subprocess.CalledProcessError:
            self.enabled = False
        GLib.idle_add(self._set_status)
