from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from typing import Callable
import modules.icons as icons


def singleton(class_: object) -> object:
    """Decorator to make a class a singleton"""
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs) # type: ignore
        return instances[class_]

    return getinstance


@singleton
class SettingsBroker():
    """Broker for managing settings-related events and listeners."""

    def register_listener(self, listener: Callable) -> None:
        """Register a listener for settings events."""
        if not hasattr(self, '_listeners'):
            self._listeners = []
        self._listeners.append(listener)

    def notify_listeners(self, event: str, *args: object, **kwargs: object) -> None:
        """Notify all registered listeners of an event."""
        for listener in getattr(self, '_listeners', []):
            listener(event, *args, **kwargs)

    def unregister_listener(self, listener: Callable) -> None:
        """Unregister a listener from settings events."""
        if hasattr(self, '_listeners'):
            self._listeners.remove(listener)


class SettingsButton(Box):
    """Base class for settings buttons with a label, icon, and dropdown menu."""

    def __init__(self,
                 label,
                 slot,
                 dropdown,
                 icon,
                 left_button_click=lambda *_: None,
                 **kwargs):
        super().__init__(
            name=f"{label}-button",
            h_expand=True,
            v_expand=True,
            spacing=4,
            orientation="h",
            **kwargs,
        )
        self.label = label
        self.slot = slot
        self.dropdown = dropdown
        self.left_button_click = left_button_click

        self.left_button_childs = Box(
            name="bluetooth-left-button-childs",
            orientation="h",
            spacing=8,
        )
        self.left_button = Button(
            name="bluetooth-left-button",
            h_expand=True,
            child=self.left_button_childs,
        )

        self.slot = slot
        self.status_text = Label(name="bluetooth-status",
                                 label=self.label,
                                 all_visible=True,
                                 visible=True,
                                 h_align="start",
                                 v_align="center",
                                 ellipsization="end")
        self.icon = Label(name="bluetooth-icon", markup=icon)
        self.devices_open_button = Button(
            style_classes=["expand-button-caret"],
            child=Label(name="bluetooth-open-label",
                        markup=icons.chevron_right),
        )
        self.slot.add(self.dropdown)

        self.left_button_childs.add(self.icon)
        self.left_button_childs.add(
            Box(
                orientation="v",
                h_align="start",
                v_align="center",
                children=[
                    Label(
                        label=self.label,
                        name="bluetooth-button-label",
                        h_align="start",
                    ),
                    self.status_text,
                ],
            ))
        self.add(self.left_button)
        self.add(self.devices_open_button)
        self.devices_open_button.connect(
            "clicked",
            lambda *_: (self.dropdown.toggle_visibility()
                        if self.dropdown.enabled else None),
        )
        self.left_button.connect("clicked", lambda *_: self.left_button_click())
