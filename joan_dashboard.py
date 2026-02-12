#!/usr/bin/env python3
"""Joan Dashboard — renders weather, Google Calendar, and Google Tasks on the Joan device.

Usage:
    python joan_dashboard.py              # render once and push
    python joan_dashboard.py --loop 300   # re-render and push every 300 seconds
    python joan_dashboard.py --preview    # save to joan_preview.png without pushing

First-time setup:
    python joan_google_auth.py            # authenticate with Google (hello@allmumstalk.com)
"""

import argparse
import calendar
import io
import math
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests
from PIL import Image, ImageDraw, ImageFont

# --- Load .env file if present ---
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

# --- Configuration (override via environment variables or .env file) ---
VSS_HOST = os.environ.get("VSS_HOST", "192.168.6.6")
VSS_PORT = int(os.environ.get("VSS_PORT", "8081"))
DEVICE_UUID = os.environ.get("DEVICE_UUID", "")
VSS_USER = os.environ.get("VSS_USER", "admin")
VSS_PASS = os.environ.get("VSS_PASS", "visionect1")

WIDTH = 1600
HEIGHT = 1200

# Weather: lat/lon for Open-Meteo (default: Waddesdon, Buckinghamshire)
WEATHER_LAT = float(os.environ.get("WEATHER_LAT", "51.845"))
WEATHER_LON = float(os.environ.get("WEATHER_LON", "-0.943"))
WEATHER_LOCATION = os.environ.get("WEATHER_LOCATION", "Waddesdon")

# Google API token file (created by joan_google_auth.py)
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")

# --- Font helpers ---
FONT_CACHE = {}

def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    key = (size, bold)
    if key not in FONT_CACHE:
        candidates = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFNSDisplay.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
        if bold:
            candidates = [
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/SFNSDisplay.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            ] + candidates
        font = None
        for path in candidates:
            try:
                idx = 1 if bold and "Helvetica" in path else 0
                font = ImageFont.truetype(path, size, index=idx)
                break
            except (OSError, IndexError):
                try:
                    font = ImageFont.truetype(path, size)
                    break
                except OSError:
                    continue
        if font is None:
            font = ImageFont.load_default(size=size)
        FONT_CACHE[key] = font
    return FONT_CACHE[key]


# --- Weather via Open-Meteo (free, no API key) ---
WMO_CODES = {
    0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Light showers", 81: "Showers", 82: "Heavy showers",
    95: "Thunderstorm", 96: "Thunderstorm + hail", 99: "Thunderstorm + heavy hail",
}


def fetch_weather() -> dict | None:
    """Fetch weather from Open-Meteo (free, reliable, no API key)."""
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": WEATHER_LAT,
                "longitude": WEATHER_LON,
                "current": (
                    "temperature_2m,relative_humidity_2m,apparent_temperature,"
                    "weather_code,wind_speed_10m,wind_direction_10m,"
                    "surface_pressure,dew_point_2m"
                ),
                "daily": (
                    "temperature_2m_max,temperature_2m_min,weather_code,"
                    "precipitation_probability_max,precipitation_sum,"
                    "sunrise,sunset"
                ),
                "hourly": "visibility",
                "timezone": "Europe/London",
                "forecast_days": 3,
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        cur = data["current"]
        daily = data["daily"]

        # Wind direction from degrees
        dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        wind_dir = dirs[int((cur["wind_direction_10m"] + 22.5) / 45) % 8]

        # Current visibility from hourly data (nearest hour)
        visibility_m = None
        hourly = data.get("hourly", {})
        if hourly.get("visibility"):
            from datetime import datetime as dt
            now_hour = dt.now().hour
            vis_list = hourly["visibility"]
            if now_hour < len(vis_list):
                visibility_m = vis_list[now_hour]

        # Sunrise/sunset for today
        sunrise = daily.get("sunrise", [""])[0]
        sunset = daily.get("sunset", [""])[0]
        sunrise_t = sunrise.split("T")[1] if "T" in sunrise else sunrise
        sunset_t = sunset.split("T")[1] if "T" in sunset else sunset

        weather = {
            "temp_c": round(cur["temperature_2m"]),
            "feels_like_c": round(cur["apparent_temperature"]),
            "humidity": cur["relative_humidity_2m"],
            "desc": WMO_CODES.get(cur["weather_code"], "Unknown"),
            "wind_kmh": round(cur["wind_speed_10m"]),
            "wind_dir": wind_dir,
            "pressure": round(cur.get("surface_pressure", 0)),
            "dew_point_c": round(cur.get("dew_point_2m", 0)),
            "visibility_km": round(visibility_m / 1000, 1) if visibility_m else None,
            "sunrise": sunrise_t,
            "sunset": sunset_t,
            "forecast": [],
        }

        for i in range(min(3, len(daily["time"]))):
            weather["forecast"].append({
                "date": daily["time"][i],
                "high_c": round(daily["temperature_2m_max"][i]),
                "low_c": round(daily["temperature_2m_min"][i]),
                "desc": WMO_CODES.get(daily["weather_code"][i], "Unknown"),
                "precip_prob": daily.get("precipitation_probability_max", [0] * 3)[i],
                "precip_mm": daily.get("precipitation_sum", [0] * 3)[i],
            })

        return weather
    except Exception as e:
        print(f"[weather] Failed: {e}")
        return None


# --- Google Calendar ---
def get_google_creds():
    """Load Google OAuth2 credentials from token.json."""
    if not os.path.exists(TOKEN_FILE):
        print(f"[google] No token.json — run joan_google_auth.py first")
        return None
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        creds = Credentials.from_authorized_user_file(TOKEN_FILE, [
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/tasks.readonly",
        ])
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        return creds
    except Exception as e:
        print(f"[google] Auth failed: {e}")
        return None


def fetch_week_events() -> dict:
    """Fetch this week's events (Mon-Sun) from ALL Google Calendars.
    Returns dict keyed by date string 'YYYY-MM-DD' -> list of events."""
    creds = get_google_creds()
    now = datetime.now()
    # Find Monday of current week
    monday = now - timedelta(days=now.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)

    # Init empty dict for each day
    week = {}
    for i in range(7):
        day = monday + timedelta(days=i)
        week[day.strftime("%Y-%m-%d")] = []

    if not creds:
        return week
    try:
        from googleapiclient.discovery import build

        service = build("calendar", "v3", credentials=creds)
        start_str = monday.isoformat() + "Z"
        end_str = sunday.isoformat() + "Z"

        cal_list = service.calendarList().list().execute()

        for cal in cal_list.get("items", []):
            cal_id = cal["id"]
            result = service.events().list(
                calendarId=cal_id,
                timeMin=start_str,
                timeMax=end_str,
                maxResults=50,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            for ev in result.get("items", []):
                start = ev["start"].get("dateTime", ev["start"].get("date", ""))
                if "T" in start:
                    t = datetime.fromisoformat(start)
                    date_key = t.strftime("%Y-%m-%d")
                    time_str = t.strftime("%H:%M")
                else:
                    date_key = start[:10]
                    time_str = ""
                if date_key in week:
                    week[date_key].append({
                        "time": time_str,
                        "title": ev.get("summary", "(No title)"),
                    })

        # Sort each day's events by time
        for date_key in week:
            week[date_key].sort(key=lambda e: e["time"] or "00:00")
        return week
    except Exception as e:
        print(f"[calendar] Failed: {e}")
        return week


# --- Google Tasks ---
def fetch_tasks() -> list:
    """Fetch incomplete tasks from Google Tasks (default list)."""
    creds = get_google_creds()
    if not creds:
        return []
    try:
        from googleapiclient.discovery import build

        service = build("tasks", "v1", credentials=creds)

        # Get first task list
        lists = service.tasklists().list(maxResults=1).execute()
        if not lists.get("items"):
            return []
        tasklist_id = lists["items"][0]["id"]

        result = service.tasks().list(
            tasklist=tasklist_id,
            showCompleted=False,
            maxResults=15,
        ).execute()

        tasks = []
        for t in result.get("items", []):
            title = t.get("title", "").strip()
            if title:
                due = t.get("due", "")
                due_str = ""
                if due:
                    try:
                        due_str = datetime.fromisoformat(due.replace("Z", "+00:00")).strftime("%d %b")
                    except ValueError:
                        pass
                tasks.append({"title": title, "due": due_str})
        return tasks
    except Exception as e:
        print(f"[tasks] Failed: {e}")
        return []


# --- Rendering ---
def draw_sun_icon(draw: ImageDraw.Draw, cx: int, cy: int, r: int = 10, fill: int = 60):
    """Draw a sun icon: filled circle with rays."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
    ray_len = r + 5
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        x1 = cx + int((r + 2) * math.cos(rad))
        y1 = cy + int((r + 2) * math.sin(rad))
        x2 = cx + int(ray_len * math.cos(rad))
        y2 = cy + int(ray_len * math.sin(rad))
        draw.line([(x1, y1), (x2, y2)], fill=fill, width=2)


def draw_moon_icon(draw: ImageDraw.Draw, cx: int, cy: int, r: int = 10, fill: int = 60, bg: int = 255):
    """Draw a crescent moon icon using two overlapping circles."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
    # Overlap a background-colored circle offset to the right to create crescent
    offset = int(r * 0.6)
    draw.ellipse([cx - r + offset, cy - r, cx + r + offset, cy + r], fill=bg)


def draw_separator(draw: ImageDraw.Draw, y: int, margin: int = 100):
    draw.line([(margin, y), (WIDTH - margin, y)], fill=180, width=2)


def render_dashboard() -> Image.Image:
    """Render the dashboard as a 1600x1200 grayscale image."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)
    now = datetime.now()

    # ── Grid constants ──
    PAD = 40
    GAP = 20
    LINE_H = 38
    HEADER_H = 420     # double-height header
    COL_DIV = 800      # divider for bottom 2-col area
    L = PAD
    R_END = WIDTH - PAD

    # Header 3-column boundaries
    H_COL1_END = 440   # clock column
    H_COL2_L = 460     # date + calendar column
    H_COL2_END = 1060
    H_COL3_L = 1080    # weather column

    def hline(y, x0=L, x1=R_END):
        draw.line([(x0, y), (x1, y)], fill=180, width=2)

    def vline(x, y0, y1):
        draw.line([(x, y0), (x, y1)], fill=180, width=2)

    # ═══════════════════════════════════════════════
    # HEADER: 3 columns — Clock | Date+Calendar | Weather
    # ═══════════════════════════════════════════════

    # ── Col 1: Clock ──
    clock_cx = (L + H_COL1_END) // 2
    draw.text((clock_cx, HEADER_H // 2 - 10), now.strftime("%H:%M"), fill=0, font=get_font(140, bold=True), anchor="mm")

    vline(H_COL1_END + 10, PAD, HEADER_H - PAD)

    # ── Col 2: Date + Calendar ──
    col2_cx = (H_COL2_L + H_COL2_END) // 2

    # Date line at top
    draw.text((col2_cx, 24), now.strftime("%A, %d %B %Y"), fill=40, font=get_font(30, bold=True), anchor="mt")

    # Calendar grid centered in remaining space below date
    cal_obj = calendar.Calendar(firstweekday=0)
    month_days = cal_obj.monthdayscalendar(now.year, now.month)
    num_weeks = len(month_days)

    cal_top = 62       # below date text
    cal_avail_w = H_COL2_END - H_COL2_L
    cal_avail_h = HEADER_H - cal_top - 10
    cell_x = cal_avail_w // 7
    grid_rows = 1 + num_weeks
    cell_y = cal_avail_h // grid_rows
    grid_w = 7 * cell_x
    grid_h = grid_rows * cell_y

    cal_x0 = H_COL2_L + (cal_avail_w - grid_w) // 2
    cal_y0 = cal_top + (cal_avail_h - grid_h) // 2

    # Day name headers
    for i, dn in enumerate(["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]):
        cx = cal_x0 + i * cell_x + cell_x // 2
        draw.text((cx, cal_y0 + cell_y // 2), dn, fill=100, font=get_font(22, bold=True), anchor="mm")

    # Date rows
    for wi, week in enumerate(month_days):
        ry = cal_y0 + (1 + wi) * cell_y
        for i, d_num in enumerate(week):
            if d_num == 0:
                continue
            cx = cal_x0 + i * cell_x + cell_x // 2
            cy = ry + cell_y // 2
            if d_num == now.day:
                r = min(cell_x, cell_y) // 2 - 2
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=0)
                draw.text((cx, cy), str(d_num), fill=255, font=get_font(22, bold=True), anchor="mm")
            else:
                draw.text((cx, cy), str(d_num), fill=40, font=get_font(22), anchor="mm")

    vline(H_COL2_END + 10, PAD, HEADER_H - PAD)

    # ── Col 3: Weather ──
    weather = fetch_weather()
    wx = H_COL3_L
    wx_end = R_END
    wx_cx = (wx + wx_end) // 2

    if weather:
        draw.text((wx_cx, 26), f"{weather['temp_c']}°", fill=0, font=get_font(90, bold=True), anchor="mt")
        draw.text((wx_cx, 120), weather["desc"], fill=30, font=get_font(30, bold=True), anchor="mt")
        draw.text((wx_cx, 155), f"Feels {weather['feels_like_c']}°", fill=80, font=get_font(26), anchor="mt")
        draw.text((wx_cx, 186), WEATHER_LOCATION, fill=100, font=get_font(22), anchor="mt")

        # Sunrise / Sunset with drawn icons
        sun_set_y = 230
        gap = 30
        rise_text = weather['sunrise']
        set_text = weather['sunset']
        # Measure text widths to center the whole group
        rise_font = get_font(26)
        rise_w = rise_font.getlength(rise_text)
        set_w = rise_font.getlength(set_text)
        icon_w = 38  # icon diameter area + spacing
        total_w = icon_w + rise_w + gap + icon_w + set_w
        start_x = int(wx_cx - total_w // 2)
        draw_sun_icon(draw, start_x + 12, sun_set_y, r=10, fill=60)
        draw.text((start_x + icon_w, sun_set_y), rise_text, fill=60, font=rise_font, anchor="lm")
        moon_x = int(start_x + icon_w + rise_w + gap)
        draw_moon_icon(draw, moon_x + 12, sun_set_y, r=10, fill=60)
        draw.text((moon_x + icon_w, sun_set_y), set_text, fill=60, font=rise_font, anchor="lm")

        # 3-day forecast: Today on its own row, then Fri + Sat side by side
        # Evenly spaced within remaining area (256 to HEADER_H)
        fc_top = 256
        fc_bot = HEADER_H - 10
        fc_mid = fc_top + (fc_bot - fc_top) // 2
        draw.line([(wx, fc_top), (wx_end, fc_top)], fill=180, width=1)

        forecast = weather["forecast"]
        # Today — full width centered, 2 lines
        if len(forecast) > 0:
            day = forecast[0]
            precip = day.get("precip_prob", 0) or 0
            precip_str = f" {precip}%" if precip > 0 else ""
            today_y = fc_top + 12
            draw.text((wx_cx, today_y), f"Today {day['high_c']}°/{day['low_c']}°", fill=0, font=get_font(26, bold=True), anchor="mt")
            draw.text((wx_cx, today_y + 30), f"{day['desc'][:14]}{precip_str}", fill=80, font=get_font(24), anchor="mt")

        # Fri + Sat side by side, centered
        if len(forecast) > 1:
            pair_y = fc_mid + 10
            fc_half = (wx_end - wx) // 2
            for i, day in enumerate(forecast[1:3]):
                try:
                    d = datetime.strptime(day["date"], "%Y-%m-%d")
                    day_name = d.strftime("%a")
                except ValueError:
                    day_name = "?"
                cx = wx + i * fc_half + fc_half // 2
                precip = day.get("precip_prob", 0) or 0
                precip_str = f" {precip}%" if precip > 0 else ""
                draw.text((cx, pair_y), f"{day_name} {day['high_c']}°/{day['low_c']}°", fill=0, font=get_font(26, bold=True), anchor="mt")
                draw.text((cx, pair_y + 30), f"{day['desc'][:12]}{precip_str}", fill=80, font=get_font(24), anchor="mt")
    else:
        draw.text((wx_cx, HEADER_H // 2), "Weather\nunavailable", fill=120, font=get_font(30), anchor="mm")

    # Full-width divider under header
    hline(HEADER_H)

    # ═══════════════════════════════════════════════
    # BOTTOM: 2 columns — To Do (left) | Schedule (right)
    # ═══════════════════════════════════════════════
    B_L = L
    B_L_END = COL_DIV - GAP
    B_R = COL_DIV + GAP
    B_R_END = R_END

    # ── Column divider ──
    vline(COL_DIV, HEADER_H + 10, HEIGHT - 40)

    # ── Left: To Do ──
    dy = HEADER_H + GAP * 2
    todo_cx = (B_L + B_L_END) // 2
    draw.text((todo_cx, dy), "To Do", fill=0, font=get_font(32, bold=True), anchor="mt")
    dy += 42

    tasks = fetch_tasks()
    if tasks:
        remaining = HEIGHT - 50 - dy
        max_tasks = max(4, remaining // LINE_H)
        for task in tasks[:max_tasks]:
            box_top = dy + (LINE_H - 24) // 2
            draw.rectangle([B_L, box_top, B_L + 24, box_top + 24], outline=60, width=2)
            draw.text((B_L + 36, dy + LINE_H // 2), task["title"][:45], fill=20, font=get_font(26), anchor="lm")
            dy += LINE_H
    else:
        draw.text((B_L, dy), "No tasks", fill=120, font=get_font(26), anchor="lt")

    # ── Right: Schedule ──
    ry = HEADER_H + GAP * 2

    sched_cx = (B_R + B_R_END) // 2
    draw.text((sched_cx, ry), "Schedule", fill=0, font=get_font(34, bold=True), anchor="mt")
    ry += 46

    # Today
    week_events = fetch_week_events()
    today_key = now.strftime("%Y-%m-%d")
    today_events = week_events.get(today_key, [])

    draw.text((B_R, ry), "Today", fill=0, font=get_font(28, bold=True), anchor="lt")
    ry += 34

    if today_events:
        for ev in today_events[:5]:
            time_label = ev["time"] if ev["time"] else "All day"
            draw.text((B_R + 12, ry), time_label, fill=80, font=get_font(26, bold=True), anchor="lt")
            draw.text((B_R + 120, ry), ev["title"][:40], fill=20, font=get_font(26), anchor="lt")
            ry += 34
    else:
        draw.text((B_R + 12, ry), "No events today", fill=120, font=get_font(26), anchor="lt")
        ry += 34

    ry += 10
    draw.line([(B_R, ry), (B_R_END, ry)], fill=180, width=1)
    ry += GAP * 2

    # This Week
    draw.text((B_R, ry), "This Week", fill=0, font=get_font(28, bold=True), anchor="lt")
    ry += 44

    monday = now - timedelta(days=now.weekday())
    has_week_events = False
    for i in range(7):
        day_date = monday + timedelta(days=i)
        date_key = day_date.strftime("%Y-%m-%d")
        events = week_events.get(date_key, [])
        if not events or date_key == today_key or day_date.date() < now.date():
            continue
        has_week_events = True
        day_label = day_date.strftime("%a %d")
        draw.text((B_R, ry), day_label, fill=0, font=get_font(26, bold=True), anchor="lt")
        ry += 32
        for ev in events:
            t = ev["time"] or ""
            prefix = f"{t} " if t else ""
            draw.text((B_R + 12, ry), f"{prefix}{ev['title'][:42]}", fill=50, font=get_font(26), anchor="lt")
            ry += 32
        ry += 6

    if not has_week_events:
        draw.text((B_R + 12, ry), "No upcoming events", fill=120, font=get_font(26), anchor="lt")

    # ── Footer ──
    draw.text((L, HEIGHT - 28), now.strftime("Updated %H:%M"), fill=160, font=get_font(26), anchor="lm")
    battery = fetch_battery()
    if battery:
        batt_str = f"Batt {battery}%"
        draw.text((R_END, HEIGHT - 28), batt_str, fill=160, font=get_font(26), anchor="rm")

    return img


# --- VSS communication ---
def fetch_battery() -> str | None:
    """Fetch battery percentage from the VSS device API."""
    if not DEVICE_UUID:
        return None
    try:
        base_url = f"http://{VSS_HOST}:{VSS_PORT}"
        s = get_session(base_url)
        r = s.get(f"{base_url}/api/device/", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                for d in data:
                    if d.get("Uuid") == DEVICE_UUID:
                        return d.get("Status", {}).get("Battery")
            elif isinstance(data, dict):
                return data.get("Status", {}).get("Battery")
    except Exception as e:
        print(f"[battery] Failed: {e}")
    return None


def get_session(base_url: str) -> requests.Session:
    """Create an authenticated session with VSS."""
    s = requests.Session()
    r = s.post(f"{base_url}/login", data={"username": VSS_USER, "password": VSS_PASS}, allow_redirects=False)
    if r.status_code not in (200, 302):
        raise RuntimeError(f"VSS login failed: {r.status_code}")
    return s


def push_image(img: Image.Image):
    """Push a PIL Image to the Joan device via VSS HTTP backend."""
    base_url = f"http://{VSS_HOST}:{VSS_PORT}"
    session = get_session(base_url)

    # Convert to RGB PNG (VSS requires no alpha)
    rgb = img.convert("RGB")
    buf = io.BytesIO()
    rgb.save(buf, format="PNG")
    buf.seek(0)

    r = session.put(
        f"{base_url}/backend/{DEVICE_UUID}",
        files=[("image", ("dashboard.png", buf, "image/png"))],
    )
    if r.status_code == 200:
        print(f"[push] Image pushed ({buf.tell()} bytes)")
    else:
        print(f"[push] Failed: {r.status_code} {r.text}")


# --- Main ---
def main():
    parser = argparse.ArgumentParser(description="Joan Dashboard")
    parser.add_argument("--loop", type=int, default=0, help="Re-render interval in seconds (0 = once)")
    parser.add_argument("--preview", action="store_true", help="Save preview PNG without pushing")
    args = parser.parse_args()

    while True:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Rendering dashboard...")
        img = render_dashboard()

        if args.preview:
            path = "joan_preview.png"
            img.save(path)
            print(f"[preview] Saved to {path}")
            return

        push_image(img)

        if args.loop <= 0:
            break
        print(f"[loop] Next update in {args.loop}s")
        time.sleep(args.loop)


if __name__ == "__main__":
    main()
