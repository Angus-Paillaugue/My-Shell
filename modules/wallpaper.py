import os
import threading
from fabric.utils import exec_shell_command_async
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.entry import Entry
from fabric.widgets.label import Label
from gi.repository import Gtk, GdkPixbuf, Gio, Gdk, GLib
from fabric.widgets.image import Image
from fabric.widgets.scrolledwindow import ScrolledWindow
from services.logger import logger


class WallpaperManager(Box):

    def __init__(self, **kwargs):
        super().__init__(
            orientation="v",
            spacing=12,
            h_expand=True,
            v_expand=True,
            h_align="fill",
            v_align="fill",
            **kwargs,
        )

        self.columns = 2
        self.wallpaper_location = os.path.expanduser("~/Pictures/wallpapers")
        self.image_cache = {}
        self.loaded_images = set()
        self.load_thread_active = False

        if not os.path.exists(self.wallpaper_location):
            os.makedirs(self.wallpaper_location)

        # Create a grid that will adapt to its contents
        self.buttons_grid = Gtk.Grid(
            column_homogeneous=True,
            row_homogeneous=True,
            column_spacing=12,
            row_spacing=12,
        )
        self.scrollable_area = ScrolledWindow(
            name="notch-scrolled-window",
            spacing=10,
            h_expand=True,
            v_expand=True,
            h_align="fill",
            v_align="fill",
            propagate_width=False,
            propagate_height=False,
            child=self.buttons_grid,
        )

        self.entry = Entry(
            placeholder="Search Wallpapers...",
            h_expand=True,
            h_align="fill",
            notify_text=self.notify_text,
            name="search-entry",
        )
        self.entry.props.xalign = 0.5
        self.add(self.entry)
        self.add(self.scrollable_area)

        self._refresh_wallpapers()
        self.setup_file_monitor()
        self.connect("key-press-event", self.on_key_press)

    def notify_text(self, entry, *_):
        """Handle text changes in the search entry"""
        text = entry.get_text()
        self._refresh_wallpapers(text)

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
        gfile = Gio.File.new_for_path(self.wallpaper_location)
        self.file_monitor = gfile.monitor_directory(Gio.FileMonitorFlags.NONE,
                                                    None)
        self.file_monitor.connect("changed",
                                  lambda *_: self._refresh_wallpapers())

    def _refresh_wallpapers(self, search=""):
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
            grid_position = 0  # Separate counter for grid positions
            filtered_wallpapers = []

            for abs_path, filename in wallpapers:
                # Filter wallpapers based on search text
                if search and search.lower() not in filename.lower():
                    continue

                # Add wallpaper to grid using the grid_position counter
                row = grid_position // self.columns
                col = grid_position % self.columns
                self._add_wallpaper_button_placeholder(abs_path, filename, col,
                                                       row)

                # Add to filtered list for background loading
                filtered_wallpapers.append((abs_path, filename))

                # Only increment grid position when we actually add a wallpaper
                grid_position += 1

            # If no wallpapers match the search
            if grid_position == 0 and search:
                label = Label(
                    name="no-wallpapers-label",
                    text=f"No wallpapers matching '{search}'",
                    h_align="center",
                    v_align="center",
                )
                self.buttons_grid.attach(label, 0, 0, self.columns, 1)
                label.show()

            # Load actual images in the background - only for filtered wallpapers
            self._load_images_in_background(filtered_wallpapers)

        # Ensure everything is visible
        self.show_all()

    def _add_wallpaper_button_placeholder(self, path: str, filename: str,
                                          col: int, row: int):
        """Add a wallpaper button with a placeholder image."""
        image_width = 330
        image_height = image_width * 3 // 4  # 16:9 aspect ratio

        # Create a placeholder image (gray rectangle)
        placeholder = Gtk.Box()
        placeholder.set_size_request(image_width, image_height)
        placeholder.get_style_context().add_class("wallpaper-placeholder")

        # Create image widget that will be updated later
        image = Image(style_classes=["wallpaper-button-image"])

        image.path = path

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
            on_clicked=lambda btn, wp=path: self.set_wallpaper(wp),
            style_classes=["wallpaper-button"],
        )

        # Use the provided row and column positions
        self.buttons_grid.attach(button, col, row, 1, 1)

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
            if not isinstance(child, Button):
                continue

            box = child.get_child()

            for widget in box.get_children():
                if isinstance(widget, Image) and hasattr(
                        widget, 'path') and widget.path == path:
                    # Update the image
                    widget.set_from_pixbuf(pixbuf)

                    # Hide the placeholder and show the actual image
                    placeholder = box.get_children()[0]
                    placeholder.hide()
                    widget.show()

                    # Exit the loop after finding the matching image
                    return

    def _list_wallpapers(self):
        """
        List all wallpapers in the wallpapers directory.
        """
        wallpapers_dir = self.wallpaper_location
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
