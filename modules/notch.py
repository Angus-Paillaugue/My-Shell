import json
import subprocess
from typing import Callable

from fabric.hyprland.service import HyprlandEvent
from fabric.hyprland.widgets import get_hyprland_connection
from fabric.utils import DesktopApp
from fabric.utils.helpers import get_desktop_applications
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.eventbox import EventBox
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.revealer import Revealer
from fabric.widgets.stack import Stack
from fabric.widgets.wayland import WaylandWindow
from gi.repository import Gdk, GLib, Gtk # type: ignore

from modules.battery import Battery
from modules.bluetooth import BluetoothButton
from modules.brightness import BrightnessRow
from modules.clipboard import ClipboardManager
from modules.color_picker import ColorPickerButton
from modules.corners import CornerContainer
from modules.dock import DockSettings
from modules.launcher import AppLauncher
from modules.notification import (NotificationHistory,
                                  NotificationHistoryIndicator)
from modules.power import PowerMenuActions
from modules.power_profile import PowerProfile
from modules.screen_record import ScreenRecordButton
from modules.screenshot import ScreenshotButton
from modules.time import CalendarBox as Calendar
from modules.volume import MicRow, VolumeRow
from modules.wallpaper import WallpaperManager
from modules.wifi import WifiModule
from modules.wired import Wired
from services.config import config
from services.logger import logger


class NotchWidgetPicker(Revealer):
    """Buttons at the top of the notch used to switch tab (launcher, networking, wallpaper, etc.)"""

    def __init__(self, notch):
        super().__init__(
            transition_duration=400,
            transition_type="slide-right",
            child_revealed=False,
            visible=True,
            all_visible=True,
        )
        self.revealer_2 = Revealer(
            transition_duration=400,
            transition_type="slide-down",
            child_revealed=False,
            visible=True,
            all_visible=True,
        )
        self.notch = notch
        self.grid = Gtk.Grid(
            column_homogeneous=True,
            row_homogeneous=False,
            column_spacing=8,
            row_spacing=8,
            visible=True,
            name="notch-widget-picker-grid",
        )
        self.actions = [
            {
                "label": "Home",
                "on_click": lambda *_: notch.show_widget("default-expanded"),
                "name": "notch-widget-button-default",
            },
            {
                "label": "Launcher",
                "on_click": lambda *_: notch.show_widget("launcher"),
                "name": "notch-widget-button-launcher",
            },
            {
                "label": "Wallpaper",
                "on_click": lambda *_: notch.show_widget("wallpaper"),
                "name": "notch-widget-button-wallpaper",
            },
        ]
        self.buttons = []
        for i, a in enumerate(self.actions):
            button = Button(
                name=a["name"],
                style_classes=["notch-widget-selector-button"],
                label=a["label"],
            )
            button.connect("clicked", a["on_click"])
            self.buttons.append(button)
            self.grid.attach(button, i, 0, 1, 1)
        self.revealer_2.add(self.grid)
        self.set_active_index(0)
        self.add(self.revealer_2)

    def show(self) -> None:
        """Show the widget picker and reveal the buttons"""
        self.revealer_2.set_reveal_child(True)
        self.set_reveal_child(True)

    def hide(self) -> None:
        """Hide the widget picker and collapse the buttons"""
        self.revealer_2.set_reveal_child(False)
        self.set_reveal_child(False)
        if hasattr(self.notch.inner._contents.get_visible_child(), "cleanup"):
            # If the visible child has a collapse_slots method, call it
            self.notch.inner._contents.get_visible_child().cleanup()
        self.notch.inner.show_widget("default")

    def set_active_index(self, index: int) -> None:
        """Set the active button based on the index and highlight it"""
        if 0 <= index < len(self.buttons):
            for i, button in enumerate(self.buttons):
                if i == index:
                    button.add_style_class("active")
                else:
                    button.remove_style_class("active")
        else:
            logger.warning(
                f"Index {index} is out of range for NotchWidgetPicker buttons.")


class NotchWidgetDefaultExpanded(Box):
    """Default widget when hovering the notch, showing various modules like wifi, bluetooth, volume, etc."""

    def __init__(self, notification_history: NotificationHistory, show_widget: Callable):
        super().__init__(
            orientation="v",
            spacing=8,
            v_align="start",
            h_align="center",
        )
        self.brightness_module = BrightnessRow()
        self.battery = Battery()
        self.power_profile = PowerProfile()
        self.bluetooth_devices_dropdown_slot = Box()
        self.wifi_networks_dropdown_slot = Box()
        self.audio_outputs_dropdown_slot = Box()
        self.mic_inputs_dropdown_slot = Box()
        self.wired_networks_dropdown_slot = Box()
        self.mic_module = MicRow(slot=self.mic_inputs_dropdown_slot)
        self.volume_module = VolumeRow(slot=self.audio_outputs_dropdown_slot)
        self.bluetooth = BluetoothButton(
            slot=self.bluetooth_devices_dropdown_slot)
        self.wifi_module = WifiModule(slot=self.wifi_networks_dropdown_slot)
        self.network_module = Wired(slot=self.wired_networks_dropdown_slot)
        self.screenshot_button = ScreenshotButton()
        self.screen_record_button = ScreenRecordButton()
        self.color_picker_button = ColorPickerButton(hide_notch=lambda: show_widget("default"))

        self.buttons_grid = Gtk.Grid(
            column_homogeneous=True,
            row_homogeneous=False,
            name="setting-buttons-grid",
            column_spacing=12,
            row_spacing=12,
            visible=True,
        )

        self.buttons_grid.attach(self.wifi_module, 0, 0, 1, 1)
        self.buttons_grid.attach(self.network_module, 1, 0, 1, 1)
        self.buttons_grid.attach(self.bluetooth, 2, 0, 1, 1)
        self.buttons_grid.attach(self.power_profile, 3, 0, 1, 1)
        self.sliders_grid = Gtk.Grid(
            column_homogeneous=True,
            row_homogeneous=False,
            name="setting-sliders-grid",
            column_spacing=12,
            visible=True,
        )
        self.sliders_grid.attach(self.brightness_module, 0, 0, 2, 1)
        self.sliders_grid.attach(self.volume_module, 0, 1, 1, 1)
        self.sliders_grid.attach(self.mic_module, 1, 1, 1, 1)
        self.sliders_grid.attach(self.mic_inputs_dropdown_slot, 0, 3, 2, 1)
        self.sliders_grid.attach(self.audio_outputs_dropdown_slot, 0, 2, 2, 1)

        self.end_children = Box(
            children=[
                self.color_picker_button,
                self.screen_record_button,
                self.screenshot_button,
            ],
            v_align="center",
            h_align="center",
            spacing=12,
        )

        self.items = [
            CenterBox(
                start_children=[self.battery],
                end_children=self.end_children,
                orientation="h",
            ),
            self.buttons_grid,
            self.wifi_networks_dropdown_slot,
            self.wired_networks_dropdown_slot,
            self.bluetooth_devices_dropdown_slot,
            self.sliders_grid,
        ]

        # Add the container to our window
        self.settings_container = Box(
            name="settings-container",
            orientation="v",
        )
        for item in self.items:
            self.settings_container.add(item)
        self.add(self.settings_container)

        self.second_row = Box(spacing=8,)
        self.notification_history = notification_history
        self.calendar = Calendar()
        self.second_row.add(self.calendar)
        self.second_row.add(self.notification_history)
        self.add(self.second_row)
        self.set_valign(Gtk.Align.START)
        self.set_halign(Gtk.Align.CENTER)

    def cleanup(self) -> None:
        """Collapse all of the Revealer used by modules"""
        self.network_module.wired_networks_dropdown.collapse()
        self.wifi_module.wifi_networks_dropdown.collapse()
        self.bluetooth.bluetooth_devices_dropdown.collapse()
        self.volume_module.outputs_box.collapse()
        self.mic_module.inputs_box.collapse()


class NotchWidgetDefault(Box):
    """Default widget for the notch (when not hovering the notch, this will be displayed), showing the current active window and its icon"""

    def __init__(self):
        super().__init__(
            orientation="h",
            spacing=8,
            v_align="center",
            h_align="center",
            name="notch-widget-default",
        )
        self.update_app_map()
        self.desktop_string = "Desktop"
        self.set_desktop_string()

        self.active_window = Label(
            label=self.desktop_string,
            v_align="center",
            h_align="center",
            h_expand=True,
            v_expand=True,
        )
        self.active_window_box = Box(
            orientation="h",
            v_align="center",
            h_align="center",
            h_expand=True,
            v_expand=True,
            children=[self.active_window],
            name="notch-active-window-box",
        )
        self.window_icon = Image(
            name="notch-window-icon",
            icon_name="application-x-executable",
            v_align="center",
            h_align="center",
            icon_size=20,
        )
        self.icon_revealer = Revealer(
            child_revealed=False,
            transition_duration=200,
            transition_type="slide-right",
            visible=True,
            all_visible=True,
            child=self.window_icon,
        )
        self.add(self.icon_revealer)
        self.add(self.active_window_box)
        self.conn = get_hyprland_connection()
        self._current_window_class = self._get_current_window_class()
        self.conn.connect("event::activewindow", self.on_active_window_changed)

    def set_desktop_string(self, update_ui: bool=False) -> None:
        """Set the desktop string to be displayed in the notch"""
        username_result = subprocess.run(["whoami"],
                                         capture_output=True,
                                         check=True)
        username = username_result.stdout.decode().strip()
        hostname_result = subprocess.run(["hostname"],
                                         capture_output=True,
                                         check=True)
        hostname = hostname_result.stdout.decode().strip()
        self.desktop_string = f"{username}@{hostname}"
        if update_ui:
            self.active_window.set_label(self.desktop_string)

    def update_window_icon(self, *args) -> None:
        """Update the window icon based on the current active window title"""

        label_widget = self.active_window
        if not isinstance(label_widget, Gtk.Label):
            return
        self._set_icon_visibility(True)
        conn = get_hyprland_connection()
        if conn:
            try:
                active_window_json = conn.send_command(
                    "j/activewindow").reply.decode()
                active_window_data = json.loads(active_window_json)
                app_id = active_window_data.get(
                    "initialClass", "") or active_window_data.get("class", "")

                icon_size = 20
                desktop_app = self.find_app(app_id)

                icon_pixbuf = None
                if desktop_app:
                    icon_pixbuf = desktop_app.get_icon_pixbuf(size=icon_size)

                if icon_pixbuf:
                    self.window_icon.set_from_pixbuf(icon_pixbuf)
                else:
                    self._set_icon_visibility(False)
            except Exception as e:
                logger.error(f"Error updating window icon: {e}")
                self._set_icon_visibility(False)
        else:
            self._set_icon_visibility(False)

    def on_active_window_changed(self, _, event: HyprlandEvent) -> None:
        if len(event.data) < 2:
            return

        class_name = event.data[0]
        title = event.data[1]
        if not class_name or not title:
            self.show_default()
        elif class_name != self._current_window_class:
            self._current_window_class = class_name
            window_name = f"{class_name[0].upper() + class_name[1:]}"[:20]
            self.active_window.set_label(window_name)
            self.update_window_icon()

    def _set_icon_visibility(self, visible: bool) -> None:
        """Set the visibility of the window icon"""
        self.icon_revealer.set_reveal_child(visible)

    def show_default(self) -> None:
        """Show the default widget"""
        self.active_window.set_label(self.desktop_string)
        self._set_icon_visibility(False)

    def _get_current_window_class(self) -> str:
        """Get the class of the currently active window"""
        try:

            conn = get_hyprland_connection()
            if conn:
                import json

                active_window_json = conn.send_command(
                    "j/activewindow").reply.decode()
                active_window_data = json.loads(active_window_json)
                return active_window_data.get(
                    "initialClass", "") or active_window_data.get("class", "")
        except Exception as e:
            logger.error(f"Error getting window class: {e}")
        return ""

    def find_app(self, app_identifier: str | dict | None) -> DesktopApp | None:
        """Find an application by its identifier, which can be a string or a dictionary."""
        if not app_identifier:
            return None
        if isinstance(app_identifier, dict):
            for key in [
                    "window_class",
                    "executable",
                    "command_line",
                    "name",
                    "display_name",
            ]:
                if key in app_identifier and app_identifier[key]:
                    app = self.find_app_by_key(app_identifier[key])
                    if app:
                        return app
            return None
        return self.find_app_by_key(app_identifier)

    def find_app_by_key(self, key_value: str) -> DesktopApp | None:
        """Find an application by a specific key value (like name, class, etc.)."""
        normalized_id = str(key_value).lower()
        if normalized_id in self.app_identifiers:
            return self.app_identifiers[normalized_id]
        for app in self._all_apps:
            if app.name and normalized_id in app.name.lower():
                return app
            if app.display_name and normalized_id in app.display_name.lower():
                return app
            if app.window_class and normalized_id in app.window_class.lower():
                return app
            if app.executable and normalized_id in app.executable.lower():
                return app
            if app.command_line and normalized_id in app.command_line.lower():
                return app
        return None

    def update_app_map(self) -> None:
        """Update the application map and identifiers from the desktop applications."""
        self._all_apps = get_desktop_applications()
        self.app_map = {app.name: app for app in self._all_apps if app.name}
        self.app_identifiers = self._build_app_identifiers_map()

    def _build_app_identifiers_map(self) -> dict[str, DesktopApp]:
        """Build a map of application identifiers to their corresponding DesktopApp objects."""
        identifiers = {}
        for app in self._all_apps:
            if app.name:
                identifiers[app.name.lower()] = app
            if app.display_name:
                identifiers[app.display_name.lower()] = app
            if app.window_class:
                identifiers[app.window_class.lower()] = app
            if app.executable:
                identifiers[app.executable.split("/")[-1].lower()] = app
            if app.command_line:
                identifiers[app.command_line.split()[0].split("/")
                            [-1].lower()] = app
        return identifiers


class NotchInner(CornerContainer):
    """Container for the notch widgets, allowing switching between them"""

    def __init__(
        self,
        notification_history: NotificationHistory,
        notch_widget_picker: NotchWidgetPicker,
        show_widget,
        notch,
    ):
        self.notch = notch
        self.widgets_labels = [
            'default', 'default-expanded', 'launcher', 'wallpaper', 'power',
            'clipboard', 'dock-settings'
        ]
        self.notch_widget_picker = notch_widget_picker
        self.notch_widget_default = NotchWidgetDefault()
        self.notch_widget_default_expanded = NotchWidgetDefaultExpanded(
            notification_history=notification_history, show_widget=show_widget
        )
        self.launcher = AppLauncher()
        self.notch_widget_wallpaper = WallpaperManager()
        self.power = PowerMenuActions()
        self.clipboard = ClipboardManager(notch_inner=self)
        self.dock_settings = DockSettings(notch=self.notch)

        self._contents = Stack(
            transition_type="slide-up-down",
            transition_duration=400,
            children=[
                self.notch_widget_default,
                self.notch_widget_default_expanded,
                self.launcher,
                self.notch_widget_wallpaper,
                self.power,
                self.clipboard,
                self.dock_settings,
            ],
            interpolate_size=True,
            h_expand=False,
        )
        self._contents.set_homogeneous(False)
        self._contents.set_visible_child(
            self._contents.get_children()
            [0])  # Show the default widget initially

        super().__init__(
            name="bar-center-container",
            corners=(True, True),
            height=30,
            v_align="center",
            h_align="center",
            orientation="v",
            children=[self.notch_widget_picker, self._contents],
        )

    def show_widget(self, widget_name: str, *_) -> bool:
        """Show a specific widget based on its name, updating the visible child of the contents stack."""
        widgets = self._contents.get_children()
        if widget_name not in self.widgets_labels:
            logger.error(f"Unknown widget name: {widget_name}")
            return False

        index = self.widgets_labels.index(widget_name)
        if self._contents.get_visible_child() is widgets[index]:
            index = 0

        self.notch_widget_picker.set_active_index(index - 1 if index > 0 else 0)
        self._contents.set_visible_child(widgets[index])
        return index == 0


class Notch(EventBox):
    """Main notch widget that contains the notch inner and the widget picker"""

    def __init__(self, notification_history: NotificationHistory, show_widget):
        self.notch_widget_picker = NotchWidgetPicker(self)
        self.inner = NotchInner(
            notification_history=notification_history,
            notch_widget_picker=self.notch_widget_picker,
            show_widget=show_widget,
            notch=self,
        )
        self.notification_history_indicator = NotificationHistoryIndicator(
            notification_history=notification_history)
        self.hovered = False
        self.show_picker = True
        self.drag_active = False

        super().__init__(
            child=Box(
                orientation="h",
                children=[self.notification_history_indicator, self.inner],
            ),
            events=[
                "leave-notify",
                "enter-notify",
            ],
        )
        self.connect("enter-notify-event", self._on_mouse_enter)
        self.connect("leave-notify-event", self._on_mouse_leave)

    def _on_mouse_enter(self, widget, event: Gdk.EventCrossing) -> bool:
        """Handle mouse enter event to show the notch widget picker and change styles."""
        if not self.hovered or not self.drag_active:
            self.hovered = True
            self.inner.add_style_class("hovered")
            if self.show_picker:
                self.notch_widget_picker.show()
            self.notification_history_indicator.add_style_class("hidden")
            self.notification_history_indicator.add_style_class("hovered")
            if self.inner._contents.get_visible_child(
            ) is self.inner.notch_widget_default:
                self.inner.show_widget("default-expanded")
        return False  # Allow event propagation

    def _on_mouse_leave(self, widget, event: Gdk.Event) -> bool:
        """Handle mouse leave event to hide the notch widget picker and change styles."""
        if (
            event.detail == Gdk.NotifyType.INFERIOR
            or self.drag_active  # Don't hide when dragging
        ):
            # Mouse is moving to a child widget or we're dragging - ignore this event
            return False

        if self.hovered:
            self.hovered = False
            self.show_picker = True
            self.inner.remove_style_class("hovered")
            self.notch_widget_picker.hide()
            self.notification_history_indicator.remove_style_class("hovered")
            # Show notification bell if has pending notifications to read
            if self.notification_history_indicator.notification_count > 0 or self.notification_history_indicator.dnd:
                GLib.timeout_add(
                    500,
                    lambda *_: self.notification_history_indicator.
                    remove_style_class("hidden"),
                )
        return False  # Allow event propagation

    def start_drag(self):
        """Called when a drag operation starts to prevent notch from hiding"""
        self.drag_active = True

    def end_drag(self):
        """Called when a drag operation ends to restore normal notch behavior"""
        # TODO: fix this sketchy race condition
        def reset_drag_active():
            self.drag_active = False
        GLib.timeout_add(500, lambda: reset_drag_active())

    def show_widget(self, widget_name: str, show_picker: bool = True) -> bool:
        """Show a specific widget in the notch inner and update the widget picker state."""
        self.show_picker = show_picker
        return self.inner.show_widget(widget_name)

class NotchWindow(WaylandWindow):
    """Window that contains the notch, used to display it on top of the screen"""

    def __init__(self, notification_history: NotificationHistory):
        margin = f"{"-54px" if config.BAR_POSITION == "top" else 0} 0 0 0"
        super().__init__(
            anchor="top center",
            layer="top",
            margin=margin,
            keyboard_mode="on_demand",
        )
        self.notch = Notch(notification_history=notification_history, show_widget=self.show_widget)
        self._container = Box(
            name="notch-container",
            orientation="h",
        )
        self._container.add(self.notch)
        self.add(self._container)

    def show_widget(self, widget_name: str, show_picker: bool = True) -> None:
        """Show a specific widget in the notch and update the notch inner state."""
        is_default = self.notch.show_widget(widget_name, show_picker)
        if is_default:
            self.notch.inner.remove_style_class("hovered")
        else:
            self.notch.inner.add_style_class("hovered")
