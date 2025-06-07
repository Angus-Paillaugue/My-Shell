from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.bluetooth.service import BluetoothClient, BluetoothDevice
from fabric.widgets.centerbox import CenterBox
import modules.icons as icons
from fabric.widgets.revealer import Revealer
from fabric.widgets.revealer import Revealer
from fabric.widgets.image import Image
from fabric.widgets.scrolledwindow import ScrolledWindow


class BluetoothDeviceSlot(CenterBox):
    def __init__(self, device: BluetoothDevice, **kwargs):
        super().__init__(name="bluetooth-device", **kwargs)
        self.device = device
        self.device.connect("changed", self.on_changed)
        self.device.connect(
            "notify::closed", lambda *_: self.device.closed and self.destroy()
        )

        self.connection_label = Label(
            name="bluetooth-connection", markup=icons.bluetooth_off
        )
        self.connect_button = Button(
            name="bluetooth-connect",
            label="Connect",
            on_clicked=lambda *_: self.device.set_connecting(not self.device.connected),
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
            icons.bluetooth if self.device.connected else icons.bluetooth_off
        )
        if self.device.connecting:
            self.connect_button.set_label(
                "Connecting..." if not self.device.connecting else "..."
            )
        else:
            self.connect_button.set_label(
                "Connect" if not self.device.connected else "Disconnect"
            )
        if self.device.connected:
            self.connect_button.add_style_class("connected")
        else:
            self.connect_button.remove_style_class("connected")
        return


class BluetoothDevicesDropdown(Revealer):
    def __init__(self, labels, **kwargs):
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
        self.bt_status_text = self.labels["bluetooth_status_text"]
        self.bt_button = self.labels["bluetooth_button"]
        self.bt_icon = self.labels["bluetooth_icon"]

        self.client = BluetoothClient(on_device_added=self.on_device_added)
        self.scan_label = Label(name="bluetooth-scan-label", markup=icons.radar)
        self.scan_button = Button(
            name="bluetooth-scan",
            child=self.scan_label,
            tooltip_text="Scan for Bluetooth devices",
            on_clicked=lambda *_: self.client.toggle_scan(),
        )

        self.client.connect("notify::enabled", lambda *_: self.status_label())
        self.client.connect("notify::scanning", lambda *_: self.update_scan_label())

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
                start_children=Label(
                    name="bluetooth-devices-title", label="Bluetooth Devices"
                ),
                end_children=self.scan_button,
            )
        )

        main_container.add(
            ScrolledWindow(
                name="bluetooth-devices",
                min_content_size=(-1, 150),  # Set a minimum height
                child=content_box,
                v_expand=True,
                propagate_width=False,
                propagate_height=False,
            )
        )

        self.add(main_container)

        self.client.notify("scanning")
        self.client.notify("enabled")

    def collapse(self):
        """Toggle the visibility of the Bluetooth devices dropdown."""
        self.shown = False
        self.set_reveal_child(self.shown)

    def toggle_visibility(self):
        """Toggle the visibility of the Bluetooth devices dropdown."""
        self.shown = not self.shown
        self.set_reveal_child(self.shown)

    def status_label(self):
        if self.client.enabled:
            self.bt_status_text.set_label("Enabled")
            for i in [
                self.bt_button,
                self.bt_status_text,
                self.bt_icon,
            ]:
                i.remove_style_class("disabled")
            self.bt_icon.set_markup(icons.bluetooth)
        else:
            self.bt_status_text.set_label("Disabled")
            for i in [
                self.bt_button,
                self.bt_status_text,
                self.bt_icon,
            ]:
                i.add_style_class("disabled")
            self.bt_icon.set_markup(icons.bluetooth_off)

    def on_device_added(self, client: BluetoothClient, address: str):
        if not (device := client.get_device(address)):
            return

        # Check if device is already displayed
        for child in self.paired_box.get_children():
            if (
                isinstance(child, BluetoothDeviceSlot)
                and child.device.address == address
            ):
                return

        for child in self.available_box.get_children():
            if (
                isinstance(child, BluetoothDeviceSlot)
                and child.device.address == address
            ):
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
            self.scan_button.set_tooltip_text("Stop scanning for Bluetooth devices")
        else:
            self.scan_label.remove_style_class("scanning")
            self.scan_button.remove_style_class("scanning")
            self.scan_button.set_tooltip_text("Scan for Bluetooth devices")


class BluetoothButton(Box):
    def __init__(self, slot=None, **kwargs):
        super().__init__(
            name="bluetooth-button",
            h_expand=True,
            v_expand=True,
            spacing=4,
            orientation="h",
            **kwargs,
        )

        self.left_button_childs = Box(
            name="bluetooth-left-button-childs",
            orientation="h",
            spacing=8,
        )
        self.left_button = Button(
            name="bluetooth-left-button",
            h_expand=True,
            child=self.left_button_childs,
        )

        self.slot = slot
        self.bluetooth_status_text = Label(
            name="bluetooth-status", label="Bluetooth", all_visible=True, visible=True
        )
        self.bluetooth_icon = Label(name="bluetooth-icon", markup=icons.bluetooth)
        self.bluetooth_devices_open_button = Button(
            name="bluetooth-open-button",
            child=Label(name="bluetooth-open-label", markup=icons.chevron_right),
        )
        self.labels = dict()
        self.labels["bluetooth_button"] = self.left_button
        self.labels["bluetooth_status_text"] = self.bluetooth_status_text
        self.labels["bluetooth_icon"] = self.bluetooth_icon
        self.bluetooth_devices_dropdown = BluetoothDevicesDropdown(labels=self.labels)
        self.slot.add(self.bluetooth_devices_dropdown)

        self.left_button_childs.add(self.bluetooth_icon)
        self.left_button_childs.add(self.bluetooth_status_text)
        self.add(self.left_button)
        self.add(self.bluetooth_devices_open_button)
        self.bluetooth_devices_open_button.connect(
            "clicked",
            lambda *_: (
                self.bluetooth_devices_dropdown.toggle_visibility()
                if self.bluetooth_devices_dropdown.client.enabled
                else None
            ),
        )
        self.left_button.connect(
            "clicked",
            lambda *_: (
                self.bluetooth_devices_dropdown.client.toggle_power(),
                (
                    self.bluetooth_devices_dropdown.toggle_visibility()
                    if self.bluetooth_devices_dropdown.shown
                    else None
                ),
            ),
        )
