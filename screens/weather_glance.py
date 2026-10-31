from .shared import *

# ── Weather Glance ───────────────────────────────────────────────────

# WMO weather code → icon character (simplified for e-ink)
def _draw_weather_icon(draw, cx, cy, code, size=28):
    """Draw a simple weather icon centered at (cx, cy) based on WMO code."""
    r = size // 2
    if code in (0, 1):  # Clear / Sunny — sun with rays
        draw.ellipse([cx - r + 4, cy - r + 4, cx + r - 4, cy + r - 4], outline=40, width=2)
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            x1 = cx + int((r - 2) * math.cos(rad))
            y1 = cy + int((r - 2) * math.sin(rad))
            x2 = cx + int((r + 5) * math.cos(rad))
            y2 = cy + int((r + 5) * math.sin(rad))
            draw.line([(x1, y1), (x2, y2)], fill=40, width=2)
    elif code in (2,):  # Partly cloudy — small sun + cloud
        draw.ellipse([cx - r, cy - r, cx, cy], outline=60, width=2)
        for angle in range(0, 360, 60):
            rad = math.radians(angle)
            sx, sy = cx - r // 2, cy - r // 2
            draw.line([(sx + int(6 * math.cos(rad)), sy + int(6 * math.sin(rad))),
                        (sx + int(10 * math.cos(rad)), sy + int(10 * math.sin(rad)))], fill=60, width=1)
        draw.ellipse([cx - 4, cy - 4, cx + r, cy + r // 2], fill=120, outline=80, width=1)
    elif code in (3, 45, 48):  # Cloud / Fog
        draw.ellipse([cx - r, cy - 6, cx + r, cy + 6], fill=140, outline=80, width=2)
        draw.ellipse([cx - r + 6, cy - 12, cx + 4, cy + 2], fill=160, outline=80, width=1)
    elif code in (51, 53, 55, 80):  # Drizzle / Shower
        draw.ellipse([cx - r + 2, cy - 10, cx + r - 2, cy + 2], fill=160, outline=80, width=1)
        for dx in (-6, 0, 6):
            draw.line([(cx + dx, cy + 6), (cx + dx - 2, cy + 12)], fill=80, width=2)
    elif code in (61, 63, 65, 81, 82):  # Rain
        draw.ellipse([cx - r + 2, cy - 10, cx + r - 2, cy + 2], fill=120, outline=60, width=2)
        for dx in (-8, -2, 4, 10):
            draw.line([(cx + dx, cy + 6), (cx + dx - 3, cy + 14)], fill=50, width=2)
    elif code in (71, 73, 75):  # Snow
        draw.ellipse([cx - r + 2, cy - 10, cx + r - 2, cy + 2], fill=170, outline=100, width=1)
        for dx in (-6, 0, 6):
            draw.text((cx + dx, cy + 10), "*", fill=60, font=get_font(14), anchor="mm")
    elif code in (95, 96, 99):  # Storm
        draw.ellipse([cx - r + 2, cy - 10, cx + r - 2, cy + 2], fill=80, outline=40, width=2)
        draw.polygon([(cx - 2, cy + 4), (cx + 4, cy + 4), (cx, cy + 14),
                       (cx + 6, cy + 4), (cx + 2, cy - 2)], fill=40)
    else:  # Unknown — small dot
        draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=120)


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
    # Render a vector pictogram at small coordinates, then scale uniformly.
    icon = Image.new('L', (100,100), 255)
    _draw_weather_icon(ImageDraw.Draw(icon), 50, 46, code, 40)
    icon = icon.resize((600,600), Image.Resampling.LANCZOS)
    img.paste(icon, ((WIDTH-600)//2,40))
    _fit_block(draw, f"{round(temp)}°", (70,650,WIDTH-140,470), 390, True)
    _fit_block(draw, WMO_CODES.get(code,'Weather unavailable'), (80,1190,WIDTH-160,180), 100, True)
    _fit_block(draw, WEATHER_LOCATION, (80,1410,WIDTH-160,110), 62)
    return img
