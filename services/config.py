from .base_conf import BaseConfig, ConfigInterface


class Config(BaseConfig):
    MONOSPACE_FONT_FAMILY = "JetBrainsMono Nerd Font" # Please choose a font installed on your system
    BAR_POSITION = "right"



config: ConfigInterface = Config()
