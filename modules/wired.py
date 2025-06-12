import gi

gi.require_version("Gtk", "3.0")
gi.require_version("NM", "1.0")
from gi.repository import GLib, NM
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.revealer import Revealer
from fabric.widgets.scrolledwindow import ScrolledWindow
import modules.icons as icons
from services.network import NetworkClient


class WiredConnectionSlot(Box):

    def __init__(self, connection_data, network_service: NetworkClient,
                 **kwargs):
        super().__init__(name="wired-connection-slot", spacing=8, **kwargs)
        self.connection_data = connection_data
        self.network_service = network_service

        # Create UI elements
        conn_name = connection_data.get("name", "Unknown connection")
        self.is_active = connection_data.get("active", False)

        self.connection_label = Label(label=conn_name,
                                      style_classes=["wired-connection-label"],
                                      h_expand=True,
                                      h_align="start",
                                      ellipsization="end")

        self.add(
            Box(
                spacing=8,
                h_expand=True,
                h_align="fill",
                children=[
                    Label(name="wired-connection-icon", markup=icons.ethernet),
                    self.connection_label,
                ],
            ))
        self.connect_button = Button(
            name="wired-connect-button",
            label="Connected" if self.is_active else "Connect",
            sensitive=not self.is_active,
            on_clicked=self._on_connect_clicked,
            style_classes=["connected"] if self.is_active else None,
        )
        self.add(self.connect_button)

    def _on_connect_clicked(self, _):
        if not self.is_active and self.connection_data.get("uuid"):
            self.connect_button.set_label("Connecting...")
            self.connect_button.set_sensitive(False)
            self.network_service.activate_connection(
                self.connection_data["uuid"])

    def update_active_status(self, is_active):
        """Update the slot to reflect its current active state"""
        self.is_active = is_active
        self.connect_button.set_sensitive(not is_active)

        if is_active:
            self.connect_button.set_label("Connected")
            self.connect_button.add_style_class("connected")
        else:
            self.connect_button.set_label("Connect")
            self.connect_button.remove_style_class("connected")


class WiredNetworksDropdown(Revealer):

    def __init__(self, labels, **kwargs):
        super().__init__(
            name="wired-connections-dropdown",
            transition_type="slide-down",
            child_revealed=False,
            h_expand=True,
            transition_duration=250,
            **kwargs,
        )

        self.shown = False
        self.connection_slots = {}
        self.labels = labels
        self.wired_status_text = self.labels["wired_status_text"]
        self.wired_button = self.labels["wired_button"]
        self.wired_icon = self.labels["wired_icon"]
        self.network_client = NetworkClient()

        self.main_box = Box(
            name="wired-connections-box",
            orientation="v",
            h_expand=True,
            v_expand=True,
            spacing=4,
        )

        self.status_label = Label(
            name="wired-networks-title",
            label="Initializing Ethernet...",
            h_expand=True,
            h_align="center",
        )

        header_box = CenterBox(
            name="wired-networks-header",
            start_children=[
                Label(name="network-title", label="Wired Connections")
            ],
            end_children=[],
        )

        self.connections_list_box = Box(orientation="vertical", spacing=4)
        scrolled_window = ScrolledWindow(
            name="wired-connections-scrolled-window",
            child=self.connections_list_box,
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
        """Toggle the visibility of the wired networks dropdown."""
        if (not self.network_client.ethernet_device or
                self.network_client.ethernet_device._device.get_state()
                != NM.DeviceState.ACTIVATED):
            return
        self.shown = not self.shown
        self.set_reveal_child(self.shown)

        if self.shown:
            self._load_connections()

    def _on_device_ready(self, _client):
        if self.network_client.ethernet_device:
            self.network_client.ethernet_device.connect("changed",
                                                        self._load_connections)
            self._update_wired_status_ui()
            self._load_connections()
            self.wired_button.remove_style_class("disabled")
        else:
            self.status_label.set_label("Wired device not available.")
            self.wired_button.set_label("Not available")
            self.wired_button.add_style_class("disabled")

    def _update_wired_status_ui(self, *args):
        if self.network_client.ethernet_device:
            state = self.network_client.ethernet_device.state

            # Get active connection name
            connection_name = "Ethernet"
            active_connection = None

            if self.network_client.ethernet_device._device.get_active_connection(
            ):
                active_connection = (self.network_client.ethernet_device.
                                     _device.get_active_connection())
                if active_connection:
                    conn = active_connection.get_connection()
                    if conn:
                        s_conn = conn.get_setting_connection()
                        if s_conn:
                            connection_name = s_conn.get_id()

            # Handle all possible states
            self.wired_button.remove_style_class("disabled")
            if state == "activated":
                self.wired_icon.set_markup(icons.ethernet)
                self.wired_status_text.set_label(connection_name)
            elif state == "disconnected":
                self.wired_icon.set_markup(icons.ethernet_off)
                self.wired_button.add_style_class("disabled")
                self.wired_status_text.set_label("Disconnected")
            # Handle transitional states specially
            elif state in ["preparing", "configuring", "ip-config", "ip-check"]:
                self.wired_icon.set_markup(icons.ethernet)
                self.wired_status_text.set_label(f"Connecting... ({state})")
            else:
                self.wired_icon.set_markup(icons.ethernet_off)
                self.wired_button.add_style_class("disabled")
                self.wired_status_text.set_label(state.capitalize())
        else:
            self.wired_icon.set_markup(icons.ethernet_off)
            self.wired_button.add_style_class("disabled")
            self.wired_status_text.set_label("Unavailable")

    def toggle_wired(self, *args):
        """Enable or disable the wired connection"""
        if self.network_client.ethernet_device:
            device = self.network_client.ethernet_device._device
            current_state = device.get_state()

            self.wired_button.add_style_class("disabled")
            if current_state == NM.DeviceState.ACTIVATED:
                # Disable the device (disconnect)
                device.disconnect(None)
                self.wired_status_text.set_label("Disconnecting...")
                self.wired_icon.set_markup(icons.ethernet_off)
            else:
                # Enable the device (connect to available connection)
                connections = self.network_client.get_wired_connections()
                if connections:
                    # Connect to the first available connection
                    self.network_client.activate_connection(
                        connections[0]["uuid"])
                    self.wired_status_text.set_label("Connecting...")
                    self.wired_icon.set_markup(icons.ethernet)
                    self.wired_button.remove_style_class("disabled")
                else:
                    # No connection profiles available
                    self.wired_status_text.set_label("No profiles")

    def _clear_connections_list(self):
        for child in self.connections_list_box.get_children():
            child.destroy()

    def _load_connections(self, *args):
        if not self.network_client.ethernet_device:
            self._clear_connections_list()
            self.status_label.set_label("Wired device not available.")
            return

        self._clear_connections_list()
        self._update_wired_status_ui()

        # Clear the connection slots dictionary
        self.connection_slots = {}

        # Get available wired connections from NetworkManager
        connections = self.network_client.get_wired_connections()

        if not connections:
            self.status_label.set_label("No wired connections available.")
        else:
            self.status_label.set_label(
                f"{len(connections)} wired connections available:")

            for conn_data in connections:
                slot = WiredConnectionSlot(conn_data, self.network_client)
                self.connections_list_box.add(slot)
                # Store the slot reference by UUID
                self.connection_slots[conn_data["uuid"]] = slot

        self.connections_list_box.show_all()


class Wired(Box):

    def __init__(self, slot, **kwargs):
        super().__init__(
            name="network-connections",
            h_expand=True,
            v_expand=True,
            spacing=4,
            orientation="h",
            **kwargs,
        )
        self.slot = slot
        self.network_client = NetworkClient()
        self.left_button_childs = Box(
            name="wired-left-button-childs",
            orientation="h",
            spacing=8,
        )
        self.left_button = Button(
            name="wired-left-button",
            h_expand=True,
            child=self.left_button_childs,
        )
        self.wired_status_text = Label(
            name="wired-status",
            label="Ethernet",
            all_visible=True,
            visible=True,
            h_align="start",
            ellipsization="end",
        )
        self.wired_icon = Label(name="wired-icon", markup=icons.ethernet_off)
        self.wired_networks_open_button = Button(
            style_classes=["expand-button-caret"],
            child=Label(name="wired-open-label", markup=icons.chevron_right),
        )

        self.labels = dict()
        self.labels["wired_button"] = self.left_button
        self.labels["wired_status_text"] = self.wired_status_text
        self.labels["wired_icon"] = self.wired_icon
        self.wired_networks_dropdown = WiredNetworksDropdown(labels=self.labels)
        self.slot.add(self.wired_networks_dropdown)

        # Set up the UI elements
        self.left_button_childs.add(self.wired_icon)
        self.left_button_childs.add(
            Box(
                orientation="v",
                h_align="start",
                v_align="center",
                children=[
                    Label(
                        label="Wired",
                        name="wired-button-label",
                        h_align="start",
                    ),
                    self.wired_status_text,
                ],
            )
        )
        self.add(self.left_button)
        self.add(self.wired_networks_open_button)

        # Connect signals
        self.wired_networks_open_button.connect(
            "clicked",
            lambda *_: self.wired_networks_dropdown.toggle_visibility())

        # Update left button to toggle ethernet connection
        self.left_button.connect(
            "clicked", lambda *_: self.wired_networks_dropdown.toggle_wired())

        # Connect to ethernet-changed signal to update UI when status changes
        # Uncomment this line - it's important for updates
        self.network_client.connect("ethernet-changed",
                                    self._on_ethernet_changed)

        # Connect to device-ready signal to initialize UI immediately
        self.network_client.connect("device-ready", self._on_device_ready)

        # IMPORTANT: Check if device is already available and update immediately
        if self.network_client.ethernet_device:
            GLib.idle_add(lambda: self._on_device_ready(self.network_client))

        # Add a fallback timer to update state after a short delay
        GLib.timeout_add(500, self._check_initial_state)

        self._update_connection_name()

        # Connect to connection changes
        if self.network_client._client:
            self.network_client._client.connect(
                "connection-added",
                lambda *_: GLib.idle_add(self._refresh_connections))
            self.network_client._client.connect(
                "connection-removed",
                lambda *_: GLib.idle_add(self._refresh_connections),
            )
            # Monitor active connection changes directly
            self.network_client._client.connect(
                "active-connection-added",
                lambda *_: GLib.idle_add(self._update_connection_name),
            )
            self.network_client._client.connect(
                "active-connection-removed",
                lambda *_: GLib.idle_add(self._update_connection_name),
            )

    def _check_initial_state(self):
        """Fallback to ensure wired state is initialized properly"""
        if self.network_client.ethernet_device:
            self._update_connection_name()
        return False  # Run only once

    def _on_device_ready(self, _client):
        """Initialize the UI as soon as devices are ready"""
        # Update UI immediately without waiting for dropdown open
        if self.network_client.ethernet_device:
            # Get connection name immediately
            GLib.idle_add(self._update_connection_name)
            # Also connect to state changes directly from the device
            self.network_client.ethernet_device._device.connect(
                "state-changed",
                lambda *_: GLib.idle_add(self._update_connection_name))
            # Monitor active connection property changes
            self.network_client.ethernet_device._device.connect(
                "notify::active-connection",
                lambda *_: GLib.idle_add(self._update_connection_name),
            )

    def _update_connection_name(self):
        """Update the connection name label directly"""
        if not self.network_client.ethernet_device:
            self.wired_icon.set_markup(icons.ethernet_off)
            self.left_button.add_style_class("disabled")
            self.wired_status_text.set_label("Unavailable")
            return

        state = self.network_client.ethernet_device.state
        connection_name = "Ethernet"

        # Get the active connection name
        if self.network_client.ethernet_device._device.get_active_connection():
            active_connection = (self.network_client.ethernet_device._device.
                                 get_active_connection())
            if active_connection:
                conn = active_connection.get_connection()
                if conn:
                    s_conn = conn.get_setting_connection()
                    if s_conn:
                        connection_name = s_conn.get_id()

        # Update the UI based on state
        self.left_button.remove_style_class("disabled")
        if state == "activated":
            self.wired_icon.set_markup(icons.ethernet)
            self.wired_status_text.set_label(connection_name)
        elif state == "disconnected":
            self.wired_icon.set_markup(icons.ethernet_off)
            self.left_button.add_style_class("disabled")
            self.wired_status_text.set_label("Disconnected")
        elif state in ["preparing", "configuring", "ip-config", "ip-check"]:
            self.wired_icon.set_markup(icons.ethernet)
            self.wired_status_text.set_label(f"Connecting...")
        else:
            self.wired_icon.set_markup(icons.ethernet_off)
            self.left_button.add_style_class("disabled")
            self.wired_status_text.set_label(state.capitalize())
        return False

    def _refresh_connections(self):
        """Refresh the connections list in the dropdown"""
        # Always update the connections list when connections change,
        # even if the dropdown isn't currently visible
        self.wired_networks_dropdown._load_connections()
        # Return False to prevent this from being called again if used with timeout_add
        return False

    def _on_ethernet_changed(self, *args):
        """Handle ethernet state changes"""
        # Make sure we update the UI
        GLib.idle_add(self._update_connection_name)
        GLib.idle_add(self.wired_networks_dropdown._update_wired_status_ui)

        # Update connection list if dropdown is visible
        if self.wired_networks_dropdown.shown:
            GLib.idle_add(self._refresh_connections)
