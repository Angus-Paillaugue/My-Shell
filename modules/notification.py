import json
import locale
import os
import uuid
from datetime import datetime, timedelta
from typing import Callable

from fabric.notifications.service import (Notification, NotificationAction,
                                          Notifications)
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.revealer import Revealer
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.wayland import WaylandWindow
from gi.repository import GdkPixbuf, GLib, Gtk  # type: ignore

import modules.icons as icons
from services.config import config
from services.logger import logger

PERSISTENT_DIR = f"/tmp/{config.APP_NAME}/notifications"
PERSISTENT_HISTORY_FILE = os.path.join(PERSISTENT_DIR,
                                       "notification_history.json")
MAX_VISIBLE_NOTIFICATIONS = 3


def cache_notification_pixbuf(notification_box):
    """
    Saves a scaled pixbuf (48x48) in the cache directory and returns the cache file path.
    """
    notification = notification_box.notification
    if notification.image_pixbuf:
        os.makedirs(PERSISTENT_DIR, exist_ok=True)
        cache_file = os.path.join(PERSISTENT_DIR,
                                  f"notification_{notification_box.uuid}.png")
        logger.debug(
            f"Caching image for notification {notification.id} to: {cache_file}"
        )
        try:
            scaled_pixbuf = notification.image_pixbuf.scale_simple(
                48, 48, GdkPixbuf.InterpType.BILINEAR)
            scaled_pixbuf.savev(cache_file, "png", [], [])
            notification_box.cached_image_path = cache_file
            return cache_file
        except Exception as e:
            logger.error(f"Failed to cache notification image: {e}")
            return None
    else:
        logger.debug(
            f"Notification {notification.id} has no image_pixbuf to cache.")
        return None


def load_scaled_pixbuf(notification_box, width, height):
    """
    Loads and scales a pixbuf for a notification_box, prioritizing cached images.
    """
    notification = notification_box.notification
    if not hasattr(notification_box, "notification") or notification is None:
        logger.error(
            "load_scaled_pixbuf: notification_box.notification is None or not set!"
        )
        return None

    pixbuf = None
    if (hasattr(notification_box, "cached_image_path") and
            notification_box.cached_image_path and
            os.path.exists(notification_box.cached_image_path)):
        try:
            logger.debug(
                f"Attempting to load cached image from: {notification_box.cached_image_path} for notification {notification.id}"
            )
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(
                notification_box.cached_image_path)
            if pixbuf:
                pixbuf = pixbuf.scale_simple(width, height,
                                             GdkPixbuf.InterpType.BILINEAR)
                logger.info(
                    f"Successfully loaded cached image from: {notification_box.cached_image_path} for notification {notification.id}"
                )
            return pixbuf
        except Exception as e:
            logger.error(
                f"Error loading cached image from {notification_box.cached_image_path} for notification {notification.id}: {e}"
            )
            logger.warning(
                f"Falling back to notification.image_pixbuf for notification {notification.id}"
            )

    if notification.image_pixbuf:
        logger.debug(
            f"Loading image directly from notification.image_pixbuf for notification {notification.id}"
        )
        pixbuf = notification.image_pixbuf.scale_simple(
            width, height, GdkPixbuf.InterpType.BILINEAR)
        return pixbuf

    logger.debug(
        f"No image_pixbuf or cached image found, trying app icon for notification {notification.id}"
    )
    return get_app_icon_pixbuf(notification.app_icon, width, height)


def get_app_icon_pixbuf(icon_path, width, height):
    """
    Loads and scales a pixbuf from an app icon path.
    """
    if not icon_path:
        return None
    if icon_path.startswith("file://"):
        icon_path = icon_path[7:]
    if not os.path.exists(icon_path):
        logger.warning(f"Icon path does not exist: {icon_path}")
        return None
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_path)
        return pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
    except Exception as e:
        logger.error(f"Failed to load or scale icon: {e}")
        return None


class ActionButton(Button):

    def __init__(self, action: NotificationAction, index: int, total: int,
                 notification_box):
        super().__init__(
            name="action-button",
            h_expand=True,
            on_clicked=self.on_clicked,
            child=Label(
                name="button-label",
                h_expand=True,
                h_align="fill",
                ellipsization="end",
                max_chars_width=1,
                label=action.label,
            ),
        )
        self.action = action
        self.notification_box = notification_box
        style_class = ("start-action" if index == 0 else
                       "end-action" if index == total - 1 else "middle-action")
        self.add_style_class(style_class)
        self.connect("enter-notify-event",
                     lambda *_: notification_box.hover_button(self))
        self.connect("leave-notify-event",
                     lambda *_: notification_box.unhover_button(self))

    def on_clicked(self, *_):
        self.action.invoke()
        self.action.parent.close("dismissed-by-user")


class NotificationBox(Box):

    def __init__(self, notification: Notification, timeout_ms=5000, **kwargs):
        super().__init__(
            name="notification-box",
            orientation="v",
            h_align="fill",
            h_expand=True,
            children=[],
        )
        self.labels_length = 30
        self.max_lines = 5
        self.notification = notification
        self.uuid = str(uuid.uuid4())
        self.timeout_ms = timeout_ms if timeout_ms >= 0 else 5000

        self._timeout_id = None
        self._container = None
        self.cached_image_path = None

        # Add entry animation style class
        self.add_style_class("notification-entering")

        # Schedule animation to visible state
        GLib.timeout_add(50, self._animate_to_visible)

        if self.timeout_ms > 0:
            self._timeout_id = GLib.timeout_add(self.timeout_ms,
                                                self.close_notification)

        if self.notification.image_pixbuf:
            cache_notification_pixbuf(self)
        else:
            logger.debug(
                f"Notification {notification.id} has no image_pixbuf to cache.")

        content = self.create_content()
        action_buttons = self.create_action_buttons()
        self.add(content)
        if action_buttons:
            self.add(action_buttons)

        self.connect("enter-notify-event", self.on_hover_enter)
        self.connect("leave-notify-event", self.on_hover_leave)

        self._destroyed = False
        self._is_history = False
        logger.debug(
            f"NotificationBox {self.uuid} created for notification {notification.id}"
        )

    def _animate_to_visible(self):
        self.remove_style_class("notification-entering")
        self.add_style_class("notification-visible")
        return False

    def set_is_history(self, is_history):
        self._is_history = is_history

    def set_container(self, container):
        self._container = container

    def get_container(self):
        return self._container

    def close_notification(self):
        if not self._destroyed:
            # Add exit animation
            self.remove_style_class("notification-visible")
            self.add_style_class("notification-exiting")

            # Wait for animation to complete before closing
            GLib.timeout_add(250, self._do_close_notification)
        return False

    def _do_close_notification(self):
        if not self._destroyed and hasattr(self, "notification"):
            self.notification.close("expired")
        return False

    def destroy(self, from_history_delete=False):
        logger.debug(
            f"NotificationBox destroy called for notification: {self.notification.id}, from_history_delete: {from_history_delete}, is_history: {self._is_history}"
        )
        if (hasattr(self, "cached_image_path") and self.cached_image_path and
                os.path.exists(self.cached_image_path) and
            (not self._is_history or from_history_delete)):
            try:
                os.unlink(self.cached_image_path)
                logger.debug(f"Deleted cached image: {self.cached_image_path}")
            except Exception as e:
                logger.error(f"Failed to delete cached image: {e}")
        self._destroyed = True
        self.stop_timeout()
        super().destroy()

    def create_header(self):
        notification = self.notification
        self.app_icon_image = (Image(
            name="notification-icon",
            image_file=notification.app_icon[7:],
            size=24,
        ) if "file://" in notification.app_icon else Image(
            name="notification-icon",
            icon_name="dialog-information-symbolic" or notification.app_icon,
            icon_size=24,
        ))
        self.app_name_label_header = Label(
            notification.app_name, name="notification-app-name", h_align="start"
        )
        self.header_close_button = self.create_close_button()

        return CenterBox(
            name="notification-title",
            start_children=[
                Box(
                    spacing=4,
                    children=[
                        self.app_icon_image,
                        self.app_name_label_header,
                    ],
                )
            ],
            end_children=[self.header_close_button],
        )

    def create_content(self):
        notification = self.notification
        pixbuf = load_scaled_pixbuf(self, 48, 48)
        self.notification_image_box = Box(
            name="notification-image",
            orientation="v",
            children=[Image(pixbuf=pixbuf),
                      Box(v_expand=True)],
        )
        notification_text_labels = []
        for i, text in enumerate(notification.summary[0 + j:self.labels_length +
                                                      j]
                                 for j in range(0, len(notification.summary),
                                                self.labels_length)):
            if i == self.max_lines - 1 and len(
                    notification.summary) > self.labels_length * self.max_lines:
                text = text[:self.labels_length - 3] + "..."
            if i >= self.max_lines:
                break
            label = Label(
                name="notification-summary",
                markup=text.strip(),
                h_align="start",
            )
            notification_text_labels.append(label)
        self.notification_summary_label = Box(orientation="v",
                                              children=notification_text_labels)
        self.notification.app_name_label_content = Label(
            name="notification-app-name",
            markup=notification.app_name,
            h_align="start",
            max_chars_width=25,
            ellipsization="end",
        )
        self.notification_body_label = (Label(
            markup=notification.body,
            h_align="start",
            max_chars_width=34,
            ellipsization="end",
        ) if notification.body else Box())
        (self.notification_body_label.set_single_line_mode(True)
         if notification.body else None)
        self.notification_text_box = Box(
            name="notification-text",
            orientation="v",
            v_align="center",
            h_expand=True,
            h_align="start",
            children=[
                Box(
                    name="notification-summary-box",
                    orientation="v",
                    children=[
                        self.notification.app_name_label_content,
                        self.notification_summary_label,
                        # Box(
                        #     name="notif-sep",
                        #     h_expand=False,
                        #     v_expand=False,
                        #     h_align="center",
                        #     v_align="center",
                        # ),
                    ],
                ),
                self.notification_body_label,
            ],
        )
        self.content_close_button = self.create_close_button()
        self.content_close_button_box = Box(
            orientation="v",
            children=[
                self.content_close_button,
            ],
        )

        return Box(
            name="notification-content",
            spacing=8,
            children=[
                self.notification_image_box if pixbuf else Box(h_expand=False),
                self.notification_text_box,
                self.content_close_button_box,
            ],
        )

    def create_action_buttons(self):
        notification = self.notification
        if not notification.actions:
            return None

        grid = Gtk.Grid()
        grid.set_column_homogeneous(True)
        grid.set_column_spacing(4)
        for i, action in enumerate(notification.actions):
            action_button = ActionButton(action, i, len(notification.actions),
                                         self)
            grid.attach(action_button, i, 0, 1, 1)
        return grid

    def create_close_button(self):
        self.close_button = Button(
            name="notif-close-button",
            child=Label(name="notif-close-label", markup=icons.cancel),
            on_clicked=lambda *_: self.notification.close("dismissed-by-user"),
        )
        self.close_button.connect(
            "enter-notify-event",
            lambda *_: self.hover_button(self.close_button))
        self.close_button.connect(
            "leave-notify-event",
            lambda *_: self.unhover_button(self.close_button))
        return self.close_button

    def on_hover_enter(self, *args):
        if self._container:
            self._container.pause_and_reset_all_timeouts()

    def on_hover_leave(self, *args):
        if self._container:
            self._container.resume_all_timeouts()

    def start_timeout(self):
        self.stop_timeout()
        self._timeout_id = GLib.timeout_add(self.timeout_ms,
                                            self.close_notification)

    def stop_timeout(self):
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None

    def hover_button(self, button):
        if self._container:
            self._container.pause_and_reset_all_timeouts()

    def unhover_button(self, button):
        if self._container:
            self._container.resume_all_timeouts()


class HistoricalNotification(object):
    def __init__(self,
                 id,
                 app_icon,
                 summary,
                 body,
                 app_name,
                 timestamp,
                 cached_image_path=None):
        self.id = id
        self.app_icon = app_icon
        self.summary = summary
        self.body = body
        self.app_name = app_name
        self.timestamp = timestamp
        self.cached_image_path = cached_image_path
        self.image_pixbuf = None
        self.actions = []
        self.cached_scaled_pixbuf = None


class NotificationHistory(Box):
    """Widget that displays the notification history with options to clear and manage notifications."""

    def __init__(self,
                 notification_server: Notifications,
                 on_event:Callable | None = None,
                 **kwargs):
        super().__init__(name="notification-history",
                         orientation="v",
                         h_expand=True,
                         **kwargs)

        self.containers = []
        self.header_label = Label(
            name="nhh",
            label="Notifications",
            h_align="start",
            h_expand=True,
        )
        self.dnd_switch_label = Label(
            name="dnd-switch-label",
            markup=icons.notification,
        )
        self.dnd_switch = Button(
            name="dnd-switch",
            style_classes=["bar-action-button", "small"],
            child=self.dnd_switch_label,
            on_clicked=lambda *_: self.on_do_not_disturb_changed(),
            tooltip_text="Enable Do Not Disturb",
        )
        self.header_clean = Button(
            name="nhh-button",
            style_classes=["bar-action-button", "small", "danger"],
            child=Label(name="nhh-button-label", markup=icons.trash),
            on_clicked=self.clear_history,
        )
        self.on_event = on_event # type: ignore
        self.do_not_disturb_enabled = False

        self.history_header = CenterBox(
            name="notification-history-header",
            spacing=8,
            start_children=[self.dnd_switch],
            center_children=[self.header_label],
            end_children=[self.header_clean],
        )
        self.notifications_list = Box(
            name="notifications-list",
            orientation="v",
            spacing=4,
            h_expand=True,
            v_expand=True,
            h_align="fill",
            v_align="fill",
        )
        self.scrolled_window = ScrolledWindow(
            name="notification-history-scrolled-window",
            orientation="v",
            h_expand=True,
            v_expand=True,
            h_align="fill",
            v_align="fill",
            propagate_width=False,
            propagate_height=False,
        )
        self.scrolled_window.add_with_viewport(self.notifications_list)
        self.persistent_notifications = []
        self.add(self.history_header)
        self.add(self.scrolled_window)
        self._load_persistent_history()
        self._cleanup_orphan_cached_images()
        self.schedule_midnight_update()

        self.LIMITED_APPS_HISTORY = ["Spotify"]
        self._server = notification_server

    def on_event(self, func: Callable) -> None:
        """ Set the event handler for notification events."""
        self.on_event = func

    def emit(self, signal_name: str, *args: object) -> None:
        """ Emit a signal to the event handler."""
        self.on_event(signal_name, *args) # type: ignore

    def get_ordinal(self, n: int) -> str:
        """Return the ordinal suffix for a given integer."""
        if 11 <= (n % 100) <= 13:
            return "th"
        else:
            return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

    def get_date_header(self, dt: datetime) -> str:
        """Return a formatted date header for the given datetime."""
        now = datetime.now()
        today = now.date()
        date = dt.date()
        if date == today:
            return "Today"
        elif date == today - timedelta(days=1):
            return "Yesterday"
        else:
            original_locale = locale.getlocale(locale.LC_TIME)
            try:
                locale.setlocale(locale.LC_TIME, ("en_US", "UTF-8"))
            except locale.Error:
                locale.setlocale(locale.LC_TIME, "C")
            try:
                day = dt.day
                ordinal = self.get_ordinal(day)
                month = dt.strftime("%B")
                if dt.year == now.year:
                    result = f"{month} {day}{ordinal}"
                else:
                    result = f"{month} {day}{ordinal}, {dt.year}"
            finally:
                locale.setlocale(locale.LC_TIME, original_locale)
            return result

    def schedule_midnight_update(self) -> None:
        """Schedule an update to rebuild notifications at midnight."""
        now = datetime.now()
        next_midnight = datetime.combine(now.date() + timedelta(days=1),
                                         datetime.min.time())
        delta_seconds = (next_midnight - now).total_seconds()
        GLib.timeout_add_seconds(int(delta_seconds), self.on_midnight)

    def on_midnight(self) -> bool:
        """Rebuild notifications with date separators at midnight."""
        self.rebuild_with_separators()
        self.schedule_midnight_update()
        return GLib.SOURCE_REMOVE

    def create_date_separator(self, date_header: str) -> Box:
        """Create a date separator box with the given date header."""
        return Box(
            name="notif-date-sep",
            children=[
                Label(
                    name="notif-date-sep-label",
                    label=date_header,
                    h_align="center",
                    h_expand=True,
                )
            ],
        )

    def rebuild_with_separators(self) -> None:
        """Rebuild the notification list with date separators."""
        GLib.idle_add(self._do_rebuild_with_separators)

    def _do_rebuild_with_separators(self) -> None:
        """Perform the actual rebuilding of the notification list."""
        children = list(self.notifications_list.get_children())
        for child in children:
            self.notifications_list.remove(child)

        current_date_header = None
        last_date_header = None
        for container in sorted(self.containers,
                                key=lambda x: x.arrival_time,
                                reverse=True):
            arrival_time = container.arrival_time
            date_header = self.get_date_header(arrival_time)
            if date_header != current_date_header:
                sep = self.create_date_separator(date_header)
                self.notifications_list.add(sep)
                current_date_header = date_header
                last_date_header = date_header
            self.notifications_list.add(container)

        if not self.containers and last_date_header:
            for child in list(self.notifications_list.get_children()):
                if child.get_name() == "notif-date-sep":
                    self.notifications_list.remove(child)

        self.notifications_list.show_all()

    def on_do_not_disturb_changed(self) -> None:
        """Toggle Do Not Disturb mode and update the UI accordingly."""
        self.do_not_disturb_enabled = not self.do_not_disturb_enabled
        logger.info(
            f"Do Not Disturb mode {'enabled' if self.do_not_disturb_enabled else 'disabled'}"
        )
        self.dnd_switch_label.set_markup(icons.notification if not self.
                                         do_not_disturb_enabled else icons.dnd)
        self.dnd_switch.set_tooltip_text(
            "Disable Do Not Disturb" if self.
            do_not_disturb_enabled else "Enable Do Not Disturb")
        self.emit("do-not-disturb-changed")

    def clear_history(self, *args: object) -> None:
        """Clear the notification history and remove all notifications."""
        for child in self.notifications_list.get_children()[:]:
            container = child
            notif_box = (container.notification_box if hasattr(
                container, "notification_box") else None)
            if notif_box:
                notif_box.destroy(from_history_delete=True)
            self.notifications_list.remove(child)
            child.destroy()

        if os.path.exists(PERSISTENT_HISTORY_FILE):
            try:
                os.remove(PERSISTENT_HISTORY_FILE)
                logger.info(
                    "Notification history cleared and persistent file deleted.")
            except Exception as e:
                logger.error(f"Error deleting persistent history file: {e}")
        self.persistent_notifications = []
        self.containers = []
        self.rebuild_with_separators()
        self.emit("notification-deleted")

    def _load_persistent_history(self) -> None:
        """Load persistent notification history from file."""
        if not os.path.exists(PERSISTENT_DIR):
            os.makedirs(PERSISTENT_DIR, exist_ok=True)
        if os.path.exists(PERSISTENT_HISTORY_FILE):
            try:
                with open(PERSISTENT_HISTORY_FILE, "r") as f:
                    self.persistent_notifications = json.load(f)
                for note in reversed(self.persistent_notifications):
                    self._add_historical_notification(note)
            except Exception as e:
                logger.error(f"Error loading persistent history: {e}")

    def delete_historical_notification(self, note_id: int, container: Box) -> None:
        """Delete a historical notification and remove it from persistent storage."""
        # Convert note_id to string for consistent comparison
        target_note_id_str = str(note_id)
        logger.debug(
            f"Attempting to delete notification {target_note_id_str} from history"
        )

        # First cleanup notification box resources
        if hasattr(container, "notification_box"):
            notif_box = container.notification_box
            notif_box.destroy(from_history_delete=True)

        # Create new list excluding the notification to delete
        new_persistent_notifications = []
        removed_from_list = False

        for note_in_list in self.persistent_notifications:
            current_note_id_str = str(note_in_list.get("id"))
            if current_note_id_str == target_note_id_str:
                removed_from_list = True
                logger.debug(
                    f"Found notification {target_note_id_str} in persistent list, removing"
                )
                continue
            new_persistent_notifications.append(note_in_list)

        # Update the list and save if changed
        if removed_from_list:
            self.persistent_notifications = new_persistent_notifications
            logger.info(
                f"Notification {target_note_id_str} removed from persistent_notifications list"
            )

            self._save_persistent_history()
        else:
            logger.warning(
                f"Notification {target_note_id_str} NOT found in persistent_notifications list"
            )

        # Remove from containers list
        self.containers = [c for c in self.containers if c != container]

        # Ensure the container is removed from the UI
        parent = container.get_parent()
        if parent:
            parent.remove(container)
        container.destroy()

        # Update UI
        self.rebuild_with_separators()

        # Notify about deletion for counter update
        self.emit("notification-deleted")

    def _save_persistent_history(self) -> None:
        try:
            # Ensure directory exists
            os.makedirs(PERSISTENT_DIR, exist_ok=True)

            with open(PERSISTENT_HISTORY_FILE, "w") as f:
                json.dump(self.persistent_notifications, f)

            logger.debug("Persistent notification history saved successfully")
        except Exception as e:
            logger.error(f"Error saving persistent history: {e}")

    def _add_historical_notification(self, note):
        hist_notif = HistoricalNotification(
            id=note.get("id"),
            app_icon=note.get("app_icon"),
            summary=note.get("summary"),
            body=note.get("body"),
            app_name=note.get("app_name"),
            timestamp=note.get("timestamp"),
            cached_image_path=note.get("cached_image_path"),
        )

        hist_box = NotificationBox(hist_notif, timeout_ms=0) # type: ignore
        hist_box.uuid = hist_notif.id
        hist_box.cached_image_path = hist_notif.cached_image_path
        hist_box.set_is_history(True)
        for child in hist_box.get_children():
            if child.get_name() == "notification-action-buttons":
                hist_box.remove(child)
        container = Box(
            name="notification-container",
            orientation="v",
            h_align="fill",
            h_expand=True,
        )
        container.notification_box = hist_box
        try:
            arrival = datetime.fromisoformat(hist_notif.timestamp)
        except Exception:
            arrival = datetime.now()
        container.arrival_time = arrival

        def compute_time_label(arrival_time):
            return arrival_time.strftime("%H:%M")

        self.hist_time_label = Label(
            name="notification-timestamp",
            markup=compute_time_label(container.arrival_time),
            h_align="start",
            ellipsization="end",
        )
        pixbuf = load_scaled_pixbuf(hist_box, 48, 48)
        self.hist_notif_image_box = Box(
            name="notification-image",
            orientation="v",
            children=[
                Image(pixbuf=pixbuf),
                Box(v_expand=True),
            ],
        )
        self.hist_notif_summary_label = Label(
            name="notification-summary",
            markup=hist_notif.summary,
            h_align="start",
            ellipsization="end",
        )

        self.hist_notif_app_name_label = Label(
            name="notification-app-name",
            markup=f"{hist_notif.app_name}",
            h_align="start",
            ellipsization="end",
        )

        self.hist_notif_body_label = (Label(
            name="notification-body",
            markup=hist_notif.body,
            h_align="start",
            ellipsization="end",
            line_wrap="word-char",
        ) if hist_notif.body else Box())
        (self.hist_notif_body_label.set_single_line_mode(True)
         if hist_notif.body else None)

        self.hist_notif_summary_box = Box(
            name="notification-summary-box",
            orientation="h",
            children=[
                self.hist_notif_summary_label,
                Box(
                    name="notif-sep",
                    h_expand=False,
                    v_expand=False,
                    h_align="center",
                    v_align="center",
                ),
                self.hist_notif_app_name_label,
                Box(
                    name="notif-sep",
                    h_expand=False,
                    v_expand=False,
                    h_align="center",
                    v_align="center",
                ),
                self.hist_time_label,
            ],
        )
        self.hist_notif_text_box = Box(
            name="notification-text",
            orientation="v",
            v_align="center",
            h_expand=True,
            children=[
                self.hist_notif_summary_box,
                self.hist_notif_body_label,
            ],
        )
        self.hist_notif_close_button = Button(
            name="notif-close-button",
            child=Label(name="notif-close-label", markup=icons.cancel),
            on_clicked=lambda *_: self.delete_historical_notification(
                hist_notif.id, container),
        )
        self.hist_notif_close_button_box = Box(
            orientation="v",
            children=[
                self.hist_notif_close_button,
                Box(v_expand=True),
            ],
        )
        content_box = Box(
            name="notification-box-hist",
            spacing=8,
            children=[
                self.hist_notif_image_box if pixbuf else Box(h_expand=False),
                self.hist_notif_text_box,
                self.hist_notif_close_button_box,
            ],
        )
        container.add(content_box)
        self.containers.insert(0, container)
        self.rebuild_with_separators()

    def add_notification(self, notification_box):
        app_name = notification_box.notification.app_name
        if app_name in self.LIMITED_APPS_HISTORY:
            self.clear_history_for_app(app_name)

        if len(self.containers) >= 50:
            oldest_container = self.containers.pop()
            if (hasattr(oldest_container, "notification_box") and hasattr(
                    oldest_container.notification_box, "cached_image_path") and
                    oldest_container.notification_box.cached_image_path and
                    os.path.exists(
                        oldest_container.notification_box.cached_image_path)):
                try:
                    os.remove(
                        oldest_container.notification_box.cached_image_path)
                    logger.info(
                        f"Deleted cached image of oldest notification due to history limit: {oldest_container.notification_box.cached_image_path}"
                    )
                except Exception as e:
                    logger.error(
                        f"Error deleting cached image of oldest notification: {e}"
                    )
            oldest_container.destroy()

        container = Box(
            name="notification-container",
            orientation="v",
            h_align="fill",
            h_expand=True,
        )

        def on_container_destroy(container, notification_box):
            if (hasattr(container, "_timestamp_timer_id") and
                    container._timestamp_timer_id):
                GLib.source_remove(container._timestamp_timer_id)
            self.delete_historical_notification(notification_box.uuid,
                                                container)
            self.rebuild_with_separators()

        container.arrival_time = datetime.now()

        def compute_time_label(arrival_time):
            return arrival_time.strftime("%H:%M")

        self.current_time_label = Label(
            name="notification-timestamp",
            markup=compute_time_label(container.arrival_time),
        )
        pixbuf = load_scaled_pixbuf(notification_box, 48, 48)
        self.current_notif_image_box = Box(
            name="notification-image",
            orientation="v",
            children=[
                Image(pixbuf=pixbuf),
                Box(v_expand=True, v_align="fill"),
            ],
        )
        self.current_notif_summary_label = Label(
            name="notification-summary",
            markup=notification_box.notification.summary,
            h_align="start",
            ellipsization="end",
        )
        self.current_notif_app_name_label    = Label(
            name="notification-app-name",
            markup=f"{notification_box.notification.app_name}",
            h_align="start",
            ellipsization="end",
        )
        self.current_notif_body_label = (Label(
            name="notification-body",
            markup=notification_box.notification.body,
            h_align="start",
            ellipsization="end",
            line_wrap="word-char",
        ) if notification_box.notification.body else Box())
        (self.current_notif_body_label.set_single_line_mode(True)
         if notification_box.notification.body else None)
        self.current_notif_summary_box = Box(
            name="notification-summary-box",
            orientation="h",
            children=[
                self.current_notif_summary_label,
                Box(
                    name="notif-sep",
                    h_expand=False,
                    v_expand=False,
                    h_align="center",
                    v_align="center",
                ),
                self.current_notif_app_name_label   ,
                Box(
                    name="notif-sep",
                    h_expand=False,
                    v_expand=False,
                    h_align="center",
                    v_align="center",
                ),
                self.current_time_label,
            ],
        )
        self.current_notif_text_box = Box(
            name="notification-text",
            orientation="v",
            v_align="center",
            h_expand=True,
            children=[
                self.current_notif_summary_box,
                self.current_notif_body_label,
            ],
        )
        self.current_notif_close_button = Button(
            name="notif-close-button",
            child=Label(name="notif-close-label", markup=icons.cancel),
            on_clicked=lambda *_: on_container_destroy(container,
                                                       notification_box),
        )
        self.current_notif_close_button_box = Box(
            orientation="v",
            children=[
                self.current_notif_close_button,
                Box(v_expand=True),
            ],
        )
        content_box = Box(
            name="notification-content",
            children=[
                self.current_notif_image_box if pixbuf else Box(h_expand=False),
                self.current_notif_text_box,
                self.current_notif_close_button_box,
            ],
        )
        container.notification_box = notification_box
        hist_box = Box(
            name="notification-box-hist",
            orientation="v",
            h_align="fill",
            h_expand=True,
        )
        hist_box.add(content_box)
        container.add(hist_box)
        self.containers.insert(0, container)
        self.rebuild_with_separators()
        self._append_persistent_notification(notification_box,
                                             container.arrival_time)
        self.emit("notification-added")

    def _append_persistent_notification(self, notification_box, arrival_time):
        note = {
            "id": notification_box.uuid,
            "app_icon": notification_box.notification.app_icon,
            "summary": notification_box.notification.summary,
            "body": notification_box.notification.body,
            "app_name": notification_box.notification.app_name,
            "timestamp": arrival_time.isoformat(),
            "cached_image_path": notification_box.cached_image_path,
        }
        self.persistent_notifications.insert(0, note)
        self.persistent_notifications = self.persistent_notifications[:50]
        self._save_persistent_history()

    def _cleanup_orphan_cached_images(self):
        logger.debug("Starting orphan cached image cleanup.")
        if not os.path.exists(PERSISTENT_DIR):
            logger.debug("Cache directory does not exist, skipping cleanup.")
            return

        cached_files = [
            f for f in os.listdir(PERSISTENT_DIR)
            if f.startswith("notification_") and f.endswith(".png")
        ]
        if not cached_files:
            logger.debug("No cached image files found, skipping cleanup.")
            return

        history_uuids = {
            note.get("id")
            for note in self.persistent_notifications
            if note.get("id")
        }
        deleted_count = 0
        for cached_file in cached_files:
            try:
                uuid_from_filename = cached_file[len("notification_"
                                                    ):-len(".png")]
                if uuid_from_filename not in history_uuids:
                    cache_file_path = os.path.join(PERSISTENT_DIR, cached_file)
                    os.remove(cache_file_path)
                    logger.info(
                        f"Deleted orphan cached image: {cache_file_path}")
                    deleted_count += 1
                else:
                    logger.debug(
                        f"Cached image {cached_file} found in history, keeping it."
                    )
            except Exception as e:
                logger.error(
                    f"Error processing cached file {cached_file} during cleanup: {e}"
                )

        if deleted_count > 0:
            logger.info(
                f"Orphan cached image cleanup finished. Deleted {deleted_count} images."
            )
        else:
            logger.info(
                "Orphan cached image cleanup finished. No orphan images found.")

    def clear_history_for_app(self, app_name):
        """Clears all notifications in history for a specific app."""
        containers_to_remove = []
        persistent_notes_to_remove_ids = set()
        for container in list(self.containers):
            if (hasattr(container, "notification_box") and
                    container.notification_box.notification.app_name
                    == app_name):
                containers_to_remove.append(container)
                persistent_notes_to_remove_ids.add(
                    container.notification_box.uuid)

        for container in containers_to_remove:
            if (hasattr(container, "notification_box") and
                    hasattr(container.notification_box, "cached_image_path") and
                    container.notification_box.cached_image_path and
                    os.path.exists(
                        container.notification_box.cached_image_path)):
                try:
                    os.remove(container.notification_box.cached_image_path)
                    logger.info(
                        f"Deleted cached image of replaced history notification: {container.notification_box.cached_image_path}"
                    )
                except Exception as e:
                    logger.error(
                        f"Error deleting cached image of replaced history notification: {e}"
                    )
            self.containers.remove(container)
            self.notifications_list.remove(container)
            container.notification_box.destroy(from_history_delete=True)
            container.destroy()

        self.persistent_notifications = [
            note for note in self.persistent_notifications
            if note.get("id") not in persistent_notes_to_remove_ids
        ]
        self._save_persistent_history()
        self.rebuild_with_separators()


class NotificationHistoryIndicator(Button):
    """Indicator button for notification history."""

    def __init__(self, notification_history: NotificationHistory, **kwargs):
        super().__init__(
            name="notification-history-indicator",
            h_align="center",
            v_align="center",
            style_classes=["hidden"],
            **kwargs,
        )
        self.set_tooltip_text("Notification History")

        # Create notification history component
        self.notification_history = notification_history
        self.notification_history.on_event = self.on_notification_history_event # type: ignore
        self.dnd = self.notification_history.do_not_disturb_enabled

        # Create container for icon and counter
        self._container = Box(
            name="notification-history-container",
            spacing=0,
        )

        # Bell icon
        self.icon = Label(name="notification-history-icon",
                          markup=icons.notification)

        # Add components to container
        self.add(self.icon)

        # Track notification count
        self.notification_count = len(
            self.notification_history.persistent_notifications)
        self.update_counter()

    def on_notification_history_event(self, signal_name: str, *args) -> None:
        """Handle notification history events with proper count management."""
        self.notification_count = len(
            self.notification_history.persistent_notifications)
        match signal_name:
            case "notification-added":
                self.update_counter()
            case "notification-deleted":
                self.update_counter()
            case "do-not-disturb-changed":
                self.dnd = self.notification_history.do_not_disturb_enabled
                style_context = self.get_style_context()
                if self.dnd:
                    self.icon.set_markup(icons.dnd)
                    self.add_style_class("dnd")
                    if not style_context.has_class("hovered"):
                        self.remove_style_class("hidden")
                    self.set_tooltip_text("Do Not Disturb Enabled")
                else:
                    self.icon.set_markup(icons.notification)
                    self.remove_style_class("dnd")
                    self.set_tooltip_text("")
                    if self.notification_count > 0 and not style_context.has_class(
                            "hovered"):
                        self.remove_style_class("hidden")
            case _:
                logger.warning(
                    f"Unhandled notification history event: {signal_name}")

    def update_counter(self) -> None:
        """Update notification counter display with proper state management."""

        # Update UI based on count
        if self.notification_count > 0:
            self.add_style_class("active")
            style_context = self.get_style_context()
            if not style_context.has_class("hovered"):
                self.remove_style_class("hidden")
        else:
            self.remove_style_class("active")
            self.add_style_class("hidden")


class NotificationContainer(Box):
    """Main container for displaying notifications."""
    LIMITED_APPS = ["Spotify"]

    def __init__(
        self,
        notification_history_instance: NotificationHistory,
        revealer_transition_type: str = "slide-down",
    ):
        super().__init__(name="notification-container-main",
                         orientation="v",
                         spacing=4)
        self.notification_history = notification_history_instance

        self._server = self.notification_history._server
        self._server.connect("notification-added", self.on_new_notification)
        self._pending_removal = False
        self._is_destroying = False

        # Vertical box to display multiple notifications
        self.notifications_box = Box(
            name="notification-stack-box",
            orientation="v",
            h_align="center",
            h_expand=False,
            spacing=8,
        )

        self.notification_box_container = Box(
            name="notification-box-internal-container",
            orientation="v",
            children=[self.notifications_box],
        )

        self.main_revealer = Revealer(
            name="notification-main-revealer",
            transition_type=revealer_transition_type,
            transition_duration=300,
            child_revealed=False,
            child=self.notification_box_container,
        )

        self.add(self.main_revealer)

        self.notifications = []
        self._destroyed_notifications = set()
        self.visible_notifications = []

    def on_new_notification(self, fabric_notif, id: str, *args) -> None:
        """Handle new notification from the server."""
        notification_history_instance = self.notification_history
        if notification_history_instance.do_not_disturb_enabled:
            logger.info(
                "Do Not Disturb mode enabled: adding notification directly to history."
            )
            notification = fabric_notif.get_notification_from_id(id)
            new_box = NotificationBox(
                notification,
                timeout_ms=notification.timeout,
            )
            if notification.image_pixbuf:
                cache_notification_pixbuf(new_box)

            notification_history_instance.add_notification(new_box)
            return

        notification = fabric_notif.get_notification_from_id(id)
        new_box = NotificationBox(
            notification,
            timeout_ms=notification.timeout,
        )
        new_box.set_container(self)
        notification.connect("closed", self.on_notification_closed)

        app_name = notification.app_name
        if app_name in self.LIMITED_APPS:
            notification_history_instance.clear_history_for_app(app_name)

            # Remove existing notification for this LIMITED_APP if present
            existing_notification_index = -1
            for index, existing_box in enumerate(self.notifications):
                if existing_box.notification.app_name == app_name:
                    existing_notification_index = index
                    break

            if existing_notification_index != -1:
                old_notification_box = self.notifications.pop(
                    existing_notification_index)
                if old_notification_box in self.visible_notifications:
                    self.visible_notifications.remove(old_notification_box)
                    self._animate_notification_removal(old_notification_box)
                else:
                    old_notification_box.destroy()

        # Add the new notification
        self.notifications.append(new_box)

        # Display the notification if we haven't reached MAX_VISIBLE_NOTIFICATIONS
        if len(self.visible_notifications) < MAX_VISIBLE_NOTIFICATIONS:
            self.visible_notifications.append(new_box)
            self.notifications_box.add(new_box)
            new_box.show_all()

        # Show the revealer if it's not already shown
        self.main_revealer.show_all()
        self.main_revealer.set_reveal_child(True)

    def _animate_notification_removal(self, notification_box: NotificationBox) -> None:
        """Animate the removal of a notification box."""
        # Add exit animation class
        notification_box.remove_style_class("notification-visible")
        notification_box.add_style_class("notification-exiting")

        # Wait for animation to complete before removing
        GLib.timeout_add(
            250, lambda: self._complete_notification_removal(notification_box))

    def _complete_notification_removal(self, notification_box: NotificationBox) -> bool:
        """Complete the removal of a notification box."""
        if notification_box.get_parent() == self.notifications_box:
            self.notifications_box.remove(notification_box)
        notification_box.destroy()

        # Show next notification if available
        self._show_next_notification()
        return False

    def _show_next_notification(self) -> bool:
        """Show the next hidden notification if available."""
        # If we have more notifications waiting to be shown, show the next one
        hidden_notifications = [
            n for n in self.notifications if n not in self.visible_notifications
        ]
        if (hidden_notifications and
                len(self.visible_notifications) < MAX_VISIBLE_NOTIFICATIONS):
            next_to_show = hidden_notifications[0]
            self.visible_notifications.append(next_to_show)
            self.notifications_box.add(next_to_show)
            next_to_show.show_all()
            return True
        return False

    def on_notification_closed(self, notification: Notification, reason: str) -> None:
        """Handle notification close event."""
        if self._is_destroying:
            return
        if notification.id in self._destroyed_notifications:
            return
        self._destroyed_notifications.add(notification.id)
        transient = notification.do_get_hint_entry("transient") or False
        try:
            logger.info(
                f"Notification {notification.id} closing with reason: {reason}")
            notif_to_remove = None
            for i, notif_box in enumerate(self.notifications):
                if notif_box.notification.id == notification.id:
                    notif_to_remove = (i, notif_box)
                    break
            if not notif_to_remove:
                return
            i, notif_box = notif_to_remove
            reason_str = str(reason)

            notification_history_instance = self.notification_history

            # Handle the notification based on close reason
            if reason_str == "NotificationCloseReason.DISMISSED_BY_USER":
                logger.info(
                    f"Cleaning up resources for dismissed notification {notification.id}"
                )

                # Remove from visible_notifications first
                if notif_box in self.visible_notifications:
                    self.visible_notifications.remove(notif_box)
                    self._animate_notification_removal(notif_box)
                else:
                    notif_box.destroy()

                # Don't add dismissed notifications to history
                # And make sure they're not in history already (could have been added by another process)
                notification_id = notification.id
                for container in list(notification_history_instance.containers):
                    if (hasattr(container, 'notification_box') and hasattr(
                            container.notification_box, 'notification') and
                            hasattr(container.notification_box.notification,
                                    'id') and
                            str(container.notification_box.notification.id)
                            == str(notification_id)):
                        notification_history_instance.delete_historical_notification(
                            notification_id, container)
                        break

            elif (reason_str == "NotificationCloseReason.EXPIRED"):
                logger.info(
                    f"Adding notification {notification.id} to history (reason: {reason_str})"
                )

                # Remove from visible_notifications first
                if notif_box in self.visible_notifications:
                    self.visible_notifications.remove(notif_box)
                    self._animate_notification_removal(notif_box)

                # Add to history only when expired naturally
                notif_box.set_is_history(True)
                notif_box.stop_timeout()

                # Add the notification to history
                if not transient:
                    notification_history_instance.add_notification(notif_box)

            elif (reason_str == "NotificationCloseReason.CLOSED" or
                  reason_str == "NotificationCloseReason.UNDEFINED"):
                logger.info(
                    f"Processing notification {notification.id} with reason: {reason_str}"
                )

                # Remove from visible_notifications
                if notif_box in self.visible_notifications:
                    self.visible_notifications.remove(notif_box)
                    self._animate_notification_removal(notif_box)

                # Don't add to history for these cases - user likely closed it
                # from somewhere else in the system
                notif_box.destroy()
            else:
                logger.warning(
                    f"Unknown close reason: {reason_str} for notification {notification.id}. Defaulting to destroy."
                )

                # Remove from visible_notifications first
                if notif_box in self.visible_notifications:
                    self.visible_notifications.remove(notif_box)
                    self._animate_notification_removal(notif_box)
                else:
                    notif_box.destroy()

            # Remove from main notifications list
            self.notifications.pop(i)

            # Hide the container if we have no more notifications
            if len(self.notifications) == 0:
                self._is_destroying = True
                self.main_revealer.set_reveal_child(False)
                GLib.timeout_add(
                    self.main_revealer.get_transition_duration(),
                    self._destroy_container,
                )
        except Exception as e:
            logger.error(f"Error closing notification: {e}")

    def _destroy_container(self) -> bool:
        """Clean up the notification container."""
        try:
            self.notifications.clear()
            self._destroyed_notifications.clear()
            for child in self.notifications_box.get_children():
                self.notifications_box.remove(child)
                child.destroy()
            self.current_index = 0
        except Exception as e:
            logger.error(f"Error cleaning up the container: {e}")
        finally:
            self._is_destroying = False
            return False

    def pause_and_reset_all_timeouts(self) -> None:
        """Pause and reset all notification timeouts."""
        if self._is_destroying:
            return
        for notification in self.notifications[:]:
            try:
                if not notification._destroyed and notification.get_parent():
                    notification.stop_timeout()
            except Exception as e:
                logger.error(f"Error pausing timeout: {e}")

    def resume_all_timeouts(self) -> None:
        """Resume all notification timeouts."""
        if self._is_destroying:
            return
        for notification in self.notifications[:]:
            try:
                if not notification._destroyed and notification.get_parent():
                    notification.start_timeout()
            except Exception as e:
                logger.error(f"Error resuming timeout: {e}")

    def close_all_notifications(self, *args) -> None:
        """Close all notifications in the container."""
        notifications_to_close = self.notifications.copy()
        for notification_box in notifications_to_close:
            notification_box.notification.close("dismissed-by-user")


class NotificationPopup(WaylandWindow):
    """Notification popup window that displays notifications."""

    def __init__(self, notification_server: Notifications,
                 notification_history: NotificationHistory, **kwargs):
        pos = config.NOTIFICATION_POSITION
        y_pos = pos.split("-")[0]
        x_pos = pos.split("-")[1]

        super().__init__(
            name="notification-popup",
            anchor=f"{x_pos} {y_pos}",
            layer="top",
            keyboard_mode="none",
            exclusivity="none",
            visible=True,
            all_visible=True,
        )

        self.widgets = kwargs.get("widgets", None)
        self._notification_server = notification_server

        self.notification_history = notification_history
        self.notification_container = NotificationContainer(
            notification_history_instance=self.notification_history,
            revealer_transition_type="slide-down"
            if y_pos == "top" else "slide-up",
        )

        self.show_box = Box()
        self.show_box.set_size_request(1, 1)

        self.add(
            Box(
                name="notification-popup-box",
                orientation="v",
                children=[self.notification_container, self.show_box],
            ))
