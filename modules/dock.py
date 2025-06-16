import subprocess
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.image import Image
from fabric.widgets.revealer import Revealer
import os
from gi.repository import GLib
import json
from services.config import config
from modules.corners import CornerContainer
from fabric.widgets.eventbox import EventBox
from fabric.utils import DesktopApp, get_desktop_applications, monitor_file

pinned_aps_location = os.path.expanduser(
    f"~/.config/{config.APP_NAME}/config/pinned_apps.json"
)


class Dock(Window):
    """
    Dock is a Wayland window that can be used to create a dock-like interface.
    """

    def __init__(self, *args, **kwargs):
        anchor = {
            "top": "top center",
            "bottom": "bottom center",
            "left": "left center",
            "right": "right center",
        }[config.DOCK_POSITION]
        margin = f"{"-54px" if config.DOCK_POSITION == "top" else 0} 0 0 0"
        super().__init__(
            name="dock-overlay",
            layer="overlay",
            anchor=anchor,
            exclusivity="none",
            h_align="end",
            visible=True,
            margin=margin,
            all_visible=True,
        )

        self.hide_timer = None
        self.hover_counter = 0
        self.is_animating = False
        self.animation_timeout = None
        self.hover_counter = 0

        self.pinned_apps = self._load_apps()
        orientation = (
            "horizontal" if config.DOCK_POSITION in ["top", "bottom"] else "vertical"
        )
        self.items_container = Box(
            name="dock-items-container",
            style_classes=[config.DOCK_POSITION],
            orientation=orientation,
            spacing=8,
        )
        self.dock_container = CornerContainer(
            name="dock-container",
            position=config.DOCK_POSITION,
            orientation=orientation,
            height=45,
            corners=(True, True),
            children=[self.items_container],
        )
        transition_type = "slide-up"
        if config.DOCK_POSITION == "left":
            transition_type = "slide-right"
        elif config.DOCK_POSITION == "bottom":
            transition_type = "slide-down"
        elif config.DOCK_POSITION == "right":
            transition_type = "slide-left"
        self.revealer = Revealer(
            transition_type=transition_type,
            transition_duration=250,
            name="dock-revealer",
            visible=True,
            all_visible=True,
            child_revealed=False,
            child=self.dock_container,
        )
        self.mouse_area = EventBox(
            child=Box(
                name="dock-mouse-area",
                style_classes=[config.DOCK_POSITION],
                children=[self.revealer],
            ),
            events=["leave-notify", "enter-notify"],
        )
        self._add_applications()
        self.add(self.mouse_area)
        self.pinned_applications_monitor = monitor_file(pinned_aps_location)
        self.pinned_applications_monitor.connect(
            "changed", self._on_pinned_apps_file_changed)
        self.mouse_area.connect("enter-notify-event", self._on_mouse_enter)
        self.mouse_area.connect("leave-notify-event", self._on_mouse_leave)
        GLib.timeout_add(1000, self.check_running_apps)

    def _on_mouse_enter(self, widget, event):
        # Cancel any pending hide operations
        if self.hide_timer is not None:
            GLib.source_remove(self.hide_timer)
            self.hide_timer = None

        if len(self.items_container.children) > 0:
            self._show_dock()
        return True  # Important: consume the event

    def _show_dock(self):
        if not self.is_animating and not self.revealer.get_reveal_child():
            self.is_animating = True
            self.revealer.set_reveal_child(True)
            self.animation_timeout = GLib.timeout_add(250, self._animation_done)

    def _animation_done(self):
        # Animation is complete, reset flag
        self.is_animating = False
        self.animation_timeout = None
        return False  # Remove the source

    def _hide_dock(self):
        if not self.is_animating and self.revealer.get_reveal_child():
            self.is_animating = True
            self.revealer.set_reveal_child(False)
            self.animation_timeout = GLib.timeout_add(250, self._animation_done)
        self.hide_timer = None
        return False  # Remove the source

    def _on_mouse_leave(self, widget, event):
        # Don't start hide timer if still animating
        if self.is_animating:
            return False

        # Start hiding after a delay
        if self.hide_timer is not None:
            GLib.source_remove(self.hide_timer)

        # Use a longer delay to prevent accidental hiding
        self.hide_timer = GLib.timeout_add(500, self._hide_dock)
        return True

    def check_running_apps(self):
        """
        Check if pinned applications are running and update their state.
        This method can be overridden to implement custom logic.
        """
        for i, app in enumerate(self.pinned_apps):
            system_app = next(
                (a for a in get_desktop_applications() if a.name == app), None)
            if not system_app:
                continue
            if self._is_app_running(system_app):
                self.items_container.children[i].add_style_class("running")
            else:
                self.items_container.children[i].remove_style_class("running")

        return True

    def _is_app_running(self, app: DesktopApp) -> bool:
        """
        Check if the application is currently running.
        This method can be overridden to implement custom logic.
        """
        process_name = app.window_class.lower(
        ) if app.window_class else app.executable or app.name.lower()
        res = subprocess.run(["pidof", "-s", process_name], capture_output=True)
        return res.returncode == 0

    def _add_application(self, app: DesktopApp):
        icon = Image(
            pixbuf=app.get_icon_pixbuf(size=30),
            h_align="center",
            v_align="center",
        )
        button = Button(
            child=icon,
            h_align="center",
            v_align="center",
            style_classes=["dock-item"],
            tooltip_text=app.name,
            on_clicked=lambda *_: app.launch(),
        )
        self.items_container.add(button)

    def _load_apps(self):
        """
        Load applications from the pinned apps file.
        This method can be overridden to load custom applications.
        """
        if not os.path.exists(pinned_aps_location):
            with open(pinned_aps_location, "w") as f:
                f.write("[]")
        with open(pinned_aps_location, "r") as f:
            pinned_apps = json.load(f)  # TODO: handle malformed JSON data
        return pinned_apps

    def _on_pinned_apps_file_changed(self, *_):
        self.pinned_apps = self._load_apps()
        self._add_applications()

    def _add_applications(self, *_):
        """
        Add items to the dock container.
        This method can be overridden to add custom items to the dock.
        """
        self.items_container.children = []  # Clear existing items
        all_system_apps = get_desktop_applications()
        for app in self.pinned_apps:
            system_app = next((a for a in all_system_apps if a.name == app),
                              None)
            if system_app:
                self._add_application(system_app)
