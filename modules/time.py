import calendar
import time
from datetime import datetime

from fabric.core.service import Property
from fabric.utils.helpers import invoke_repeater
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from gi.repository import Gdk, GLib, Gtk

import modules.icons as icons
from services.config import config


class CalendarBox(Box):
    """Widget that displays a calendar with month navigation and day buttons."""

    def __init__(self, **kwargs):
        super().__init__(name="calendar-container",
                         orientation="v",
                         spacing=8,
                         **kwargs)

        self.current_date = datetime.now()

        # Month navigation bar
        self.month_nav = Box(
            name="month-navigation",
            orientation="h",
            spacing=8,
        )

        self.prev_month_btn = Button(
            name="calendar-nav-button",
            style_classes=["bar-action-button", "small"],
            child=Label(name="calendar-nav-button-icon",
                        markup=icons.chevron_left),
            on_clicked=self.prev_month,
            h_align="start",
        )

        self.month_label = Label(
            name="month-year-label",
            label=self.current_date.strftime("%B %Y"),
            h_align="center",
            h_expand=True,
        )

        self.next_month_btn = Button(
            name="calendar-nav-button",
            style_classes=["bar-action-button", "small"],
            child=Label(name="calendar-nav-button-icon",
                        markup=icons.chevron_right),
            on_clicked=self.next_month,
            h_align="end",
        )

        # Add elements to the container with appropriate packing
        self.month_nav.pack_start(self.prev_month_btn, False, False, 0)
        self.month_nav.pack_start(self.month_label, True, True, 0)
        self.month_nav.pack_start(self.next_month_btn, False, False, 0)

        # Days of week header
        self.days_header = Box(
            name="days-header",
            orientation="h",
            spacing=4,
        )

        for day in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]:
            self.days_header.add(
                Label(
                    name="day-label",
                    label=day,
                    h_align="center",
                    h_expand=True,
                ))

        # Calendar grid - convert from Box to Gtk.Grid
        self.calendar_grid = Gtk.Grid(
            name="calendar-grid",
            column_spacing=4,
            row_spacing=4,
            column_homogeneous=True,
            row_homogeneous=True,
        )

        # Add containers to main calendar container
        self.add(self.month_nav)
        self.add(self.days_header)
        self.add(self.calendar_grid)
        self.render_calendar()

    def render_calendar(self) -> None:
        """Render the calendar for the current month."""
        # Clear existing calendar grid
        for child in self.calendar_grid.get_children():
            self.calendar_grid.remove(child)

        # Get calendar data
        year = self.current_date.year
        month = self.current_date.month
        today = (datetime.now().day if datetime.now().year == year and
                 datetime.now().month == month else -1)

        # Update month label
        self.month_label.set_label(self.current_date.strftime("%B %Y"))

        # Get calendar matrix
        cal = calendar.monthcalendar(year, month)

        # Create calendar grid with days - use grid positioning instead of week boxes
        for row_idx, week in enumerate(cal):
            for col_idx, day in enumerate(week):
                if day == 0:
                    # Empty day
                    day_btn = Button(
                        name="empty-day",
                        child=Label(name="empty-day-label", markup=icons.point),
                        h_expand=True,
                    )
                elif day == today:
                    # Today
                    day_btn = Button(
                        name="today-button",
                        label=str(day),
                        h_expand=True,
                    )
                else:
                    # Regular day
                    day_btn = Button(
                        name="day-button",
                        label=str(day),
                        h_expand=True,
                    )

                # Attach the button to the grid at the specific position
                self.calendar_grid.attach(day_btn, col_idx, row_idx, 1, 1)

        self.calendar_grid.show_all()

    def prev_month(self, *args: object) -> None:
        """Navigate to the previous month."""
        # Go to previous month
        year = self.current_date.year
        month = self.current_date.month - 1

        if month == 0:
            month = 12
            year -= 1

        self.current_date = self.current_date.replace(year=year, month=month)
        self.render_calendar()

    def next_month(self, *args: object) -> None:
        # Go to next month
        year = self.current_date.year
        month = self.current_date.month + 1

        if month == 13:
            month = 1
            year += 1

        self.current_date = self.current_date.replace(year=year, month=month)
        self.render_calendar()


class Time(Button):
    """A button that displays the current time and date, updating at a set interval."""

    @Property(int, "read-write")
    def interval(self):
        return self._interval

    @interval.setter
    def interval(self, value: int):
        self._interval = value
        if self._repeater_id:
            GLib.source_remove(self._repeater_id)
        self._repeater_id = invoke_repeater(self._interval, self.do_update_time)
        self.do_update_time()
        return

    def __init__(
        self,
        interval: int = 1000,
        **kwargs,
    ):
        super().__init__(
            style_classes=[
                "bar-item",
                (
                    "horizontal"
                    if config.BAR_POSITION in ["top", "bottom"]
                    else "vertical"
                ),
            ],
            v_expand=True,
            h_expand=True,
            **kwargs,
        )

        self.time_label = Label(
            name="time-label",
            label="",
            v_expand=False,
            h_align="center",
            v_align="center",
        )
        self.date_label = Label(
            name="date-label",
            label="",
            h_align="center",
            v_align="center",
            visible=config.BAR_POSITION in ["top", "bottom"],
        )
        self.add(
            Box(
                orientation="h",
                spacing=8,
                v_expand=False,
                h_expand=False,
                v_align="center",
                h_align="center",
                children=[self.date_label, self.time_label],
            )
        )

        self.add_events(Gdk.EventMask.SCROLL_MASK)
        self._interval: int = interval
        self._repeater_id: int | None = None
        self.interval = interval

    def set_button_label(self) -> None:
        """Set the button label to the current time and date."""
        if config.BAR_POSITION in ["left", "right"]:
            current_time = time.strftime("%H\n%M", time.localtime())
        else:
            current_time = time.strftime("%H:%M:%S", time.localtime())
            current_date = time.strftime("%b %d", time.localtime())
            self.date_label.set_label(current_date)

        self.time_label.set_label(current_time)

    def do_update_time(self) -> bool:
        """Update the time label and date label."""
        self.set_button_label()
        return True
