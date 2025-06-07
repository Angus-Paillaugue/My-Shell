import gi
from fabric.widgets.datetime import DateTime
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.box import Box
from fabric.utils.helpers import invoke_repeater
import time
import calendar
from datetime import datetime
from gi.repository import Gdk, Gtk, GLib
from collections.abc import Iterable
from fabric.core.service import Property
from fabric.widgets.wayland import WaylandWindow
import modules.icons as icons
from services.logger import logger


class CalendarDropdown(WaylandWindow):
    def __init__(self, parent_button, **kwargs):
        super().__init__(
            layer="overlay",
            anchor="top left",
            exclusivity="none",
            visible=False,
            name="calendar-dropdown",
            margin="0 0 0 8px",
            **kwargs,
        )

        self.parent_button = parent_button
        self.parent_box = parent_button.get_parent()

        self.current_date = datetime.now()

        # Create main container with background styling
        self.calendar_container = Box(
            name="calendar-container",
            orientation="v",
            spacing=8,
            margin=12,  # Increased margin for better visual appearance
        )

        # Month navigation bar
        self.month_nav = Box(
            name="month-navigation",
            orientation="h",
            spacing=8,
        )

        self.prev_month_btn = Button(
            name="calendar-nav-button",
            child=Label(name="calendar-nav-button-icon", markup=icons.chevron_left),
            on_clicked=self.prev_month,
            h_align="start",  # Align to the left edge
        )

        self.month_label = Label(
            name="month-year-label",
            label=self.current_date.strftime("%B %Y"),
            h_align="center",  # Center the text
            h_expand=True,  # Make the label expand to fill available space
        )

        self.next_month_btn = Button(
            name="calendar-nav-button",
            child=Label(name="calendar-nav-button-icon", markup=icons.chevron_right),
            on_clicked=self.next_month,
            h_align="end",  # Align to the right edge
        )

        # Add elements to the container with appropriate packing
        self.month_nav.pack_start(
            self.prev_month_btn, False, False, 0
        )  # Don't expand or fill
        self.month_nav.pack_start(self.month_label, True, True, 0)  # Expand and fill
        self.month_nav.pack_start(
            self.next_month_btn, False, False, 0
        )  # Don't expand or fill

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
                )
            )

        # Calendar grid
        self.calendar_grid = Box(
            name="calendar-grid",
            orientation="v",
            spacing=4,
        )

        # Add containers to main calendar container
        self.calendar_container.add(self.month_nav)
        self.calendar_container.add(self.days_header)
        self.calendar_container.add(self.calendar_grid)

        # Add calendar container to window
        self.add(self.calendar_container)

        # Render initial calendar
        self.render_calendar()

    def render_calendar(self):
        # Clear existing calendar grid
        for child in self.calendar_grid.get_children():
            self.calendar_grid.remove(child)

        # Get calendar data
        year = self.current_date.year
        month = self.current_date.month
        today = (
            datetime.now().day
            if datetime.now().year == year and datetime.now().month == month
            else -1
        )

        # Update month label
        self.month_label.set_label(self.current_date.strftime("%B %Y"))

        # Get calendar matrix
        cal = calendar.monthcalendar(year, month)

        # Create calendar grid with days
        for week in cal:
            week_box = Box(
                name="week-row",
                orientation="h",
                spacing=4,
            )

            for day in week:
                if day == 0:
                    # Empty day
                    day_btn = Button(
                        name="empty-day",
                        label=" ",
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

                week_box.add(day_btn)

            self.calendar_grid.add(week_box)

        self.calendar_grid.show_all()

    def prev_month(self, *args):
        # Go to previous month
        year = self.current_date.year
        month = self.current_date.month - 1

        if month == 0:
            month = 12
            year -= 1

        self.current_date = self.current_date.replace(year=year, month=month)
        self.render_calendar()

    def next_month(self, *args):
        # Go to next month
        year = self.current_date.year
        month = self.current_date.month + 1

        if month == 13:
            month = 1
            year += 1

        self.current_date = self.current_date.replace(year=year, month=month)
        self.render_calendar()

    def toggle_visibility(self):
        try:
            if self.is_visible():
                self.hide()
            else:
                # Update parent_box reference if it was None initially
                if not self.parent_box and self.parent_button:
                    self.parent_box = self.parent_button.get_parent()

                self.show_all()
                # Make sure window has focus
                self.present()
        except Exception as e:
            logger.error(f"Error toggling calendar visibility: {e}")


class Time(Button):
    @Property(tuple[str, ...], "read-write")
    def formatters(self):
        return self._formatters

    @formatters.setter
    def formatters(self, value: str | Iterable[str]):
        if isinstance(value, (tuple, list)):
            self._formatters = tuple(value)
        elif isinstance(value, str):
            self._formatters = (value,)
        if len(self._formatters) < 1:
            self._formatters = ("%I:%M %p", "%d-%m-%Y")
        return

    @Property(int, "read-write")
    def interval(self):
        return self._interval

    @interval.setter
    def interval(self, value: int):
        self._interval = value
        if self._repeater_id:
            GLib.source_remove(self._repeater_id)
        self._repeater_id = invoke_repeater(self._interval, self.do_update_label)
        self.do_update_label()
        return

    def __init__(
        self,
        interval: int = 1000,
        **kwargs,
    ):
        super().__init__(
            name="time",
            style_classes=["bar-item"],
            **kwargs,
        )

        self.add_events(Gdk.EventMask.SCROLL_MASK)
        self._formatters: tuple[str, ...] = tuple()
        self._current_index: int = 0
        self._interval: int = interval
        self._repeater_id: int | None = None

        self.formatters = ("%H:%M:%S", "%d-%m-%Y")
        self.interval = interval

        # Connect events first
        self.connect(
            "button-press-event",
            lambda *args: self.do_handle_press(*args),  # to allow overriding
        )
        self.connect("scroll-event", lambda *args: self.do_handle_scroll(*args))

        # Create calendar dropdown with a delay to ensure the button is realized
        GLib.timeout_add(100, self.setup_calendar_dropdown)

    def setup_calendar_dropdown(self):
        # Create calendar dropdown after button is realized
        self.calendar_dropdown = CalendarDropdown(self)
        return False  # Stop the timeout

    def toggle_calendar(self):
        if hasattr(self, "calendar_dropdown"):
            self.calendar_dropdown.toggle_visibility()
        else:
            # If calendar isn't ready yet, create it now
            self.calendar_dropdown = CalendarDropdown(self)
            GLib.timeout_add(100, lambda: self.calendar_dropdown.toggle_visibility())

    def update_time(self):
        current_time = time.strftime("%H:%M:%S", time.localtime())
        self.time_label.set_label(current_time)

    def do_format(self) -> str:
        return time.strftime(self._formatters[self._current_index])

    def do_update_label(self):
        self.set_label(self.do_format())
        return True

    def do_check_invalid_index(self, index: int) -> bool:
        return (index < 0) or (index > (len(self.formatters) - 1))

    def do_cycle_next(self):
        self._current_index = self._current_index + 1
        if self.do_check_invalid_index(self._current_index):
            self._current_index = 0  # reset tags

        return self.do_update_label()

    def do_cycle_prev(self):
        self._current_index = self._current_index - 1
        if self.do_check_invalid_index(self._current_index):
            self._current_index = len(self.formatters) - 1

        return self.do_update_label()

    def do_handle_press(self, _, event, *args):
        match event.button:
            case 1:  # left click
                self.toggle_calendar()
            case 2:  # middle click
                self.do_cycle_next()
            case 3:  # right click
                self.do_cycle_prev()
        return

    def do_handle_scroll(self, _, event, *args):
        match event.direction:
            case Gdk.ScrollDirection.UP:  # scrolling up
                self.do_cycle_next()
            case Gdk.ScrollDirection.DOWN:  # scrolling down
                self.do_cycle_prev()
        return
