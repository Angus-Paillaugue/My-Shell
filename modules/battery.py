from fabric.core.fabricator import Fabricator
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.label import Label
from fabric.widgets.revealer import Revealer
from gi.repository import GLib

import modules.icons as icons
from services.metrics import shared_provider


class Battery(Button):
    """Widget that displays the battery status with an icon and percentage."""

    def __init__(self, **kwargs):
        super().__init__(name="battery-container", **kwargs)

        main_box = Box(
            spacing=0,
            orientation="h",
            visible=True,
            all_visible=True,
        )

        self.bat_icon = Label(name="battery-icon", markup=icons.battery_0)
        self.bat_circle = CircularProgressBar(
            name="battery-circle",
            value=0,
            size=30,
            line_width=2,
            start_angle=150,
            end_angle=390,
            style_classes="bat",
            child=self.bat_icon,
        )
        self.bat_level = Label(name="battery-level",
                               style_classes="bat",
                               label="100%")
        self.bat_revealer = Revealer(
            name="battery-level-revealer",
            transition_duration=250,
            transition_type="slide-left",
            child=self.bat_level,
            child_revealed=False,
        )
        self.bat_box = Box(
            name="battery-level-box",
            orientation="h",
            spacing=0,
            children=[self.bat_circle, self.bat_revealer],
        )

        main_box.add(self.bat_box)

        self.add(main_box)

        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)

        self.batt_fabricator = Fabricator(
            poll_from=lambda v: shared_provider.get_battery(),
            on_changed=lambda f, v: self.update_battery,
            interval=1000,
            stream=False,
            default_value=0,
        )
        self.batt_fabricator.changed.connect(self.update_battery)
        GLib.idle_add(self.update_battery, None, shared_provider.get_battery())

        self.hide_timer = None
        self.hover_counter = 0

    def _format_percentage(self, value: int) -> str:
        return f"{value}%"

    def on_mouse_enter(self, *args) -> bool:
        self.hover_counter += 1
        if self.hide_timer is not None:
            GLib.source_remove(self.hide_timer)
            self.hide_timer = None

        self.bat_revealer.set_reveal_child(True)
        return False

    def on_mouse_leave(self, *args) -> bool:
        if self.hover_counter > 0:
            self.hover_counter -= 1
        if self.hover_counter == 0:
            if self.hide_timer is not None:
                GLib.source_remove(self.hide_timer)
            self.hide_timer = GLib.timeout_add(100, self.hide_revealer)
        return False

    def hide_revealer(self) -> bool:
        self.bat_revealer.set_reveal_child(False)
        self.hide_timer = None
        return False

    def update_battery(self, sender, battery_data: tuple[float, bool]) -> None:
        value, charging = battery_data
        if value == 0:
            self.set_visible(False)
        else:
            self.set_visible(True)
            self.bat_circle.set_value(value / 100)
        percentage = int(value)
        self.bat_level.set_label(self._format_percentage(percentage))

        if percentage < 20 and not charging:
            self.bat_icon.add_style_class("alert")
            self.bat_circle.add_style_class("alert")
        elif percentage <= 40 and not charging:
            self.bat_icon.add_style_class("warning")
            self.bat_circle.add_style_class("warning")
        else:
            self.bat_icon.remove_style_class("alert")
            self.bat_circle.remove_style_class("alert")
            self.bat_icon.remove_style_class("warning")
            self.bat_circle.remove_style_class("warning")

        if charging == True:
            self.bat_icon.set_markup(icons.battery_charging)
        elif percentage <= 20:
            self.bat_icon.set_markup(icons.battery_0)
        elif percentage <= 40:
            self.bat_icon.set_markup(icons.battery_1)
        elif percentage <= 60:
            self.bat_icon.set_markup(icons.battery_2)
        elif percentage <= 80:
            self.bat_icon.set_markup(icons.battery_3)
        else:
            self.bat_icon.set_markup(icons.battery_4)
