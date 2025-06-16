from .base_conf import BaseConfig, ConfigInterface
from dataclasses import dataclass


@dataclass
class Config(BaseConfig):
  APP_NAME: str = "my-shell"


config: ConfigInterface = Config()
