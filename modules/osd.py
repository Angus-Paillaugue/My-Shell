from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.revealer import Revealer
from fabric.widgets.wayland import WaylandWindow
from gi.repository import GLib  # type: ignore

import modules.icons as icons
from modules.settings import SettingsBroker
from services.logger import logger


class OSD(WaylandWindow):
    """On-Screen Display (OSD) for volume, brightness, and microphone changes."""

    def __init__(self, **kwargs) -> None:
        super().__init__(
            layer="top",
            anchor="bottom center",
            margin="0 0 100px 0",
            pass_through=True,
            exclusivity="none",
            keyboard_mode="none",
            visible=True,
            **kwargs,
        )
        self._broker = SettingsBroker() # type: ignore
        self._broker.register_listener(self.on_event)
        self._contents = Box(name="osd-contents",
                             orientation='h',
                             spacing=8,
                             h_align="center",
                             v_align="center")
        self.revealer = Revealer(
            transition_type="crossfade",
            all_visible=True,
            transition_duration=200,
            child=self._contents,
            child_revealed=False,
            name="osd-revealer",
        )
        self.add(self.revealer)
        self._hide_timeout = None

    def _set_visible(self, visible: bool) -> None:
        """Set the visibility of the OSD."""
        self.revealer.child_revealed = visible

    def on_event(self, event: str, *args: object, **kwargs: object) -> None:
        """Handle events to update the OSD contents."""
        ok = True
        if self._hide_timeout is not None:
            GLib.source_remove(self._hide_timeout)

        match event:
            case "volume-changed":
                percentage = f"{args[0]}%"
                enabled = args[1] if len(args) > 1 else True
                self._contents.children = [
                    Label(markup=icons.volume_high if enabled else icons.volume_muted),
                    Label(label=percentage),
                ]
            case "brightness-changed":
                percentage = f"{args[0]}%"
                self._contents.children = [
                    Label(markup=icons.brightness_high),
                    Label(label=percentage),
                ]
            case "mic-changed":
                percentage = f"{args[0]}%"
                enabled = args[1] if len(args) > 1 else True
                self._contents.children = [
                    Label(markup=icons.mic if enabled else icons.mic_muted),
                    Label(label=percentage),
                ]
            case _:
                ok = False
                logger.error(f"An event has not been taken into account")

        if ok:
            self._set_visible(True)
            self._hide_timeout = GLib.timeout_add(
                750, lambda *_: self._set_visible(False))
