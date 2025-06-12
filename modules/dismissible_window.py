from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.button import Button
from fabric.widgets.box import Box


class DismissibleWindow(Window):

    def __init__(self, visible=False, **kwargs):
        super().__init__(
            layer="top",
            anchor="top bottom left right",
            exclusivity="none",
            keyboard_mode="none",
            margin="-54px 0 0 0",
            visible=visible,
        )
        kwargs = dict(
            filter(
                lambda item: item[0] in [
                    "anchor",
                    "exclusivity",
                    "keyboard_mode",
                    "margin",
                ],
                kwargs.items(),
            ))
        self.inner_window = Window(visible=visible, layer="overlay", **kwargs)
        self.dismiss_button = Button(
            name="dismiss_button",
            h_expand=True,
            v_expand=True,
            on_clicked=lambda *_: self.hide(),
        )
        self.box = Box(
            children=[self.inner_window, self.dismiss_button],
            h_align="fill",
            v_align="fill",
        )
        self._add = super().add
        self._add(self.box)

    def add(self, widget):
        self.inner_window.add(widget)

    def show(self):
        self.inner_window.show()
        super().show()

    def hide(self):
        self.inner_window.hide()
        super().hide()

    def is_visible(self):
        return self.inner_window.get_visible()

    def toggle(self):
        if self.is_visible():
            self.hide()
        else:
            self.show()
