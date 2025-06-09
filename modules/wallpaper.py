import os
import threading
from fabric.utils import exec_shell_command_async
from fabric.widgets.wayland import WaylandWindow
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from gi.repository import Gtk, GdkPixbuf, Gio, Gdk, GLib
from fabric.widgets.image import Image
from fabric.widgets.scrolledwindow import ScrolledWindow
import modules.icons as icons
from services.logger import logger


class WallpaperManager(WaylandWindow):

    def __init__(self, **kwargs):
        super().__init__(
            layer="overlay",
            anchor="center center",
            exclusivity="exclusive",
            keyboard_mode="exclusive",
            visible=False,
            **kwargs,
        )

        self.columns = 3
        self.wallpaper_location = "~/Pictures/wallpapers"
        self.image_cache = {}
        self.loaded_images = set()
        self.load_thread_active = False

        if not os.path.exists(os.path.expanduser(self.wallpaper_location)):
            os.makedirs(os.path.expanduser(self.wallpaper_location))

        # Make title more visible with markup
        self.title_label = Label(label="Wallpaper Manager",
                                 name="wallpaper-manager-title")
        self.header = CenterBox(
            name="wallpaper-manager-header",
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
        self.buttons_grid = Gtk.Grid(
            column_homogeneous=True,
            row_homogeneous=False,
            name="wallpaper-grid",
            column_spacing=12,
            row_spacing=12,
        )

        # Configure scrolled window to allow vertical scrolling as needed
        self.scrollable_area = ScrolledWindow(
            child=self.buttons_grid,
            h_expand=True,
            v_expand=True,
            h_scroll_policy=Gtk.PolicyType.
            NEVER,  # Never show horizontal scrollbar
            v_scroll_policy=Gtk.PolicyType.
            AUTOMATIC,  # Show vertical scrollbar when needed
        )

        # Make sure container has explicit minimum size but can grow
        self.main_container = Box(
            name="wallpaper-manager-container",
            orientation="v",
            spacing=12,
            h_expand=True,
            v_expand=True,
            h_align="fill",
            v_align="fill",
            children=[self.header, self.scrollable_area],
        )

        # Set a minimum size that accommodates 3 columns
        # Calculate based on image width (300px) * 3 + padding/spacing
        min_width = ((300 * self.columns) + (12 * (self.columns + 1)) + 30
                    )  # Images + spacing + padding
        min_height = 420

        self.main_container.set_size_request(min_width, min_height)
        self.add(self.main_container)

        self._refresh_wallpapers()
        self.setup_file_monitor()
        self.connect("key-press-event", self.on_key_press)
        self.connect("show", self._on_window_show)

    def on_key_press(self, widget, event):
        """Handle keyboard navigation"""
        keyval = event.get_keyval()[1]

        # Close on Escape key
        if keyval == Gdk.KEY_Escape:
            self.hide()
            return True

        # Let Tab navigation work normally
        return False

    def setup_file_monitor(self):
        gfile = Gio.File.new_for_path(
            os.path.expanduser(self.wallpaper_location))
        self.file_monitor = gfile.monitor_directory(Gio.FileMonitorFlags.NONE,
                                                    None)
        self.file_monitor.connect("changed", self._refresh_wallpapers)

    def _refresh_wallpapers(self, *args):
        """
        Refresh the list of wallpapers and update the buttons.
        """
        # Remove existing children
        for child in self.buttons_grid.get_children():
            self.buttons_grid.remove(child)

        wallpapers = self._list_wallpapers()
        if not wallpapers:
            # Add a message when no wallpapers are found
            label = Label(
                name="no-wallpapers-label",
                text=f"No wallpapers found in {self.wallpaper_location}",
                h_align="center",
                v_align="center",
            )
            self.buttons_grid.attach(label, 0, 0, self.columns, 1)
        else:
            # Create all buttons with placeholder images first
            for i, (abs_path, filename) in enumerate(wallpapers):
                self._add_wallpaper_button_placeholder(abs_path, filename, i)

            # Load actual images in the background
            self._load_images_in_background(wallpapers)

        # Ensure everything is visible
        self.main_container.show_all()

    def _add_wallpaper_button_placeholder(self, path: str, filename: str,
                                          index: int):
        """Add a wallpaper button with a placeholder image."""
        image_width = 240
        image_height = 135

        # Create a placeholder image (gray rectangle)
        placeholder = Gtk.Box()
        placeholder.set_size_request(image_width, image_height)
        placeholder.get_style_context().add_class("wallpaper-placeholder")

        # Create image widget that will be updated later
        image = Image(style_classes=["wallpaper-button-image"],)
        image.set_size_request(image_width, image_height)

        # Use normal Python attributes instead of set_data
        image.path = path  # Changed from set_data

        contents = Box(
            children=[
                placeholder,  # Add placeholder first
                image,  # Add image (hidden initially)
                Label(
                    label=filename,
                    name="wallpaper-button-label",
                    h_align="center",
                    v_align="center",
                ),
            ],
            spacing=8,
            orientation="v",
            h_align="fill",
            v_align="fill",
        )

        # Hide the actual image until it's loaded
        image.set_no_show_all(True)
        image.hide()

        button = Button(
            child=contents,
            on_clicked=lambda btn, wp=path:
            (self.set_wallpaper(wp), self.toggle()),
            style_classes=["wallpaper-button"],
        )

        self.buttons_grid.attach(button, index % self.columns,
                                 index // self.columns, 1, 1)

    def _load_images_in_background(self, wallpapers):
        """Load images in a background thread to avoid UI freezes."""
        if self.load_thread_active:
            return

        def load_worker():
            self.load_thread_active = True
            for path, filename in wallpapers:
                # Skip if already cached
                if path in self.image_cache:
                    pixbuf = self.image_cache[path]
                    GLib.idle_add(self._update_image, path, pixbuf)
                    continue

                try:
                    # Load and scale the image
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        path, 240, 135, True)
                    # Cache the pixbuf
                    self.image_cache[path] = pixbuf
                    # Update the UI in the main thread
                    GLib.idle_add(self._update_image, path, pixbuf)
                except Exception as e:
                    logger.error(f"Error loading image {path}: {e}")

            self.load_thread_active = False

        # Start the worker thread
        thread = threading.Thread(target=load_worker)
        thread.daemon = True
        thread.start()

    def _update_image(self, path, pixbuf):
        """Update the image widget with the loaded pixbuf."""
        # Mark this image as loaded
        self.loaded_images.add(path)

        # Find all image widgets with this path
        for child in self.buttons_grid.get_children():
            box = child.get_child()
            if not box or not isinstance(box, Box):
                continue

            for widget in box.get_children():
                if (isinstance(widget, Image) and hasattr(widget, "path") and
                        widget.path == path):
                    # Found our image widget, update it
                    widget.set_from_pixbuf(pixbuf)

                    # Make the placeholder invisible and show the image
                    placeholder = None
                    for sibling in box.get_children():
                        if isinstance(sibling, Gtk.Box) and not isinstance(
                                sibling, Image):
                            placeholder = sibling
                            break

                    if placeholder:
                        placeholder.hide()

                    widget.show()
                    return False  # Remove this idle callback

        return False  # Remove this idle callback

    def _on_window_show(self, widget):
        """Called when the window is shown - ensure proper image visibility."""
        # Go through all loaded images and ensure placeholders are hidden
        if self.loaded_images:
            for child in self.buttons_grid.get_children():
                box = child.get_child()
                if not box or not isinstance(box, Box):
                    continue

                for widget in box.get_children():
                    if (isinstance(widget, Image) and
                            hasattr(widget, "path") and
                            widget.path in self.loaded_images):
                        # This image has been loaded, update visibilities
                        placeholder = None
                        for sibling in box.get_children():
                            if isinstance(sibling, Gtk.Box) and not isinstance(
                                    sibling, Image):
                                placeholder = sibling
                                break

                        if placeholder:
                            placeholder.hide()

                        widget.show()

    def toggle(self):
        if self.is_visible():
            self.hide()
        else:
            self.show_all()
            self.present()

    def _list_wallpapers(self):
        """
        List all wallpapers in the wallpapers directory.
        """
        wallpapers_dir = os.path.expanduser(self.wallpaper_location)
        if not os.path.exists(wallpapers_dir):
            return []

        return [(os.path.join(wallpapers_dir, f), f)
                for f in os.listdir(wallpapers_dir)
                if f.endswith((".jpg", ".png", ".jpeg", ".webp"))]

    def set_wallpaper(self, path: str) -> None:
        """
        Set the desktop wallpaper to the specified image path.

        Args:
            path (str): The file path of the image to set as wallpaper.
        """
        path = os.path.abspath(path)

        if not os.path.exists(path):
            raise FileNotFoundError(
                f"The specified path does not exist: {path}")

        try:
            # exec_shell_command_async(
            #     f'swww img "{path}" -t outer --transition-duration 1.5 --transition-step 255 --transition-fps 60 -f Nearest',
            #     lambda *_: None,
            # )
            # Link the wallpaper to the current directory
            current_wall = os.path.expanduser("~/.current.wall")
            if os.path.isfile(current_wall) or os.path.islink(
                    current_wall):  # Check for link too
                os.remove(current_wall)

            os.symlink(path, current_wall)

            exec_shell_command_async(
                f'matugen image "{current_wall}"',
                lambda process, stdout: logger.debug(stdout),
            )
        except Exception as e:
            logger.error(f"Failed to set wallpaper: {e}")
