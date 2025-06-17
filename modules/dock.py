import json
import os
import subprocess

import cairo
from fabric.utils import DesktopApp, get_desktop_applications, monitor_file
from fabric.utils.helpers import exec_shell_command_async
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.eventbox import EventBox
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.revealer import Revealer
from fabric.widgets.wayland import WaylandWindow as Window
from gi.repository import Gdk, GLib, Gtk

import modules.icons as icons
from modules.corners import CornerContainer
from services.config import config
from services.logger import logger

pinned_aps_location = os.path.expanduser(
    f"~/.config/{config.APP_NAME}/config/pinned_apps.json"
)


def createSurfaceFromWidget(widget: Gtk.Widget) -> cairo.ImageSurface:
    alloc = widget.get_allocation()
    surface = cairo.ImageSurface(
        cairo.Format.ARGB32,
        alloc.width,
        alloc.height,
    )
    cr = cairo.Context(surface)
    cr.set_source_rgba(255, 255, 255, 0)
    cr.rectangle(0, 0, alloc.width, alloc.height)
    cr.fill()
    widget.draw(cr)
    return surface

def check_pinned_app_structure(pinned_apps: list[str]) -> bool:
    """
    Check if the pinned apps structure is valid.
    This function can be overridden to implement custom validation logic.
    """
    if not isinstance(pinned_apps, list):
        return False
    for app in pinned_apps:
        if not isinstance(app, str):
            return False
    return True

def save_pinned_apps(pinned_apps: list[str]) -> None:
    """Save the current pinned applications to the file."""
    if not check_pinned_app_structure(pinned_apps):
        logger.error("Malformed pinned apps data, not saving.")
        return
    with open(pinned_aps_location, "w") as f:
        json.dump(pinned_apps, f) 


def load_apps() -> list[str]:
    """
    Load applications from the pinned apps file.
    This method can be overridden to load custom applications.
    """
    if not os.path.exists(pinned_aps_location):
        with open(pinned_aps_location, "w") as f:
            f.write("[]")

    with open(pinned_aps_location, "r") as f:
        pinned_apps = json.load(f)
    if not check_pinned_app_structure(pinned_apps):
        logger.error("Malformed pinned apps file, resetting to default.")
        return []
    return pinned_apps


class DockSettingsApp(Gtk.EventBox):

    def __init__(self, app: DesktopApp, notch, is_first=False, is_last=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = app
        self.notch = notch
        self.is_first = is_first
        self.is_last = is_last

        # Create app icon
        icon = Image(
            pixbuf=self.app.get_icon_pixbuf(size=30),
            h_align="center",
            v_align="center",
        )

        # Create app name label
        self.app_name = Label(
            label=self.app.name,
            h_align="start",
            v_align="center",
            h_expand=True,
        )

        # Create drag handle
        drag_handle = Label(
            markup=icons.drag_handle,  # Or another icon that looks like a drag handle
            h_align="center",
            v_align="center",
        )

        # Create container box
        self.box = Box(
            children=[drag_handle, icon, self.app_name],
            orientation="h",
            spacing=8,
            h_expand=True,
            visible=True,
            style_classes=["dock-app-item"],
        )

        self.add(self.box)
        self.show_all()

        # Setup drag and drop functionality
        self.setup_dnd()

    def setup_dnd(self):
        # Set up drag source (enable dragging from this widget)
        self.drag_source_set(
            Gdk.ModifierType.BUTTON1_MASK,
            [Gtk.TargetEntry.new("text/plain", Gtk.TargetFlags.SAME_APP, 0)],
            Gdk.DragAction.MOVE,
        )

        self.drag_dest_set(
            Gtk.DestDefaults.ALL,
            [Gtk.TargetEntry.new("text/plain", Gtk.TargetFlags.SAME_APP, 0)],
            Gdk.DragAction.MOVE,
        )

        # Connect drag and drop signal handlers
        self.connect("drag-begin", self.on_drag_begin)
        self.connect("drag-data-get", self.on_drag_data_get)
        self.connect("drag-data-received", self.on_drag_data_received)
        self.connect("drag-end", self.on_drag_end)

        # Add visual feedback when dragging
        self.connect("drag-motion", self.on_drag_motion)
        self.connect("drag-leave", self.on_drag_leave)

    def on_drag_begin(self, widget, drag_context):
        # Use the existing utility function to create a surface from the widget
        surface = createSurfaceFromWidget(self)

        # Set the drag icon
        Gtk.drag_set_icon_surface(drag_context, surface)

        # Notify notch that drag has started (if you have a notch reference)
        parent = self.get_parent()
        if hasattr(parent, "notch") and parent.notch:
            parent.notch.start_drag()

        # Add visual feedback
        self.box.add_style_class("dragging")
        self.notch.start_drag()

    def on_drag_data_get(self, widget, context, selection_data, info, time):
        # Provide data for the drag operation - we'll use the app name as identifier
        selection_data.set_text(self.app.name, -1)

    def on_drag_data_received(self, widget, context, x, y, selection_data, info, time):
        # Handle receiving dropped data
        source_app_name = selection_data.get_text()
        target_app_name = self.app.name

        if source_app_name == target_app_name:
            # Dropped on self, do nothing
            context.finish(False, False, time)
            return

        # Get parent and app positions
        parent = self.get_parent()

        source_index = parent.pinned_apps.index(source_app_name)
        target_index = parent.pinned_apps.index(target_app_name)

        # Create a new list for clarity
        new_order = parent.pinned_apps.copy()
        # Remove source app from list
        new_order.remove(source_app_name)

        # Insert source app before or after target based on position
        new_target_index = new_order.index(target_app_name)
        if target_index > source_index:
            # Dragging downward - insert after target
            new_order.insert(new_target_index + 1, source_app_name)
        else:
            # Dragging upward - insert before target
            new_order.insert(new_target_index, source_app_name)

        parent.pinned_apps = new_order
        save_pinned_apps(parent.pinned_apps)
        parent.refresh_ui()
        context.finish(True, False, time)
        self.notch.end_drag()

    def on_drag_end(self, widget, context):
        # Remove visual feedback
        self.box.remove_style_class("dragging")

    def on_drag_motion(self, widget, context, x, y, time):
        # Add visual feedback when dragging over this item
        self.box.add_style_class("drag-hover")
        return True

    def on_drag_leave(self, widget, context, time):
        # Remove visual feedback when drag leaves this item
        self.box.remove_style_class("drag-hover")


class DockSettings(Box):

    def __init__(self, notch=None, *args, **kwargs):
        super().__init__(
            name="dock-settings",
            h_expand=True,
            spacing=8,
            v_expand=True,
            orientation="vertical",
            all_visible=True,
            *args,
            **kwargs,
        )
        self.notch = notch  # Store the notch reference
        self.event_listeners = []
        self.pinned_apps = load_apps()
        self.refresh_ui()
        self.pinned_applications_monitor = monitor_file(pinned_aps_location)
        self.pinned_applications_monitor.connect(
            "changed", self._on_pinned_apps_file_changed
        )

    def update_pinned_apps(self, new_pinned_apps: list[str]) -> None:
        """Update the pinned applications in the dock settings."""
        self.pinned_apps = new_pinned_apps

    def _unpin_application(self, app_name: str) -> None:
        """Unpin an application from the dock."""
        if app_name in self.pinned_apps:
            self.pinned_apps.remove(app_name)
            with open(pinned_aps_location, "w") as f:
                json.dump(self.pinned_apps, f)
            # No need to refresh UI here, as the file change will trigger it

    def _on_pinned_apps_file_changed(self, *_) -> None:
        """Handle changes to the pinned apps file."""
        self.pinned_apps = load_apps()
        self.refresh_ui()

    def refresh_ui(self) -> None:
        """Refresh the UI to reflect the current pinned applications."""
        self.children = []
        for i, app_name in enumerate(self.pinned_apps):
            app = next(
                (a for a in get_desktop_applications() if a.name == app_name), None)
            if app:
                entry = DockSettingsApp(app, notch=self.notch, is_first=i == 0, is_last=i == len(self.pinned_apps) - 1)
                self.add(entry)

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
        margin = f"0 0 {"-54px" if config.BAR_POSITION == "bottom" else 0} 0"
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

        self.pinned_apps = load_apps()
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

    def _on_mouse_enter(self, widget, event) -> bool:
        # Cancel any pending hide operations
        if self.hide_timer is not None:
            GLib.source_remove(self.hide_timer)
            self.hide_timer = None

        if len(self.items_container.children) > 0:
            self._show_dock()
        return True  # Important: consume the event

    def _show_dock(self) -> None:
        """Show the dock with an animation."""
        if (
            not self.is_animating
            and not self.revealer.get_reveal_child()
            and len(self.pinned_apps) > 0
        ):
            self.is_animating = True
            self.revealer.set_reveal_child(True)
            self.animation_timeout = GLib.timeout_add(250, self._animation_done)

    def _animation_done(self) -> bool:
        """Callback for when the animation is done."""
        # Animation is complete, reset flag
        self.is_animating = False
        self.animation_timeout = None
        return False  # Remove the source

    def _hide_dock(self) -> bool:
        """Hide the dock with an animation."""
        if not self.is_animating and self.revealer.get_reveal_child():
            self.is_animating = True
            self.revealer.set_reveal_child(False)
            self.animation_timeout = GLib.timeout_add(250, self._animation_done)
        self.hide_timer = None
        return False  # Remove the source

    def _on_mouse_leave(self, widget, event) -> bool:
        """Handle mouse leave event to start hiding the dock."""
        # Don't start hide timer if still animating
        if self.is_animating:
            return False

        # Start hiding after a delay
        if self.hide_timer is not None:
            GLib.source_remove(self.hide_timer)

        # Use a longer delay to prevent accidental hiding
        self.hide_timer = GLib.timeout_add(500, self._hide_dock)
        return True

    def check_running_apps(self) -> bool:
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
        """ Add a single application to the dock."""
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

    def _on_pinned_apps_file_changed(self, *_) -> None:
        """Handle changes to the pinned apps file."""
        self.pinned_apps = load_apps()
        self._add_applications()

    def _add_applications(self, *_) -> None:
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

        # Add a settings button to the dock that opens the dock settings widget
        settings_button = Button(
            child=Label(markup=icons.grid_dots, size=30, style="font-size: 30px;"),
            h_align="center",
            v_align="center",
            style_classes=["dock-item"],
            tooltip_text="Dock Settings",
            on_clicked=lambda *_: exec_shell_command_async(
                f"fabric-cli exec {config.APP_NAME} 'notch.show_widget(\"dock-settings\", False)'"
            ),
        )
        self.items_container.add(settings_button)
