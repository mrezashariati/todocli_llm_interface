from typing import Any, Optional
import logging
import time
import requests
import os
import json

from langchain_core.pydantic_v1 import BaseModel
from langchain_core.utils import get_from_dict_or_env
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM

import pyowm
from pyowm.commons.exceptions import NotFoundError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("debug.log"),
        # logging.StreamHandler()
    ],
)


class LLAMA2(LLM):
    api_url = "https://6xtdhvodk2.execute-api.us-west-2.amazonaws.com/dsa_llm/generate"
    retries = 3
    max_gen_len = 1024
    temperature = 0.2
    top_p = 0.9

    @property
    def _llm_type(self) -> str:
        return "LLAMA2_70b"

    def _call(
        self,
        prompt: str,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        with open("./aws_api_quota_remaining", "r") as f:
            aws_api_quota_remaining = int(f.readlines()[0].strip())
        body = {
            "prompt": prompt,
            "max_gen_len": self.max_gen_len,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "api_token": os.environ["AWS_API_KEY"],
        }
        result = ""
        # Retry for i times if request timed out
        for i in range(self.retries):
            try:
                res = requests.post(self.api_url, json=body, timeout=30)
            except requests.exceptions.Timeout as e:
                logging.info(f"LLM response timeout")
                time.sleep(5)
                continue

            aws_api_quota_remaining -= 1
            with open("./aws_api_quota_remaining", "w") as f:
                f.write(str(aws_api_quota_remaining))
            logging.info(f"ramining AWS API calls: {aws_api_quota_remaining}")
            try:
                result = json.loads(res.text)["body"]["generation"]
                break
            except KeyError:
                logging.info(f"LLM response is empty. The response text:\n{res.text}")
                time.sleep(5)

        if result:
            logging.info(
                f"Raw LLM response:\n----------\n{result}\n----------",
            )
            return result
        else:
            raise Exception("Failed to get response from LLM")


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

    def run(self, city_date) -> str:
        """Get the forcasted weather information for a specified city and date.
        There is only one parameter. The city_date parameter should be formatted as: CITY WITHOUT COUNTRY, DATE. Nothing more or less. The date part should be formatted like YYYY-MM-DD HH:MM:SS
        do not ever input country.
        """
        try:
            location, date = city_date.split(",")
            location, date = location.strip(), date.strip()
            mgr = self.owm.weather_manager()

            observation = mgr.forecast_at_place(
                name=location, interval="3h", limit=None
            )
            w = observation.get_weather_at(date)
        except (NotFoundError, ValueError) as e:
            logging.info(e)
            return f"Tool failed to execute. Weather forecast information not available. No response can be provided to the user."
        return self._format_weather_info(location, date, w)
