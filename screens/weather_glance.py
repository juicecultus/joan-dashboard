from .shared import *

# ── Weather Glance ───────────────────────────────────────────────────

from .weather_icons import weather_icon


def _fetch_weather_glance():
    """Fetch 7-day forecast from Open-Meteo for weather glance."""
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={WEATHER_LAT}&longitude={WEATHER_LON}"
        f"&current=temperature_2m,weather_code,relative_humidity_2m,apparent_temperature,wind_speed_10m"
        f"&daily=temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max"
        f"&timezone=auto&wind_speed_unit=mph&forecast_days=2"
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


def _weather_value(value, suffix=''):
    return f'{round(value)}{suffix}' if isinstance(value,(int,float)) and math.isfinite(value) else '—'


def _today_rain(data):
    daily=data.get('daily',{})
    date=str(data.get('current',{}).get('time',''))[:10]
    try:
        return daily['precipitation_probability_max'][daily['time'].index(date)]
    except (KeyError,ValueError,IndexError,TypeError):
        return None


def render_weather_glance():
    from joan_dashboard import WMO_CODES
    data = _require(_cache_fetch('weather_glance_v2',900,1800,_fetch_weather_glance))
    current = data.get('current', {})
    temp = _require(current.get('temperature_2m'))
    img, draw = _canvas()
    _panel(draw,(25,25,1150,840),42)
    img.paste(weather_icon(current.get('weather_code'),440),(380,40))
    _poster_text(draw,f'{round(temp)}°',(90,455,1020,260),370)
    _poster_text(draw,WMO_CODES.get(current.get('weather_code'),'Weather unavailable'),(70,755,1060,75),100,False)
    _panel(draw,(25,890,1150,240))
    limits = _daily_range(data)
    if limits:
        low, high = limits
        _poster_text(draw,f'Low {round(low)}°',(70,915,450,80),85,False)
        _poster_text(draw,f'High {round(high)}°',(680,915,450,80),85,False)
        x0,x1,y=110,1090,1065
        marker=round(x0+_range_fraction(temp,low,high)*(x1-x0))
        draw.rounded_rectangle((x0,y-2,x1,y+2),radius=2,fill=0)
        for x in (x0,x1): draw.line((x,y-12,x,y+12),fill=0,width=3)
        draw.ellipse((marker-20,y-20,marker+20,y+20),fill=255)
        draw.ellipse((marker-12,y-12,marker+12,y+12),fill=0)
    else:
        _poster_text(draw,'Daily range unavailable',(65,940,1070,130),85,False)
    metrics = [
        ('Humidity',_weather_value(current.get('relative_humidity_2m'),'%')),
        ('Wind',_weather_value(current.get('wind_speed_10m'),' mph')),
        ('Rain chance today',_weather_value(_today_rain(data),'%')),
        ('Feels like',_weather_value(current.get('apparent_temperature'),'°')),
    ]
    for i,(label,value) in enumerate(metrics):
        _metric_panel(draw,label,value,(25+(i%2)*590,1160+(i//2)*210,560,190))
    return img
