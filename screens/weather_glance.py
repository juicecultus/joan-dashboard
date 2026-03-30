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


def render_weather_glance() -> Image.Image:
    """Render a weather glance screen with current temp and 7-day bar forecast."""
    img = Image.new("L", (WIDTH, HEIGHT), 230)
    draw = ImageDraw.Draw(img)

    data = _cache_fetch("weather_glance", 1800, 7200, _fetch_weather_glance)

    # Footer bar
    footer_h = 60
    footer_y = HEIGHT - footer_h
    draw.rectangle([0, footer_y, WIDTH, HEIGHT], fill=30)
    draw.text((PAD, footer_y + footer_h // 2), "Weather Glance",
              fill=220, font=get_font(28, bold=True), anchor="lm")
    draw.text((WIDTH - PAD, footer_y + footer_h // 2), WEATHER_LOCATION,
              fill=160, font=get_font(26), anchor="rm")

    if not data:
        _centered_text(draw, HEIGHT // 2, "No weather data", 40, fill=80)
        return img

    current = data.get("current", {})
    daily = data.get("daily", {})

    # Current temperature (left side)
    cur_temp = current.get("temperature_2m", "?")
    cur_code = current.get("weather_code", 0)
    time_str = datetime.now().strftime("%-I:%M %p")
    draw.text((PAD, 340), time_str, fill=100, font=get_font(28), anchor="lt")
    draw.text((PAD, 380), f"{int(cur_temp) if isinstance(cur_temp, (int, float)) else cur_temp}°",
              fill=20, font=get_font(140, bold=True), anchor="lt")

    # 7-day forecast bars (right side)
    dates = daily.get("time", [])
    highs = daily.get("temperature_2m_max", [])
    lows = daily.get("temperature_2m_min", [])
    codes = daily.get("weather_code", [])
    n_days = min(7, len(dates))

    if n_days > 0 and highs and lows:
        # Bar chart area
        bar_left = 340
        bar_right = WIDTH - PAD
        bar_top = 120
        bar_bottom = footer_y - 60
        bar_w = 60
        gap_w = (bar_right - bar_left - bar_w * n_days) // max(n_days - 1, 1)

        all_temps = [t for t in highs[:n_days] + lows[:n_days] if t is not None]
        if all_temps:
            t_min = min(all_temps)
            t_max = max(all_temps)
            t_range = max(t_max - t_min, 1)

            for i in range(n_days):
                cx = bar_left + i * (bar_w + gap_w) + bar_w // 2
                bx = cx - bar_w // 2

                # Day label at top
                try:
                    dt = datetime.strptime(dates[i], "%Y-%m-%d")
                    day_label = dt.strftime("%a %-d")
                except (ValueError, IndexError):
                    day_label = ""
                draw.text((cx, bar_top - 30), day_label, fill=80,
                          font=get_font(22), anchor="mt")

                # Temperature bar
                hi = highs[i] if i < len(highs) and highs[i] is not None else t_min
                lo = lows[i] if i < len(lows) and lows[i] is not None else t_min
                hi_y = bar_bottom - int((hi - t_min) / t_range * (bar_bottom - bar_top - 80))
                lo_y = bar_bottom - int((lo - t_min) / t_range * (bar_bottom - bar_top - 80))

                # Today's bar is darker
                bar_fill = 160 if i == 0 else 200
                if codes and i < len(codes) and codes[i] in (61, 63, 65, 80, 81, 82, 95, 96, 99):
                    bar_fill = 100  # darker for rain

                draw.rounded_rectangle([bx, hi_y, bx + bar_w, lo_y],
                                       radius=bar_w // 2, fill=bar_fill)

                # High temp above bar
                draw.text((cx, hi_y - 8), f"{int(hi)}", fill=40,
                          font=get_font(24, bold=True), anchor="mb")
                # Low temp below bar
                draw.text((cx, lo_y + 8), f"{int(lo)}", fill=100,
                          font=get_font(22), anchor="mt")

                # Weather icon above high temp
                wcode = codes[i] if i < len(codes) else 0
                _draw_weather_icon(draw, cx, hi_y - 45, wcode, size=32)

    return img
