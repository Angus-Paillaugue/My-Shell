from typing import Any, List, Literal

import gi
from fabric.core.service import Property, Service, Signal
from fabric.utils import (bulk_connect, exec_shell_command,
                          exec_shell_command_async)
from gi.repository import Gio

from services.logger import logger

try:
    gi.require_version("NM", "1.0")
    from gi.repository import NM
except ValueError:
    logger.error("Failed to start network manager")


class Wifi(Service):
    """A service to manage the wifi connection."""

    @Signal
    def changed(self) -> None:
        ...

    @Signal
    def enabled(self) -> bool:
        ...

    def __init__(self, client: NM.Client, device: NM.DeviceWifi, **kwargs):
        self._client: NM.Client = client
        self._device: NM.DeviceWifi = device
        self._ap: NM.AccessPoint | None = None
        self._ap_signal: int | None = None
        super().__init__(**kwargs)

        self._client.connect(
            "notify::wireless-enabled",
            lambda *args: self.notifier("enabled", args),
        )
        if self._device:
            bulk_connect(
                self._device,
                {
                    "notify::active-access-point":
                        lambda *args: self._activate_ap(),
                    "access-point-added":
                        lambda *args: self.emit("changed"),
                    "access-point-removed":
                        lambda *args: self.emit("changed"),
                    "state-changed":
                        lambda *args: self.ap_update(),
                },
            )
            self._activate_ap()

    def ap_update(self) -> None:
        self.emit("changed")
        for sn in [
                "enabled",
                "internet",
                "strength",
                "frequency",
                "access-points",
                "ssid",
                "state",
                "icon-name",
        ]:
            self.notify(sn)

    def _activate_ap(self) -> None:
        if self._ap:
            self._ap.disconnect(self._ap_signal)
        self._ap = self._device.get_active_access_point()
        if not self._ap:
            return

        self._ap_signal = self._ap.connect(
            "notify::strength", lambda *args: self.ap_update())  # type: ignore

    def toggle_wifi(self) -> None:
        """Toggle the wifi connection."""
        self._client.wireless_set_enabled(
            not self._client.wireless_get_enabled())

    def scan(self) -> None:
        """Request a scan for available WiFi access points."""
        self._device.request_scan_async(
            None,
            lambda device, result: [
                device.request_scan_finish(result),
                self.emit("changed"),
            ],
        )

    def notifier(self, name: str, *args: object) -> None:
        """Notify listeners about a change in the wifi state."""
        self.notify(name)
        self.emit("changed")
        return

    @Property(bool, "read-write", default_value=False)
    def enabled(self) -> bool:  # type: ignore
        return bool(self._client.wireless_get_enabled())

    @enabled.setter
    def enabled(self, value: bool):
        self._client.wireless_set_enabled(value)

    @Property(int, "readable")
    def strength(self):
        return self._ap.get_strength() if self._ap else -1

    @Property(str, "readable")
    def icon_name(self):
        if not self._ap:
            return "network-wireless-disabled-symbolic"

        if self.internet == "activated":
            return {
                80: "network-wireless-signal-excellent-symbolic",
                60: "network-wireless-signal-good-symbolic",
                40: "network-wireless-signal-ok-symbolic",
                20: "network-wireless-signal-weak-symbolic",
                00: "network-wireless-signal-none-symbolic",
            }.get(
                min(80, 20 * round(self._ap.get_strength() / 20)),
                "network-wireless-no-route-symbolic",
            )
        if self.internet == "activating":
            return "network-wireless-acquiring-symbolic"

        return "network-wireless-offline-symbolic"

    @Property(int, "readable")
    def frequency(self):
        return self._ap.get_frequency() if self._ap else -1

    @Property(str, "readable")
    def internet(self):
        try:
            if self._device.get_active_connection():
                return {
                    NM.ActiveConnectionState.ACTIVATED: "activated",
                    NM.ActiveConnectionState.ACTIVATING: "activating",
                    NM.ActiveConnectionState.DEACTIVATING: "deactivating",
                    NM.ActiveConnectionState.DEACTIVATED: "deactivated",
                }.get(
                    self._device.get_active_connection().get_state(),
                    "unknown",
                )
        except Exception:
            pass
        return "unknown"

    @Property(object, "readable")
    def access_points(self) -> List[object]:
        points: list[NM.AccessPoint] = self._device.get_access_points()

        def make_ap_dict(ap: NM.AccessPoint):
            return {
                "bssid": ap.get_bssid(),
                "last_seen": ap.get_last_seen(),
                "ssid": (NM.utils_ssid_to_utf8(ap.get_ssid().get_data())
                         if ap.get_ssid() else "Unknown"),
                "active-ap": self._ap,
                "strength": ap.get_strength(),
                "frequency": ap.get_frequency(),
                "icon-name": {
                    80: "network-wireless-signal-excellent-symbolic",
                    60: "network-wireless-signal-good-symbolic",
                    40: "network-wireless-signal-ok-symbolic",
                    20: "network-wireless-signal-weak-symbolic",
                    00: "network-wireless-signal-none-symbolic",
                }.get(
                    min(80, 20 * round(ap.get_strength() / 20)),
                    "network-wireless-no-route-symbolic",
                ),
            }

        return list(map(make_ap_dict, points))

    @Property(str, "readable")
    def ssid(self):
        if not self._ap:
            return "Disconnected"
        ssid = self._ap.get_ssid().get_data()
        return NM.utils_ssid_to_utf8(ssid) if ssid else "Unknown"

    @Property(str, "readable")
    def state(self):
        return {
            NM.DeviceState.UNMANAGED: "unmanaged",
            NM.DeviceState.UNAVAILABLE: "unavailable",
            NM.DeviceState.DISCONNECTED: "disconnected",
            NM.DeviceState.PREPARE: "preparing",
            NM.DeviceState.CONFIG: "configuring",
            NM.DeviceState.NEED_AUTH: "need_auth",
            NM.DeviceState.IP_CONFIG: "ip_config",
            NM.DeviceState.IP_CHECK: "ip_check",
            NM.DeviceState.SECONDARIES: "secondaries",
            NM.DeviceState.ACTIVATED: "activated",
            NM.DeviceState.DEACTIVATING: "deactivating",
            NM.DeviceState.FAILED: "failed",
        }.get(self._device.get_state(), "unknown")


class Ethernet(Service):
    """A service to manage the ethernet connection."""

    @Signal
    def changed(self) -> None:
        ...

    @Signal
    def enabled(self) -> bool:
        ...

    def __init__(self, client: NM.Client, device: NM.DeviceEthernet,
                 **kwargs) -> None:
        super().__init__(**kwargs)
        self._client: NM.Client = client
        self._device: NM.DeviceEthernet = device
        self._state_map = {
            NM.DeviceState.UNKNOWN: "unknown",
            NM.DeviceState.UNMANAGED: "unmanaged",
            NM.DeviceState.UNAVAILABLE: "unavailable",
            NM.DeviceState.DISCONNECTED: "disconnected",
            NM.DeviceState.PREPARE: "preparing",
            NM.DeviceState.CONFIG: "configuring",
            NM.DeviceState.NEED_AUTH: "need-auth",
            NM.DeviceState.IP_CONFIG: "ip-config",
            NM.DeviceState.IP_CHECK: "ip-check",
            NM.DeviceState.SECONDARIES: "secondaries",
            NM.DeviceState.ACTIVATED: "activated",
            NM.DeviceState.DEACTIVATING: "deactivating",
            NM.DeviceState.FAILED: "failed",
        }

        for pn in (
                "active-connection",
                "icon-name",
                "speed",
                "state",
        ):
            self._device.connect(f"notify::{pn}", lambda *_: self.notifier(pn))

    def notifier(self, pn: str) -> None:
        """Notify listeners about a change in the ethernet state."""
        self.notify(pn)
        self.emit("changed")

    @property
    def state(self):
        """Return the current state of the ethernet device."""
        return self._state_map.get(self._device.get_state(), "unknown")

    @property
    def internet(self):
        """Check if the ethernet device has internet connectivity."""
        try:
            if self._device.get_active_connection():
                return {
                    NM.ActiveConnectionState.ACTIVATED: "activated",
                    NM.ActiveConnectionState.ACTIVATING: "activating",
                    NM.ActiveConnectionState.DEACTIVATING: "deactivating",
                    NM.ActiveConnectionState.DEACTIVATED: "deactivated",
                }.get(
                    self._device.get_active_connection().get_state(),
                    "unknown",
                )
        except Exception:
            pass
        return "disconnected"

    @Property(int, "readable")
    def speed(self) -> int:
        return self._device.get_speed()

    @Property(str, "readable")
    def active_interface(self):
        if self._device.get_active_connection():
            conn = self._device.get_active_connection().get_connection()
            if conn:
                s_conn = conn.get_setting_connection()
                if s_conn:
                    return s_conn.get_id()
        return "Disconnected"

    @Property(tuple[str, ...], "readable")
    def interfaces(self):
        return [
            d.get_iface()
            for d in self._client.get_devices()
            if d.get_type_description() == "ethernet"
        ]

    def connect_to_interface(self, interface: str) -> str:
        """Connect to a specific ethernet interface."""
        if interface not in self.interfaces:
            raise ValueError(
                f"The interface {interface} does not seem to exist!")
        res = exec_shell_command(f"nmcli device connect {interface}")
        return res


class NetworkClient(Service):
    """A service to manage the network connections."""

    @Signal
    def device_ready(self) -> None:
        ...

    @Signal
    def ethernet_changed(self) -> None:
        ...

    @Signal
    def wifi_changed(self) -> None:
        ...

    def __init__(self):
        super().__init__()
        self._client = None
        self.ethernet_device = None
        self.wifi_device = None

        # Initialize NetworkManager client
        try:
            self._client = NM.Client.new(None)
            self._init_devices()
            self.emit("device-ready")
        except Exception as e:
            logger.error(f"Failed to initialize NetworkManager client: {e}")

    def _init_devices(self) -> None:
        """Initialize network devices."""
        if not self._client:
            return

        # Look for ethernet devices
        for device in self._client.get_devices():
            if device.get_device_type() == NM.DeviceType.ETHERNET:
                self.ethernet_device = Ethernet(self._client, device)
                # Connect state change signal
                device.connect("state-changed", self._on_ethernet_state_changed)

                # Also connect to property changes
                if device.get_active_connection():
                    device.get_active_connection().connect(
                        "notify::state",
                        lambda *args: self.emit("ethernet-changed"))
                break

        # Look for WiFi devices
        for device in self._client.get_devices():
            if device.get_device_type() == NM.DeviceType.WIFI:
                self.wifi_device = Wifi(self._client, device)
                # Connect state change signal
                device.connect("state-changed", self._on_wifi_state_changed)
                break

    def _init_network_client(self, client: NM.Client, task: Gio.Task, **kwargs):
        self._client = client
        wifi_device: NM.DeviceWifi | None = self._get_device(
            NM.DeviceType.WIFI)  # type: ignore
        ethernet_device: NM.DeviceEthernet | None = self._get_device(
            NM.DeviceType.ETHERNET)

        if wifi_device:
            self.wifi_device = Wifi(self._client, wifi_device)
            self.emit("device-ready")

        if ethernet_device:
            self.ethernet_device = Ethernet(client=self._client,
                                            device=ethernet_device)
            self.emit("device-ready")

        self.notify("primary-device")

    def _on_ethernet_state_changed(self, device, new_state, old_state, reason):
        """Handle ethernet device state changes."""
        if self.ethernet_device:
            # Update the active connection watcher if needed
            if device.get_active_connection():
                device.get_active_connection().connect(
                    "notify::state",
                    lambda *args: self.emit("ethernet-changed"))

        # Emit the signal to notify listeners
        self.emit("ethernet-changed")

    def _on_wifi_state_changed(self, device, new_state, old_state, reason):
        """Handle WiFi device state changes."""
        self.emit("wifi-changed")

    def _get_device(self, device_type) -> Any:
        devices: List[NM.Device] = self._client.get_devices()  # type: ignore
        for device in devices:
            if device.get_device_type() == device_type:
                return device
        return None

    def _get_primary_device(self) -> Literal["wifi", "wired"] | None:
        if not self._client or not self._client.get_primary_connection():
            return None

        conn_type = self._client.get_primary_connection().get_connection_type()
        if "wireless" in str(conn_type):
            return "wifi"
        elif "ethernet" in str(conn_type):
            return "wired"
        return None

    def connect_wifi_bssid(self, bssid):
        # We are using nmcli here, idk im lazy
        exec_shell_command_async(f"nmcli device wifi connect {bssid}",
                                 lambda *args: logger.debug(args))

    @Property(str, "readable")
    def primary_device(self) -> Literal["wifi", "wired"] | None:
        return self._get_primary_device()

    def get_wired_connections(self):
        """Get available wired connection profiles."""
        if not self._client or not self.ethernet_device:
            return []

        connections = []
        active_connection = None

        if self.ethernet_device._device.get_active_connection():
            active_connection = self.ethernet_device._device.get_active_connection(
            )

        # Get all connection profiles
        for conn in self._client.get_connections():
            # Filter for ethernet connections
            s_conn = conn.get_setting_connection()
            if not s_conn:
                continue

            if s_conn.get_connection_type() == "802-3-ethernet":
                is_active = False
                if active_connection and active_connection.get_connection(
                ) == conn:
                    is_active = True

                connections.append({
                    "uuid": s_conn.get_uuid(),
                    "id": s_conn.get_id(),
                    "name": s_conn.get_id(),
                    "active": is_active,
                })

        return connections

    def activate_connection(self, uuid: str) -> bool:
        """Activate a connection by UUID."""
        if not self._client:
            return False

        try:
            # Find the connection by UUID
            connection = None
            for conn in self._client.get_connections():
                s_conn = conn.get_setting_connection()
                if s_conn and s_conn.get_uuid() == uuid:
                    connection = conn
                    break

            if connection:
                self._client.activate_connection_async(
                    connection,
                    None,
                    None,
                    None,  # No cancellable
                    lambda client, result: self._on_connection_activated(
                        client, result, uuid),
                )
                return True
        except Exception as e:
            logger.error(f"Failed to activate connection: {e}")

        return False

    def _on_connection_activated(self, client, result, uuid):
        """Callback when a connection activation has completed."""
        try:
            active_conn = client.activate_connection_finish(result)
            # Emit signal to update UI
            self.emit("ethernet-changed")
        except Exception as e:
            logger.error(f"Error activating connection {uuid}: {e}")

    def toggle_wired(self):
        """Toggle the ethernet connection."""
        if self.ethernet_device:
            device = self.ethernet_device._device
            current_state = device.get_state()

            if current_state == NM.DeviceState.ACTIVATED:
                # Disable the device (disconnect)
                device.disconnect(None)
            else:
                # Enable the device (connect to available connection)
                connections = self.get_wired_connections()
                if connections:
                    # Connect to the first available connection
                    self.activate_connection(connections[0]["uuid"])
