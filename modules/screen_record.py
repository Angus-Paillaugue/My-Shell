from fabric.utils.helpers import exec_shell_command_async, get_relative_path
from fabric.widgets.button import Button
from fabric.widgets.label import Label
import modules.icons as icons


class ScreenRecordButton(Button):

    def __init__(self):
        super().__init__(
            tooltip_text="Screen Record",
            orientation="h",
            style_classes=['settings-action-button'],
            spacing=4,
            v_align="center",
            h_align="center",
            visible=True,
            child=Label(markup=icons.screen_record),
            on_clicked=self.screen_record,
        )

    def screen_record(self, *args):
        script_location = get_relative_path("../services/screen-record.sh")
        exec_shell_command_async(
            f"bash -c 'nohup bash {script_location} > /dev/null 2>&1 & disown'")
