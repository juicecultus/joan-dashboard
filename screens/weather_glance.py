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


def _daily_range(data):
    """Match the current observation's local date to its daily forecast."""
    daily = data.get('daily', {})
    day = str(data.get('current', {}).get('time', ''))[:10]
    dates = daily.get('time', [])
    if day not in dates:
        return None
    i = dates.index(day)
    try:
        low, high = daily['temperature_2m_min'][i], daily['temperature_2m_max'][i]
        import math
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (low, high)) or low > high:
            return None
        return low, high
    except (KeyError, IndexError, TypeError):
        return None


def _range_fraction(temp, low, high):
    return max(0, min(1, (temp-low)/(high-low))) if high > low else 0.5


def render_weather_glance():
    from joan_dashboard import WMO_CODES
    data = _require(_cache_fetch("weather_glance", 900, 1800, _fetch_weather_glance))
    current = data.get('current', {})
    temp = _require(current.get('temperature_2m'))
    code = current.get('weather_code')
    img, draw = _canvas()
    img.paste(weather_icon(code, 600), ((WIDTH-600)//2,40))
    _fit_block(draw, f"{round(temp)}°", (70,650,WIDTH-140,470), 390, True)
    _fit_block(draw, WMO_CODES.get(code,'Weather unavailable'), (70,1080,WIDTH-140,160), 100, True)
    limits = _daily_range(data)
    if limits:
        low, high = limits
        x0, x1, y = 170, WIDTH-170, 1350
        marker = round(x0 + _range_fraction(temp, low, high)*(x1-x0))
        draw.rounded_rectangle((x0,y-12,x1,y+12),radius=12,fill=0)
        for x in (x0,x1):
            draw.line((x,y-30,x,y+30),fill=0,width=10)
        # White halo keeps the current-temperature marker distinct from the rail.
        draw.ellipse((marker-38,y-38,marker+38,y+38),fill=255)
        draw.ellipse((marker-27,y-27,marker+27,y+27),fill=0)
        draw.text((x0,1410), f'{round(low)}°', font=get_font(100,bold=True),fill=0,anchor='mt')
        draw.text((x1,1410), f'{round(high)}°', font=get_font(100,bold=True),fill=0,anchor='mt')
        draw.text((x0,1530), 'LOW', font=get_font(42,bold=True),fill=0,anchor='mm')
        draw.text((x1,1530), 'HIGH', font=get_font(42,bold=True),fill=0,anchor='mm')
    return img
