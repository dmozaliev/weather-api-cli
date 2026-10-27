import json
import sys
from pathlib import Path

from api_client import WeatherAPIError, WeatherReport, get_weather_report

FAVORITES_PATH = Path(__file__).resolve().parent / "favorites.json"


def load_favorites(path: Path = FAVORITES_PATH) -> list[str]:
    """Loads the list of favorite cities from a local JSON file."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [str(city) for city in data] if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_favorites(cities: list[str], path: Path = FAVORITES_PATH) -> None:
    """Saves the list of favorite cities to a local JSON file."""
    path.write_text(json.dumps(cities, indent=2, ensure_ascii=False), encoding="utf-8")


def add_favorite(city: str, path: Path = FAVORITES_PATH) -> str:
    """Adds a city to favorites if not already saved."""
    cleaned = city.strip()
    if not cleaned:
        return "Usage: fav add <city>"
    favorites = load_favorites(path)
    if any(c.lower() == cleaned.lower() for c in favorites):
        return f"'{cleaned}' is already in favorites."
    favorites.append(cleaned)
    save_favorites(favorites, path)
    return f"Added '{cleaned}' to favorites."


def remove_favorite(city: str, path: Path = FAVORITES_PATH) -> str:
    """Removes a city from favorites."""
    cleaned = city.strip()
    favorites = load_favorites(path)
    updated = [c for c in favorites if c.lower() != cleaned.lower()]
    if len(updated) == len(favorites):
        return f"'{cleaned}' was not found in favorites."
    save_favorites(updated, path)
    return f"Removed '{cleaned}' from favorites."


def format_weather_report(report: WeatherReport) -> str:
    """Formats a WeatherReport into a clean terminal dashboard."""
    loc = report.location
    region_str = f", {loc.region}" if loc.region else ""
    title = f"{loc.name}{region_str} ({loc.country})"

    lines = [
        "=" * 62,
        f" WEATHER REPORT: {title}",
        "=" * 62,
        f" Condition   : {report.condition}",
        f" Temperature : {report.temperature:.1f} °C (Feels like {report.feels_like:.1f} °C)",
        f" Humidity    : {report.humidity}%",
        f" Wind Speed  : {report.wind_speed:.1f} km/h",
        "-" * 62,
        " 5-DAY FORECAST:",
        f" {'Date':<12} | {'Min / Max':<17} | {'Rain %':<8} | {'Condition'}",
        "-" * 62,
    ]

    for day in report.daily:
        temp_range = f"{day.temp_min:>5.1f} / {day.temp_max:>5.1f} °C"
        rain = f"{day.precip_prob:>4}%"
        lines.append(f" {day.date:<12} | {temp_range:<17} | {rain:<8} | {day.condition}")

    lines.append("=" * 62)
    return "\n".join(lines)


def show_help() -> str:
    return (
        "Commands:\n"
        "  <city>            - Show weather & 5-day forecast (e.g. Kaufering, Augsburg)\n"
        "  fav list          - Show saved favorite cities\n"
        "  fav add <city>    - Save a city to favorites.json\n"
        "  fav del <city>    - Remove a city from favorites.json\n"
        "  fav weather       - Fetch current weather for all favorite cities\n"
        "  help              - Show this help message\n"
        "  exit / close      - Quit the program"
    )


def handle_favorites_command(parts: list[str]) -> str:
    """Handles 'fav ...' subcommands."""
    if not parts or parts[0].lower() == "list":
        favs = load_favorites()
        return "Favorite cities: " + (", ".join(favs) if favs else "(empty)")

    sub = parts[0].lower()
    arg = " ".join(parts[1:])

    if sub == "add":
        return add_favorite(arg)
    if sub in ("del", "delete", "remove"):
        return remove_favorite(arg)
    if sub == "weather":
        favs = load_favorites()
        if not favs:
            return "No favorite cities saved yet. Use 'fav add <city>'."
        outputs = []
        for city in favs:
            try:
                outputs.append(format_weather_report(get_weather_report(city)))
            except WeatherAPIError as err:
                outputs.append(f"[{city}] Error: {err}")
        return "\n\n".join(outputs)

    return "Unknown 'fav' subcommand. Type 'help' for usage."


def main() -> None:
    reconfigure_stdout = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure_stdout):
        reconfigure_stdout(encoding="utf-8", errors="replace")

    # Support direct one-shot CLI usage: python main.py Augsburg
    if len(sys.argv) > 1:
        city_arg = " ".join(sys.argv[1:])
        try:
            print(format_weather_report(get_weather_report(city_arg)))
        except WeatherAPIError as err:
            print(f"Error: {err}")
            sys.exit(1)
        return

    print("Welcome to Weather REST API CLI! (Type a city name or 'help')")
    while True:
        try:
            raw = input("\ncity> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBis dann!")
            break

        if not raw:
            continue

        lower = raw.lower()
        if lower in ("exit", "close", "quit"):
            print("Bis dann!")
            break
        if lower == "help":
            print(show_help())
            continue
        if lower.startswith("fav"):
            parts = raw.split()[1:]
            print(handle_favorites_command(parts))
            continue

        try:
            report = get_weather_report(raw)
            print(format_weather_report(report))
        except WeatherAPIError as err:
            print(f"Error: {err}")


if __name__ == "__main__":
    main()
