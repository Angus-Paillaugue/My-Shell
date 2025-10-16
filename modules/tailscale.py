from fabric.core.fabricator import Fabricator
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label

import modules.icons as icons
from services.tailscale import TailscaleProvider


class Tailscale(Button):
    """Widget to manage tailscale status"""

    def __init__(self, **kwargs):
        super().__init__(
            name="tailscale-button",
            on_clicked=lambda b: self.on_click(),
        )
        self.status = "down"
        self.tailscale_icon = Label(name="tailscale-icon",
                                  markup=icons.tailscale)
        self.tailscale_name = Label(
            name="tailscale-status",
            label=self.status,
            h_align="start",
        )

        self.add(Box(
                spacing=12,
                children=[
                    self.tailscale_icon,
                    Box(
                        orientation="v",
                        h_align="start",
                        v_align="center",
                        children=[
                            Label(
                                label="Tailscale",
                                name="tailscale-button-label",
                                h_align="start",
                            ),
                            self.tailscale_name,
                        ],
                    ),
                ],
                orientation="h",
            ))
        self.provider = TailscaleProvider()
        self.tailscale_fabricator = Fabricator(
            poll_from=lambda v: self.provider.get_status(),
            on_changed=lambda f, v: self._update_ui,
            interval=1000,
            stream=False,
            default_value=0,
        )
        self.tailscale_fabricator.connect("changed", self._update_ui)
        self._update_ui(self, self.status)

    def _update_ui(self, sender, status: str) -> None:
        """Update the UI to reflect the current power profile."""
        self.status = status
        if self.status == "down":
            self.add_style_class("down")
            self.remove_style_class("up")
            self.tailscale_name.set_label("Disabled")
        else:
            self.remove_style_class("down")
            self.add_style_class("up")
            self.tailscale_name.set_label("Enabled")

    def on_click(self):
        self.status = self.provider.toggle()
