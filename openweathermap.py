"""Util that calls OpenWeatherMap using PyOWM."""

from typing import Any

from langchain_core.pydantic_v1 import BaseModel, Extra
from langchain_core.utils import get_from_dict_or_env

import pyowm


class OpenWeatherMapAPIWrapper(BaseModel):
    """Wrapper for OpenWeatherMap API using PyOWM.

    Docs for using:

    1. Go to OpenWeatherMap and sign up for an API key
    2. Save your API KEY into OPENWEATHERMAP_API_KEY env variable
    3. pip install pyowm
    """

    openweathermap_api_key = get_from_dict_or_env(
        {}, "openweathermap_api_key", "OPENWEATHERMAP_API_KEY"
    )
    owm = pyowm.OWM(openweathermap_api_key)

    class Config:
        """Configuration for this pydantic object."""

        arbitrary_types_allowed = True

    def _format_weather_info(self, location: str, time: str, w: Any) -> str:
        detailed_status = w.detailed_status
        wind = w.wind()
        humidity = w.humidity
        temperature = w.temperature("celsius")
        rain = w.rain
        heat_index = w.heat_index
        clouds = w.clouds

        return (
            f"In {location}, closest to {time}, the weather is as follows:\n"
            f"Detailed status: {detailed_status}\n"
            f"Wind speed: {wind['speed']} m/s, direction: {wind['deg']}°\n"
            f"Humidity: {humidity}%\n"
            f"Temperature: \n"
            f"  - Current: {temperature['temp']}°C\n"
            f"  - High: {temperature['temp_max']}°C\n"
            f"  - Low: {temperature['temp_min']}°C\n"
            f"  - Feels like: {temperature['feels_like']}°C\n"
            f"Rain: {rain}\n"
            f"Heat index: {heat_index}\n"
            f"Cloud cover: {clouds}%"
        )

    def run(self, location: str, time: str) -> str:
        """Get the current weather information for a specified location."""
        mgr = self.owm.weather_manager()
        observation = mgr.forecast_at_place(name=location, interval="3h", limit=None)
        w = observation.get_weather_at(time)
        # w = observation.weather

        return self._format_weather_info(location, time, w)
