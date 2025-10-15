from fabric.utils import exec_shell_command_async
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from gi.repository import Gtk  # type: ignore

import modules.icons as icons
from services.config import config


class PowerButton(Button):
    """Button to trigger the power menu in the bar."""

    def __init__(self, **kwargs):
        super().__init__(
            name="power-button",
            style_classes=[
                "bar-item",
                (
                    "horizontal"
                    if config['POSITIONS']['BAR'] in ["top", "bottom"]
                    else "vertical"
                ),
            ],
            child=Label(markup=icons.shutdown),
            on_clicked=lambda *args: self.on_clicked(*args),
            **kwargs,
        )

    def on_clicked(self, *args: object) -> None:
        """Handle the button click to show or hide the power menu."""
        exec_shell_command_async(
            f"fabric-cli exec {config['APP_NAME']} 'notch.show_widget(\"power\", False)'"
        )


class PowerMenuActions(Gtk.Grid):
    """Grid to display power options like logout, reboot, and shutdown."""

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
                    'command']),
            )
            self.attach(button, i, 0, 1, 1)
