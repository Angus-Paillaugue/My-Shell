from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
import modules.icons as icons
from services.metrics import shared_provider
from fabric.core.fabricator import Fabricator
from gi.repository import GLib


class Metrics(Button):

    def __init__(self, **kwargs):
        super().__init__(
            visible=True,
            **kwargs,
        )
        self.main_box = Box(
            name="metrics-main-box",
            orientation="h",
            spacing=12,
            v_align="center",
            h_align="center",
            style_classes=["bar-item"],
        )
        self.add(self.main_box)

        # CPU
        self.cpu_percentage = Label(
            name="cpu-percentage",
            label="0%",
        )
        self.cpu_container = Box(
            name="cpu-container",
            orientation="h",
            spacing=4,
            v_align="center",
            h_align="center",
            children=[
                Label(name="cpu-label", markup=icons.cpu), self.cpu_percentage
            ],
        )
        self.main_box.add(self.cpu_container)

        # RAM
        self.mem_percentage = Label(
            name="mem-percentage",
            label="0%",
        )
        self.mem_container = Box(
            name="mem-container",
            orientation="h",
            spacing=4,
            v_align="center",
            h_align="center",
            children=[
                Label(
                    name="memory-label",
                    markup=
                    "<span font-family='JetBrainsMono Nerd Font' font-weight='normal'> </span>",
                ),
                self.mem_percentage,
            ],
        )
        self.main_box.add(self.mem_container)

        # Temperature
        self.temp_level = Label(
            name="temp-level",
            markup=icons.temperature,
        )
        self.temp_container = Box(
            name="cpu-container",
            orientation="h",
            spacing=4,
            v_align="center",
            h_align="center",
            children=[
                Label(name="temp-label", markup=icons.temperature),
                self.temp_level,
            ],
        )
        self.main_box.add(self.temp_container)

        self.metrics_fabricator = Fabricator(
            poll_from=lambda v: shared_provider.get_metrics(),
            on_changed=lambda f, v: self.update_metrics,
            interval=1000,
            stream=False,
            default_value=0,
        )
        self.metrics_fabricator.changed.connect(self.update_metrics)
        GLib.idle_add(self.update_metrics, None, shared_provider.get_metrics())

    def update_metrics(self, sender, metrics):
        cpu, mem, temp, disk = metrics
        self.cpu_percentage.set_label("{:.0f}%".format(cpu))
        self.mem_percentage.set_label("{:.0f}%".format(mem))
        self.temp_level.set_label("{:.0f}°C".format(temp))
