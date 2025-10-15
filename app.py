import gi
import setproctitle

from styles.interpreter.main import StylesInterpreter

gi.require_version("GLib", "2.0")
from fabric.utils import get_relative_path, monitor_file
from fabric import Application
from modules.bar import Bar
from services.config import config
from modules.notification import NotificationPopup
from modules.corners import Corners
from fabric.notifications.service import Notifications
from modules.notification import NotificationHistory
from modules.notch import NotchWindow
from modules.desktop_widget.registry import DesktopWidgetRegistry
from modules.osd import OSD

if __name__ == "__main__":
    setproctitle.setproctitle(config['APP_NAME'])
    notification_server = Notifications()
    notification_history = NotificationHistory(
        notification_server=notification_server)
    notification = NotificationPopup(
        notification_server=notification_server,
        notification_history=notification_history,
    )
    bar = Bar()
    corners = Corners()
    notch = NotchWindow(notification_history=notification_history)
    osd = OSD()
    widget_registry = DesktopWidgetRegistry()
    app = Application(
        config['APP_NAME'],
        bar,
        notch,
        notification,
        corners,
        osd,
        *widget_registry.all_widgets(),
    )
    input_styles_dir = get_relative_path("styles")
    styles_interpretor = StylesInterpreter(input_styles_dir, config['STYLES'])

    def apply_stylesheet(*_) -> None:
        config.init()
        styles_interpretor.set_variables(config['STYLES'])
        styles_interpretor.process_directory()
        return app.set_stylesheet_from_string(
            styles_interpretor.get_stylesheet())

    style_monitor = monitor_file(input_styles_dir)
    style_monitor.connect("changed", apply_stylesheet)
    config_monitor = monitor_file(get_relative_path("config.yaml"))
    config_monitor.connect("changed", apply_stylesheet)
    app.apply_stylesheet = apply_stylesheet
    apply_stylesheet()
    app.run()
