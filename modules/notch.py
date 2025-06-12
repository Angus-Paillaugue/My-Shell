from modules.time import Time
from modules.corners import CornerContainer
from modules.notification import NotificationHistoryIndicator, NotificationHistory
from gi.repository import Gdk
from fabric.widgets.eventbox import EventBox
from services.logger import logger
from fabric.widgets.stack import Stack
from modules.time import CalendarBox as Calendar
from fabric.widgets.wayland import WaylandWindow
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.revealer import Revealer
from gi.repository import Gtk
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from modules.bluetooth import BluetoothButton
from modules.battery import Battery
from modules.brightness import BrightnessRow
from modules.power import PowerMenuActions, PowerMenuButton
from modules.power_profile import PowerProfile
from modules.volume import VolumeRow, MicRow
from modules.wifi import WifiModule
from modules.wired import Wired
from modules.screenshot import ScreenshotButton
from modules.screen_record import ScreenRecordButton
from fabric.widgets.centerbox import CenterBox
from modules.wallpaper import WallpaperManager
from modules.launcher import AppLauncher

class NotchWidgetPicker(Revealer):
    def __init__(self, notch):
        super().__init__(
            transition_duration=300,
            transition_type="slide-right",
            child_revealed=False,
            visible=True,
            all_visible=True,
        )
        self.revealer_2 = Revealer(
            transition_duration=300,
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

    def show(self):
        self.set_reveal_child(True)
        self.revealer_2.set_reveal_child(True)

    def hide(self):
        self.set_reveal_child(False)
        self.revealer_2.set_reveal_child(False)
        if hasattr(self.notch.inner._contents.get_visible_child(), "cleanup"):
            # If the visible child has a collapse_slots method, call it
            self.notch.inner._contents.get_visible_child().cleanup()
        self.notch.inner.show_widget("default")

    def set_active_index(self, index: int):
        if 0 <= index < len(self.buttons):
            for i, button in enumerate(self.buttons):
                if i == index:
                    button.add_style_class("active")
                else:
                    button.remove_style_class("active")
        else:
            logger.error(f"Index {index} is out of range for NotchWidgetPicker buttons.")


class NotchWidgetDefaultExpanded(Box):

    def __init__(self, notification_history: NotificationHistory):
        super().__init__(
            orientation="v",
            spacing=8,
            v_align="start",
            h_align="center",
        )
        self.brightness_module = BrightnessRow()
        self.battery = Battery()
        self.power_profile = PowerProfile()
        self.power_menu_actions = PowerMenuActions()
        self.power_menu_button = PowerMenuButton(power_actions=self.power_menu_actions)
        self.bluetooth_devices_dropdown_slot = Box()
        self.wifi_networks_dropdown_slot = Box()
        self.audio_outputs_dropdown_slot = Box()
        self.mic_inputs_dropdown_slot = Box()
        self.wired_networks_dropdown_slot = Box()
        self.mic_module = MicRow(slot=self.mic_inputs_dropdown_slot)
        self.volume_module = VolumeRow(slot=self.audio_outputs_dropdown_slot)
        self.bluetooth = BluetoothButton(slot=self.bluetooth_devices_dropdown_slot)
        self.wifi_module = WifiModule(slot=self.wifi_networks_dropdown_slot)
        self.network_module = Wired(slot=self.wired_networks_dropdown_slot)
        self.screenshot_button = ScreenshotButton()
        self.screen_record_button = ScreenRecordButton()

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
                self.screen_record_button,
                self.screenshot_button,
                self.power_menu_button,
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
            self.power_menu_actions,
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

        self.second_row = Box(
            spacing=8,
        )
        self.notification_history = notification_history
        self.calendar = Calendar()
        self.second_row.add(self.calendar)
        self.second_row.add(self.notification_history)
        self.add(self.second_row)
        self.set_valign(Gtk.Align.START)
        self.set_halign(Gtk.Align.CENTER)

    def cleanup(self):
        """Collapse all of the Revealer used by modules"""
        self.network_module.wired_networks_dropdown.collapse()
        self.wifi_module.wifi_networks_dropdown.collapse()
        self.bluetooth.bluetooth_devices_dropdown.collapse()
        self.volume_module.outputs_box.collapse()
        self.mic_module.inputs_box.collapse()


class NotchWidgetDefault(Box):
    def __init__(self, notification_history: NotificationHistory):
        super().__init__(
            orientation="h",
            spacing=8,
        )
        self.notification_history_indicator = NotificationHistoryIndicator(
            notification_history=notification_history
        )
        self.time = Time()
        self.add(self.notification_history_indicator)
        self.add(self.time)


class NotchInner(CornerContainer):

    def __init__(
        self,
        notification_history: NotificationHistory,
        notch_widget_picker: NotchWidgetPicker,
    ):
        self.notch_widget_picker = notch_widget_picker
        self.notch_widget_default = NotchWidgetDefault(
            notification_history=notification_history
        )
        self.notch_widget_default_expanded = NotchWidgetDefaultExpanded(
            notification_history=notification_history
        )
        self.launcher = AppLauncher()
        self.notch_widget_wallpaper = WallpaperManager()

        self._contents = Stack(
            transition_type="slide-up-down",
            transition_duration=400,
            children=[
                self.notch_widget_default,
                self.notch_widget_default_expanded,
                self.launcher,
                self.notch_widget_wallpaper,
            ],
            interpolate_size=True,
            h_expand=False
        )
        self._contents.set_homogeneous(False)
        self._contents.set_visible_child(self._contents.get_children()[0])  # Show the default widget initially


        super().__init__(
            name="bar-center-container",
            corners=["left", "right"],
            height=30,
            v_align="center",
            orientation="v",
            children=[self.notch_widget_picker, self._contents],
        )

    def show_widget(self, widget_name: str, *_):
        widgets = self._contents.get_children()
        if widget_name == "default":
            index = 0
        elif widget_name == "default-expanded":
            index = 1
        elif widget_name == "launcher":
            index = 2
        elif widget_name == "wallpaper":
            index = 3
        else:
            logger.error(f"Unknown widget name: {widget_name}")
            return
        self.notch_widget_picker.set_active_index(index - 1 if index > 0 else 0)
        self._contents.set_visible_child(widgets[index])


class Notch(EventBox):

    def __init__(self, notification_history: NotificationHistory):
        self.notch_widget_picker = NotchWidgetPicker(self)
        self.inner = NotchInner(
            notification_history=notification_history,
            notch_widget_picker=self.notch_widget_picker,
        )
        self.hovered = False

        super().__init__(
            child=self.inner,
            events=["leave-notify", "enter-notify"],
        )
        self.connect("enter-notify-event", self._on_mouse_enter)
        self.connect("leave-notify-event", self._on_mouse_leave)

    def _on_mouse_enter(self, widget, event):
        if not self.hovered:
            self.hovered = True
            self.inner.add_style_class("hovered")
            self.notch_widget_picker.show()
            if self.inner._contents.get_visible_child() is self.inner.notch_widget_default: # if we are still showing the default widget, move to the expanded one
                self.inner.show_widget("default-expanded")
        return False  # Allow event propagation

    def _on_mouse_leave(self, widget, event):
        if event.detail == Gdk.NotifyType.INFERIOR:
            # Mouse is moving to a child widget - ignore this event
            return False

        if self.hovered:
            self.hovered = False
            self.inner.remove_style_class("hovered")
            self.show_widget("default-expanded")
            self.notch_widget_picker.hide()
        return False  # Allow event propagation

    def show_widget(self, widget_name: str):
        self.inner.show_widget(widget_name)


class NotchWindow(WaylandWindow):
    def __init__(self, notification_history: NotificationHistory):
        super().__init__(
            anchor="top center",
            layer="overlay",
            margin="-54px 0 0 0",
            keyboard_mode="on_demand",
        )
        self.notch = Notch(notification_history=notification_history)
        self._container = Box(
            name="notch-container",
            orientation="v",
            spacing=8,
        )
        self._container.add(self.notch)
        self.add(self._container)

    def show_widget(self, widget_name: str):
        self.notch.show_widget(widget_name)
        self.notch.inner.add_style_class("hovered")
