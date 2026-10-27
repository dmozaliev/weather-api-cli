from pathlib import Path
from unittest.mock import patch

import pytest

from api_client import WeatherAPIError, describe_weather_code, geocode_city, get_weather_report
from main import add_favorite, load_favorites, remove_favorite


def test_describe_weather_code() -> None:
    assert describe_weather_code(0) == "Clear sky"
    assert describe_weather_code(61) == "Slight rain"
    assert describe_weather_code(999) == "Code 999"


def test_geocode_city_mocked() -> None:
    fake_geo = {
        "results": [
            {
                "name": "Kaufering",
                "country": "Germany",
                "admin1": "Bavaria",
                "latitude": 48.09,
                "longitude": 10.88,
            }
        ]
    }
    with patch("api_client.fetch_json", return_value=fake_geo):
        loc = geocode_city("Kaufering")
        assert loc.name == "Kaufering"
        assert loc.country == "Germany"
        assert loc.region == "Bavaria"
        assert loc.latitude == 48.09


def test_geocode_unknown_city_raises() -> None:
    with patch("api_client.fetch_json", return_value={}):
        with pytest.raises(WeatherAPIError, match="was not found"):
            geocode_city("NonExistentPlace12345")


def test_get_weather_report_mocked() -> None:
    fake_geo = {
        "results": [
            {
                "name": "Augsburg",
                "country": "Germany",
                "admin1": "Bavaria",
                "latitude": 48.37,
                "longitude": 10.89,
            }
        ]
    }
    fake_forecast = {
        "current": {
            "temperature_2m": 14.5,
            "apparent_temperature": 13.2,
            "relative_humidity_2m": 68,
            "wind_speed_10m": 11.4,
            "weather_code": 2,
        },
        "daily": {
            "time": ["2026-10-27", "2026-10-28"],
            "temperature_2m_max": [16.0, 14.0],
            "temperature_2m_min": [7.5, 6.0],
            "precipitation_probability_max": [10, 40],
            "weather_code": [2, 61],
        },
    }
    with patch("api_client.fetch_json", side_effect=[fake_geo, fake_forecast]):
        report = get_weather_report("Augsburg")
        assert report.location.name == "Augsburg"
        assert report.temperature == 14.5
        assert report.condition == "Partly cloudy"
        assert len(report.daily) == 2
        assert report.daily[1].condition == "Slight rain"


def test_favorites_persistence(tmp_path: Path) -> None:
    fav_file = tmp_path / "favorites.json"
    assert load_favorites(fav_file) == []
    assert "Added 'Kaufering'" in add_favorite("Kaufering", fav_file)
    assert "already in favorites" in add_favorite("kaufering", fav_file)
    assert load_favorites(fav_file) == ["Kaufering"]
    assert "Removed" in remove_favorite("Kaufering", fav_file)
    assert load_favorites(fav_file) == []
