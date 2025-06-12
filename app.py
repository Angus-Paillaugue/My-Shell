import gi
import setproctitle

gi.require_version("GLib", "2.0")
from fabric.utils import get_relative_path, monitor_file
from fabric import Application
from modules.bar import Bar
from modules.launcher import AppLauncher
import services.config as config
from modules.clipboard import ClipboardManager
from modules.notification import NotificationPopup
from modules.corners import Corners
from modules.dock import Dock
from fabric.notifications.service import Notifications
from modules.notification import NotificationHistory
from modules.notch import NotchWindow

if __name__ == "__main__":
    setproctitle.setproctitle(config.APP_NAME)
    notification_server = Notifications()
    notification_history = NotificationHistory(
        notification_server=notification_server)
    notification = NotificationPopup(
        notification_server=notification_server,
        notification_history=notification_history,
    )
    bar = Bar()
    clipboard_manager = ClipboardManager()
    corners = Corners()
    dock = Dock()
    notch = NotchWindow(notification_history=notification_history)
    app = Application(
        config.APP_NAME,
        bar,
        notch,
        clipboard_manager,
        notification,
        corners,
        dock,
    )

    def apply_stylesheet(*_):
        return app.set_stylesheet_from_file(get_relative_path("main.css"))

    # Load main stylesheet
    style_monitor = monitor_file(get_relative_path("main.css"))
    style_monitor.connect("changed", apply_stylesheet)
    app.apply_stylesheet = apply_stylesheet
    apply_stylesheet()
    app.run()
