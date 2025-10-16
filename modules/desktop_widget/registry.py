import os

from services.config import config

class DesktopWidgetRegistry():
    def __init__(self, **kwargs):
        self.widgets = {}
        widgets_location = os.path.join(os.path.dirname(__file__), "widgets")
        for file in os.listdir(widgets_location):
            if file.endswith(".py"):
                module_name = file[:-3]
                module = __import__(f"modules.desktop_widget.widgets.{module_name}", fromlist=[module_name])
                widget_class = getattr(module, ''.join([part.capitalize()+"Widget" for part in module_name.split('_')]))
                if module_name.upper() in config['DESKTOP_WIDGETS']['WIDGETS']:
                    instance = widget_class(**kwargs)
                    self.widgets[module_name] = instance

    def all_widgets(self):
        return self.widgets.values()
