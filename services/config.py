from .base_conf import BaseConfig, ConfigInterface


class Config(BaseConfig):
    MONOSPACE_FONT_FAMILY: str = "JetBrainsMono Nerd Font" # Please choose a font installed on your system


config: ConfigInterface = Config()
