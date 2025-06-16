from .base_conf import BaseConfig, ConfigInterface
from dataclasses import dataclass


@dataclass
class Config(BaseConfig):
    APP_NAME = "my-shell"


config: ConfigInterface = Config()
