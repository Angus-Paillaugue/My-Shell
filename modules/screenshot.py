import os
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.utils import exec_shell_command_async
import modules.icons as icons


class ScreenshotButton(Button):
    def __init__(self, close_settings=None):
        super().__init__(
            name="screenshot-button",
            orientation="h",
            spacing=4,
            v_align="center",
            h_align="center",
            visible=True,
            child=Label(markup=icons.screenshot),
            tooltip_text="Screenshot",
            on_clicked=lambda *_: self._on_click(),
        )
        self.close_settings = close_settings
        self.output_path = os.path.expanduser("~/Pictures/screenshots")

    def _on_click(self):
        # self.close_settings()
        exec_shell_command_async(
            f"hyprshot -m region -o {self.output_path}", lambda *_: None
        )
