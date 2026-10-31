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
    # A six-segment gauge makes the index's position visible without a table.
    _poster_text(draw, str(round(value)), (40,40,1120,800), 1100)
    _poster_text(draw, quality + " air", (40,900,1120,260), 250)
    selected = min(5,max(0,math.ceil(value/20)-1))
    for i in range(6):
        x = 50+i*185
        draw.rounded_rectangle((x,1260,x+170,1360),radius=16,outline=0,width=9,fill=0 if i<=selected else 255)
    x = 135+selected*185
    draw.polygon([(x-24,1400),(x+24,1400),(x,1372)],fill=0)
    _poster_text(draw, 'European air quality index', (40,1480,1120,80), 90, False)
    return img
