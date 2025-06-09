from fabric.widgets.box import Box
from fabric.widgets.shapes import Corner

from fabric.widgets.wayland import WaylandWindow as Window


class MyCorner(Corner):

    def __init__(self, corner, size=20, name="corner", **kwargs):
        super().__init__(
            name=name,
            style_classes=["corner"],
            orientation=corner,
            size=size,
            **kwargs,
        )


class CornerContainer(Box):

    def __init__(
        self,
        name=None,
        position="top",
        corners=["left", "right"],
        children=[],
        height=25,
        **kwargs,
    ):
        super().__init__(
            name=name,
            h_align="start" if position == "top" else "end",
            v_align="start" if position == "top" else "end",
            h_expand=False,
            v_expand=False,
            style_classes=["corner-container"],
            **kwargs,
            orientation="h",
        )
        self._name = name
        self._children = children
        self._position = position

        if not "left" in corners:
            self._add_children()

        for corner in corners:
            if corner == "right":
                self.add(
                    MyCorner(
                        f"{self._position}-left",
                        name=f"{self._name}-corner-right",
                        size=height,
                        h_align="start" if position == "top" else "end",
                        v_align="start" if position == "top" else "end",
                    ))
            elif corner == "left":
                self.add(
                    MyCorner(
                        f"{self._position}-right",
                        name=f"{self._name}-corner-left",
                        size=height,
                        h_align="start" if position == "top" else "end",
                        v_align="start" if position == "top" else "end",
                    ))
                self._add_children()
            else:
                raise ValueError(
                    "Invalid corner specified, must be 'left' or 'right'")

    def _add_children(self):
        self.inner = Box(
            name=f"{self._name}-inner",
            orientation="h",
            h_align="fill",
            v_align="fill",
        )
        self.add(self.inner)
        for child in self._children:
            self.inner.add(child)


class Corners(Window):

    def __init__(self):
        super().__init__(
            name="corners",
            layer="top",
            anchor="top bottom left right",
            margin="-56px 0 0 0",
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
                    name="top-corners",
                    orientation="h",
                    h_align="fill",
                    children=[
                        MyCorner("top-left"),
                        Box(h_expand=True),
                        MyCorner("top-right"),
                    ],
                ),
                Box(v_expand=True),
                Box(
                    name="bottom-corners",
                    orientation="h",
                    h_align="fill",
                    children=[
                        MyCorner("bottom-left"),
                        Box(h_expand=True),
                        MyCorner("bottom-right"),
                    ],
                ),
            ],
        )

        self.add(self.all_corners)

        self.show_all()
