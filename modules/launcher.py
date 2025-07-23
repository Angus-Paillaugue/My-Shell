import json
import math
import os
import re
import subprocess
from collections.abc import Iterator

import numpy as np
from fabric.utils import (DesktopApp, get_desktop_applications, idle_add,
                          remove_handler)
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.entry import Entry
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.scrolledwindow import ScrolledWindow
from gi.repository import Gdk, GLib  # type: ignore

import modules.icons as icons
from modules.dock import pinned_aps_location
from services.config import config
from services.interfaces import NotchWidgetInterface
from services.logger import logger


class AppLauncher(Box, NotchWidgetInterface):
    """Application launcher widget that allows searching and launching applications."""

    def __init__(self, **kwargs):
        super().__init__(
            spacing=10,
            orientation="v",
            **kwargs,
        )
        self.selected_index = -1

        self._arranger_handler: int = 0
        self._all_apps = get_desktop_applications()

        CACHE_DIR = str(GLib.get_user_cache_dir()) + f"/{config.APP_NAME}"
        self.calc_history_path = f"{CACHE_DIR}/calc.json"
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
        if os.path.exists(self.calc_history_path):
            with open(self.calc_history_path, "r") as f:
                self.calc_history = json.load(f)
        else:
            self.calc_history = []

        with open(pinned_aps_location, "r") as f:
            self.pinned_apps = json.load(f)

        self.viewport = Box(name="viewport", spacing=4, orientation="v")
        self.search_entry = Entry(
            name="search-entry",
            placeholder="Search Applications...",
            h_expand=True,
            h_align="fill",
            notify_text=self.notify_text,
            on_activate=lambda entry, *_: self.on_search_entry_activate(
                entry.get_text()),
            on_key_press_event=self.on_search_entry_key_press,
        )
        self.search_entry.props.xalign = 0.5 # type: ignore
        self.scrolled_window = ScrolledWindow(
            name="notch-scrolled-window",
            spacing=10,
            h_expand=True,
            v_expand=True,
            h_align="fill",
            v_align="fill",
            child=self.viewport,
            propagate_width=False,
            propagate_height=False,
        )

        self.add(self.search_entry)
        self.add(self.scrolled_window)

    def on_show(self) -> None:
        """On widget show, rebuild the list of entries."""
        self.open_launcher()

    def open_launcher(self) -> None:
        """Open the application launcher and initialize it with the list of applications."""
        self._all_apps = get_desktop_applications()
        self.arrange_viewport()

        def clear_selection():
            entry = self.search_entry
            if entry.get_text():
                pos = len(entry.get_text())
                entry.set_position(pos)
                entry.select_region(pos, pos)
            return False

        def focus_search_entry():
            self.search_entry.grab_focus()
            self.search_entry.select_region(0, -1)

        GLib.idle_add(clear_selection)
        GLib.timeout_add(250, focus_search_entry)
        # self.show()

    def ensure_initialized(self) -> bool:
        """Make sure the launcher is initialized with apps list before opening"""
        if not hasattr(self, "_initialized"):

            self._all_apps = get_desktop_applications()
            self._initialized = True
            return True
        return False

    def arrange_viewport(self, query: str = "") -> None:
        if query.startswith("="):
            self.update_calculator_viewport()
            return
        remove_handler(
            self._arranger_handler) if self._arranger_handler else None
        self.viewport.children = []
        self.selected_index = -1

        filtered_apps_iter = iter(
            sorted(
                [
                    app for app in self._all_apps if query.casefold() in (
                        (app.display_name or "") + (" " + app.name + " ") +
                        (app.generic_name or "")).casefold()
                ],
                key=lambda app: (app.display_name or "").casefold(),
            ))

        self._arranger_handler = idle_add(
            lambda apps_iter: self.add_next_application(apps_iter) or self.
            handle_arrange_complete(query),
            filtered_apps_iter,
            pin=True,
        )

    def handle_arrange_complete(self, query: str) -> bool:
        """Handle the completion of the viewport arrangement"""
        if query.strip() != "" and self.viewport.get_children():
            self.update_selection(0)
        return False

    def add_next_application(self, apps_iter: Iterator[DesktopApp]) -> bool:
        """Add the next application to the viewport"""
        try:
            app = next(apps_iter)
            slot = self.bake_application_slot(app)
            self.viewport.add(slot)
            idle_add(self.add_next_application, apps_iter)
            return True
        except StopIteration:
            return False

    def bake_application_slot(self, app: DesktopApp, **kwargs) -> Box:
        """Create a button for the application with pin functionality"""
        # Check if app is pinned
        is_pinned = app.name in self.pinned_apps

        # Create pin button
        pin_icon = icons.pin_on if is_pinned else icons.pin_off
        pin_button = Button(
            child=Label(markup=pin_icon, name="pin-icon"),
            style_classes=["pin-button", "pinned" if is_pinned else "unpinned"],
            tooltip_text="Unpin from dock" if is_pinned else "Pin to dock",
            on_clicked=lambda button, *_: self.toggle_pin_status(button, app),
            v_align="center",
        )

        # Create app button (without the pin button as a child)
        app_button = Button(
            name="app-button",
            h_expand=True,
            child=Box(
                name="app-content-box",
                orientation="h",
                spacing=10,
                h_expand=True,
                children=[
                    Image(
                        name="app-icon",
                        pixbuf=app.get_icon_pixbuf(size=24),
                        h_align="start",
                    ),
                    Label(
                        name="app-label",
                        label=app.display_name or "Unknown",
                        ellipsization="end",
                        v_align="center",
                        h_align="center",
                    ),
                    Label(
                        name="app-desc",
                        label=app.description or "",
                        ellipsization="end",
                        v_align="center",
                        h_align="start",
                        h_expand=True,
                    ),
                ],
            ),
            on_clicked=lambda *_: app.launch(),
        )

        # Create a container that holds both buttons side by side
        container = Box(
            name="slot-button",
            orientation="h",
            spacing=4,
            children=[app_button, pin_button],
            **kwargs,
        )

        return container

    def toggle_pin_status(self, button, app: DesktopApp) -> bool:
        """Toggle whether an app is pinned to the dock"""

        # Toggle the pin status
        if app.name in self.pinned_apps:
            self.pinned_apps.remove(app.name)
            is_pinned = False
            tooltip = "Pin to dock"
            icon = icons.pin_off
        else:
            self.pinned_apps.append(app.name)
            is_pinned = True
            tooltip = "Unpin from dock"
            icon = icons.pin_on

        # Update the button
        icon_label = button.get_child(
        )  # Direct access, no need for get_children()
        icon_label.set_markup(icon)
        button.set_tooltip_text(tooltip)

        # Update CSS classes
        style_context = button.get_style_context()
        if is_pinned:
            style_context.remove_class("unpinned")
            style_context.add_class("pinned")
        else:
            style_context.remove_class("pinned")
            style_context.add_class("unpinned")

        # Save the updated list
        with open(pinned_aps_location, "w") as f:
            json.dump(self.pinned_apps, f)

        # Stop event propagation
        return True

    def update_selection(self, new_index: int) -> None:
        """Update the selected index and highlight the corresponding button"""

        if self.selected_index != -1 and self.selected_index < len(
                self.viewport.get_children()):
            current_button = self.viewport.get_children()[self.selected_index]
            current_button.get_style_context().remove_class("selected")

        if new_index != -1 and new_index < len(self.viewport.get_children()):
            new_button = self.viewport.get_children()[new_index]
            new_button.get_style_context().add_class("selected")
            self.selected_index = new_index
            self.scroll_to_selected(new_button)
        else:
            self.selected_index = -1

    def scroll_to_selected(self, button) -> None:
        """Scroll the viewport to ensure the selected button is visible"""

        def scroll():
            adj = self.scrolled_window.get_vadjustment()
            alloc = button.get_allocation()
            if alloc.height == 0:
                return False

            y = alloc.y
            height = alloc.height
            page_size = adj.get_page_size()
            current_value = adj.get_value()

            visible_top = current_value
            visible_bottom = current_value + page_size

            if y < visible_top:

                adj.set_value(y)
            elif y + height > visible_bottom:

                new_value = y + height - page_size
                adj.set_value(new_value)

            return False

        GLib.idle_add(scroll)

    def on_search_entry_activate(self, text: str) -> None:
        """Handle the activation of the search entry"""
        if text.startswith("="):

            if self.selected_index == -1:
                self.evaluate_calculator_expression(text)
            return
        if text.startswith(";"):
            # If in calculator mode and no history item is selected, evaluate new expression.
            if self.selected_index == -1:
                self.evaluate_calculator_expression(text)
            return
        match text:
            case _:
                children = self.viewport.get_children()
                if children:

                    if text.strip() == "" and self.selected_index == -1:
                        return
                    selected_index = (
                        self.selected_index if self.selected_index != -1 else 0
                    )
                    if 0 <= selected_index < len(children):
                        children[selected_index].get_children()[0].clicked()

    def on_search_entry_key_press(self, widget: Entry, event: Gdk.EventKey) -> bool:
        """Handle key press events in the search entry"""
        text = widget.get_text()

        if text.startswith("="):
            if event.keyval == Gdk.KEY_Down:
                self.move_selection(1)
                return True
            elif event.keyval == Gdk.KEY_Up:
                self.move_selection(-1)
                return True
            elif event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):

                if self.selected_index != -1 and self.selected_index < len(
                        self.calc_history):
                    if event.state & Gdk.ModifierType.SHIFT_MASK:

                        self.delete_selected_calc_history()
                    else:

                        selected_text = self.calc_history[self.selected_index]
                        self.copy_text_to_clipboard(selected_text)

                        self.selected_index = -1
                else:

                    self.selected_index = -1

                    self.evaluate_calculator_expression(text)
                return True
            return False
        if text.startswith(";"):
            if event.keyval == Gdk.KEY_Down:
                self.move_selection(1)
                return True
            elif event.keyval == Gdk.KEY_Up:
                self.move_selection(-1)
                return True
            return False
        else:

            if event.keyval == Gdk.KEY_Down:
                self.move_selection(1)
                return True
            elif event.keyval == Gdk.KEY_Up:
                self.move_selection(-1)
                return True
            elif event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and (
                    event.state & Gdk.ModifierType.SHIFT_MASK):
                return True
            return False

    def notify_text(self, entry: Entry, *_) -> None:
        """Handle text changes in the search entry"""
        text = entry.get_text()
        if text.startswith("="):
            self.update_calculator_viewport()

            self.selected_index = -1
        else:
            self.arrange_viewport(text)

    def move_selection(self, delta: int) -> None:
        """Move the selection in the viewport by the specified delta"""
        children = self.viewport.get_children()
        if not children:
            return

        if self.selected_index == -1 and delta == 1:
            new_index = 0
        else:
            new_index = self.selected_index + delta
        new_index = max(0, min(new_index, len(children) - 1))
        self.update_selection(new_index)

    def save_calc_history(self) -> None:
        """Save the calculator history to a JSON file"""
        with open(self.calc_history_path, "w") as f:
            json.dump(self.calc_history, f)

    def evaluate_calculator_expression(self, text: str):
        """Evaluate a calculator expression and update the history"""
        logger.debug(f"Evaluating calculator expression: {text}")

        expr = text.lstrip("=").strip()
        if not expr:
            return

        replacements = {
            "^": "**",
            "×": "*",
            "÷": "/",
            "π": "np.pi",
            "pi": "np.pi",
            "e": "np.e",
            "sin(": "np.sin(",
            "cos(": "np.cos(",
            "tan(": "np.tan(",
            "log(": "np.log10(",
            "ln(": "np.log(",
            "sqrt(": "np.sqrt(",
            "abs(": "np.abs(",
            "exp(": "np.exp(",
        }

        for old, new in replacements.items():
            expr = expr.replace(old, new)

        expr = re.sub(r"(\d+)!", r"np.factorial(\1)", expr)

        for old, new in [("[", "("), ("]", ")"), ("{", "("), ("}", ")")]:
            expr = expr.replace(old, new)

        safe_dict = {
            "np": np,
            "math": math,
            "arange": np.arange,
            "linspace": np.linspace,
            "array": np.array,
        }

        try:
            result = eval(expr, {"__builtins__": None}, safe_dict)

            if isinstance(result, np.ndarray):
                if result.size > 10:
                    result_str = f"Array of shape {result.shape}"
                else:
                    result_str = str(result)
            elif isinstance(result, (int, float, np.number)):

                if isinstance(result, (int, np.integer)):
                    result_str = str(int(result))
                elif isinstance(result, float) and result.is_integer():
                    result_str = str(int(result))
                else:
                    result_str = f"{float(result):.10g}"
            else:
                result_str = str(result)

        except Exception as e:
            result_str = f"Error: {str(e)}"

        self.calc_history.insert(0, f"{text} => {result_str}")
        self.save_calc_history()
        self.update_calculator_viewport()

    def update_calculator_viewport(self) -> None:
        """Update the calculator viewport with the current history"""
        self.viewport.children = []
        for item in self.calc_history:
            btn = self.create_calc_history_button(item)
            self.viewport.add(btn)

        if self.selected_index >= len(self.calc_history):
            self.selected_index = -1

    def create_calc_history_button(self, text: str) -> Button:
        """Create a button for a calculator history item"""
        if "=>" in text:
            parts = text.split("=>")
            expression = parts[0].strip()
            result = parts[1].strip()

            display_text = text
            if len(result) > 50:
                display_text = f"{expression} => {result[:47]}..."

            btn = Button(
                name="slot-button",
                child=Box(
                    name="calc-slot-box",
                    orientation="h",
                    spacing=10,
                    children=[
                        Label(
                            name="calc-label",
                            label=display_text,
                            ellipsization="end",
                            v_align="center",
                            h_align="center",
                        ),
                    ],
                ),
                tooltip_text=text,
                on_clicked=lambda *_: self.copy_text_to_clipboard(text),
            )
        else:

            btn = Button(
                name="slot-button",
                child=Box(
                    name="calc-slot-box",
                    orientation="h",
                    spacing=10,
                    children=[
                        Label(
                            name="calc-label",
                            label=text,
                            ellipsization="end",
                            v_align="center",
                            h_align="center",
                        ),
                    ],
                ),
                tooltip_text=text,
                on_clicked=lambda *_: self.copy_text_to_clipboard(text),
            )
        return btn

    def copy_text_to_clipboard(self, text: str) -> None:
        """Copy the given text to the clipboard using wl-copy"""
        parts = text.split("=>", 1)
        copy_text = parts[1].strip() if len(parts) > 1 else text
        try:
            subprocess.run(["wl-copy"], input=copy_text.encode(), check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Clipboard copy failed: {e}")

    def delete_selected_calc_history(self) -> None:
        """Delete the currently selected calculator history item"""
        if self.selected_index != -1 and self.selected_index < len(
                self.calc_history):

            current_index = self.selected_index

            del self.calc_history[current_index]
            self.save_calc_history()

            new_index = 0 if current_index == 0 else current_index - 1

            self.selected_index = -1

            self.update_calculator_viewport()

            if len(self.calc_history) > 0:
                self.update_selection(min(new_index,
                                          len(self.calc_history) - 1))
