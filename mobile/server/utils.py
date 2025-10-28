import os
import json
import uuid
import netifaces as ni
from services.config import config

CONFIG_PATH = os.path.expanduser("~/.config/vellum-shell/config/sync-app/config.json")

def init_config():
    base_config = {
        "device_id": str(uuid.uuid4()),
        "api_key": str(uuid.uuid4())
    }
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(base_config, f, indent=2)
        return base_config

def get_config():
    if not os.path.exists(CONFIG_PATH):
        return init_config()
    with open(CONFIG_PATH, "r") as f:
        data = json.load(f)
        return data

def get_lan_ip():
    for iface in ni.interfaces():
        if iface.startswith("wl") or iface.startswith("en"):
            addrs = ni.ifaddresses(iface).get(ni.AF_INET, [])
            if addrs:
                return addrs[0]["addr"]
    return "127.0.0.1"

def _upper_snake_object_to_lower_camel_case(obj):
    if isinstance(obj, list):
        return [_upper_snake_object_to_lower_camel_case(item) for item in obj]
    elif isinstance(obj, dict):
        new_obj = {}
        for key, value in obj.items():
            components = key.lower().split('_')
            camel_case_key = components[0] + ''.join(x.title() for x in components[1:])
            new_obj[camel_case_key] = _upper_snake_object_to_lower_camel_case(value)
        return new_obj
    else:
        return obj

def config_file_changed():
    config.init()

def get_actions(sanitized=False):
    actions = config.get('SYNC.ACTIONS')
    for key in actions:
        actions[key]['id'] = key
    actions = list(actions.values())
    if sanitized:
        sanitized_actions = []
        for action in actions:
            sanitized_action = action.copy()
            if "command" in sanitized_action:
                del sanitized_action["command"]
            sanitized_actions.append(sanitized_action)
        return _upper_snake_object_to_lower_camel_case(sanitized_actions)
    return _upper_snake_object_to_lower_camel_case(actions)

def get_config_mtime():
    path = config.get_path()
    if os.path.exists(path):
        return os.path.getmtime(path)
    return None
