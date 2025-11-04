from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.scrolledwindow import ScrolledWindow
from services.interfaces import NotchWidgetInterface


class SyncApp(Box, NotchWidgetInterface):
    """Widget to manage vellum-shell sync."""

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

        self.client_list_box = Box(
            orientation="v",
            spacing=10,
            h_expand=True,
            v_expand=True,
            h_align="fill",
            v_align="fill",
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
            child=self.client_list_box,
        )

        self.add(self.scrollable_area)

    def on_show(self) -> None:
        self._set_client_list()

    def _on_client_list_updated(self, *args):
        self._set_client_list()

    def _set_client_list(self):
      # Clear existing clients
      for child in self.client_list_box.get_children():
        child.destroy()

      # Add connected clients
      for client in []: # TODO: Replace with actual client list retrieval
        name = Label(text=client['sid'])
        print("Adding client to sync app:", client['sid'])
        box = Box(
            orientation="h",
            spacing=10,
            h_expand=True,
            v_expand=False,
            h_align="fill",
            v_align="center",
            children=[name],
        )
        self.client_list_box.add(box)
