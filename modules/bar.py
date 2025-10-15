import os

from fabric.widgets.box import Box
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.wayland import WaylandWindow

from modules.language import Language
from modules.metrics import Metrics
from modules.power import PowerButton
from modules.tailscale import Tailscale
from modules.time import Time
from modules.tray import SystemTray
from modules.weather import WeatherButton
from modules.workspaces import Workspaces
from services.config import config


class Bar(WaylandWindow):
    """The main bar widget that contains various components like workspaces, system tray, time, etc."""

    def __init__(self, **kwargs):
        anchors = {
            "top": "left top right",
            "bottom": "left bottom right",
            "left": "top left bottom",
            "right": "top right bottom",
        }
        orientation = ("horizontal" if config['POSITIONS']['BAR']
                       in ["top", "bottom"] else "vertical")
        super().__init__(
            name="bar",
            layer="top",
            anchor=anchors[config['POSITIONS']['BAR']],
            exclusivity="auto",
            visible=True,
            all_visible=True,
            **kwargs,
        )

        self.workspaces = Workspaces()
        self.language = Language()
        self.metrics = Metrics()
        self.time = Time()
        self.system_tray = SystemTray()
        self.tailscale = Tailscale()
        self.weather_button = (WeatherButton() if not os.environ.get("DEV_MODE")
                               else Box(visible=False))
        self.power_button = PowerButton()

        self.start_box = Box(
            name="bar-start-container",
            style_classes=[config['POSITIONS']['BAR']],
            spacing=8,
            orientation=orientation,
            children=[
                self.workspaces,
                self.weather_button,
                self.metrics,
            ],
        )
        self.end_box = Box(
            name="bar-end-container",
            style_classes=[config['POSITIONS']['BAR']],
            spacing=8,
            orientation=orientation,
            children=[
                self.system_tray, self.tailscale, self.language, self.time,
                self.power_button
            ],
        )

        self.bar_inner = CenterBox(
            name="bar-inner",
            orientation=orientation,
            h_align="fill",
            v_align="fill",
            start_children=self.start_box,
            end_children=self.end_box,
        )

        self.children = self.bar_inner
