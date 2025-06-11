from gi.repository import Gtk
from fabric.widgets.wayland import WaylandWindow
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.box import Box
import os
from modules.time import Time
from modules.settings import Settings
from modules.metrics import Metrics
from modules.tray import SystemTray
from modules.weather import WeatherButton
from modules.corners import CornerContainer
from modules.workspaces import Workspaces
from modules.language import Language
from modules.notification import NotificationHistoryIndicator, NotificationHistory
from fabric.notifications.service import Notifications


class Bar(WaylandWindow):

    def __init__(self, notification_server: Notifications,
                 notification_history: NotificationHistory, **kwargs):
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
        self.settings = Settings()
        self.notification_server = notification_server
        self.notification_history_indicator = NotificationHistoryIndicator(
            notification_history=notification_history,)
        self.weather_button = (WeatherButton() if not os.environ.get("DEV_MODE")
                               else Box(visible=False))

        self.start_box = Box(
            name="bar-start-container",
            children=Box(
                name="bar-start-container-inner",
                children=[
                    self.workspaces,
                    self.weather_button,
                    self.metrics,
                ],
            ),
        )
        self.center_box = CornerContainer(
            name="bar-center-container",
            corners=["left", "right"],
            height=30,
            spacing=8,
            v_align="center",
            children=[
                self.notification_history_indicator,
                self.time,
            ],
        )
        self.end_box = Box(
            name="bar-end-container",
            children=Box(
                name="bar-end-container-inner",
                children=[
                    self.system_tray,
                    self.language,
                    self.settings,
                ],
            ),
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
