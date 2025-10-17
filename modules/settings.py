import os
import sys

import setproctitle

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from styles.interpreter.main import StylesInterpreter
from fabric import Application
from fabric.utils.helpers import exec_shell_command_async, get_relative_path, monitor_file
from fabric.widgets.stack import Stack
from fabric.widgets.window import Window
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.entry import Entry
import modules.icons as icons
from services.config import config

class SettingsButton(Button):
    def __init__(self):
        super().__init__(
            tooltip_text="Settings",
            orientation="h",
            style_classes=['settings-action-button'],
            spacing=4,
            v_align="center",
            h_align="center",
            visible=True,
            child=Label(markup=icons.settings),
            on_clicked=self.on_clicked,
        )

    def on_clicked(self, *args) -> None:
        script = get_relative_path("../services/open-settings.sh")
        exec_shell_command_async(f"bash {script}")

class SettingsTab(Box):
    def __init__(self, name: str, **kwargs):
        super().__init__(
            orientation="v",
            spacing=10,
            v_expand=True,
            h_expand=True,
            name=name,
            children=[
                Label(label=name.capitalize(), h_align="start", style_classes=['settings-ui-tab-label'])
            ],
            visible=True,
            **kwargs
        )
        self.main_box = Box(
            orientation="v",
            spacing=10,
            v_expand=True,
            h_expand=True,
            style_classes=['settings-ui-tab-main-box'],
        )
        self.footer_box = Box(
            orientation="h",
            spacing=10,
            v_expand=False,
            h_expand=True,
            h_align="end",
            visible=False,
        )
        self.add(self.main_box)
        self.add(self.footer_box)

class StylesTab(SettingsTab):
    def __init__(self):
        super().__init__(
            name="styles",
        )
        self._copied_values = config['STYLES'].copy()
        fields = [
            ("Border Radius", "BORDER_RADIUS"),
            ("Font Size", "FONT_SIZE"),
            ("Bar Size", "BAR_SIZE"),
            ("Padding", "PADDING"),
        ]
        for field in fields:
            field_box = self._bake_field(field)
            self.main_box.add(field_box)

        self.save_button = Button(
            child=Label(label="Save"),
            style_classes=['settings-ui-save-button'],
            on_clicked=lambda _: self._save()
        )
        self.reset_form_button = Button(
            child=Label(label="Reset to defaults"),
            style_classes=['settings-ui-reset-form-button'],
            on_clicked=lambda _: self._reset_form()
        )
        self.footer_box.add(self.reset_form_button)
        self.footer_box.add(self.save_button)

    def _reset_form(self) -> None:
        for child in self.main_box.get_children():
            entry = child.get_children()[1]  # Assuming the Entry is always the second child
            name = child.get_name().replace("settings-ui-field-box-", "").upper()
            entry.set_text(str(config['STYLES'][name.upper()]))

    def _needs_save(self) -> bool:
        for key, value in self._copied_values.items():
            if value != config.get(f"STYLES.{key}"):
                return True
        return False

    def _save(self) -> None:
        if self._needs_save():
            config['STYLES'] = self._copied_values.copy()
            config.save()
            print("Configuration saved.")
        else:
            print("No changes to save.")

    def on_field_changed(self, entry: Entry, name: str) -> None:
        text = entry.get_text()
        self._copied_values[name] = int(text) if text.isdigit() else text
        if self._needs_save():
            self.footer_box.set_visible(True)
        else:
            self.footer_box.set_visible(False)

    def _bake_field(self, field: tuple[str, str]) -> Box:
        name, config_key = field
        initial_value = self._copied_values[config_key]
        entry = Entry(placeholder=f"Set {name.lower()}...", h_expand=False, size=(100, -1),
                        style_classes=['settings-ui-field-entry'], editable=True, text=str(initial_value))
        entry.connect("changed", self.on_field_changed, config_key)
        field_box = Box(
            orientation="h",
            name=f"settings-ui-field-box-{config_key.lower()}",
            spacing=4,
            v_expand=False,
            h_expand=True,
            children=[
                Label(label=name, h_align="start", style_classes=['settings-ui-field-label'], h_expand=True),
                entry
            ],
            style_classes=['settings-ui-field-box']
        )
        return field_box

class SettingsGUIWindow(Window):
    def __init__(self, **kwargs) -> None:
        super().__init__(
            title="Settings GUI",
            name="settings-ui-window",
            size=(640, 640),
            visible=True,
            **kwargs,
        )
        self._active_tab_index = 0
        self._tabs = [
            "styles",
            # "bar",    
            # "corners",
            # "notch",
            # "osd",
            # "notifications",
        ]
        self.set_resizable(False)
        self._sidebar = self._build_sidebar()
        self._tab_stack = Stack(
            transition_type="slide-up-down",
            transition_duration=250,
            name="settings-ui-tab-stack",
            v_expand=True,
            h_expand=True,
            children=[
                StylesTab(),
            ]
        )
        self.root_box = Box(
            orientation="h",
            spacing=0,
            children=[self._sidebar, self._tab_stack],
            visible=True
        )
        self.add(self.root_box)

    def _change_tab(self, tab_name: str) -> None:
        self._active_tab_index = self._tabs.index(tab_name)
        self._tab_stack.set_visible_child_name(tab_name)
        self._update_sidebar_styles()

    def _build_sidebar(self) -> Box:
        self._sidebar_buttons = []  # Store references to the buttons
        sidebar = Box(
            orientation="v",
            name="settings-gui-sidebar",
            spacing=5,
            v_expand=True,
        )
        for child in self.get_children():
            self.remove(child)
        for i, tab in enumerate(self._tabs):
            button = Button(
                child=Label(label=tab.capitalize()),
                style_classes=['sidebar-tab-button', 'active' if self._active_tab_index == i else ''],
                on_clicked=lambda _, t=tab: self._change_tab(t)
            )
            self._sidebar_buttons.append(button)  # Keep track of buttons
            sidebar.add(button)

        return sidebar

    def _update_sidebar_styles(self) -> None:
        for i, button in enumerate(self._sidebar_buttons):
            if i == self._active_tab_index:
                button.style_classes = ['sidebar-tab-button', 'active']
            else:
                button.style_classes = ['sidebar-tab-button']

def open_config():
    """
    Entry point for opening the configuration GUI using Fabric Application.
    """
    setproctitle.setproctitle(f"{config['APP_NAME']}-settings")
    app = Application(f"{config['APP_NAME']}-settings")
    window = SettingsGUIWindow()
    app.add_window(window)

    window.show_all()
    input_styles_dir = get_relative_path("../styles")
    styles_interpretor = StylesInterpreter(input_styles_dir, config['STYLES'])

    def apply_stylesheet(*_) -> None:
        config.init()
        styles_interpretor.set_variables(config['STYLES'])
        styles_interpretor.process_directory()
        return app.set_stylesheet_from_string(
            styles_interpretor.get_stylesheet())

    style_monitor = monitor_file(input_styles_dir)
    style_monitor.connect("changed", apply_stylesheet)
    config_monitor = monitor_file(get_relative_path("../config.yaml"))
    config_monitor.connect("changed", apply_stylesheet)
    app.apply_stylesheet = apply_stylesheet
    apply_stylesheet()
    app.run()


if __name__ == "__main__":
    open_config()
