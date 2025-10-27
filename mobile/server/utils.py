import os
import json
import uuid
import netifaces as ni

CONFIG_PATH = os.path.expanduser("~/.config/vellum-shell/config/sync-app/config.json")

default_actions = [
    {
      "id": "lock",
      "title": "Lock Screen",
      "icon": "lock",
      "command": "setsid hyprlock >/dev/null 2>&1 &"
    },
    {
      "id": "unlock",
      "title": "Unlock Screen",
      "icon": "lock_open",
      "command": "pkill -USR1 -f hyprlock"
    },
    {
      "id": "notify",
      "title": "Notify",
      "icon": "notifications",
      "command": "notify-send -e -a 'Vellum Shell PhoneBridge' 'Hello from PhoneBridge!'"
    }
  ]
cached_config = None

def init_config():
    global cached_config
    base_config = {
        "actions": default_actions,
        "device_id": str(uuid.uuid4()),
        "api_key": str(uuid.uuid4())
    }
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(base_config, f, indent=2)
        cached_config = base_config
        return base_config
    with open(CONFIG_PATH, "r") as f:
        try:
            data = json.load(f)
            updated = False
            for key, value in base_config.items():
                if key not in data:
                    data[key] = value
                    updated = True
            if updated:
                with open(CONFIG_PATH, "w") as fw:
                    json.dump(data, fw, indent=2)
            cached_config = data
            return data
        except json.JSONDecodeError:
            with open(CONFIG_PATH, "w") as f:
                json.dump(base_config, f, indent=2)
            cached_config = base_config
            return base_config

def config_changed():
    global cached_config
    if not os.path.exists(CONFIG_PATH):
        return False
    with open(CONFIG_PATH, "r") as f:
        try:
            data = json.load(f)
            if data != cached_config:
                cached_config = data
                return True
            return False
        except json.JSONDecodeError:
            return False

def get_config():
    global cached_config
    if cached_config is None:
        init_config()
    return cached_config

def get_lan_ip():
    for iface in ni.interfaces():
        if iface.startswith("wl") or iface.startswith("en"):
            addrs = ni.ifaddresses(iface).get(ni.AF_INET, [])
            if addrs:
                return addrs[0]["addr"]
    return "127.0.0.1"

def get_actions(sanitized=False):
    config = get_config()
    if sanitized:
        # Remove the command field for sanitized output
        actions = config.get("actions", default_actions)
        sanitized_actions = []
        for action in actions:
            sanitized_action = action.copy()
            if "command" in sanitized_action:
                del sanitized_action["command"]
            sanitized_actions.append(sanitized_action)
        return sanitized_actions
    return config.get("actions", default_actions)

def get_config_mtime():
    if os.path.exists(CONFIG_PATH):
        return os.path.getmtime(CONFIG_PATH)
    return None
