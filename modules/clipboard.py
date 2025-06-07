import subprocess
from fabric.utils import exec_shell_command_async
from fabric.widgets.wayland import WaylandWindow
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from gi.repository import Gtk, Gdk
from fabric.widgets.scrolledwindow import ScrolledWindow
import modules.icons as icons


class ClipboardManager(WaylandWindow):

    def __init__(self, **kwargs):
        super().__init__(
            layer="overlay",
            anchor="center center",
            exclusivity="exclusive",
            keyboard_mode="exclusive",
            visible=False,
            **kwargs,
        )

        # Make title more visible with markup
        self.title_label = Label(
            label="Clipboard Manager", name="clipboard-manager-title"
        )
        self.header = CenterBox(
            name="clipboard-manager-header",
            orientation="h",
            start_children=[self.title_label],
            end_children=[
                Button(
                    child=Label(markup=icons.cancel),
                    on_clicked=lambda btn: self.toggle(),
                    style_classes=["close-button"],
                )
            ],
        )

        # Create a grid that will adapt to its contents
        self.clipboard_items = Box(
            name="clipboard-items-grid",
            orientation="v",
            spacing=12,
            h_expand=True,
            v_expand=True,
            h_align="fill",
            v_align="fill",
        )

        # Configure scrolled window to allow vertical scrolling as needed
        self.scrollable_area = ScrolledWindow(
            child=self.clipboard_items,
            h_expand=True,
            v_expand=True,
            h_scroll_policy=Gtk.PolicyType.NEVER,  # Never show horizontal scrollbar
            v_scroll_policy=Gtk.PolicyType.AUTOMATIC,  # Show vertical scrollbar when needed
        )

        # Make sure container has explicit minimum size but can grow
        self.main_container = Box(
            name="clipboard-manager-container",
            orientation="v",
            spacing=12,
            h_expand=True,
            v_expand=True,
            h_align="fill",
            v_align="fill",
            children=[self.header, self.scrollable_area],
        )

        self.add(self.main_container)
        self._build_list()
        self.connect("key-press-event", self.on_key_press)

    def on_key_press(self, widget, event):
        """Handle keyboard navigation"""
        keyval = event.get_keyval()[1]

        # Close on Escape key
        if keyval == Gdk.KEY_Escape:
            self.hide()
            return True

        # Let Tab navigation work normally
        return False

    def toggle(self):
        if self.is_visible():
            self.hide()
        else:
            self.show_all()
            self.present()

    def _clear_items(self):
        for child in self.clipboard_items.get_children():
            self.clipboard_items.remove(child)

    def _build_list(self, filter_text=""):
        result = subprocess.run(["cliphist", "list"], capture_output=True, check=True)
        # Decode stdout with error handling
        stdout_str = result.stdout.decode("utf-8", errors="replace")
        lines = stdout_str.strip().split("\n")
        items = []
        for line in lines:
            if not line or "<meta http-equiv" in line:
                continue
            items.append(line)

        filtered_items = []
        for item in items:
            content = item.split("\t", 1)[1] if "\t" in item else item
            if filter_text.lower() in content.lower():
                filtered_items.append(item)

        self._clear_items()
        for entry in filtered_items:
            parts = entry.split("\t", 1)
            item_id = parts[0] if len(parts) > 1 else "0"
            content = parts[1] if len(parts) > 1 else entry
            button = Button(
                child=Label(label=content, ellipsization="end", h_align="start"),
                on_clicked=lambda btn, e=item_id: self._copy_entry(e),
                style_classes=["clipboard-item-button"],
                v_align="fill",
                h_align="fill",
                v_expand=False,
                h_expand=True,
            )
            self.clipboard_items.add(button)

    def _copy_entry(self, id):
        result = subprocess.run(
            ["cliphist", "decode", id], capture_output=True, check=True
        )
        subprocess.run(["wl-copy"], input=result.stdout, check=True)
        exec_shell_command_async("notify-send 'Clipboard' 'Copied to clipboard!'")
        self.toggle()  # Close the manager after copying
