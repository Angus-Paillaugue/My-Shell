import psutil
from gi.repository import GLib


class MetricsProvider:
    """
    Class responsible for obtaining centralized CPU, memory, disk usage, and battery metrics.
    It updates periodically so that all widgets querying it display the same values.
    """

    def __init__(self):
        self.cpu = 0.0
        self.mem = 0.0
        self.temp = 0.0
        self.disk = []

        self.bat_percent = 0.0
        self.bat_charging = None

        GLib.timeout_add_seconds(1, self._update)

    def _update(self):
        self.cpu = psutil.cpu_percent(interval=0)
        self.mem = psutil.virtual_memory().percent
        self.disk = [psutil.disk_usage(path).percent for path in ["/"]]
        self.temp = psutil.sensors_temperatures()["coretemp"][0]
        temps = psutil.sensors_temperatures()["coretemp"]
        core_temps = [t.current for t in temps if t.label.startswith("Core")]
        self.temp = sum(core_temps) / len(core_temps)

        battery = psutil.sensors_battery()
        if battery is None:
            self.bat_percent = 0.0
            self.bat_charging = None
        else:
            self.bat_percent = battery.percent
            self.bat_charging = battery.power_plugged

        return True

    def get_metrics(self):
        return (self.cpu, self.mem, self.temp, self.disk)

    def get_battery(self):
        return (self.bat_percent, self.bat_charging)


shared_provider = MetricsProvider()
