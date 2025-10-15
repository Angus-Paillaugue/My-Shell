from services.config import config
import os
from fabric.utils.helpers import exec_shell_command_async
import toml
import shutil

app_location = os.path.expanduser(f"~/.config/{config['APP_NAME']}")


def deep_update(target: dict, update: dict) -> dict:
    """
    Recursively update a nested dictionary with values from another dictionary.
    Modifies target in-place.
    """
    for key, value in update.items():
        if isinstance(value, dict) and key in target and isinstance(
                target[key], dict):
            deep_update(target[key], value)
        else:
            target[key] = value
    return target


def ensure_matugen_config() -> None:
    """
    Ensure that the matugen configuration file exists and is updated
    with the expected settings.
    """
    expected_config = {
        "config": {
            "reload_apps": True,
            "wallpaper": {
                "command": "swww",
                "arguments": [
                    "img",
                    "--transition-type",
                    "grow",
                    "--transition-pos",
                    "0.854,0.033",
                    "--transition-step",
                    "90",
                    "--transition-fps",
                    "60",
                    "-f",
                    "Nearest",
                ],
                "set": True,
            },
            "custom_colors": {
                "red": {
                    "color": "#FF0000",
                    "blend": True
                },
                "green": {
                    "color": "#00FF00",
                    "blend": True
                },
                "yellow": {
                    "color": "#FFFF00",
                    "blend": True
                },
                "blue": {
                    "color": "#0000FF",
                    "blend": True
                },
                "magenta": {
                    "color": "#FF00FF",
                    "blend": True
                },
                "cyan": {
                    "color": "#00FFFF",
                    "blend": True
                },
                "white": {
                    "color": "#FFFFFF",
                    "blend": True
                },
            },
        },
        "templates": {
            "hyprland": {
                "input_path":
                    os.path.join(
                        app_location,
                        "config/matugen/templates/hyprland-colors.conf"),
                "output_path":
                    os.path.join(app_location, "config/hypr/colors.conf"),
            },
            f"{config['APP_NAME']}": {
                "input_path":
                    os.path.join(
                        app_location,
                        f"config/matugen/templates/{config['APP_NAME']}.css"),
                "output_path":
                    os.path.join(app_location, "styles/colors.mcss"),
                "post_hook":
                    f"fabric-cli exec {config['APP_NAME']} 'app.apply_stylesheet()' &",
            },
            "kitty": {
                "input_path":
                    os.path.join(app_location,
                                 "config/matugen/templates/kitty.conf"),
                "output_path":
                    "~/.config/kitty/colors.conf",
            },
        },
    }

    config_path = os.path.expanduser("~/.config/matugen/config.toml")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    existing_config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                existing_config = toml.load(f)
            shutil.copyfile(config_path, config_path + ".bak")
        except toml.TomlDecodeError:
            print(
                f"Warning: Could not decode TOML from {config_path}. A new default config will be created."
            )
            existing_config = {}
        except Exception as e:
            print(f"Error reading or backing up {config_path}: {e}")

    merged_config = deep_update(existing_config, expected_config)

    try:
        with open(config_path, "w") as f:
            toml.dump(merged_config, f)
    except Exception as e:
        print(f"Error writing matugen config to {config_path}: {e}")

    current_wall = os.path.expanduser("~/.current.wall")
    hypr_colors = os.path.join(app_location, "config/hypr/colors.conf")
    css_colors = os.path.join(app_location, "styles/colors.mcss")

    if (not os.path.exists(current_wall) or not os.path.exists(hypr_colors) or
            not os.path.exists(css_colors)):
        os.makedirs(os.path.dirname(hypr_colors), exist_ok=True)
        os.makedirs(os.path.dirname(css_colors), exist_ok=True)

        image_path = ""
        if not os.path.exists(current_wall):
            example_wallpaper_path = os.path.join(
                app_location, "assets/wallpapers_example/green_forest.jpg")
            if os.path.exists(example_wallpaper_path):
                try:
                    if os.path.lexists(current_wall):
                        os.remove(current_wall)
                    os.symlink(example_wallpaper_path, current_wall)
                    image_path = example_wallpaper_path
                except Exception as e:
                    print(f"Error creating symlink for wallpaper: {e}")
        else:
            image_path = (os.path.realpath(current_wall)
                          if os.path.islink(current_wall) else current_wall)

        if image_path and os.path.exists(image_path):
            print(f"Generating color theme from wallpaper: {image_path}")
            try:
                matugen_cmd = f"matugen image '{image_path}'"
                exec_shell_command_async(matugen_cmd)
                print("Matugen color theme generation initiated.")
            except FileNotFoundError:
                print(
                    "Error: matugen command not found. Please install matugen.")
            except Exception as e:
                print(f"Error initiating matugen: {e}")
        elif not image_path:
            print(
                "Warning: No wallpaper path determined to generate matugen theme from."
            )
        else:
            print(
                f"Warning: Wallpaper at {image_path} not found. Cannot generate matugen theme."
            )


def generate_hypr_entrypoint() -> None:
    contents = f"""source = ~/.config/{config['APP_NAME']}/config/hypr/overrides.conf"""
    location = os.path.expanduser(f"~/.config/hypr/hyprland.conf")
    if not os.path.exists(location):
        raise FileNotFoundError(
            f"Hyprland configuration file not found at {location}. Please ensure Hyprland is installed."
        )
    already_contains = False
    with open(location, "r") as f:
        if contents.strip() in f.read():
            already_contains = True
    if not already_contains:
        with open(location, "a") as f:
            f.write(contents + "\n")
            print(f"Hyprland entrypoint updated at {location}")


def generate_hyprlock_config() -> None:
    location = os.path.expanduser(f"~/.config/hypr/hyprlock.conf")
    template_location = os.path.join(app_location, "config/hypr/hyprlock.conf")
    backup_location = os.path.expanduser(f"~/.config/hypr/hyprlock.conf.bak")

    # Create a backup of the existing hyprlock configuration if it exists
    if os.path.exists(location) and not os.path.exists(backup_location):
        shutil.copyfile(location, backup_location)
        print(f"Backup created at {backup_location}")

    with open(template_location, "r") as f:
        contents = f.read()
        contents = contents.replace("{{APP_NAME}}", config['APP_NAME'])
    with open(location, "w") as f:
        f.write(contents)
    print(f"Hyprlock configuration updated")


def update_kitty_config() -> None:
    contents = "include colors.conf"
    location = os.path.expanduser(f"~/.config/kitty/kitty.conf")
    if not os.path.exists(location):
        print(f"Kitty configuration file not found at {location}.")

    already_contains = False
    with open(location, "r") as f:
        if contents.strip() in f.read():
            already_contains = True
    if not already_contains:
        with open(location, "r") as original_file:
            data = original_file.read()
        with open(location, "w") as modified_file:
            modified_file.write(contents + "\n" + data)
        print(f"Kitty configuration updated at {location}")


def wallpapers() -> None:
    """
    Ensure the wallpapers directory exists and contains example wallpapers.
    """
    input_dir = os.path.join(app_location, "assets/wallpapers_example")
    output_dir = os.path.expanduser(f"~/Pictures/wallpapers/")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(input_dir):
        src_path = os.path.join(input_dir, filename)
        dest_path = os.path.join(output_dir, filename)
        if not os.path.exists(dest_path):
            shutil.copy(src_path, dest_path)


def ensure_app_config() -> None:
    """
    Ensure that the application configuration file exists.
    """
    config_path = os.path.join(app_location, "config.yaml")
    if not os.path.exists(config_path):
        default_config_path = os.path.join(app_location, "config.default.yaml")
        shutil.copyfile(default_config_path, config_path)
        print(f"Default configuration copied to {config_path}")


def install_fonts() -> None:
    """
    Install the required fonts if they are not already installed.
    """
    fonts_dir = os.path.join(app_location, "assets/fonts")
    user_fonts_dir = os.path.expanduser("~/.local/share/fonts")
    if not os.path.exists(user_fonts_dir):
        os.makedirs(user_fonts_dir)
    for font_file in os.listdir(fonts_dir):
        src_path = os.path.join(fonts_dir, font_file)
        dest_path = os.path.join(user_fonts_dir, font_file)
        if not os.path.exists(dest_path):
            shutil.copy(src_path, dest_path)
            print(f"Installed font: {font_file}")


if __name__ == "__main__":
    ensure_app_config()
    install_fonts()
    ensure_matugen_config()
    generate_hypr_entrypoint()
    generate_hyprlock_config()
    update_kitty_config()
    wallpapers()
