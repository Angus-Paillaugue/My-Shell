from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.circularprogressbar import CircularProgressBar
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

        self.thresholds = {
            'cpu': {    # CPU usage thresholds in percentage
                'warning': 70,
                'danger': 90,
            },
            'ram': {    # RAM usage thresholds in percentage
                'warning': 70,
                'danger': 90,
            },
            'disk': {    # Disk usage thresholds in percentage
                'warning': 70,
                'danger': 90,
            },
            'temp': {    # Temperature thresholds in Celsius
                'warning': 70,
                'danger': 85,
            },
        }

        self.main_box = Box(
            name="metrics-main-box",
            orientation="h",
            spacing=12,
            v_align="center",
            h_align="center",
        )
        self.add(self.main_box)

        self.cpu = CircularProgressBar(
            value=0,
            size=30,
            line_width=2,
            start_angle=150,
            end_angle=390,
            style_classes=['metrics-progress-bar'],
            child=Label(markup=icons.cpu),
        )
        self.ram = CircularProgressBar(
            value=0,
            size=30,
            line_width=2,
            start_angle=150,
            end_angle=390,
            style_classes=['metrics-progress-bar'],
            child=Label(
                name="ram-label",
                markup=
                "<span font-family='JetBrainsMono Nerd Font' font-weight='normal'> </span>",
            ),
        )
        self.temp = CircularProgressBar(
            value=0,
            size=30,
            line_width=2,
            start_angle=150,
            end_angle=390,
            style_classes=['metrics-progress-bar'],
            child=Label(markup=icons.temperature),
        )
        self.main_box.add(self.cpu)
        self.main_box.add(self.ram)
        self.main_box.add(self.temp)

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
        cpu, ram, temp = metrics

        self.cpu.set_value(cpu / 100)
        self.cpu.set_tooltip_text(f"{cpu:.1f}%")
        self.cpu.add_style_class(
            "danger" if self.thresholds["cpu"]["danger"] <= cpu else (
                "warning" if self.thresholds["cpu"]["warning"] <=
                cpu else "normal"))

        self.ram.set_value(ram / 100)
        self.ram.set_tooltip_text(f"{ram:.1f}%")
        self.ram.add_style_class(
            "danger" if self.thresholds["ram"]["danger"] <= ram else (
                "warning" if self.thresholds["ram"]["warning"] <=
                ram else "normal"))

        self.temp.set_value(temp / 100)
        self.temp.set_tooltip_text(f"{temp:.0f}°C")
        self.temp.add_style_class(
            "danger" if self.thresholds["temp"]["danger"] <= temp else (
                "warning" if self.thresholds["temp"]["warning"] <=
                temp else "normal"))
