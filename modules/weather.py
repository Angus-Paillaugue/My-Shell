import threading

import requests
from fabric import Property, Service
from fabric.core.fabricator import Fabricator
from fabric.core.service import Property
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from gi.repository import GLib  # type: ignore

import modules.icons as icons
from services.config import config
from services.logger import logger


class Weather:
    """Class to represent weather data with icon and temperature."""

    def __init__(self, icon=None, temperature=None):
        self.icon = icon
        self.temperature = temperature

    def get_weather(self):
        return {"icon": self.icon, "temperature": self.temperature}

    def set_weather(self, icon, temperature):
        self.icon = icon
        self.temperature = temperature

    def __str__(self):
        return f"Weather(icon={self.icon}, temperature={self.temperature})"


class WeatherWorker(Service):
    """Service to fetch and update weather data."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._weather = Weather()
        self.update_thread_active = False

    @Property(Weather, "read-write")
    def weather(self):
        return self._weather

    def update_weather(self) -> None:
        """Fetch weather data from an external API and update the weather property."""
        if self.update_thread_active:
            return

        def worker():
            self.update_thread_active = True
            uri = "https://wttr.in/?format=%c+%t"
            res = requests.get(uri)
            if not res.ok:
                logger.error(f"Failed to fetch weather data: {res.status_code}")
                self._weather.set_weather(icon=None, temperature=None)
                self.update_thread_active = False
                return
            elements_list = [el for el in res.text.split(" ") if el != ""]
            print(res.text)
            if (not all(isinstance(item, str) for item in elements_list) or
                    len(elements_list) != 2):
                logger.error("Weather data format is incorrect.")
                self._weather.set_weather(icon=None, temperature=None)
            else:
                self._weather.set_weather(icon=elements_list[0],
                                          temperature=elements_list[1].replace(
                                              "+", ""))
                logger.info(f"Weather updated: {self._weather}")
            self.update_thread_active = False

        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()


class WeatherButton(Button):
    """A button that displays the current weather icon and temperature, updating at a set interval."""

    def __init__(self, update_interval=10, **kwargs):
        super().__init__(
            name="weather-button",
            style_classes=[
                "bar-item",
                (
                    "horizontal"
                    if config['POSITIONS']['BAR'] in ["top", "bottom"]
                    else "vertical"
                ),
            ],
            **kwargs,
        )
        self.weather_worker = WeatherWorker()
        self.main_container = Box(
            orientation="h" if config['POSITIONS']['BAR'] in ["top", "bottom"] else "v",
            spacing=8,
        )
        self.loading_icon = Label(
            name="weather-loading-icon",
            markup=icons.loading,
            style_classes=["loading-icon"],
        )
        self.icon = Label(
            name="weather-icon",
            label="",
        )
        self.temperature = Label(
            name="weather-temperature",
            label="",
        )
        self.main_container.add(self.loading_icon)
        self.main_container.add(self.icon)
        self.main_container.add(self.temperature)
        self.add(self.main_container)
        self.weather_fabricator = Fabricator(
            poll_from=lambda v: self.weather_worker.update_weather(),
            on_changed=lambda f, v: self._build(),
            interval=1000 * 60 *
            update_interval,  # Update every update_interval (10) minutes
            stream=False,
            default_value=0,
        )
        GLib.idle_add(self._build, None, self.weather_worker.update_weather())

    def update_weather(self) -> None:
        """Trigger the weather update process."""
        self._set_loading(True)
        self.weather_worker.update_weather()

    def _set_loading(self, is_loading: bool) -> None:
        """Set the loading state of the weather button."""
        self.is_loading = is_loading
        if is_loading:
            self.loading_icon.show()
            self.icon.hide()
            self.temperature.hide()
        else:
            self.loading_icon.hide()
            self.icon.show()
            self.temperature.show()

    def _build(self, *args: object) -> bool:
        """Build the weather button with the current weather data."""
        weather = self.weather_worker.weather
        self._set_loading(False)
        if weather.icon is None or weather.temperature is None:
            self.set_visible(False)
            return False
        self.set_visible(True)
        self.icon.set_label(weather.icon)
        self.temperature.set_label(weather.temperature)
        self.main_container.add(self.icon)
        self.main_container.add(self.temperature)
        return True
