import os

from fabric.utils import exec_shell_command_async
from fabric.widgets.button import Button
from fabric.widgets.label import Label

import modules.icons as icons


class ScreenshotButton(Button):

    def __init__(self):
        super().__init__(
            orientation="h",
            spacing=4,
            v_align="center",
            h_align="center",
            visible=True,
            style_classes=["settings-action-button"],
            child=Label(markup=icons.screenshot),
            tooltip_text="Screenshot",
            on_clicked=self._on_click,
        )
        self.output_path = os.path.expanduser("~/Pictures/screenshots")

    def _on_click(self, *_):
        exec_shell_command_async(f"hyprshot -m region -o {self.output_path}",
                                 lambda *_: None)
