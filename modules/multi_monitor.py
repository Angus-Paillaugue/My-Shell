import json
import subprocess
from typing import List, TypedDict

from fabric.hyprland.widgets import get_hyprland_connection
from fabric.notifications.service import Notifications

from modules.bar import Bar
from modules.corners import Corners
from modules.desktop_widget.registry import DesktopWidgetRegistry
from modules.notch import NotchWindow
from modules.notification import NotificationHistory, NotificationPopup
from modules.osd import OSD
from services.config import config


class MonitorType(TypedDict):
  id: int
  name: str
  width: int
  height: int
  x: int
  y: int
  focused: bool
  scale: float
  primary: bool

class MultiMonitorManager:
  def __init__(self):
    self.notification_server = Notifications()
    self.notification_history = NotificationHistory(
        notification_server=self.notification_server)
    self._monitors: List[MonitorType] = []
    self._multi_monitor_components = []
    self._single_monitor_components = []
    self._conn = get_hyprland_connection()
    self._set_monitors_infos()
    self._spawn_single_monitor_components()
    self._spawn_multi_monitors_components()
    if config['MULTI_MONITOR']:
      self._conn.connect("event::monitoradded", self._on_monitors_changed)
      self._conn.connect("event::monitorremoved", self._on_monitors_changed)

  def _on_monitors_changed(self, *args):
    """Handle monitor configuration changes."""
    old_primary = self.get_primary_monitor()
    self._set_monitors_infos()
    new_primary = self.get_primary_monitor()
    if old_primary != new_primary:
      self._move_single_monitor_components_to_primary()
    self._spawn_multi_monitors_components()

  def _spawn_single_monitor_components(self):
    """Set single monitor components to primary monitor."""
    primary_monitor = self.get_primary_monitor()
    primary_monitor_id = primary_monitor['id'] if primary_monitor else 0
    notification = NotificationPopup(
        notification_server=self.notification_server,
        notification_history=self.notification_history,
        monitor=primary_monitor_id
    )
    notch = NotchWindow(notification_history=self.notification_history, monitor=primary_monitor_id)
    osd = OSD(monitor=primary_monitor_id)
    widget_registry = DesktopWidgetRegistry(monitor=primary_monitor_id)
    self._single_monitor_components = [
        notification,
        notch,
        osd,
        *widget_registry.all_widgets()
    ]

  def _move_single_monitor_components_to_primary(self):
    """Move single monitor components to the primary monitor."""
    self._clear_single_monitor_components()
    self._spawn_single_monitor_components()

  def _spawn_multi_monitors_components(self):
    """Spawn bars and corners for each monitor based on configuration."""
    self._clear_multi_monitor_components()
    if not config['MULTI_MONITOR']:
      primary_monitor = self.get_primary_monitor()
      bar = Bar(monitor=primary_monitor['id'] if primary_monitor else 0)
      corners = Corners(monitor=primary_monitor['id'] if primary_monitor else 0)
      self._multi_monitor_components.append(bar)
      self._multi_monitor_components.append(corners)
    else:
      for monitor in self._monitors:
        monitor_id = monitor['id']
        bar = Bar(monitor=monitor_id)
        corners = Corners(monitor=monitor_id)
        self._multi_monitor_components.append(bar)
        self._multi_monitor_components.append(corners)

  def _clear_multi_monitor_components(self) -> None:
    """Destroy and clear existing components."""
    for comp in self._multi_monitor_components:
      comp.destroy()
    self._multi_monitor_components.clear()
    self._multi_monitor_components = []

  def _clear_single_monitor_components(self) -> None:
    """Destroy and clear existing single monitor components."""
    for comp in self._single_monitor_components:
      comp.destroy()
    self._single_monitor_components.clear()
    self._single_monitor_components = []

  def _set_monitors_infos(self) -> None:
    """Initialize monitor information from Hyprland."""
    self._monitors = []
    result = subprocess.run(
        ["hyprctl", "monitors", "-j"],
        capture_output=True,
        text=True,
        check=True
    )
    hypr_monitors = json.loads(result.stdout)

    for i, monitor in enumerate(hypr_monitors):
        monitor_name = monitor.get('name', f'monitor-{i}')

        # Get scale directly from Hyprland (more reliable)
        hypr_scale = monitor.get('scale', 1.0)

        self._monitors.append({
            'id': i,
            'name': monitor_name,
            'width': monitor.get('width', 1920),
            'height': monitor.get('height', 1080),
            'x': monitor.get('x', 0),
            'y': monitor.get('y', 0),
            'focused': monitor.get('focused', False),
            'scale': hypr_scale,
            'primary': i == 0
        })

  def get_primary_monitor(self) -> MonitorType | None:
    """Return the primary monitor information."""
    return next((m for m in self._monitors if m['primary']), None)

  def get_components(self):
    """Return the list of bar and corner components."""
    return [*self._multi_monitor_components, *self._single_monitor_components]
