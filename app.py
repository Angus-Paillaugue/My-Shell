import gi
import setproctitle

from modules.multi_monitor import MultiMonitorManager
from styles.interpreter.main import StylesInterpreter

gi.require_version("GLib", "2.0")
from fabric.utils import get_relative_path, monitor_file
from fabric import Application
from services.config import config

if __name__ == "__main__":
    setproctitle.setproctitle(config['APP_NAME'])
    monitor_manager = MultiMonitorManager()
    app = Application(config['APP_NAME'], *monitor_manager.get_components())

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
