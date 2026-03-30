from .shared import *

# ── 8. Weather Radar ─────────────────────────────────────────────────

def render_weather_radar() -> Image.Image:
    """Display weather radar map for your area from RainViewer."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    def _fetch_tiles():
        r = requests.get("https://api.rainviewer.com/public/weather-maps.json", timeout=8)
        r.raise_for_status()
        data = r.json()
        radar = data.get("radar", {}).get("past", [])
        if not radar:
            raise ValueError("No radar data available")
        ts_path = radar[-1]["path"]

        lat = float(WEATHER_LAT)
        lon = float(WEATHER_LON)
        zoom = 7
        import math as _math
        n = 2 ** zoom
        x_tile = int((lon + 180.0) / 360.0 * n)
        lat_rad = _math.radians(lat)
        y_tile = int((1.0 - _math.asinh(_math.tan(lat_rad)) / _math.pi) / 2.0 * n)

        tiles_img = Image.new("RGBA", (256 * 3, 256 * 3), (0, 0, 0, 0))
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                tx, ty = x_tile + dx, y_tile + dy
                tile_url = f"https://tilecache.rainviewer.com{ts_path}/256/{zoom}/{tx}/{ty}/2/1_1.png"
                try:
                    tr = requests.get(tile_url, timeout=5)
                    if tr.status_code == 200:
                        tile = Image.open(BytesIO(tr.content)).convert("RGBA")
                        tiles_img.paste(tile, ((dx + 1) * 256, (dy + 1) * 256))
                except Exception:
                    pass

        base_img = Image.new("RGB", (256 * 3, 256 * 3), (240, 240, 240))
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                tx, ty = x_tile + dx, y_tile + dy
                osm_url = f"https://tile.openstreetmap.org/{zoom}/{tx}/{ty}.png"
                try:
                    tr = requests.get(osm_url, headers={"User-Agent": "JoanDashboard/1.0"}, timeout=5)
                    if tr.status_code == 200:
                        tile = Image.open(BytesIO(tr.content)).convert("RGB")
                        base_img.paste(tile, ((dx + 1) * 256, (dy + 1) * 256))
                except Exception:
                    pass

        base_img = base_img.convert("RGBA")
        composite = Image.alpha_composite(base_img, tiles_img)
        radar_gray = composite.convert("L")

        rw, rh = radar_gray.size
        scale = max(WIDTH / rw, HEIGHT / rh)
        new_w = int(rw * scale)
        new_h = int(rh * scale)
        radar_gray = radar_gray.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - WIDTH) // 2
        top = (new_h - HEIGHT) // 2
        return radar_gray.crop((left, top, left + WIDTH, top + HEIGHT))

    radar_img = _cache_fetch("radar", 120, 600, _fetch_tiles)  # 2min TTL, 10min stale

    if radar_img:
        img = radar_img.copy()
        draw = ImageDraw.Draw(img)
        for y in range(60):
            for x in range(WIDTH):
                px = img.getpixel((x, y))
                img.putpixel((x, y), min(255, px + 80))
        draw.text((WIDTH // 2, 30), f"Weather Radar — {WEATHER_LOCATION}", fill=0, font=get_font(30, bold=True), anchor="mm")
        _dashboard_footer(draw)
    else:
        draw.text((WIDTH // 2, HEIGHT // 2 - 20), "Weather Radar", fill=0, font=get_font(50, bold=True), anchor="mm")
        draw.text((WIDTH // 2, HEIGHT // 2 + 40), "Could not load radar data", fill=120, font=get_font(30), anchor="mm")

    return img
