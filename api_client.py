import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Standard WMO weather interpretation codes returned by Open-Meteo
WMO_WEATHER_CODES: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Moderate showers",
    82: "Heavy showers",
    95: "Thunderstorm",
}


class WeatherAPIError(Exception):
    """Custom exception for network, HTTP, or city-lookup errors."""


@dataclass
class CityLocation:
    """Geographic coordinates and metadata returned by the Geocoding API."""

    name: str
    country: str
    region: str
    latitude: float
    longitude: float


@dataclass
class DailyForecast:
    """Weather summary for a single forecast day."""

    date: str
    temp_min: float
    temp_max: float
    precip_prob: int
    condition: str


@dataclass
class WeatherReport:
    """Complete current weather and 5-day forecast for a location."""

    location: CityLocation
    temperature: float
    feels_like: float
    humidity: int
    wind_speed: float
    condition: str
    daily: list[DailyForecast]


def describe_weather_code(code: int) -> str:
    """Maps a numeric WMO weather code to a readable description."""
    return WMO_WEATHER_CODES.get(code, f"Code {code}")


def fetch_json(base_url: str, params: dict[str, str | int | float]) -> dict:
    """Sends an HTTP GET request with URL-encoded query parameters and parses JSON."""
    query_string = urlencode(params)
    full_url = f"{base_url}?{query_string}"
    request = Request(full_url, headers={"User-Agent": "PythonWeatherCLI/1.0"})

    try:
        with urlopen(request, timeout=7) as response:
            raw_body = response.read().decode("utf-8")
            return json.loads(raw_body)
    except HTTPError as err:
        raise WeatherAPIError(f"HTTP error {err.code} while contacting API.") from err
    except URLError as err:
        raise WeatherAPIError("Network error: please check your internet connection.") from err
    except TimeoutError as err:
        raise WeatherAPIError("Request timed out while waiting for the server.") from err
    except json.JSONDecodeError as err:
        raise WeatherAPIError("Invalid JSON response received from server.") from err


def geocode_city(city_name: str) -> CityLocation:
    """Resolves a city name into geographic coordinates via Open-Meteo Geocoding API."""
    cleaned = city_name.strip()
    if not cleaned:
        raise WeatherAPIError("City name cannot be empty.")

    data = fetch_json(
        GEOCODING_URL,
        {"name": cleaned, "count": 1, "language": "en", "format": "json"},
    )
    results = data.get("results")
    if not results:
        raise WeatherAPIError(f"City '{cleaned}' was not found.")

    item = results[0]
    return CityLocation(
        name=item.get("name", cleaned),
        country=item.get("country", "Unknown"),
        region=item.get("admin1", ""),
        latitude=float(item["latitude"]),
        longitude=float(item["longitude"]),
    )


def get_weather_report(city_name: str) -> WeatherReport:
    """Fetches current conditions and a 5-day forecast for the given city."""
    location = geocode_city(city_name)

    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "forecast_days": 5,
        "timezone": "auto",
    }
    data = fetch_json(FORECAST_URL, params)

    current = data.get("current", {})
    daily_raw = data.get("daily", {})

    dates = daily_raw.get("time", [])
    t_max = daily_raw.get("temperature_2m_max", [])
    t_min = daily_raw.get("temperature_2m_min", [])
    precip = daily_raw.get("precipitation_probability_max", [])
    codes = daily_raw.get("weather_code", [])

    daily_list: list[DailyForecast] = []
    for i in range(len(dates)):
        prob = precip[i] if i < len(precip) and precip[i] is not None else 0
        daily_list.append(
            DailyForecast(
                date=dates[i],
                temp_min=float(t_min[i]),
                temp_max=float(t_max[i]),
                precip_prob=int(prob),
                condition=describe_weather_code(int(codes[i])),
            )
        )

    return WeatherReport(
        location=location,
        temperature=float(current.get("temperature_2m", 0.0)),
        feels_like=float(current.get("apparent_temperature", 0.0)),
        humidity=int(current.get("relative_humidity_2m", 0)),
        wind_speed=float(current.get("wind_speed_10m", 0.0)),
        condition=describe_weather_code(int(current.get("weather_code", 0))),
        daily=daily_list,
    )
