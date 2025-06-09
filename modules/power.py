from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.utils import exec_shell_command_async
import modules.icons as icons
from fabric.widgets.revealer import Revealer
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.wayland import WaylandWindow
from gi.repository import GLib, Gdk


class PowerConfirmDialog(WaylandWindow):

    def __init__(self, action_name, action_icon, command, **kwargs):
        super().__init__(
            layer="overlay",
            anchor="center",
            exclusivity="exclusive",  # Make it modal
            visible=False,
            keyboard_mode="exclusive",
            margin="0",
            name="power-confirm-dialog",
            **kwargs,
        )

        self.command = command

        # Main container
        self.main_box = Box(
            name="power-confirm-box",
            orientation="v",
            spacing=16,
            h_align="center",
            v_align="center",
            margin=24,
        )

        # Header with icon and action name
        self.header = Box(
            name="power-confirm-header",
            orientation="v",
            spacing=12,
            h_align="center",
            children=[
                Label(name="confirm-icon", markup=action_icon),
                Label(name="confirm-title", label=f"{action_name}?"),
            ],
        )

        # Message
        self.message = Label(
            name="confirm-message",
            label=f"Are you sure you want to {action_name.lower()}?",
            h_align="center",
        )

        # Buttons
        self.button_box = Box(
            name="power-confirm-buttons",
            orientation="h",
            spacing=12,
            h_align="center",
            margin_top=16,
        )

        self.cancel_button = Button(
            name="confirm-cancel-button",
            child=Label(label="Cancel"),
            on_clicked=self.on_cancel,
            can_focus=True,  # Make sure it can receive focus
        )

        self.confirm_button = Button(
            name="confirm-ok-button",
            child=Label(label=action_name),
            on_clicked=self.on_confirm,
            can_focus=True,  # Make sure it can receive focus
        )

        self.button_box.add(self.cancel_button)
        self.button_box.add(self.confirm_button)

        # Add all elements to main container
        self.main_box.add(self.header)
        self.main_box.add(self.message)
        self.main_box.add(self.button_box)

        self.add(self.main_box)

        # Set up keyboard handling for Escape and Enter keys
        self.connect("key-press-event", self.on_key_press)

        # Set up click outside handling
        self.connect("button-press-event", self.on_button_press)

        # Make dialog focusable
        self.set_accept_focus(True)

        # Connect to the map event to set focus when the dialog appears
        self.connect("map", self.on_map)

    def on_map(self, widget):
        """Set initial focus to the cancel button when dialog is displayed"""
        GLib.timeout_add(50, lambda: self.cancel_button.grab_focus())
        return False

    def on_cancel(self, button):
        """Cancel the action and close the dialog"""
        self.hide()

    def on_confirm(self, button):
        """Execute the command and close the dialog"""
        self.hide()
        exec_shell_command_async(self.command)

    def on_key_press(self, widget, event):
        """Handle keyboard navigation"""
        keyval = event.get_keyval()[1]

        # Close on Escape key
        if keyval == Gdk.KEY_Escape:
            self.hide()
            return True

        # Activate focused button on Enter
        elif keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            # Find which button has focus and activate it
            if self.cancel_button.has_focus():
                self.on_cancel(self.cancel_button)
                return True
            elif self.confirm_button.has_focus():
                self.on_confirm(self.confirm_button)
                return True

        # Let Tab navigation work normally
        return False

    def on_button_press(self, widget, event):
        """Check if click is outside our content area"""
        # Get position and size of our content
        alloc = self.main_box.get_allocation()

        # Get click coordinates relative to window
        x, y = event.get_coords()

        # If click is outside content area, close dialog
        if (x < alloc.x or x > alloc.x + alloc.width or y < alloc.y or
                y > alloc.y + alloc.height):
            self.hide()

        return False


class PowerMenuActions(Revealer):

    def __init__(self, **kwargs):
        super().__init__(
            name="power-options-revealer",
            transition_type="slide-down",
            child_revealed=False,
            transition_duration=250,
            **kwargs,
        )

        self.revealed = False
        self.main_box = Box(
            name="power-options-container",
            orientation="v",
            spacing=8,
            h_align="fill",
            v_align="fill",
        )

        self.actions = [
            {
                "label": "Logout",
                "icon": icons.logout,
                "command": "hyprctl dispatch exit",
            },
            {
                "label": "Reboot",
                "icon": icons.reboot,
                "command": "systemctl reboot"
            },
            {
                "label": "Shutdown",
                "icon": icons.shutdown,
                "command": "systemctl poweroff",
            },
        ]

        # Store dialog references
        self.dialogs = {}

        for action in self.actions:
            button = Button(
                name="power-option-button",
                child=Box(
                    orientation="h",
                    spacing=8,
                    children=[
                        Label(name="option-icon", markup=action["icon"]),
                        Label(name="option-label", label=action["label"]),
                    ],
                ),
                on_clicked=lambda b, a=action: self.show_confirmation(a),
            )
            self.main_box.add(button)

        self.add(self.main_box)

    def show_confirmation(self, action):
        """Show confirmation dialog for the selected action"""
        # Hide the power menu first
        self.toggle_visibility()

        # Create dialog if it doesn't exist yet
        action_key = action["label"].lower()
        if action_key not in self.dialogs:
            self.dialogs[action_key] = PowerConfirmDialog(
                action["label"], action["icon"], action["command"])

        # Show the dialog
        dialog = self.dialogs[action_key]
        dialog.show_all()

        # Make sure it has focus
        GLib.timeout_add(50, lambda: dialog.present())

    def toggle_visibility(self):
        """Toggle the visibility of the power menu actions."""
        if self.revealed:
            self.unreveal()
        else:
            self.reveal()

        self.revealed = not self.revealed


class PowerMenuButton(Box):

    def __init__(self, power_actions=None, **kwargs):
        super().__init__(
            name="power-menu-container",
            orientation="h",
            spacing=4,
            v_align="center",
            h_align="center",
            visible=True,
            **kwargs,
        )

        # Reference to the PowerMenuActions instance
        self.power_actions = power_actions

        # Main power button
        self.power_button = Button(
            child=Label(name="button-label", markup=icons.shutdown),
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
            style_classes=['settings-action-button'],
        )

        # Add the button to our container
        self.add(self.power_button)

        # Connect button to toggle dropdown
        self.power_button.connect("clicked", self.toggle_power_menu)

    def toggle_power_menu(self, *_):
        if self.power_actions:
            self.power_actions.toggle_visibility()
