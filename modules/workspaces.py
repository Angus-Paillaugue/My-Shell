from fabric.hyprland.widgets import (
    WorkspaceButton,
    Workspaces as BaseWorkspaces,
)


class Workspaces(BaseWorkspaces):

    def __init__(self):
        super().__init__(
            name="workspaces",
            style_classes=["bar-item"],
            invert_scroll=True,
            empty_scroll=True,
            v_align="fill",
            orientation="h",
            spacing=8,
            buttons=[
                WorkspaceButton(
                    h_expand=False,
                    v_expand=False,
                    h_align="center",
                    v_align="center",
                    id=i,
                ) for i in range(1, 5)
            ],
        )
