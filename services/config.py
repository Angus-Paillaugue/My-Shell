import json
import os
import re
import warnings

import yaml
from mergedeep import merge

default_config = {
    "APP_NAME": "my-shell",
    "STYLES": {
        "BORDER_RADIUS": 12,
        "FONT_SIZE": 16,
        "BAR_SIZE": 40,
        "PADDING": 8,
        "NOTCH_HEIGHT": 47,
    },
    "MULTI_MONITOR": True,
    "NOTCH": {
        "VISIBLE": True,
        "MODULES": {
            "WIFI": {
                "VISIBLE": True,
            },
            "WIRED": {
                "VISIBLE": True,
            },
            "BLUETOOTH": {
                "VISIBLE": True,
            },
            "TAILSCALE": {
                "VISIBLE": True,
            },
            "POWER_PROFILE": {
                "VISIBLE": True,
            },
            "SUNSET": {
                "VISIBLE": True,
                "TEMPERATURE": 3500,
                "GAMMA": 100
            },
        },
    },
    "NOTIFICATION": {
        "VISIBLE": True,
        "TIMEOUT": 5,  # in seconds
        "POSITION": "top-right",
    },
    "OSD": {
        "VISIBLE": True,
        "TIMEOUT": 2,  # in seconds
    },
    "DESKTOP_WIDGETS": {
        "VISIBLE": True,
        "WIDGETS": ["DAY"],
    },
    "BAR": {
        "POSITION": "top",
        "VISIBLE": True,
        "MODULES": {
            "WORKSPACES": True,
            "WEATHER": {
                "VISIBLE": True,
                "REFRESH_INTERVAL": 10,  # in minutes
            },
            "PERFORMANCE": True,
            "TRAY": True,
            "CLOCK": True,
            "KEYBOARD_LAYOUT": True,
            "TIME": True,
            "POWER": True
        },
    },
    "CORNERS": {
        "VISIBLE": True,
        "SIZE": 24,
    },
}

class Config:
    def __init__(self, path: str = "config.yaml") -> None:
        self._path = os.path.join(os.path.dirname(__file__), "..", path)
        self._user_config = {}
        self._config = {}
        self.init()

    def _from_any_case_to_upper_snake(self, name: str) -> str:
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).upper()

    def _read_yaml(self) -> dict:
        if not os.path.exists(self._path):
            return {}
        with open(self._path, "r") as f:
            return yaml.safe_load(f)

    def _build(self, user_config: dict) -> dict:
        return merge(default_config, user_config) # type: ignore

    def init(self):
        # Walk config and updated variables names
        def walk(d: dict | list) -> dict | list:
            if isinstance(d, dict):
                return {self._from_any_case_to_upper_snake(k): walk(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [walk(i) for i in d]
            else:
                return d
        self._user_config = walk(self._read_yaml())
        if self._user_config is None:
            self._user_config = {}
        self._user_config['APP_NAME'] = self._user_config.get('APP_NAME', default_config['APP_NAME'])
        self._user_config['STYLES'] = self._user_config.get('STYLES', default_config['STYLES'])
        self._user_config['STYLES']['NOTCH_HEIGHT'] = self._user_config['STYLES'].get('NOTCH_HEIGHT', default_config['STYLES']['NOTCH_HEIGHT'])

        # Validate the user configuration
        self._validate(self._user_config, default_config) # type: ignore

        self._config = self._user_config # type: ignore

    def __getitem__(self, key: str):
        return self._config[key] # type: ignore

    def __setitem__(self, key: str, value):
        """
        Allows setting configuration values at runtime.
        """
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value # type: ignore

    def get(self, key: str) -> str | int | float | bool | dict | list:
        """
        Retrieves a configuration value by key, with support for nested keys.
        """
        keys = key.split(".")
        config = self._config
        for k in keys:
            config = config[k] # type: ignore
        return config

    def set(self, key: str, value):
        """
        Sets a configuration value by key, with support for nested keys.
        """
        self.__setitem__(key, value)

    def save(self):
        """
        Saves the current configuration to the YAML file.
        """
        with open(self._path, "w") as f:
            yaml.dump(self._config, f, sort_keys=False)

    def _validate(self, config: dict, reference: dict, path: str = "") -> None:
        """
        Validates the structure and types of the user-provided configuration
        against the default configuration.

        :param config: The user-provided configuration to validate.
        :param reference: The reference configuration (default_config).
        :param path: The current path in the configuration (used for error messages).
        :raises ValueError: If the structure or types are invalid.
        """
        for key in config:
            current_path = f"{path}.{key}" if path else key

            if key not in reference:
                warnings.warn(f"Warning: Unused key in configuration: '{current_path}'")
                continue  # Skip validation for unused keys

            ref_value = reference[key]
            user_value = config[key]

            # Check type
            if isinstance(ref_value, dict):
                if not isinstance(user_value, dict):
                    raise ValueError(f"Invalid type at '{current_path}': expected dict, got {type(user_value).__name__}")
                # Recursively validate nested dictionaries
                self._validate(user_value, ref_value, current_path)
            elif isinstance(ref_value, list):
                if not isinstance(user_value, list):
                    raise ValueError(f"Invalid type at '{current_path}': expected list, got {type(user_value).__name__}")
                # Validate list elements (if the reference list is not empty)
                if ref_value and not all(isinstance(item, type(ref_value[0])) for item in user_value):
                    raise ValueError(f"Invalid list element types at '{current_path}'")
            else:
                if not isinstance(user_value, type(ref_value)):
                    raise ValueError(f"Invalid type at '{current_path}': expected {type(ref_value).__name__}, got {type(user_value).__name__}")

config = Config()
