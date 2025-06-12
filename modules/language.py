from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.box import Box
from fabric.hyprland.service import HyprlandEvent
from fabric.hyprland.widgets import (
    Language as HyprlandLanguage,
    get_hyprland_connection,
)
import modules.icons as icons


class Language(Button):

    def __init__(self, **kwargs):
        super().__init__(
            name="language",
            style_classes=["bar-item"],
            h_align="center",
            v_align="center",
            **kwargs,
        )
        self.connection = get_hyprland_connection()

        self.lang_label = Label(name="lang-label",)
        self.lang_icon = Label(markup=icons.keyboard, name="keyboard-lang-icon")
        self.add(Box(children=[self.lang_icon, self.lang_label], spacing=4))
        self.on_language_switch()
        self.connection.connect("event::activelayout", self.on_language_switch)

    def on_language_switch(self, _=None, event: HyprlandEvent = None):
        """Update the language widget based on the active layout."""
        lang_data = (event.data[1] if event and event.data and
                     len(event.data) > 1 else HyprlandLanguage().get_label())
        self.set_tooltip_text(lang_data)
        self.lang_label.set_label(lang_data[:2].upper())
