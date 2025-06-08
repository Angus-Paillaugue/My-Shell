from gi.repository import Gtk
from fabric.widgets.wayland import WaylandWindow
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.label import Label
from fabric.widgets.box import Box
from fabric.hyprland.service import HyprlandEvent
import os
from fabric.hyprland.widgets import (
    Language,
    WorkspaceButton,
    Workspaces,
    get_hyprland_connection,
)
from modules.time import Time
from modules.settings import Settings
from modules.metrics import Metrics
from modules.tray import SystemTray
from modules.weather import WeatherButton
from modules.corners import CornerContainer
import modules.icons as icons


class Bar(WaylandWindow):

    def __init__(self, **kwargs):
        super().__init__(name="bar",
                         layer="top",
                         anchor="left top right",
                         exclusivity="auto",
                         visible=True,
                         all_visible=True,
                         **kwargs)
        self.connection = get_hyprland_connection()

        self.workspaces = Workspaces(
            name="workspaces",
            invert_scroll=True,
            empty_scroll=True,
            v_align="fill",
            orientation="h",
            spacing=8,
            buttons=[
                WorkspaceButton(
                    h_expand=False,
                    v_expand=False,
                    h_align="center",
                    v_align="center",
                    id=i,
                ) for i in range(1, 5)
            ],
        )

        self.lang_label = Label(name="lang-label",)
        self.lang_icon = Label(markup=icons.keyboard, name="keyboard-lang-icon")
        self.language = Button(
            name="language",
            h_align="center",
            v_align="center",
            child=Box(children=[self.lang_icon, self.lang_label], spacing=4),
        )
        self.on_language_switch()
        self.connection.connect("event::activelayout", self.on_language_switch)

        self.start_box = CornerContainer(
            name="bar-start-container",
            corners=["right"],
            children=[
                Time(),
                (WeatherButton() if not os.environ.get("DEV_MODE") else Box(
                    visible=False)),
                Metrics(),
            ],
        )
        self.center_box = CornerContainer(
            name="bar-center-container",
            corners=["left", "right"],
            children=[self.workspaces],
        )
        self.end_box = CornerContainer(
            name="bar-end-container",
            corners=["left"],
            children=[
                SystemTray(),
                self.language,
                Settings(),
            ],
        )

        self.bar_inner = CenterBox(
            name="bar-inner",
            orientation=(Gtk.Orientation.HORIZONTAL),
            h_align="fill",
            v_align="fill",
            start_children=self.start_box,
            center_children=self.center_box,
            end_children=self.end_box,
        )

        self.children = self.bar_inner

    def on_language_switch(self, _=None, event: HyprlandEvent = None):
        """Update the language widget based on the active layout."""
        lang_data = (event.data[1] if event and event.data and
                     len(event.data) > 1 else Language().get_label())
        self.language.set_tooltip_text(lang_data)
        self.lang_label.set_label(lang_data[:2].upper())
