# Parameters
font_family: str = "tabler-icons"
font_weight: str = "normal"

span: str = f"<span font-family='{font_family}' font-weight='{font_weight}'>"

settings: str = "&#xf1f6;"
keyboard: str = "&#xebd6;"
# Chevrons
chevron_up: str = "&#xea62;"
chevron_down: str = "&#xea5f;"
chevron_left: str = "&#xea60;"
chevron_right: str = "&#xea61;"
# Power
lock: str = "&#xeae2;"
suspend: str = "&#xece7;"
logout: str = "&#xeba8;"
reboot: str = "&#xeb13;"
shutdown: str = "&#xeb0d;"
# Network
wifi_off: str = "&#xecfa;"
wifi_0: str = "&#xeba3;"
wifi_1: str = "&#xeba4;"
wifi_2: str = "&#xeba5;"
wifi_3: str = "&#xeb52;"
ethernet: str = "&#xeb54;"
ethernet_off: str = "&#xf1ca;"
reload: str = "&#xf3ae;"
# Bluetooth
bluetooth_off: str = "&#xf081;"
bluetooth: str = "&#xea37;"
radar: str = "&#xf017;"
# Brightness
brightness_low: str = "&#xeb7e;"
brightness_high: str = "&#xfb24;"
# Volume
volume_muted: str = "&#xeb50;"
volume_low: str = "&#xeb4f;"
volume_high: str = "&#xeb51;"
mic: str = "&#xeaf0;"
mic_muted: str = "&#xed16;"
check: str = "&#xea5e;"
# Battery
battery_danger: str = "&#xff1d;"
battery_0: str = "&#xea34;"
battery_1: str = "&#xea2f;"
battery_2: str = "&#xea30;"
battery_3: str = "&#xea31;"
battery_4: str = "&#xea32;"
battery_eco: str = "&#xef3c;"
battery_charging: str = "&#xea33;"
# Metrics
cpu: str = "&#xef8e;"
memory: str = "&#xf384;" # TODO: find a better icon
temperature: str = "&#xeb38;"
disk: str = "&#xea88;"
# Launcher
cancel: str = "&#xf640;"
pin_off: str = "&#xec9c;"
pin_on: str = "&#xf68d;"
# Power profile
performance: str = "&#xea38;"
eco: str = "&#xed4f;"
balanced: str = "&#xebc2;"
# Notification
trash: str = "&#xeb41;"
dnd: str = "&#xece9;"
notification: str = "&#xea35;"
notifications_off: str = "&#xece9;"
# Time
point: str = "&#xf698;"
# Dock
grid_dots: str = "&#xeaba;"
arrow_up: str = "&#xfaf3;"
arrow_down: str = "&#xfaf0;"
drag_handle: str = "&#xec01;"
# VPN
tailscale: str = "&#xf39a;"
# Others
screen_record: str = "&#xfca8;"
screenshot: str = "&#xf201;"
loading: str = "&#xea95;"
color_picker: str = "&#xebe6;"

exceptions: list[str] = ["font_family", "font_weight", "span"]


def apply_span() -> None:
    global_dict = globals()
    for key in global_dict:
        if key not in exceptions and not key.startswith("__"):
            global_dict[key] = f"{span}{global_dict[key]}</span>"


apply_span()
