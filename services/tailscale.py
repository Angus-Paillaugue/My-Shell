import json
import subprocess
from typing import Literal

from gi.repository import GLib  # type: ignore

status = Literal["down", "up"]

class TailscaleProvider:
    """
    Class responsible for obtaining centralized CPU, memory and battery metrics.
    It updates periodically so that all widgets querying it display the same values.
    """

    def __init__(self):
        self.status: status = "down"

        GLib.timeout_add_seconds(1, self._update)

    def _update(self):
        res = subprocess.run("tailscale status --json --self --active", capture_output=True, text=True, shell=True)
        if res.returncode == 0:
            json_output = json.loads(res.stdout)
            running = json_output['BackendState'] == "Running"
            self.status = "up" if running else "down"
        else:
            self.status = "down"

        return True

    def get_status(self) -> status:
        return self.status

    def toggle(self) -> status:
        status = self.status
        if status == "up":
            status = "down"
        else:
            status = "up"
        subprocess.run(f"tailscale {status}", shell=True)
        return status
