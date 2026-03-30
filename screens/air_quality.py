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
            "current": "european_aqi,us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone",
            "hourly": "european_aqi,uv_index",
            "forecast_days": 1,
        }
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        return r.json()

    data = _cache_fetch("air_quality", 600, 1800, _fetch)  # 10min TTL, 30min stale

    # Header
    draw.text((WIDTH // 2, 70), "Air Quality", fill=0, font=get_font(50, bold=True), anchor="mm")
    draw.text((WIDTH // 2, 120), WEATHER_LOCATION, fill=140, font=get_font(28), anchor="mm")
    draw.line([(PAD, 155), (WIDTH - PAD, 155)], fill=200, width=2)

    if not data or "current" not in data:
        draw.text((WIDTH // 2, HEIGHT // 2), "Could not load air quality data", fill=120, font=get_font(36), anchor="mm")
        _footer(draw, now_str())
        return img

    current = data["current"]
    eu_aqi = current.get("european_aqi", 0)
    us_aqi = current.get("us_aqi", 0)
    pm25 = current.get("pm2_5", 0)
    pm10 = current.get("pm10", 0)
    no2 = current.get("nitrogen_dioxide", 0)
    o3 = current.get("ozone", 0)

    # AQI category
    if eu_aqi <= 20:
        quality = "Good"
        quality_fill = 60
    elif eu_aqi <= 40:
        quality = "Fair"
        quality_fill = 60
    elif eu_aqi <= 60:
        quality = "Moderate"
        quality_fill = 40
    elif eu_aqi <= 80:
        quality = "Poor"
        quality_fill = 20
    elif eu_aqi <= 100:
        quality = "Very Poor"
        quality_fill = 0
    else:
        quality = "Hazardous"
        quality_fill = 0

    # Big AQI display
    draw.text((WIDTH // 2, 280), str(int(eu_aqi)), fill=quality_fill, font=get_font(140, bold=True), anchor="mm")
    draw.text((WIDTH // 2, 370), f"European AQI — {quality}", fill=80, font=get_font(34), anchor="mm")
    draw.text((WIDTH // 2, 415), f"US AQI: {int(us_aqi)}", fill=140, font=get_font(26), anchor="mm")

    # AQI bar
    bar_x = 200
    bar_w = WIDTH - 400
    bar_y = 460
    bar_h = 30
    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=bar_h // 2, fill=220)
    fill_pct = min(eu_aqi / 100, 1.0)
    fill_w = int(bar_w * fill_pct)
    if fill_w > bar_h:
        draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=bar_h // 2, fill=60)
    # Scale labels
    for label, pos in [("Good", 0.1), ("Fair", 0.3), ("Mod", 0.5), ("Poor", 0.7), ("V.Poor", 0.9)]:
        lx = bar_x + int(bar_w * pos)
        draw.text((lx, bar_y + bar_h + 15), label, fill=160, font=get_font(18), anchor="mt")

    # Pollutant details — 2 columns
    y = 560
    col1_x = WIDTH // 4
    col2_x = 3 * WIDTH // 4
    items = [
        ("PM2.5", f"{pm25:.1f} µg/m³", col1_x),
        ("PM10", f"{pm10:.1f} µg/m³", col2_x),
        ("NO₂", f"{no2:.1f} µg/m³", col1_x),
        ("Ozone", f"{o3:.1f} µg/m³", col2_x),
    ]
    row = 0
    for label, value, cx in items:
        ry = y + (row // 2) * 90
        draw.text((cx, ry), label, fill=0, font=get_font(30, bold=True), anchor="mm")
        draw.text((cx, ry + 38), value, fill=80, font=get_font(26), anchor="mm")
        row += 1

    # UV index from hourly data
    hourly = data.get("hourly", {})
    uv_values = hourly.get("uv_index", [])
    if uv_values:
        max_uv = max(v for v in uv_values if v is not None) if any(v is not None for v in uv_values) else 0
        uv_y = y + 200
        draw.line([(PAD + 100, uv_y - 20), (WIDTH - PAD - 100, uv_y - 20)], fill=220, width=1)
        draw.text((WIDTH // 2, uv_y + 20), f"UV Index: {max_uv:.0f} (today's peak)", fill=60, font=get_font(30), anchor="mm")
        if max_uv <= 2:
            uv_label = "Low"
        elif max_uv <= 5:
            uv_label = "Moderate"
        elif max_uv <= 7:
            uv_label = "High"
        elif max_uv <= 10:
            uv_label = "Very High"
        else:
            uv_label = "Extreme"
        draw.text((WIDTH // 2, uv_y + 60), uv_label, fill=80, font=get_font(26, bold=True), anchor="mm")

    _footer(draw, now_str())
    return img
