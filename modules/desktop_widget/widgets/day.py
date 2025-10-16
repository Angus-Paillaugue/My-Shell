from time import strftime
from fabric.widgets.label import Label
from fabric.widgets.box import Box
from ..source import DesktopWidget

class DayWidget(DesktopWidget):
  def __init__(self, **kwargs):
        super().__init__(
            anchor="top left",
            **kwargs,
        )
        week_day = strftime("%A").upper()
        day = strftime("%d %B %Y")
        week_day_label = Label(label=week_day, name="desktop-widget-day-week-day")
        day_label = Label(label=day, name="desktop-widget-day-day")
        self.add(
          Box(
            orientation="vertical",
            style_classes=["desktop-widget-day"],
            visible=True,
            all_visible=True,
            children=[
                week_day_label,
                day_label,
            ]
          )
        )
