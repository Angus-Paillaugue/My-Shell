import os

from fabric.widgets.box import Box
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.revealer import Revealer
from fabric.widgets.wayland import WaylandWindow

from modules.language import Language
from modules.metrics import Metrics
from modules.power import PowerButton
from modules.tailscale import Tailscale
from modules.time import Time
from modules.tray import SystemTray
from fabric.widgets.eventbox import EventBox
from modules.weather import WeatherButton
from modules.workspaces import Workspaces
from services.config import config

class Bar(WaylandWindow):
    def __init__(self, **kwargs):
        anchors = {
            "top": "left top right",
            "bottom": "left bottom right",
            "left": "top left bottom",
            "right": "top right bottom",
        }
        contents = BarContents()
        self._revealer = Revealer(
            transition_duration=400,
            transition_type="slide-down",
            child_revealed=False,
            visible=True,
            all_visible=True,
            child=contents,
        )
        self._container =Box(
                name="bar-outer",
                orientation=("vertical" if config['BAR']['POSITION']
                             in ["top", "bottom"] else "horizontal"),
                children=[self._revealer, Box(name="bar-shadow")],
            )

        self._event_box = EventBox(
            name="bar-event-box",
            child=self._container,
            events=[
                "leave-notify",
                "enter-notify",
            ],
        )
        super().__init__(
            name="bar",
            layer="overlay",
            anchor=anchors[config['BAR']['POSITION']],
            exclusivity="none",
            visible=True,
            all_visible=True,
            child=self._event_box,
            **kwargs,
        )
        self._event_box.connect("enter-notify-event", self.on_mouse_enter)
        self._event_box.connect("leave-notify-event", self.on_mouse_leave)

    def on_mouse_enter(self, widget, event):
        print("Mouse entered bar area")
        self._revealer.child_revealed = True

    def on_mouse_leave(self, widget, event):
        print("Mouse left bar area")
        self._revealer.child_revealed = False


class BarContents(CenterBox):
    """The main bar widget that contains various components like workspaces, system tray, time, etc."""

    def __init__(self, **kwargs):
        orientation = ("horizontal" if config['BAR']['POSITION']
                       in ["top", "bottom"] else "vertical")

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
            style_classes=[config['BAR']['POSITION']],
            spacing=8,
            orientation=orientation,
        )
        self.end_box = Box(
            name="bar-end-container",
            style_classes=[config['BAR']['POSITION']],
            spacing=8,
            orientation=orientation,
        )

        # Adding the chosen modules to the bar based on the configuration
        if config['BAR']['MODULES']['WORKSPACES']:
            self.start_box.add(self.workspaces)
        if config['BAR']['MODULES']['WEATHER']['VISIBLE']:
            self.start_box.add(self.weather_button)
        if config['BAR']['MODULES']['PERFORMANCE']:
            self.start_box.add(self.metrics)

        if config['BAR']['MODULES']['TRAY']:
            self.end_box.add(self.system_tray)
        # if config['BAR']['MODULES']['TAILSCALE']:
        #     self.end_box.add(self.tailscale)
        if config['BAR']['MODULES']['KEYBOARD_LAYOUT']:
            self.end_box.add(self.language)
        if config['BAR']['MODULES']['TIME']:
            self.end_box.add(self.time)
        if config['BAR']['MODULES']['POWER']:
            self.end_box.add(self.power_button)

        super().__init__(
            name="bar-inner",
            orientation=orientation,
            h_align="fill",
            v_align="fill",
            start_children=self.start_box,
            end_children=self.end_box,
            **kwargs
        )
