from gi.repository import Gtk
from fabric.widgets.wayland import WaylandWindow
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.box import Box
import os
from modules.time import Time
from modules.metrics import Metrics
from modules.tray import SystemTray
from modules.weather import WeatherButton
from modules.workspaces import Workspaces
from modules.language import Language
from modules.power import PowerButton


class Bar(WaylandWindow):

    def __init__(self, **kwargs):
        super().__init__(name="bar",
                         layer="overlay",
                         anchor="left top right",
                         exclusivity="auto",
                         visible=True,
                         all_visible=True,
                         **kwargs)

        self.workspaces = Workspaces()
        self.language = Language()
        self.metrics = Metrics()
        self.time = Time()
        self.system_tray = SystemTray()
        self.weather_button = (WeatherButton() if not os.environ.get("DEV_MODE")
                               else Box(visible=False))
        self.power_button = PowerButton()

        self.start_box = Box(
            name="bar-start-container",
            spacing=8,
            children=[
                self.workspaces,
                self.weather_button,
                self.metrics,
            ],
        )
        self.end_box = Box(
            name="bar-end-container",
            spacing=8,
            children=[
                self.system_tray, self.language, self.time, self.power_button
            ],
        )

        self.bar_inner = CenterBox(
            name="bar-inner",
            orientation=(Gtk.Orientation.HORIZONTAL),
            h_align="fill",
            v_align="fill",
            start_children=self.start_box,
            end_children=self.end_box,
        )

        self.children = self.bar_inner
