from datetime import date
from typing import Optional

import requests

# Open-Meteo is free and needs no API key, unlike weather websites, which block scrapers or draw the forecast with JavaScript
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_S = 15

# Where the robot lives, used when nobody names a place
HOME_LOCATION = "San Luis Obispo, California"
MAX_FORECAST_DAYS = 7

# WMO weather interpretation codes, as Open-Meteo reports them
WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "freezing fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 56: "light freezing drizzle", 57: "freezing drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain", 66: "light freezing rain", 67: "freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "light showers", 81: "showers", 82: "violent showers", 85: "light snow showers", 86: "snow showers",
    95: "thunderstorms", 96: "thunderstorms with hail", 99: "thunderstorms with heavy hail",
}


def find_place(location: str) -> dict:
    """
    The best geocoding match for a place such as "Paris" or "Portland, Oregon".
    The geocoder only understands a bare place name, so anything after the first comma is used to pick between matches.
    """
    name, _, region = location.partition(",")
    response = requests.get(GEOCODING_URL, params={"name": name.strip(), "count": 10, "language": "en"}, timeout=TIMEOUT_S)
    response.raise_for_status()
    places = response.json().get("results") or []
    if not places:
        raise ValueError(f"Could not find a place called {location!r}.")
    region = region.strip().lower()
    if region:
        for place in places:
            labels = (place.get("admin1", ""), place.get("country", ""), place.get("country_code", ""))
            if any(region == label.lower() or region in label.lower() for label in labels if label):
                return place
    return places[0]


def describe(code) -> str:
    return WEATHER_CODES.get(code, "unknown conditions")


def get_weather(location: Optional[str] = None, days: Optional[int] = None) -> str:
    """
    Get the current weather and the forecast for the next few days. Use this for any question about the weather instead of searching the web.

    :param location: The town or city, optionally followed by a comma and the state or country, such as "Portland, Oregon". Leave it out for home.
    :param days: How many days of forecast to get, counting today. Values between 1 and 7 (default: 3).
    """
    # Each day in the result is named, so the LLM doesn't have to work out dates
    days = max(1, min(int(days or 3), MAX_FORECAST_DAYS))
    place = find_place(location or HOME_LOCATION)
    response = requests.get(FORECAST_URL, params={
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": "auto",
        "forecast_days": days,
    }, timeout=TIMEOUT_S)
    response.raise_for_status()
    data = response.json()

    place_name = ", ".join(p for p in (place.get("name"), place.get("admin1"), place.get("country")) if p)
    current = data["current"]
    lines = [
        f"Weather for {place_name}.",
        f"Now: {describe(current['weather_code'])}, {current['temperature_2m']:.0f}°F "
        f"(feels like {current['apparent_temperature']:.0f}°F), wind {current['wind_speed_10m']:.0f} mph.",
    ]
    daily = data["daily"]
    today = date.fromisoformat(daily["time"][0])
    for i, day_text in enumerate(daily["time"]):
        day = date.fromisoformat(day_text)
        label = {0: "Today", 1: "Tomorrow"}.get((day - today).days, day.strftime("%A"))
        lines.append(
            f"{label} ({day.strftime('%A %d %B')}): {describe(daily['weather_code'][i])}, "
            f"high {daily['temperature_2m_max'][i]:.0f}°F, low {daily['temperature_2m_min'][i]:.0f}°F, "
            f"{daily['precipitation_probability_max'][i] or 0}% chance of rain, "
            f"wind up to {daily['wind_speed_10m_max'][i]:.0f} mph."
        )
    return "\n".join(lines)
