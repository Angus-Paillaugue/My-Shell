from fabric.hyprland.service import HyprlandEvent
from fabric.hyprland.widgets import Language as HyprlandLanguage
from fabric.hyprland.widgets import get_hyprland_connection
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label

import modules.icons as icons
from services.config import config


class Language(Button):
    """Widget that displays the current keyboard layout language in the bar."""

    def __init__(self, **kwargs):
        orientation = (
            "horizontal" if config['POSITIONS']['BAR'] in ["top", "bottom"] else "vertical"
        )
        super().__init__(
            name="language",
            style_classes=["bar-item", orientation],
            h_align="center",
            v_align="center",
            spacing=4,
            v_expand=True,
            h_expand=True,
            orientation=orientation,
            **kwargs,
        )
        self.connection = get_hyprland_connection()

        self.lang_label = Label(name="lang-label",)
        self.lang_icon = Label(markup=icons.keyboard, name="keyboard-lang-icon")
        self.add(Box(
            name="icon-container",
            spacing=config['STYLES']['PADDING'],
            orientation=orientation,
            children=[self.lang_icon, self.lang_label],
            h_align="center",
            v_align="center",
        ))
        self.on_language_switch()
        self.connection.connect("event::activelayout", self.on_language_switch)

    def on_language_switch(self, _=None, event: HyprlandEvent|None = None) -> None:
        """Update the language widget based on the active layout."""
        lang_data = (event.data[1] if event and event.data and
                     len(event.data) > 1 else HyprlandLanguage().get_label())
        self.set_tooltip_text(lang_data)
        self.lang_label.set_label(lang_data[:2].upper())
