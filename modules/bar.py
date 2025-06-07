from gi.repository import Gtk
from fabric.widgets.wayland import WaylandWindow
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.label import Label
from fabric.widgets.box import Box
from fabric.hyprland.service import HyprlandEvent
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
import modules.icons as icons


class Bar(WaylandWindow):

    def __init__(self, **kwargs):
        super().__init__(name="bar",
                         layer="top",
                         anchor="left top right",
                         exclusivity="auto",
                         visible=True,
                         margin="4px 4px 0px 4px",
                         all_visible=True,
                         **kwargs)
        self.connection = get_hyprland_connection()

        self.workspaces = Workspaces(
            name="workspaces",
            invert_scroll=True,
            empty_scroll=True,
            v_align="fill",
            orientation="h",
            style_classes=["bar-item"],
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
            style_classes=["bar-item"],
            h_align="center",
            v_align="center",
            child=Box(children=[self.lang_icon, self.lang_label], spacing=4),
        )
        self.on_language_switch()
        self.connection.connect("event::activelayout", self.on_language_switch)

        self.start_children = [Time(), Metrics()]
        self.center_children = [self.workspaces]
        self.end_children = [
            SystemTray(),
            self.language,
            Settings(),
        ]

        self.bar_inner = CenterBox(
            name="bar-inner",
            orientation=(Gtk.Orientation.HORIZONTAL),
            h_align="fill",
            v_align="fill",
            start_children=(Box(
                name="start-container",
                spacing=8,
                orientation=(Gtk.Orientation.HORIZONTAL),
                children=self.start_children,
            )),
            center_children=Box(
                name="center-container",
                spacing=8,
                orientation=(Gtk.Orientation.HORIZONTAL),
                children=self.center_children,
            ),
            end_children=(Box(
                name="end-container",
                spacing=8,
                orientation=(Gtk.Orientation.HORIZONTAL),
                children=self.end_children,
            )),
        )

        self.children = self.bar_inner

    def on_language_switch(self, _=None, event: HyprlandEvent = None):
        """Update the language widget based on the active layout."""
        lang_data = (event.data[1] if event and event.data
                     and len(event.data) > 1 else Language().get_label())
        self.language.set_tooltip_text(lang_data)
        self.lang_label.set_label(lang_data[:2].upper())

    def open_launcher(self):
        self.launcher.open_launcher()
