import os

import yaml
from mergedeep import merge

default_config = {
    "APP_NAME": "my-shell",
    "POSITIONS": {
        "BAR": "top",
        "DOCK": "bottom",
        "NOTIFICATION": "top-right",
    },
    "STYLES": {
        "BORDER_RADIUS": 12,
        "FONT_SIZE": 16,
        "BAR_SIZE": 40,
        "PADDING": 8,
        "NOTCH_HEIGHT": 47,
    },
    "MULTI_MONITOR": True,
}

class Config:
    def __init__(self, path: str = "config.yaml") -> None:
        self.path = path
        self.init()

    def read_yaml(self, path: str) -> dict:
        if not os.path.exists(path):
            return {}
        with open(path, "r") as f:
            return yaml.safe_load(f)

    def build(self, user_config: dict) -> dict:
        return merge(default_config, user_config) # type: ignore

    def init(self):
        self.user_config = self.read_yaml(self.path) if self.path else {}
        self.config = self.build(self.user_config)

    def __getitem__(self, key: str):
        return self.config[key]

config = Config()
