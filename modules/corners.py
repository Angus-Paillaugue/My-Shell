from typing import Literal

from fabric.widgets.box import Box
from fabric.widgets.shapes import Corner
from fabric.widgets.wayland import WaylandWindow as Window

from services.config import config


class MyCorner(Corner):
    """Custom corner widget that extends the Corner class with additional properties."""

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
        position: Literal["top", "bottom", "left", "right"] = "top",
        corners=(True, True),
        children=[],
        height=25,
        style_classes=["corner-container"],
        **kwargs,
    ):
        is_vertical = position in ["left", "right"]

        # Set orientation based on position
        orientation = "v" if is_vertical else "h"
        super().__init__(
            name=name,
            h_align=("start" if position != "right" else "end"),
            v_align=("start" if position != "bottom" else "end"),
            h_expand=False,
            v_expand=False,
            style_classes=style_classes,
            orientation=orientation,
        )
        self._name = name
        self._children = children
        self._position = position if position in ["top", "bottom"] else "top"
        self.kwargs = kwargs
        self.is_vertical = is_vertical

        first_corner = None
        second_corner = None

        if is_vertical:
            first_corner = f"bottom-{position}"
            second_corner = f"top-{position}"
        else:
            # Horizontal container (top/bottom dock)
            first_corner = f"{position}-right"
            second_corner = f"{position}-left"

        # Add first corner if requested
        if corners[0]:
            self.add(
                MyCorner(
                    first_corner,
                    name=f"{self._name}-corner-first",
                    size=height,
                    h_align=(
                        "start"
                        if position == "left"
                        else "end" if position == "right" else "fill"
                    ),
                    v_align=(
                        "start"
                        if position == "top"
                        else "end" if position == "bottom" else "fill"
                    ),
                )
            )

        # Add children
        self._add_children()

        # Add second corner if requested
        if corners[1]:
            self.add(
                MyCorner(
                    second_corner,
                    name=f"{self._name}-corner-second",
                    size=height,
                    h_align=(
                        "start"
                        if position == "left"
                        else "end" if position == "right" else "fill"
                    ),
                    v_align=(
                        "start"
                        if position == "top"
                        else "end" if position == "bottom" else "fill"
                    ),
                )
            )

    def _add_children(self) -> None:
        """Add children to the inner box."""
        kwargs = self.kwargs.copy()
        kwargs["h_align"] = kwargs.get("h_align", "fill")
        kwargs["v_align"] = kwargs.get("v_align", "fill")
        kwargs["orientation"] = kwargs.get("orientation", "h")
        self.inner = Box(
            name=f"{self._name}-inner",
            **self.kwargs,
        )
        self.add(self.inner)
        for child in self._children:
            self.inner.add(child)

        kwargs = self.kwargs.copy()
        kwargs["h_align"] = kwargs.get("h_align", "fill")
        kwargs["v_align"] = kwargs.get("v_align", "fill")
        kwargs["h_expand"] = True if self.is_vertical else False
        kwargs["v_expand"] = True if not self.is_vertical else False
        kwargs["orientation"] = self.kwargs.get(
            "inner_orientation", self.get_orientation()
        )

        self.inner = Box(
            name=f"{self._name}-inner",
            **kwargs,
        )


class Corners(Window):
    """Window that contains all four corners of the screen."""

    def __init__(self):
        offset = '-'+str(config['STYLES']['BAR_SIZE'] + config['STYLES']['PADDING'])
        margin = f"{offset if config['POSITIONS']['BAR'] == "top" else "0"} {offset if config['POSITIONS']['BAR'] == "right" else "0"} {offset if config['POSITIONS']['BAR'] == "bottom" else "0"} {offset if config['POSITIONS']['BAR'] == "left" else "0"}"
        super().__init__(
            name="corners",
            layer="top",
            anchor="top bottom left right",
            margin=margin,
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
