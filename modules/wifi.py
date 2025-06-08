import gi

gi.require_version("Gtk", "3.0")
gi.require_version("NM", "1.0")
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.revealer import Revealer
from fabric.widgets.scrolledwindow import ScrolledWindow
from gi.repository import GLib

import modules.icons as icons
from services.network import NetworkClient


class WifiAccessPointSlot(Box):

    def __init__(self, ap_data: dict, network_service: NetworkClient,
                 wifi_service, **kwargs):
        super().__init__(name="wifi-ap-slot", **kwargs)
        self.ap_data = ap_data
        self.network_service = network_service
        self.wifi_service = wifi_service

        ssid = ap_data.get("ssid", "Unknown SSID")
        icon_name = ap_data.get("icon-name",
                                "network-wireless-signal-none-symbolic")

        freq = ap_data.get("frequency", 0)
        freq_text = ""
        if freq > 0:
            if freq >= 5000:
                freq_text = "5 GHz"
            else:
                freq_text = "2.4 GHz"

        self.is_active = False
        active_ap_details = ap_data.get("active-ap")
        if (active_ap_details and hasattr(active_ap_details, "get_bssid") and
                active_ap_details.get_bssid() == ap_data.get("bssid")):
            self.is_active = True

        self.ap_icon = Image(icon_name=icon_name, size=16)

        self.ssid_label = Label(
            label=ssid,
            h_align="start",
            ellipsization="end",
        )

        self.freq_label = Label(
            label=(f" ({freq_text})" if freq_text else ""),
            h_expand=False,
            h_align="start",
            name="wifi-freq-label",
        )

        ssid_freq_box = Box(
            orientation="horizontal",
            spacing=0,
            h_expand=True,
            h_align="fill",
            children=[
                self.ssid_label,
                self.freq_label,
            ],
        )

        self.connect_button = Button(
            name="wifi-connect-button",
            label="Connected" if self.is_active else "Connect",
            sensitive=not self.is_active,
            on_clicked=self._on_connect_clicked,
            style_classes=["connected"] if self.is_active else None,
            h_expand=True,
            h_align="end",
        )
        self.children = [
            Box(
                spacing=8,
                h_expand=True,
                h_align="fill",
                children=[
                    self.ap_icon,
                    ssid_freq_box,
                ],
            ),
            self.connect_button,
        ]

    def _on_connect_clicked(self, _):
        if not self.is_active and self.ap_data.get("bssid"):
            self.connect_button.set_label("Connecting...")
            self.connect_button.set_sensitive(False)
            self.network_service.connect_wifi_bssid(self.ap_data["bssid"])


class WifiNetworksDropdown(Revealer):

    def __init__(self, labels, **kwargs):
        super().__init__(
            name="network-connections-dropdown",
            transition_type="slide-down",
            child_revealed=False,
            h_expand=True,
            transition_duration=250,
            **kwargs,
        )

        self.main_box = Box(
            name="wifi-connections-box",
            orientation="v",
            h_expand=True,
            v_expand=True,
            spacing=4,
        )
        self.shown = False
        self.labels = labels
        self.wifi_status_text = self.labels["wifi_status_text"]
        self.wifi_button = self.labels["wifi_button"]
        self.wifi_icon = self.labels["wifi_icon"]
        self.network_client = NetworkClient()

        self.status_label = Label(
            name="wifi-networks-title",
            label="Initializing Wi-Fi...",
            h_expand=True,
            h_align="center",
        )

        self.refresh_button_icon = Label(name="network-refresh-label",
                                         markup=icons.reload)
        self.refresh_button = Button(
            name="wifi-scan",
            child=self.refresh_button_icon,
            tooltip_text="Scan for Wi-Fi networks",
            on_clicked=self._refresh_access_points,
        )

        header_box = CenterBox(
            name="wifi-networks-header",
            start_children=[
                Label(name="network-title", label="Wi-Fi Networks")
            ],
            end_children=[
                Box(orientation="horizontal",
                    spacing=4,
                    children=[self.refresh_button])
            ],
        )

        self.ap_list_box = Box(orientation="vertical", spacing=4)
        scrolled_window = ScrolledWindow(
            name="network-ap-scrolled-window",
            child=self.ap_list_box,
            h_expand=True,
            min_content_size=(-1, 150),
            v_expand=True,
            propagate_width=False,
            propagate_height=False,
        )

        self.main_box.add(header_box)
        self.main_box.add(scrolled_window)
        self.add(self.main_box)

        self.network_client.connect("device-ready", self._on_device_ready)

    def collapse(self):
        self.shown = False
        self.set_reveal_child(self.shown)

    def toggle_visibility(self):
        """Toggle the visibility of the Wifi networks dropdown."""
        if not self.network_client._client.wireless_get_enabled():
            return
        self.shown = not self.shown
        self.set_reveal_child(self.shown)

        if self.shown:
            self._update_wifi_status_ui()
            # Only try to load APs if WiFi is enabled
            if (self.network_client.wifi_device and
                    self.network_client.wifi_device.enabled):
                self._load_access_points()

    def _on_device_ready(self, _client):
        if self.network_client.wifi_device:
            self.network_client.wifi_device.connect("changed",
                                                    self._load_access_points)
            self.network_client.wifi_device.connect("notify::enabled",
                                                    self._update_wifi_status_ui)
            self._update_wifi_status_ui()
            if self.network_client.wifi_device.enabled:
                self._load_access_points()
                self.wifi_button.remove_style_class("disabled")
            else:
                self.wifi_status_text.set_label("Disabled")
                self.wifi_button.add_style_class("disabled")
                self.status_label.set_label("Wi-Fi disabled.")
        else:
            self.status_label.set_label("Wi-Fi device not available.")
            self.wifi_status_text.set_label("Not available")
            self.wifi_button.add_style_class("disabled")
            self.refresh_button.set_sensitive(False)

    def _update_wifi_status_ui(self, *args):
        """Update the WiFi status display in the dropdown."""
        if not self.network_client._client:
            return

        # Check if WiFi is enabled at the NM level first
        wifi_enabled = self.network_client._client.wireless_get_enabled()

        if not wifi_enabled:
            self.wifi_status_text.set_label("Disabled")
            self.wifi_button.add_style_class("disabled")
            self.wifi_icon.set_markup(icons.wifi_off)
            self.status_label.set_label("Wi-Fi disabled.")
            self._clear_ap_list()
            self.refresh_button.set_sensitive(False)
            return

        # WiFi is enabled, now check the device
        if self.network_client.wifi_device:
            self.refresh_button.set_sensitive(True)
            self.wifi_button.remove_style_class("disabled")

            if self.network_client.wifi_device.ssid:
                ssid = self.network_client.wifi_device.ssid
                strength = self.network_client.wifi_device.strength
                if strength > 80:
                    self.wifi_icon.set_markup(icons.wifi_3)
                elif strength > 50:
                    self.wifi_icon.set_markup(icons.wifi_2)
                elif strength > 20:
                    self.wifi_icon.set_markup(icons.wifi_1)
                else:
                    self.wifi_icon.set_markup(icons.wifi_0)
                self.wifi_status_text.set_label(ssid)
            else:
                self.wifi_icon.set_markup(icons.wifi_off)
                self.wifi_status_text.set_label("Not Connected")

            # Check if we need to load access points
            if not self.ap_list_box.get_children() and self.shown:
                GLib.idle_add(self._refresh_access_points)
        else:
            self.wifi_status_text.set_label("Not available")
            self.wifi_button.add_style_class("disabled")
            self.wifi_icon.set_markup(icons.wifi_off)
            self.refresh_button.set_sensitive(False)

    def toggle_wifi(self, *args):
        """Enable or disable the WiFi connection"""
        if not self.network_client._client:
            return

        current_state = self.network_client._client.wireless_get_enabled()

        # Toggle WiFi state
        self.network_client._client.wireless_set_enabled(not current_state)

        # Update UI immediately for better feedback
        if current_state:  # we're turning it off
            self.wifi_status_text.set_label("Disabled")
            self.wifi_button.add_style_class("disabled")
            self.wifi_icon.set_markup(icons.wifi_off)
            # Close dropdown if it's open
            if self.shown:
                self.toggle_visibility()
        else:  # we're turning it on
            self.wifi_status_text.set_label("Enabling...")
            self.wifi_button.remove_style_class("disabled")
            self.wifi_icon.set_markup(icons.wifi_1)

            # If the dropdown is open, update it after a short delay
            if self.shown:
                GLib.timeout_add(1000, self._load_access_points)

    def _refresh_access_points(self, _=None):
        if self.network_client.wifi_device and self.network_client.wifi_device.enabled:
            self.status_label.set_label("Scanning for Wi-Fi networks...")
            self._clear_ap_list()
            self.network_client.wifi_device.scan()
            self._load_access_points()
        return False

    def _clear_ap_list(self):
        for child in self.ap_list_box.get_children():
            child.destroy()

    def _load_access_points(self, *args):
        if (not self.network_client.wifi_device or
                not self.network_client.wifi_device.enabled):
            self._clear_ap_list()
            self.status_label.set_label("Wi-Fi disabled.")
            self.wifi_status_text.set_label("Disabled")
            self.wifi_button.add_style_class("disabled")
            return

        self._clear_ap_list()
        self.wifi_button.remove_style_class("disabled")

        access_points = self.network_client.wifi_device.access_points

        if not access_points:
            self.status_label.set_label("No Wi-Fi networks found.")
        else:
            sorted_aps = sorted(access_points,
                                key=lambda x: x.get("strength", 0),
                                reverse=True)
            self.status_label.set_label(
                f"{len(sorted_aps)} Wi-Fi networks found:")
            for ap_data in sorted_aps:
                slot = WifiAccessPointSlot(ap_data, self.network_client,
                                           self.network_client.wifi_device)
                self.ap_list_box.add(slot)
        self.ap_list_box.show_all()


class WifiModule(Box):

    def __init__(self, slot, **kwargs):
        super().__init__(
            name="wifi-connections",
            h_expand=True,
            v_expand=True,
            spacing=4,
            orientation="h",
            **kwargs,
        )
        self.slot = slot
        self.network_client = NetworkClient()
        self.left_button_childs = Box(
            name="wifi-left-button-childs",
            orientation="h",
            spacing=8,
        )
        self.left_button = Button(
            name="wifi-left-button",
            h_expand=True,
            child=self.left_button_childs,
        )
        self.wifi_status_text = Label(
            name="wifi-status",
            label="Wi-Fi",
            all_visible=True,
            visible=True,
            ellipsization="end",
        )
        self.wifi_icon = Label(name="wifi-icon", markup=icons.wifi_off)
        self.wifi_networks_open_button = Button(
            style_classes=["expand-button-caret"],
            child=Label(name="wifi-open-label", markup=icons.chevron_right),
        )

        self.labels = dict()
        self.labels["wifi_button"] = self.left_button
        self.labels["wifi_status_text"] = self.wifi_status_text
        self.labels["wifi_icon"] = self.wifi_icon
        self.wifi_networks_dropdown = WifiNetworksDropdown(labels=self.labels)
        self.slot.add(self.wifi_networks_dropdown)

        # Set up the UI elements
        self.left_button_childs.add(self.wifi_icon)
        self.left_button_childs.add(self.wifi_status_text)
        self.add(self.left_button)
        self.add(self.wifi_networks_open_button)

        # Connect chevron button to toggle dropdown
        self.wifi_networks_open_button.connect(
            "clicked",
            lambda *_: self.wifi_networks_dropdown.toggle_visibility(),
        )

        # Connect left button to toggle WiFi on/off
        self.left_button.connect(
            "clicked",
            lambda *_: self.wifi_networks_dropdown.toggle_wifi(),
        )

        # Initialize UI state when device is ready
        self.network_client.connect("device-ready", self._on_device_ready)

        # Important: Check if WiFi device is already available
        # This is the key fix - the device might already be ready
        if self.network_client.wifi_device:
            GLib.idle_add(self._on_device_ready, self.network_client)

        # Also add a fallback timer to check WiFi state after a short delay
        GLib.timeout_add(500, self._check_initial_state)

        # Connect to WiFi state changes
        if self.network_client._client:
            self.network_client._client.connect(
                "notify::wireless-enabled",
                lambda *_: GLib.idle_add(self._update_wifi_state),
            )

    def _check_initial_state(self):
        """Fallback to ensure WiFi state is initialized properly"""
        if self.network_client.wifi_device:
            self._update_wifi_state()
        return False  # Run only once

    def _on_device_ready(self, _client):
        """Initialize the UI state when WiFi device becomes ready"""
        if self.network_client.wifi_device:
            # Update UI with current WiFi info
            GLib.idle_add(self._update_wifi_state)
            # Connect to WiFi device signals
            self.network_client.wifi_device.connect(
                "changed", lambda *_: GLib.idle_add(self._update_wifi_state))
            # Also listen for property changes related to connection state
            self.network_client.wifi_device.connect(
                "notify::ssid",
                lambda *_: GLib.idle_add(self._update_wifi_state))
            self.network_client.wifi_device.connect(
                "notify::strength",
                lambda *_: GLib.idle_add(self._update_wifi_state))

    def _update_wifi_state(self):
        """Update the WiFi status display"""
        if not self.network_client.wifi_device:
            return

        # Update based on current WiFi state
        enabled = self.network_client.wifi_device.enabled

        if enabled:
            self.left_button.remove_style_class("disabled")
            if self.network_client.wifi_device.ssid:
                ssid = self.network_client.wifi_device.ssid
                strength = self.network_client.wifi_device.strength
                if strength > 80:
                    self.wifi_icon.set_markup(icons.wifi_3)
                elif strength > 50:
                    self.wifi_icon.set_markup(icons.wifi_2)
                elif strength > 20:
                    self.wifi_icon.set_markup(icons.wifi_1)
                else:
                    self.wifi_icon.set_markup(icons.wifi_0)
                self.wifi_status_text.set_label(ssid)
            else:
                self.wifi_icon.set_markup(icons.wifi_off)
                self.wifi_status_text.set_label("Not Connected")
        else:
            self.wifi_icon.set_markup(icons.wifi_off)
            self.left_button.add_style_class("disabled")
            self.wifi_status_text.set_label("Disabled")

        return False
