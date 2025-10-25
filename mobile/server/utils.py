import os
import json
import uuid
import random
import netifaces as ni

CONFIG_PATH = os.path.expanduser("~/.config/my-shell/config/mobile-app/config.json")

def get_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
            return data
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump({}, f)
    return {}

def get_or_create_device_id():
  config = get_config()
  if "device_id" in config:
      return config["device_id"]
  device_id = str(uuid.uuid4())
  config["device_id"] = device_id
  with open(CONFIG_PATH, "w") as f:
      json.dump(config, f)
  return device_id

def get_or_create_api_key():
  config = get_config()
  if "api_key" in config:
      return config["api_key"]
  api_key = str(random.randint(100000, 999999))
  config["api_key"] = api_key
  with open(CONFIG_PATH, "w") as f:
      json.dump(config, f)
  return api_key

def get_lan_ip():
    for iface in ni.interfaces():
        if iface.startswith("wl") or iface.startswith("en"):
            addrs = ni.ifaddresses(iface).get(ni.AF_INET, [])
            if addrs:
                return addrs[0]["addr"]
    return "127.0.0.1"
