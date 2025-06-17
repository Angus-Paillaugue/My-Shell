from typing import Literal, Protocol


class ConfigInterface(Protocol):
    APP_NAME: str
    BAR_POSITION: Literal["top", "left", "right", "bottom"]
    DOCK_POSITION: Literal["top", "left", "right", "bottom"]
    MONOSPACE_FONT_FAMILY: str
    NOTIFICATION_POSITION: Literal[
        "top-left",
        "top-right",
        "bottom-left",
        "bottom-right",
        "top-center",
        "bottom-center",
    ] = "top-right"


class BaseConfig(ConfigInterface):
    APP_NAME: str = "my-shell"
    BAR_POSITION: Literal["top", "left", "right", "bottom"] = "top"
    DOCK_POSITION: Literal["top", "left", "right", "bottom"] = "bottom"
    MONOSPACE_FONT_FAMILY: str = "monospace"
