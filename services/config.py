from .base_conf import BaseConfig, ConfigInterface


class Config(BaseConfig):
    APP_NAME = "my-shell"
    BAR_POSITION = "left"


config: ConfigInterface = Config()
