import os
import threading
import time

from fabric.utils.helpers import exec_shell_command_async
from fabric.widgets.button import Button
from fabric.widgets.label import Label

import modules.icons as icons
from services.config import config
from services.logger import logger
from typing import Callable

class ColorPickerButton(Button):
    """Button that triggers a color picker script when clicked."""

    def __init__(self, hide_notch: Callable, **kwargs):
        super().__init__(
            orientation="h",
            spacing=4,
            v_align="center",
            h_align="center",
            visible=True,
            style_classes=["settings-action-button"],
            child=Label(markup=icons.color_picker),
            tooltip_text="Color Picker",
            on_clicked=self._on_click,
        )
        self.hide_notch = hide_notch
        self.script_thread_active = False
        self.path = os.path.expanduser(
            f"~/.config/{config.APP_NAME}/services/color-picker.sh")

    def _on_click(self, *_) -> None:
        if self.script_thread_active:
            logger.warning("Color picker update already in progress.")
            return

        if not os.path.exists(self.path):
            logger.error(f"Script not found: {self.path}")
            return

        self.hide_notch()

        def worker():
            self.script_thread_active = True
            time.sleep(0.5)  # Allow the notch to hide before running the script
            exec_shell_command_async(f"bash {self.path}")
            self.script_thread_active = False

        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
