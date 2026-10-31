from .shared import *

# ── 16. Air Quality ─────────────────────────────────────────────────

def render_air_quality() -> Image.Image:
    """Display air quality index, pollen, and UV from Open-Meteo."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    def _fetch():
        url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        params = {
            "latitude": WEATHER_LAT,
            "longitude": WEATHER_LON,
            "current": "european_aqi",
            "forecast_days": 1,
        }
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        return r.json()

    data = _cache_fetch("air_quality", 600, 1800, _fetch)  # 10min TTL, 30min stale

    current = _require(data).get("current", {})
    value = _require(current.get("european_aqi"), "AQI missing")
    quality = next((label for limit, label in [(20,"Good"),(40,"Fair"),(60,"Moderate"),(80,"Poor"),(100,"Very poor")] if value <= limit), "Extremely poor")
    img, draw = _canvas()
    _fit_block(draw, str(round(value)), (75, 93, 1050, 707), 440, True)
    _fit_block(draw, quality + " air", (75, 853, 1050, 267), 140, True)
    _fit_block(draw, "European air quality index\n" + WEATHER_LOCATION, (75, 1240, 1050, 227), 56)
    return img
