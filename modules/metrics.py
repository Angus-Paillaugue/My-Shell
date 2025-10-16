from fabric.core.fabricator import Fabricator
from fabric.widgets.box import Box
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.label import Label
from gi.repository import GLib  # type: ignore

import modules.icons as icons
from services.config import config
from services.metrics import shared_provider


class Metrics(Box):
    """Widget that displays system metrics such as CPU, RAM, and temperature."""

    def __init__(self, **kwargs):
        orientation = ("horizontal" if config['POSITIONS']['BAR']
                       in ["top", "bottom"] else "vertical")
        super().__init__(
            visible=True,
            style_classes=[
                "bar-item",
                orientation,
            ],
            name="metrics-main-box",
            spacing=12,
            v_align="center",
            h_align="center",
            orientation=orientation,
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
            'temp': {    # Temperature thresholds in Celsius
                'warning': 70,
                'danger': 85,
            },
        }

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
            child=Label(name="ram-label", markup=icons.memory),
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
        self.add(self.cpu)
        self.add(self.ram)
        self.add(self.temp)

        self.metrics_fabricator = Fabricator(
            poll_from=lambda v: shared_provider.get_metrics(),
            on_changed=lambda f, v: self.update_metrics,
            interval=1000,
            stream=False,
            default_value=0,
        )
        self.metrics_fabricator.connect("changed", self.update_metrics)
        GLib.idle_add(self.update_metrics, None, shared_provider.get_metrics())

    def update_metrics(self, sender, metrics: tuple[float, float,
                                                    float]) -> None:
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
