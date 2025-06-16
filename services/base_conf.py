from dataclasses import dataclass
from typing import Literal, Protocol, Literal


class ConfigInterface(Protocol):
    APP_NAME: str
    BAR_POSITION: Literal["top", "left", "right", "bottom"]
    DOCK_POSITION: Literal["top", "left", "right", "bottom"]


@dataclass
class BaseConfig(ConfigInterface):
    APP_NAME: str = "my-shell"
    BAR_POSITION: Literal["top", "left", "right", "bottom"] = "top"
    DOCK_POSITION: Literal["top", "left", "right", "bottom"] = "bottom"
