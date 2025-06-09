from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.centerbox import CenterBox
from gi.repository import Gtk
from modules.dismissible_window import DismissibleWindow
import modules.icons as icons
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


class SettingsMenuDropdown(DismissibleWindow):

    def __init__(self, parent_button, **kwargs):
        super().__init__(
            anchor="top right",
            exclusivity="none",
            visible=False,
            margin="6px 8px 0 0",
            **kwargs,
        )

        self.parent_button = parent_button
        self.parent_box = parent_button.get_parent()

        self.brightness_module = BrightnessRow()
        self.battery = Battery()
        self.power_profile = PowerProfile()
        self.power_menu_actions = PowerMenuActions()
        self.bluetooth_devices_dropdown_slot = Box()
        self.wifi_networks_dropdown_slot = Box()
        self.audio_outputs_dropdown_slot = Box()
        self.mic_inputs_dropdown_slot = Box()
        self.wired_networks_dropdown_slot = Box()
        self.mic_module = MicRow(slot=self.mic_inputs_dropdown_slot)
        self.volume_module = VolumeRow(slot=self.audio_outputs_dropdown_slot)
        self.bluetooth = BluetoothButton(
            slot=self.bluetooth_devices_dropdown_slot)
        self.power_menu_button = PowerMenuButton(
            power_actions=self.power_menu_actions)
        self.wifi_module = WifiModule(slot=self.wifi_networks_dropdown_slot)
        self.network_module = Wired(slot=self.wired_networks_dropdown_slot)
        self.screenshot_button = ScreenshotButton(
            close_settings=self.toggle_visibility)
        self.screen_record_button = ScreenRecordButton(
            close_settings=self.toggle_visibility)

        self.buttons_grid = Gtk.Grid(
            column_homogeneous=True,
            row_homogeneous=False,
            name="setting-buttons-grid",
            column_spacing=12,
            row_spacing=12,
        )

        self.buttons_grid.attach(self.wifi_module, 0, 0, 1, 1)
        self.buttons_grid.attach(self.network_module, 1, 0, 1, 1)
        self.buttons_grid.attach(self.bluetooth, 0, 1, 1, 1)
        self.buttons_grid.attach(self.power_profile, 1, 1, 1, 1)

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
            self.volume_module,
            self.audio_outputs_dropdown_slot,
            self.mic_module,
            self.mic_inputs_dropdown_slot,
            self.brightness_module,
        ]

        # Add the container to our window
        self.settings_container = Box(
            name="settings-container",
            orientation="v",
        )
        self.add(self.settings_container)

        for item in self.items:
            self.settings_container.add(item)

    def toggle_visibility(self):
        if self.is_visible():
            self.hide()
            self.collapse_slots()
        else:
            self.show_all()
            # Make sure our window has focus so we can detect focus out events
            self.present()

    def collapse_slots(self):
        """Collapse all of the Revealer used by modules"""
        self.network_module.wired_networks_dropdown.collapse()
        self.wifi_module.wifi_networks_dropdown.collapse()
        self.bluetooth.bluetooth_devices_dropdown.collapse()
        self.volume_module.outputs_box.collapse()
        self.mic_module.inputs_box.collapse()


class Settings(Box):

    def __init__(self, **kwargs):
        super().__init__(
            name="settings-menu-container",
            orientation="h",
            spacing=4,
            v_align="center",
            h_align="center",
            visible=True,
            **kwargs,
        )

        # Main power button
        self.settings_button = Button(
            name="settings-menu-main-button",
            child=Label(markup=icons.settings),
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
            style_classes=["bar-action-button"],
        )

        # Add the button to our container
        self.add(self.settings_button)

        # Create dropdown window
        self.dropdown = SettingsMenuDropdown(self.settings_button)

        # Connect button to toggle dropdown
        self.settings_button.connect("clicked", self.toggle_dropdown)

    def toggle_dropdown(self, *_):
        self.dropdown.toggle_visibility()
