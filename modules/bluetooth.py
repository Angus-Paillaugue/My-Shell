from fabric.bluetooth.service import BluetoothClient, BluetoothDevice
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.revealer import Revealer
from fabric.widgets.scrolledwindow import ScrolledWindow

import modules.icons as icons
from modules.settings import SettingsButton


class BluetoothDeviceSlot(CenterBox):

    def __init__(self, device: BluetoothDevice, **kwargs):
        super().__init__(name="bluetooth-device", **kwargs)
        self.device = device
        self.device.connect("changed", self.on_changed)
        self.device.connect("notify::closed",
                            lambda *_: self.device.closed and self.destroy())

        self.connection_label = Label(name="bluetooth-connection",
                                      markup=icons.bluetooth_off)
        self.connect_button = Button(
            name="bluetooth-connect",
            label="Connect",
            on_clicked=lambda *_: self.device.set_connecting(not self.device.
                                                             connected),
            style_classes=["connected"] if self.device.connected else None,
        )

        self.start_children = [
            Box(
                spacing=8,
                h_expand=True,
                h_align="fill",
                children=[
                    Image(icon_name=device.icon_name + "-symbolic", size=16),
                    Label(
                        label=device.name,
                        h_expand=True,
                        h_align="start",
                        ellipsization="end",
                    ),
                    self.connection_label,
                ],
            )
        ]
        self.end_children = self.connect_button

        self.device.emit("changed")

    def on_changed(self, *_):
        self.connection_label.set_markup(
            icons.bluetooth if self.device.connected else icons.bluetooth_off)
        if self.device.connecting:
            self.connect_button.set_label(
                "Connecting..." if not self.device.connecting else "...")
        else:
            self.connect_button.set_label(
                "Connect" if not self.device.connected else "Disconnect")
        if self.device.connected:
            self.connect_button.add_style_class("connected")
        else:
            self.connect_button.remove_style_class("connected")
        return


class BluetoothDevicesDropdown(Revealer):

    def __init__(self, labels=dict(), **kwargs):
        super().__init__(
            name="bluetooth-devices-dropdown",
            transition_type="slide-down",
            child_revealed=False,
            h_expand=True,
            transition_duration=250,
            **kwargs,
        )

        self.shown = False
        self.labels = labels

        self.client = BluetoothClient(on_device_added=self.on_device_added)
        self.enabled = self.client.enabled
        self.scan_label = Label(name="bluetooth-scan-label", markup=icons.radar)
        self.scan_button = Button(
            name="bluetooth-scan",
            child=self.scan_label,
            tooltip_text="Scan for Bluetooth devices",
            on_clicked=lambda *_: self.client.toggle_scan(),
        )

        self.client.connect("notify::enabled", lambda *_: self.status_label())
        self.client.connect("notify::scanning",
                            lambda *_: self.update_scan_label())

        self.paired_box = Box(spacing=2, orientation="vertical")
        self.available_box = Box(spacing=2, orientation="vertical")

        content_box = Box(spacing=4, orientation="vertical")
        content_box.add(self.paired_box)
        content_box.add(Label(name="bluetooth-section", label="Available"))
        content_box.add(self.available_box)

        main_container = Box(
            name="bluetooth-devices-container",
            orientation="v",
            h_expand=True,
            spacing=8,
        )

        main_container.add(
            CenterBox(
                name="bluetooth-header",
                start_children=Label(name="bluetooth-devices-title",
                                     label="Bluetooth Devices"),
                end_children=self.scan_button,
            ))

        main_container.add(
            ScrolledWindow(
                name="bluetooth-devices",
                min_content_size=(-1, 150),  # Set a minimum height
                child=content_box,
                v_expand=True,
                propagate_width=False,
                propagate_height=False,
            ))

        self.add(main_container)

        self.client.notify("scanning")
        self.client.notify("enabled")

    def get_label(self, label_name):
        """Get the label for the Bluetooth devices dropdown."""
        return self.labels.get(label_name, Label())

    def set_labels(self, labels):
        """Set the labels for the Bluetooth devices dropdown."""
        self.labels = labels
        self.status_label()

    def collapse(self):
        """Toggle the visibility of the Bluetooth devices dropdown."""
        self.shown = False
        self.set_reveal_child(self.shown)

    def toggle_visibility(self):
        """Toggle the visibility of the Bluetooth devices dropdown."""
        self.shown = not self.shown
        self.set_reveal_child(self.shown)

    def status_label(self):
        self.enabled = self.client.enabled
        if self.client.enabled:
            self.get_label("status_text").set_label("Enabled")
            for i in [
                    self.get_label("button"),
                    self.get_label("status_text"),
                    self.get_label("icon"),
            ]:
                i.remove_style_class("disabled")
            self.get_label("icon").set_markup(icons.bluetooth)
        else:
            self.get_label("status_text").set_label("Disabled")
            for i in [
                    self.get_label("button"),
                    self.get_label("status_text"),
                    self.get_label("icon"),
            ]:
                i.add_style_class("disabled")
            self.get_label("icon").set_markup(icons.bluetooth_off)

    def on_device_added(self, client: BluetoothClient, address: str):
        if not (device := client.get_device(address)):
            return

        # Check if device is already displayed
        for child in self.paired_box.get_children():
            if (isinstance(child, BluetoothDeviceSlot) and
                    child.device.address == address):
                return

        for child in self.available_box.get_children():
            if (isinstance(child, BluetoothDeviceSlot) and
                    child.device.address == address):
                return

        slot = BluetoothDeviceSlot(device)

        if device.paired:
            self.paired_box.add(slot)
            self.paired_box.show_all()
        else:
            self.available_box.add(slot)
            self.available_box.show_all()

    def update_scan_label(self):
        if self.client.scanning:
            self.scan_label.add_style_class("scanning")
            self.scan_button.add_style_class("scanning")
            self.scan_button.set_tooltip_text(
                "Stop scanning for Bluetooth devices")
        else:
            self.scan_label.remove_style_class("scanning")
            self.scan_button.remove_style_class("scanning")
            self.scan_button.set_tooltip_text("Scan for Bluetooth devices")


class BluetoothButton(SettingsButton):

    def __init__(self, slot=None, **kwargs):
        self.labels = dict()
        self.bluetooth_devices_dropdown = BluetoothDevicesDropdown(
            labels=self.labels)
        super().__init__(
            label="Bluetooth",
            slot=slot,
            dropdown=self.bluetooth_devices_dropdown,
            icon=icons.bluetooth,
            left_button_click=lambda *_: (
                self.bluetooth_devices_dropdown.client.toggle_power(),
                (self.bluetooth_devices_dropdown.toggle_visibility()
                 if self.bluetooth_devices_dropdown.shown else None),
            ),
            **kwargs,
        )
        self.labels["button"] = self.left_button
        self.labels["status_text"] = self.status_text
        self.labels["icon"] = self.icon
        self.bluetooth_devices_dropdown.set_labels(self.labels)
