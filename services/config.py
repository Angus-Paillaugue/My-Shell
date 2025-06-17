from .base_conf import BaseConfig, ConfigInterface


class Config(BaseConfig):
    APP_NAME = "my-shell"


config: ConfigInterface = Config()
