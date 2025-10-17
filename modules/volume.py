import gi

gi.require_version("Gtk", "3.0")
from fabric.audio.service import Audio
from fabric.utils import exec_shell_command_async
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.revealer import Revealer
from fabric.widgets.scale import Scale
from fabric.widgets.scrolledwindow import ScrolledWindow
from gi.repository import GLib  # type: ignore

import modules.icons as icons
from modules.bluetooth import SettingsBroker
from services.logger import logger


class VolumeSlider(Scale):
    """Slider widget to control audio volume."""

    def __init__(self, audio, settings_notifier, **kwargs):
        super().__init__(
            name="control-slider",
            orientation="h",
            h_expand=True,
            h_align="fill",
            has_origin=True,
            increments=(0.01, 0.1),
            **kwargs,
        )
        self.audio = audio
        self.audio.connect("notify::speaker", self.on_new_speaker)
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.on_speaker_changed)
        self.connect("value-changed", self.on_value_changed)
        self.add_style_class("vol")
        self.on_speaker_changed()
        self.settings_notifier = settings_notifier

    def on_new_speaker(self, *args: object) -> None:
        """Handle new speaker connection."""
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.on_speaker_changed)
            self.on_speaker_changed()

    def on_value_changed(self, *args: object) -> None:
        """Update speaker volume when slider value changes."""
        if self.audio.speaker:
            self.audio.speaker.volume = self.value * 100

    def on_speaker_changed(self, *args: object) -> None:
        """Update slider value and style based on speaker state."""
        if not self.audio.speaker:
            return

        if self.audio.speaker.muted:
            self.add_style_class("muted")
        else:
            self.remove_style_class("muted")
        if self.value == round(self.audio.speaker.volume / 100, 2):
            return
        self.value = round(self.audio.speaker.volume / 100, 2)
        self.settings_notifier.notify_listeners("volume-changed",
                                                round(self.value * 100),
                                                not self.audio.speaker.muted)


class VolumeIcon(Button):
    """Button widget to toggle audio volume mute state and display icon."""

    def __init__(self, audio: Audio, settings_notifier, **kwargs):
        super().__init__(name="volume-icon", **kwargs)
        self.audio = audio
        self.settings_notifier = settings_notifier
        self.value = 0
        self.hide_timer = None
        self.hover_counter = 0

        self.label = Label(
            name="volume-icon-label",
            markup=icons.volume_muted,
        )
        self.connect("clicked", self.on_clicked)
        self.add(self.label)

        self.volume_icons = [
            icons.volume_low,
            icons.volume_high,
        ]

        self.set_icon()

    def set_icon(self) -> None:
        """Set the icon based on the current speaker volume and mute state."""
        if not self.audio or not self.audio.speaker:
            return
        percentage = round(
            (self.audio.speaker.volume / self.audio.max_volume) * 100)
        if self.audio.speaker.muted:
            icon = icons.volume_muted
        else:
            num_icons = len(self.volume_icons)
            range_per_icon = 100 // num_icons
            icon_index = min(percentage // range_per_icon, num_icons - 1)
            icon = self.volume_icons[icon_index]
        self.label.set_markup(icon)

    def on_clicked(self, *args: object) -> None:
        """Toggle the speaker mute state and update the icon."""
        self.audio.speaker.muted = not self.audio.speaker.muted
        self.set_icon()
        self.settings_notifier.notify_listeners(
            "volume-changed", round(self.audio.speaker.volume),
            not self.audio.speaker.muted)


class VolumeOutputsRevealer(Revealer):
    """Revealer widget to show/hide audio output options."""

    def __init__(self, **kwargs):
        super().__init__(
            name="outputs-box",
            transition_duration=250,
            transition_type="slide-down",
            child_revealed=False,
            h_expand=True,  # Add horizontal expansion
            **kwargs,
        )

        self.output_container = Box(
            spacing=4,
            orientation="v",
            name="outputs-container-box",
            h_expand=True,  # Make container expand horizontally
        )

        self.scrolled_box = ScrolledWindow(
            name="outputs-container",
            child=self.output_container,
            propagate_height=False,
            h_expand=True,
            min_content_size=(-1, 160),
            propagate_width=True,  # Ensure width propagation
            h_align="fill",  # Fill available space
        )
        self.add(self.scrolled_box)

        self.shown = False

    def toggle(self) -> None:
        """Toggle the visibility of the outputs box."""
        self.shown = not self.shown
        self.set_reveal_child(self.shown)

    def collapse(self) -> None:
        """Collapse the outputs box to hide it."""
        self.shown = False
        self.set_reveal_child(self.shown)


class VolumeRow(Box):
    """A horizontal row widget that contains the volume icon, slider, and output options."""

    def __init__(self, slot: Box = Box(), **kwargs):
        super().__init__(
            name="volume-row",
            orientation="h",
            spacing=12,
            h_expand=True,
            **kwargs,
        )

        self.slot = slot
        self.audio = Audio()
        self.outputs_box = VolumeOutputsRevealer()
        self.settings_notifier = SettingsBroker()  # type: ignore
        self.output_box_button = Button(
            style_classes=["volume-outputs-open-button"],
            child=Label(markup=icons.chevron_right),
            v_expand=True,
            h_align="center",
            v_align="center",
            on_clicked=lambda _: (self.outputs_box.toggle(), self.notify()),
        )

        self.audio.connect("notify::speaker", self.notify)
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.notify)

        self.volume_slider = VolumeSlider(self.audio, self.settings_notifier)
        self.volume_icon = VolumeIcon(self.audio, self.settings_notifier)

        self.add(self.volume_icon)
        self.add(self.volume_slider)
        self.add(self.output_box_button)
        self.slot.add(self.outputs_box)

    def notify(self, *args: object) -> None:
        """Update the list of available audio outputs."""
        self._clear_slot()
        for speaker in self.audio.get_speakers():
            self.add_output(speaker)

        if self.audio.speaker:
            self.volume_slider.on_speaker_changed()
            self.volume_icon.set_icon()
            self.volume_slider.on_new_speaker(*args)

            # Make sure the dropdown shows the correct selection
            self._highlight_active_output()

    def _clear_slot(self) -> None:
        """Clear the outputs container to remove old output buttons."""
        for child in self.outputs_box.output_container.get_children():
            self.outputs_box.output_container.remove(child)

    def _highlight_active_output(self) -> None:
        """Highlight the currently active output in the dropdown"""
        if not self.audio.speaker:
            return

        for child in self.outputs_box.output_container.get_children():
            # Use object identity instead of index
            if hasattr(child, "output") and child.output == self.audio.speaker:
                child.add_style_class("selected-output")
            else:
                child.remove_style_class("selected-output")

    def switch_to_output(self, output: object) -> None:
        """Change the audio output to the selected sink using shell commands"""
        if not output:
            return

        # Store the current volume
        current_vol = None
        if self.audio.speaker:
            current_vol = self.audio.speaker.volume

        # Get the sink name/ID from the output object
        sink_id = self._get_sink_id(output)
        if not sink_id:
            logger.error("Error: Could not determine sink ID for output")
            return

        # Use pactl to set the default sink
        command = f"pactl set-default-sink {sink_id}"
        exec_shell_command_async(command)

        # Move all sink inputs (running audio streams) to the new sink
        self._move_streams_to_sink(sink_id)

        # Close dropdown after selection
        self.outputs_box.toggle()

        # Update UI after a delay to allow PulseAudio to update
        GLib.timeout_add(300, self.notify)

    def _move_streams_to_sink(self, sink_id: str) -> None:
        """Move all audio streams to the specified sink"""
        # Create a lambda that handles just one output parameter
        callback = lambda output: self._on_sink_inputs_received(output, sink_id)

        # Call pactl to list all running audio streams
        exec_shell_command_async("pactl list short sink-inputs", callback)

    def _on_sink_inputs_received(self, output: str, sink_id: str) -> None:
        """Process sink inputs and move each to the new sink"""
        if not output:
            return

        # Parse each line to get sink input IDs
        for line in output.strip().split("\n"):
            if not line:
                continue

            parts = line.split()
            if parts:
                try:
                    # The first field is the sink input ID
                    stream_id = parts[0]
                    # Move this stream to the new sink
                    move_cmd = f"pactl move-sink-input {stream_id} {sink_id}"
                    exec_shell_command_async(move_cmd)
                except IndexError:
                    pass  # Skip malformed lines

    def _get_sink_id(self, output: object) -> str:
        """Extract the sink ID from the output object"""
        # Try different common properties that might contain the sink name/ID
        for attr in ["name", "id", "sink_name", "identifier", "index"]:
            if hasattr(output, attr):
                value = getattr(output, attr)
                if value is not None:
                    return str(value)

        # Try props dictionary if available
        if hasattr(output, "props"):
            for prop in ["name", "device.name", "alsa.name", "pulse.name"]:
                if hasattr(output.props, prop):  # type: ignore
                    value = getattr(output.props, prop)  # type: ignore
                    if value:
                        return str(value)

        # As a last resort, try __str__ in case it returns something useful
        return str(output)

    def add_output(self, output: object) -> None:
        """Add an audio output option to the outputs list"""
        # Get more descriptive name like HDMI/DisplayPort
        descriptive_name = self._get_descriptive_name(output)

        # Visual indicator for the currently active output - compare objects directly
        is_current = self.audio.speaker and output == self.audio.speaker

        # Create children list conditionally to avoid None values
        check_icon = (Label(markup=icons.check, h_expand=False)
                      if is_current else Label(h_expand=False))

        row = Box(
            children=[
                Label(
                    label=descriptive_name,
                    ellipsization="end",
                    h_expand=True,
                    h_align="start",
                    style_classes=["volume-entry-label"],
                ),
                check_icon,
            ],
            h_expand=True,
            h_align="fill",
            orientation="h",
        )

        button = Button(
            orientation="h",
            h_align="fill",
            h_expand=True,
            spacing=12,
            child=row,
            on_clicked=lambda _: self.switch_to_output(output),
        )

        # Store output reference for later use
        button.output = output

        button.add_style_class("volume-entry-button")
        if is_current:
            button.add_style_class("selected-output")

        self.outputs_box.output_container.add(button)

    def _get_descriptive_name(self, output: object) -> str:
        """Get a more descriptive name for the output similar to PulseAudio Volume Control"""
        # Try different properties to find the most descriptive name

        # First check if there's a description directly on the output
        if hasattr(output,
                   "description") and output.description:  # type: ignore
            return output.description  # type: ignore

        # Check if there's a display name property
        if hasattr(output,
                   "display_name") and output.display_name:  # type: ignore
            return output.display_name  # type: ignore

        # Check if there's a name property
        if hasattr(output, "name") and output.name:  # type: ignore
            return output.name  # type: ignore

        # Check if there are properties available
        if hasattr(output, "props"):
            # Common property in PulseAudio for friendly names
            if hasattr(output.props, "device_description"):  # type: ignore
                return output.props.device_description  # type: ignore

            # Try alternate properties
            for prop_name in ["description", "alsa.name", "device.description"]:
                if hasattr(output.props, prop_name):  # type: ignore
                    prop_value = getattr(output.props,
                                         prop_name)  # type: ignore
                    if prop_value:
                        return prop_value

        # Default: use a generic name if nothing else is available
        return "Audio Output"


class MicSlider(Scale):
    """Slider widget to control microphone volume."""

    def __init__(self, audio, settings_notifier, **kwargs):
        super().__init__(
            name="control-slider",
            orientation="h",
            h_expand=True,
            has_origin=True,
            increments=(0.01, 0.1),
            **kwargs,
        )
        self.audio = audio
        self.settings_notifier = settings_notifier
        self.audio.connect("notify::microphone", self.on_new_microphone)
        if self.audio.microphone:
            self.audio.microphone.connect("changed", self.on_microphone_changed)
        self.connect("value-changed", self.on_value_changed)
        self.add_style_class("mic")
        self.on_microphone_changed()

    def on_new_microphone(self, *args: object) -> None:
        """Handle new microphone connection."""
        if self.audio.microphone:
            self.audio.microphone.connect("changed", self.on_microphone_changed)
            self.on_microphone_changed()

    def on_value_changed(self, *args: object) -> None:
        """Update microphone volume when slider value changes."""
        if self.audio.microphone:
            self.audio.microphone.volume = self.value * 100

    def on_microphone_changed(self, *args: object) -> None:
        """Update slider value and style based on microphone state."""
        if not self.audio.microphone:
            return

        if self.audio.microphone.muted:
            self.add_style_class("muted")
        else:
            self.remove_style_class("muted")

        if self.value == round(self.audio.microphone.volume / 100, 2):
            return
        self.value = round(self.audio.microphone.volume / 100, 2)
        self.settings_notifier.notify_listeners("mic-changed",
                                                round(self.value * 100),
                                                not self.audio.microphone.muted)


class MicIcon(Button):
    """Button widget to toggle microphone mute state and display icon."""

    def __init__(self, audio: Audio, settings_notifier, **kwargs):
        super().__init__(name="volume-icon", **kwargs)
        self.audio = audio
        self.settings_notifier = settings_notifier
        self.value = 0
        self.hide_timer = None
        self.hover_counter = 0

        self.label = Label(
            name="volume-icon-label",
            markup=icons.mic,
        )
        self.connect("clicked", self.on_clicked)
        self.set_icon()
        self.add(self.label)

    def set_icon(self) -> None:
        """Set the icon based on the current microphone state."""
        if not self.audio or not self.audio.microphone:
            return
        if self.audio.microphone.muted:
            icon = icons.mic_muted
        else:
            icon = icons.mic
        self.label.set_markup(icon)

    def on_clicked(self, *args: object) -> None:
        """Toggle the microphone mute state and update the icon."""
        self.audio.microphone.muted = not self.audio.microphone.muted
        self.set_icon()
        self.settings_notifier.notify_listeners(
            "mic-changed", round(self.audio.microphone.volume),
            not self.audio.microphone.muted)


class MicInputsRevealer(Revealer):
    """Revealer widget to show/hide microphone input options."""

    def __init__(self, **kwargs):
        super().__init__(
            name="mic-inputs-box",
            transition_duration=250,
            transition_type="slide-down",
            child_revealed=False,
            h_expand=True,
            **kwargs,
        )

        self.input_container = Box(
            spacing=4,
            orientation="v",
            name="mic-inputs-container-box",
            h_expand=True,
        )

        self.scrolled_box = ScrolledWindow(
            name="mic-inputs-container",
            child=self.input_container,
            propagate_height=False,
            h_expand=True,
            h_scrollbar_policy="never",
            min_content_size=(-1, 150),
            propagate_width=True,
            h_align="fill",
        )
        self.add(self.scrolled_box)

        self.shown = False

    def collapse(self) -> None:
        """Collapse the inputs box to hide it."""
        self.shown = False
        self.set_reveal_child(self.shown)

    def toggle(self) -> None:
        """Toggle the visibility of the inputs box."""
        self.shown = not self.shown
        self.set_reveal_child(self.shown)


class MicRow(Box):
    """A horizontal row widget that contains the microphone icon, slider, and input options."""

    def __init__(self, slot: Box = Box(), **kwargs):
        super().__init__(
            name="mic-row",
            orientation="h",
            spacing=12,
            h_expand=True,
            visible=True,  # Start hidden by default
            **kwargs,
        )

        self.slot = slot
        self.audio = Audio()
        self.inputs_box = MicInputsRevealer()
        self.input_box_button = Button(
            style_classes=["volume-outputs-open-button"],
            child=Label(markup=icons.chevron_right),
            v_expand=True,
            h_align="center",
            v_align="center",
            on_clicked=lambda _:
            (self.inputs_box.toggle(), self.notify_inputs()),
        )
        self.settings_notifier = SettingsBroker()  # type: ignore
        self.mic_slider = MicSlider(self.audio, self.settings_notifier)
        self.mic_icon = MicIcon(self.audio, self.settings_notifier)

        # Connect to microphone change events
        self.audio.connect("notify::microphone", self.on_new_microphone)
        if self.audio.microphone:
            self.audio.microphone.connect("changed", self.on_microphone_changed)

        # Add UI elements
        self.add(self.mic_icon)
        self.add(self.mic_slider)
        self.add(self.input_box_button)
        self.slot.add(self.inputs_box)

        # Initialize microphone inputs
        GLib.timeout_add(500, self.notify_inputs)

    def on_new_microphone(self, *args: object) -> None:
        """Handle new microphone connection."""
        if self.audio.microphone:
            self.audio.microphone.connect("changed", self.on_microphone_changed)

            # Optional: check for the specific signal name your Audio class uses
            if hasattr(self.audio.microphone, "stream") and hasattr(
                    self.audio.microphone.stream, "connect"):
                self.audio.microphone.stream.connect(
                    "notify::microphone_changed", self.on_microphone_changed)

    def on_microphone_changed(self, *args: object) -> None:
        """Update the UI when the microphone state changes."""
        if not self.audio.microphone:
            return

        # Update UI based on microphone state
        self.mic_slider.on_microphone_changed()
        self.mic_icon.set_icon()
        self._highlight_active_input()

    def notify_inputs(self, *args: object) -> bool:
        """Update the list of available microphone inputs"""
        self._clear_inputs()

        # Get all available microphone/sound sources
        inputs = self.audio.microphones

        # Add each input to the dropdown
        for input_src in inputs:
            self.add_input(input_src)

        # Make sure the correct input is highlighted
        if self.audio.microphone:
            self._highlight_active_input()

        return False  # Don't repeat if called from timeout

    def _clear_inputs(self) -> None:
        """Clear the inputs container"""
        for child in self.inputs_box.input_container.get_children():
            self.inputs_box.input_container.remove(child)

    def _highlight_active_input(self) -> None:
        """Highlight the currently active microphone input"""
        if not self.audio.microphone:
            return

        for child in self.inputs_box.input_container.get_children():
            if (hasattr(child, "input_source") and
                    child.input_source == self.audio.microphone):
                child.add_style_class(
                    "selected-output")  # Reuse the same style class
            else:
                child.remove_style_class("selected-output")

    def switch_to_input(self, input_src: object) -> None:
        """Change the audio input to the selected source"""
        if not input_src:
            return

        # Get the source ID from the input object
        source_id = self._get_source_id(input_src)
        if not source_id:
            logger.error(f"Could not determine source ID for input {input_src}")
            return

        # Use pactl to set the default source
        command = f"pactl set-default-source {source_id}"
        exec_shell_command_async(command)

        # Move any recording streams to the new source
        self._move_recording_streams_to_source(source_id)

        # Close dropdown after selection
        self.inputs_box.toggle()

        # Update UI after a delay
        GLib.timeout_add(300, self.notify_inputs)

    def _move_recording_streams_to_source(self, source_id: str) -> None:
        """Move any recording streams to the new source"""
        # Create callback to handle the output
        callback = lambda output: self._on_source_outputs_received(
            output, source_id)

        # Call pactl to list all recording streams
        exec_shell_command_async("pactl list short source-outputs", callback)

    def _on_source_outputs_received(self, output: str, source_id: str) -> None:
        """Process source outputs and move each to the new source"""
        if not output:
            return

        for line in output.strip().split("\n"):
            if not line:
                continue

            parts = line.split()
            if parts:
                try:
                    # The first field is the source output ID
                    stream_id = parts[0]
                    # Move this recording stream to the new source
                    move_cmd = f"pactl move-source-output {stream_id} {source_id}"
                    exec_shell_command_async(move_cmd)
                except IndexError:
                    pass  # Skip malformed lines

    def _get_source_id(self, input_src: object) -> str:
        """Extract the source ID from the input object"""
        # Try different common properties
        for attr in ["name", "id", "source_name", "identifier", "index"]:
            if hasattr(input_src, attr):
                value = getattr(input_src, attr)
                if value is not None:
                    return str(value)

        # Try props dictionary if available
        if hasattr(input_src, "props"):
            for prop in ["name", "device.name", "alsa.name", "pulse.name"]:
                if hasattr(input_src.props, prop):  # type: ignore
                    value = getattr(input_src.props, prop)  # type: ignore
                    if value:
                        return str(value)

        # Last resort: try string representation
        return str(input_src)

    def add_input(self, input_src: object) -> None:
        """Add a microphone input to the inputs list"""
        # Get descriptive name for the input
        descriptive_name = self._get_descriptive_name(input_src)

        # Visual indicator for current input
        is_current = self.audio.microphone and input_src == self.audio.microphone
        check_icon = (Label(markup=icons.check, h_expand=False)
                      if is_current else Label(h_expand=False))

        row = Box(
            children=[
                Label(
                    label=descriptive_name,
                    ellipsization="end",
                    h_expand=True,
                    h_align="start",
                    style_classes=["volume-entry-label"],
                ),
                check_icon,
            ],
            h_expand=True,
            h_align="fill",
            orientation="h",
        )

        button = Button(
            orientation="h",
            h_align="fill",
            h_expand=True,
            spacing=12,
            child=row,
            on_clicked=lambda _: self.switch_to_input(input_src),
        )

        button.input_source = input_src

        button.add_style_class("volume-entry-button")
        if is_current:
            button.add_style_class("selected-output")

        self.inputs_box.input_container.add(button)

    def _get_descriptive_name(self, input_src: object) -> str:
        """Get a more descriptive name for the input source"""
        # Try different properties to find the most descriptive name

        # First check if there's a description directly on the input
        if hasattr(input_src,
                   "description") and input_src.description:  # type: ignore
            return input_src.description  # type: ignore

        # Check for display_name
        if hasattr(input_src,
                   "display_name") and input_src.display_name:  # type: ignore
            return input_src.display_name  # type: ignore

        # Check for name
        if hasattr(input_src, "name") and input_src.name:  # type: ignore
            return input_src.name  # type: ignore

        # Check property dictionary
        if hasattr(input_src, "props"):
            if hasattr(input_src.props, "device_description"):  # type: ignore
                return input_src.props.device_description  # type: ignore

            # Try other common properties
            for prop_name in ["description", "alsa.name", "device.description"]:
                if hasattr(input_src.props, prop_name):  # type: ignore
                    prop_value = getattr(input_src.props,
                                         prop_name)  # type: ignore
                    if prop_value:
                        return prop_value

        # Default name
        return "Microphone Input"
