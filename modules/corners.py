from fabric.widgets.box import Box
from fabric.widgets.shapes import Corner

from fabric.widgets.wayland import WaylandWindow as Window


class MyCorner(Box):

    def __init__(self, corner, size=20, name="corner", **kwargs):
        super().__init__(
            name="corner-container",
            children=Corner(
                name=name,
                style_classes=["corner"],
                orientation=corner,
                size=size,
            ),
            **kwargs,
        )


class CornerContainer(Box):

    def __init__(self,
                 name=None,
                 corners=["left", "right"],
                 children=[],
                 height=25,
                 **kwargs):
        super().__init__(
            name=name,
            h_align="start",
            v_align="start",
            h_expand=False,
            v_expand=False,
            style_classes=["corner-container"],
            **kwargs,
            orientation="h",
        )
        self._name = name
        self._children = children

        if not "left" in corners:
            self._add_children()

        for corner in corners:
            if corner == "right":
                self.add(
                    MyCorner(
                        f"top-left",
                        name=f"{self._name}-corner-right",
                        size=height,
                        h_align="start",
                        v_align="start",
                    ))
            elif corner == "left":
                self.add(
                    MyCorner(
                        f"top-right",
                        name=f"{self._name}-corner-left",
                        size=height,
                        h_align="start",
                        v_align="start",
                    ))
                self._add_children()
            else:
                raise ValueError(
                    "Invalid corner specified, must be 'left' or 'right'")

    def _add_children(self):
        inner = Box(
            name=f"{self._name}-inner",
            orientation="h",
            h_align="fill",
            v_align="fill",
        )
        self.add(inner)
        for child in self._children:
            inner.add(child)


class Corners(Window):

    def __init__(self):
        super().__init__(
            name="corners",
            layer="top",
            anchor="bottom left right",
            exclusivity="normal",
            pass_through=True,
            visible=False,
            all_visible=False,
        )

        self.all_corners = Box(
            name="all-corners",
            orientation="v",
            h_expand=True,
            v_expand=True,
            h_align="fill",
            v_align="fill",
            children=[
                Box(
                    name="bottom-corners",
                    orientation="h",
                    h_align="fill",
                    children=[
                        MyCorner("bottom-left", size=12),
                        Box(h_expand=True),
                        MyCorner("bottom-right", size=12),
                    ],
                ),
            ],
        )

        self.add(self.all_corners)

        self.show_all()
