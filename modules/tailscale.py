from fabric import Fabricator
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from gi.repository import GLib  # type: ignore

import modules.icons as icons
from services.config import config
from services.tailscale import TailscaleProvider


class Tailscale(Button):
    """Widget that is used to manage tailscale VPN status."""

    def __init__(self, **kwargs):
        super().__init__(
            name="tailscale",
            style_classes=[
                "bar-item",
                ("horizontal" if config['POSITIONS']['BAR']
                 in ["top", "bottom"] else "vertical")
            ],
            h_align="center",
            v_align="center",
            spacing=4,
            v_expand=True,
            h_expand=True,
            on_clicked=lambda *_: self.on_click(),
            **kwargs,
        )
        self.status = "down"
        self.lang_icon = Label(markup=icons.tailscale, name="tailscale-icon")
        self.add(self.lang_icon)
        self.provider = TailscaleProvider()
        self.metrics_fabricator = Fabricator(
            poll_from=lambda v: self.provider.get_status(),
            on_changed=lambda f, v: self.set_status,
            interval=1000,
            stream=False,
            default_value=0,
        )
        self.metrics_fabricator.connect("changed", self.set_status)
        GLib.idle_add(self.set_status, None, self.provider.get_status())

    def set_status(self, sender, status: str):
        """Set the icon color based on the VPN status."""
        self.status = status
        if self.status == "down":
            self.lang_icon.add_style_class("down")
        else:
            self.lang_icon.remove_style_class("down")

    def on_click(self):
        self.status = self.provider.toggle()
        self.set_status(None, self.status)
