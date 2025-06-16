from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.utils import exec_shell_command_async
import modules.icons as icons
from gi.repository import Gtk
from services.config import config

class PowerButton(Button):

    def __init__(self, **kwargs):
        super().__init__(
            name="power-button",
            style_classes=[
                "bar-item",
                (
                    "horizontal"
                    if config.BAR_POSITION in ["top", "bottom"]
                    else "vertical"
                ),
            ],
            child=Label(markup=icons.shutdown),
            on_clicked=lambda *args: self.on_clicked(*args),
            **kwargs,
        )

    def on_clicked(self, button):
        exec_shell_command_async(
            "fabric-cli exec my-shell 'notch.show_widget(\"power\", False)'")


class PowerMenuActions(Gtk.Grid):

    def __init__(self, **kwargs):
        super().__init__(
            name="power-options-container",
            column_homogeneous=True,
            row_homogeneous=False,
            column_spacing=8,
            row_spacing=8,
            visible=True,
            **kwargs,
        )

        self.actions = [
            {
                "label": "Logout",
                "icon": icons.logout,
                "command": "hyprctl dispatch exit",
            },
            {
                "label": "Reboot",
                "icon": icons.reboot,
                "command": "systemctl reboot"
            },
            {
                "label": "Shutdown",
                "icon": icons.shutdown,
                "command": "systemctl poweroff",
            },
        ]

        for i, action in enumerate(self.actions):
            button = Button(
                name="power-option-button",
                child=Box(
                    orientation="v",
                    spacing=8,
                    h_align="center",
                    v_align="center",
                    children=[
                        Label(name="option-icon", markup=action["icon"]),
                        Label(name="option-label", label=action["label"]),
                    ],
                ),
                on_clicked=lambda b, a=action: exec_shell_command_async(a[
                    'command'])(a),
            )
            self.attach(button, i, 0, 1, 1)
