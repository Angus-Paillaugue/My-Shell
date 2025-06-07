from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.utils import exec_shell_command_async, exec_shell_command
from gi.repository import GLib
import modules.icons as icons
from fabric.core.fabricator import Fabricator


class PowerProfile(Box):

    def __init__(self, **kwargs):
        super().__init__(
            name="power-profile",
            orientation="h",
            h_align="fill",
            margin=8,
            **kwargs,
        )

        self.profiles = [
            {
                "name": "balanced",
                "label": "Balanced",
                "icon": icons.balanced
            },
            {
                "name": "throughput-performance",
                "label": "Performance",
                "icon": icons.performance,
            },
            {
                "name": "powersave",
                "label": "Eco",
                "icon": icons.eco
            },
        ]

        self.active_profile = self.profiles[0]  # Default to the first profile

        # Placeholder for WiFi module content
        self.profile_icon = Label(name="power-profile-icon",
                                  markup=self.active_profile["icon"])
        self.profile_name = Label(name="power-profile-name",
                                  label=self.active_profile["label"])

        self.button = Button(
            name="power-profile-button",
            child=Box(
                spacing=12,
                children=[self.profile_icon, self.profile_name],
                orientation="h",
            ),
            on_clicked=lambda b: self.rotate_profile(),
        )
        self.add(self.button)

        self.power_profile_fabricator = Fabricator(
            poll_from=lambda v: self.get_profile(),
            on_changed=lambda f, v: self.update_ui,
            interval=1000,
            stream=False,
            default_value=0,
        )
        self.power_profile_fabricator.changed.connect(self.update_ui)
        GLib.idle_add(self.update_ui, None, self.get_profile())

    def update_ui(self, *args):
        """Update the UI to reflect the current power profile."""
        self.profile_icon.set_markup(self.active_profile["icon"])
        self.profile_name.set_label(self.active_profile["label"])
        self.add_style_class(self.active_profile["name"])

    def get_profile(self):
        res = exec_shell_command("tuned-adm active")
        if res:
            profile_name = res.split(":")[1].strip()
            for profile in self.profiles:
                if profile["name"] == profile_name:
                    self.active_profile = profile
                    return profile_name
        return None  # Return None if no profile matches or command fails

    def rotate_profile(self):
        """Rotate through the available power profiles."""
        current_index = self.profiles.index(self.active_profile)
        next_index = (current_index + 1) % len(self.profiles)
        self.active_profile = self.profiles[next_index]

        # Update the UI to reflect the new profile
        self.update_ui()

        # Apply the new profile using tuned-adm
        exec_shell_command_async(
            f"tuned-adm profile {self.active_profile['name']}",
            lambda _: None,
        )
