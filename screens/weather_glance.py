from .shared import *

# ── Weather Glance ───────────────────────────────────────────────────

from .weather_icons import weather_icon


def _fetch_weather_glance():
    """Fetch 7-day forecast from Open-Meteo for weather glance."""
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={WEATHER_LAT}&longitude={WEATHER_LON}"
        f"&current=temperature_2m,weather_code"
        f"&daily=temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max"
        f"&timezone=auto"
    )
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()


def render_weather_glance():
    from joan_dashboard import WMO_CODES
    data = _require(_cache_fetch("weather_glance", 900, 1800, _fetch_weather_glance))
    current = data.get('current', {})
    temp = _require(current.get('temperature_2m'))
    code = current.get('weather_code')
    img, draw = _canvas()
    img.paste(weather_icon(code, 600), ((WIDTH-600)//2,40))
    _fit_block(draw, f"{round(temp)}°", (70,650,WIDTH-140,470), 390, True)
    _fit_block(draw, WMO_CODES.get(code,'Weather unavailable'), (80,1190,WIDTH-160,180), 100, True)
    _fit_block(draw, WEATHER_LOCATION, (80,1410,WIDTH-160,110), 62)
    return img
