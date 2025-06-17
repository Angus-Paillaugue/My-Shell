from fabric.hyprland.widgets import WorkspaceButton
from fabric.hyprland.widgets import Workspaces as BaseWorkspaces

from services.config import config


class Workspaces(BaseWorkspaces):

    def __init__(self):
        orientation = (
            "horizontal" if config.BAR_POSITION in ["top", "bottom"] else "vertical"
        )
        super().__init__(
            name="workspaces",
            style_classes=[
                "bar-item",
                orientation,
            ],
            invert_scroll=True,
            empty_scroll=True,
            orientation=orientation,
            spacing=8,
            buttons=[
                WorkspaceButton(
                    h_expand=False,
                    v_expand=False,
                    h_align="center",
                    v_align="center",
                    id=i,
                    style_classes=[orientation],
                )
                for i in range(1, 5)
            ],
        )
