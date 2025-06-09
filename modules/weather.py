import requests
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.box import Box
from fabric.core.service import Property
import modules.icons as icons
from fabric import Property, Service, Signal
import threading
from services.logger import logger


class Weather():

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

    @Signal
    def update(self):
        ...

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._weather = Weather()
        self.update_thread_active = False

    @Property(Weather, "read-write")
    def weather(self):
        return self._weather

    def update_weather(self):
        if self.update_thread_active:
            return

        def worker():
            self.update_thread_active = True
            uri = "https://wttr.in/?format=%c+%t"
            res = requests.get(uri)
            elements_list = [el for el in res.text.split(" ") if el != ""]
            if not all(isinstance(item, str) for item in elements_list):
                logger.error("Weather data format is incorrect.")
                self._weather.set_weather(icon=None, temperature=None)
            else:
                self._weather.set_weather(icon=elements_list[0],
                                          temperature=elements_list[1].replace(
                                              "+", ""))
                logger.info(f"Weather updated: {self._weather}")
            self.update_thread_active = True
            self.emit("update")

        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()


class WeatherButton(Button):

    def __init__(self, **kwargs):
        super().__init__(
            name="weather-button",
            **kwargs,
        )
        self.weather_worker = WeatherWorker()
        self.weather_worker.connect("update", self._build)
        self.main_container = Box(
            orientation="h",
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
        self.update_weather()

    def update_weather(self):
        self._set_loading(True)
        self.weather_worker.update_weather()

    def _set_loading(self, is_loading):
        self.is_loading = is_loading
        if is_loading:
            self.loading_icon.show()
            self.icon.hide()
            self.temperature.hide()
        else:
            self.loading_icon.hide()
            self.icon.show()
            self.temperature.show()

    def _build(self, *_):
        weather = self.weather_worker.weather
        print(weather)
        self._set_loading(False)
        if weather.icon is None or weather.temperature is None:
            return
        self.icon.set_label(weather.icon)
        self.temperature.set_label(weather.temperature)
        self.main_container.add(self.icon)
        self.main_container.add(self.temperature)
