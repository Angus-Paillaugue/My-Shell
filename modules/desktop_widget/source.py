from fabric.widgets.wayland import WaylandWindow as Window

class DesktopWidget(Window):
  def __init__(self, **kwargs):
    defaults = {
        "layer": "background",
        "anchor": "center center",
        "exclusivity": "none",
        "visible": True,
        "all_visible": True,
    }
    for key, value in defaults.items():
        kwargs.setdefault(key, value)
    super().__init__(
        **kwargs,
    )
