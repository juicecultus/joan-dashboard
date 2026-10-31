#!/usr/bin/env python3
"""Joan Dashboard — renders weather, Google Calendar, and Google Tasks on the Joan device.

Usage:
    python joan_dashboard.py              # render once and push
    python joan_dashboard.py --loop 300   # re-render and push every 300 seconds
    python joan_dashboard.py --preview    # save PNG previews under /previews without pushing

First-time setup:
    python joan_google_auth.py            # authenticate with Google (hello@allmumstalk.com)
"""

import argparse
import calendar
import io
import json
import math
import os
import sys
import threading
import time
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

# Prevent double-import: when run as __main__, register this module under its
# real name so that 'from joan_dashboard import ...' in joan_screens.py reuses
# the SAME module instance (sharing globals like _active_device_uuid).
if __name__ == "__main__" and "joan_dashboard" not in sys.modules:
    sys.modules["joan_dashboard"] = sys.modules["__main__"]
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
# Devices: comma-separated UUIDs, or single UUID (backward compat)
_DEVICE_UUIDS_RAW = os.environ.get("DEVICE_UUIDS", os.environ.get("DEVICE_UUID", ""))
DEVICE_UUID = _DEVICE_UUIDS_RAW.split(",")[0].strip() if _DEVICE_UUIDS_RAW else ""
VSS_USER = os.environ.get("VSS_USER", "admin")
VSS_PASS = os.environ.get("VSS_PASS", "visionect1")

# Port for the local HTTP server that serves rendered images to the VSS engine.
# The VSS engine's WebKit fetches from this server instead of using the broken
# /backend/ push endpoint (port 11116 never binds on Pi 5).
IMAGE_SERVE_PORT = int(os.environ.get("IMAGE_SERVE_PORT", "8888"))
# Host IP reachable from inside the VSS Docker container (docker0 bridge)
IMAGE_SERVE_HOST = os.environ.get("IMAGE_SERVE_HOST", "172.17.0.1")

WIDTH = 1200
HEIGHT = 1600
PREVIEW_DIR = Path("/previews")
FALLBACK_PREVIEW_DIR = Path(__file__).resolve().parent / "previews"

# Weather: lat/lon for Open-Meteo (default: Waddesdon, Buckinghamshire)
WEATHER_LAT = float(os.environ.get("WEATHER_LAT", "51.845"))
WEATHER_LON = float(os.environ.get("WEATHER_LON", "-0.943"))
WEATHER_LOCATION = os.environ.get("WEATHER_LOCATION", "Waddesdon")

# UK Trains: Rail Data Marketplace (Live Departure Board)
TRAINS_API_KEY = os.environ.get("TRAINS_API_KEY", "")
TRAINS_STATION = os.environ.get("TRAINS_STATION", "AVP")       # CRS code (Aylesbury Vale Parkway)
TRAINS_DESTINATION = os.environ.get("TRAINS_DESTINATION", "MYB")  # CRS code (London Marylebone)

# Bin Collection: Buckinghamshire Council (via iTouchVision API)
BIN_UPRN = os.environ.get("BIN_UPRN", "766351323")  # UPRN for 26 Golden Mede, Waddesdon

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


def _truncate_text(font, text: str, max_width: int) -> str:
    if font.getlength(text) <= max_width:
        return text
    if max_width <= font.getlength("…"):
        return "…"
    trimmed = text
    while trimmed and font.getlength(trimmed + "…") > max_width:
        trimmed = trimmed[:-1]
    return trimmed.rstrip() + "…"


def _save_preview_image(img: Image.Image, filename: str) -> Path:
    """Save a preview PNG under /previews and return the path."""
    for directory in (PREVIEW_DIR, FALLBACK_PREVIEW_DIR):
        try:
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / filename
            img.save(path)
            return path
        except OSError as exc:
            print(f"[preview] Cannot write to {directory}: {exc}")
            continue
    raise OSError("Unable to save preview image to /previews or local previews/")


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


_events_cache = {"data": None, "ts": 0}

def fetch_week_events() -> dict:
    """Fetch this week's events (Mon-Sun) from ALL Google Calendars.
    Returns dict keyed by date string 'YYYY-MM-DD' -> list of events.
    Cached for 2 min; stale fallback up to 30 min."""
    now_ts = time.time()
    if _events_cache["data"] is not None and (now_ts - _events_cache["ts"]) < 120:
        return _events_cache["data"]

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
        _events_cache["data"] = week
        _events_cache["ts"] = time.time()
        return week
    except Exception as e:
        print(f"[calendar] Failed: {e}")
        if _events_cache["data"] is not None and (time.time() - _events_cache["ts"]) < 1800:
            print(f"[cache] Serving stale calendar (age {int(time.time() - _events_cache['ts'])}s)")
            return _events_cache["data"]
        return week


# --- Google Tasks ---
_tasks_cache = {"data": None, "ts": 0}

def fetch_tasks() -> list:
    """Fetch incomplete tasks from Google Tasks (default list).
    Cached for 2 min; stale fallback up to 30 min."""
    now_ts = time.time()
    if _tasks_cache["data"] is not None and (now_ts - _tasks_cache["ts"]) < 120:
        return _tasks_cache["data"]

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
        _tasks_cache["data"] = tasks
        _tasks_cache["ts"] = time.time()
        return tasks
    except Exception as e:
        print(f"[tasks] Failed: {e}")
        if _tasks_cache["data"] is not None and (time.time() - _tasks_cache["ts"]) < 1800:
            print(f"[cache] Serving stale tasks (age {int(time.time() - _tasks_cache['ts'])}s)")
            return _tasks_cache["data"]
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
    from screens.weather_glance import render_weather_glance
    return render_weather_glance()


# --- Image-serving HTTP server ---
# Instead of pushing images via the broken VSS /backend/ endpoint (port 11116
# never binds on Pi 5 due to WebKit/Xorg incompatibility), we save rendered
# images to disk and serve them via a local HTTP server.  The VSS engine's
# WebKit fetches our page and pushes the result to the Joan device.

_SERVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "serve")
os.makedirs(_SERVE_DIR, exist_ok=True)


class _ImageHandler(BaseHTTPRequestHandler):
    """Serve the latest rendered image as a full-screen HTML page."""

    def do_GET(self):
        path = self.path.strip("/")
        # Serve PNG file directly
        if path.endswith(".png"):
            fpath = os.path.join(_SERVE_DIR, path)
            if os.path.exists(fpath):
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Cache-Control", "no-cache, no-store")
                self.end_headers()
                with open(fpath, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404)
            return
        # Serve HTML page with the image embedded as base64 data URI.
        # This avoids a second HTTP request that WebKit can't complete
        # within the engine's short RenderTimeout (100ms).
        import base64
        uuid = path if path else DEVICE_UUID
        png_name = f"{uuid}.png"
        fpath = os.path.join(_SERVE_DIR, png_name)
        if not os.path.exists(fpath):
            pngs = [f for f in os.listdir(_SERVE_DIR) if f.endswith(".png")]
            if pngs:
                fpath = os.path.join(_SERVE_DIR, pngs[0])
            else:
                self.send_error(404, "No image available yet")
                return
        with open(fpath, "rb") as f:
            image_bytes = f.read()
        with Image.open(io.BytesIO(image_bytes)) as served_image:
            frame_width, frame_height = served_image.size
        b64 = base64.b64encode(image_bytes).decode()
        html = (f'<!DOCTYPE html><html><head><meta charset="utf-8">'
                f'<meta name="viewport" content="width={frame_width},height={frame_height},initial-scale=1">'
                f'<style>*{{margin:0;padding:0}}body{{overflow:hidden;background:#fff}}'
                f'img{{display:block;width:{frame_width}px;height:{frame_height}px}}</style></head>'
                f'<body><img src="data:image/png;base64,{b64}"></body></html>')
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Cache-Control", "no-cache, no-store")
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        pass  # silence request logs


def _start_image_server():
    """Start the image-serving HTTP server in a daemon thread."""
    server = HTTPServer(("0.0.0.0", IMAGE_SERVE_PORT), _ImageHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"[http] Image server started on port {IMAGE_SERVE_PORT}")


def _configure_vss_session(device_uuid: str):
    """Point the VSS device session URL to our local image server."""
    base_url = f"http://{VSS_HOST}:{VSS_PORT}"
    try:
        s = get_session(base_url)
        serve_url = f"http://{IMAGE_SERVE_HOST}:{IMAGE_SERVE_PORT}/{device_uuid}"
        session_data = {
            "Uuid": device_uuid,
            "Backend": {
                "Name": "HTML",
                "Fields": {"url": serve_url, "ReloadTimeout": "180"}
            },
            "Options": {
                "Beautify": "pretty,gamma=1.0",  # Keep precomputed photo tones neutral.
                "ChangesAutodetect": "true,threshold=0",
                "DefaultDithering": "none",
                "DefaultEncoding": "4"
            },
            "Storage": None
        }
        r = s.put(f"{base_url}/api/session/{device_uuid}",
                  json=session_data, timeout=5)
        if r.status_code in (200, 204):
            print(f"[vss] Session configured: {device_uuid[:12]}... -> {serve_url}")
        else:
            print(f"[vss] Session config failed: {r.status_code} {r.text}")
    except Exception as e:
        print(f"[vss] Session config error: {e}")


# --- VSS communication ---
_active_device_uuid = None  # set per-device before rendering for correct footer

# Session cache: reuse a single authenticated session instead of logging in
# for every API call (previously created 128+ sessions per playlist cycle).
_vss_session = None
_vss_session_ts = 0
_VSS_SESSION_TTL = 300  # reuse session for 5 minutes

# Device status cache: fetch device list once per render cycle, not per screen.
_device_status_cache = {}   # uuid -> {"battery": ..., "temperature": ...}
_device_status_ts = 0
_DEVICE_STATUS_TTL = 30     # refresh every 30s (well within 3-min heartbeat)


def get_session(base_url: str) -> requests.Session:
    """Get an authenticated VSS session (cached, reused for 5 min)."""
    global _vss_session, _vss_session_ts
    now = time.time()
    if _vss_session and (now - _vss_session_ts) < _VSS_SESSION_TTL:
        return _vss_session
    s = requests.Session()
    r = s.post(f"{base_url}/login", data={"username": VSS_USER, "password": VSS_PASS}, allow_redirects=False)
    if r.status_code not in (200, 302):
        raise RuntimeError(f"VSS login failed: {r.status_code}")
    _vss_session = s
    _vss_session_ts = now
    return s


def _refresh_device_status_cache():
    """Fetch all device statuses from VSS and cache them."""
    global _device_status_cache, _device_status_ts
    now = time.time()
    if _device_status_cache and (now - _device_status_ts) < _DEVICE_STATUS_TTL:
        return
    try:
        base_url = f"http://{VSS_HOST}:{VSS_PORT}"
        s = get_session(base_url)
        r = s.get(f"{base_url}/api/device/", timeout=5)
        if r.status_code == 200:
            new_cache = {}
            temps = []
            for d in r.json():
                uuid = d.get("Uuid")
                status = d.get("Status", {})
                if uuid:
                    new_cache[uuid] = {
                        "battery": status.get("Battery"),
                        "temperature": status.get("Temperature"),
                    }
                    t = status.get("Temperature")
                    if t is not None:
                        try:
                            temps.append(int(t))
                        except (ValueError, TypeError):
                            pass
            # Use lowest device temperature as room temp (charging devices
            # read high due to internal heat; the coolest sensor is most
            # accurate for ambient room temperature).
            room_temp = str(min(temps)) if temps else None
            for entry in new_cache.values():
                entry["room_temperature"] = room_temp
            _device_status_cache = new_cache
            _device_status_ts = now
        elif r.status_code in (401, 403):
            # Session expired, force re-login next call
            global _vss_session
            _vss_session = None
    except Exception as e:
        print(f"[device_status] Refresh failed: {e}")


def fetch_device_status() -> dict:
    """Fetch battery and room temperature for the active device.

    Battery is per-device. Room temperature is shared across all devices
    (uses the lowest sensor reading to avoid inflated readings from
    charging devices).

    Uses _active_device_uuid when set (multi-device rendering),
    otherwise falls back to DEVICE_UUID (first configured device).
    Results are cached per render cycle to avoid excessive API calls.
    """
    _refresh_device_status_cache()
    uuid = _active_device_uuid or DEVICE_UUID
    if not uuid:
        return {"battery": None, "temperature": None}
    entry = _device_status_cache.get(uuid, {})
    return {
        "battery": entry.get("battery"),
        "temperature": entry.get("room_temperature"),
    }


def discover_devices() -> list:
    """Auto-discover allowed devices from VSS with their native resolutions.

    If DEVICE_UUIDS is set, only those UUIDs are included.
    If no UUIDs are configured, all allowed devices are included.
    Falls back to configured UUIDs at canvas resolution on failure.
    """
    devices = []
    try:
        base_url = f"http://{VSS_HOST}:{VSS_PORT}"
        s = get_session(base_url)
        r = s.get(f"{base_url}/api/device/", timeout=5)
        if r.status_code == 200:
            configured = [u.strip() for u in _DEVICE_UUIDS_RAW.split(",") if u.strip()]
            for d in r.json():
                if d.get("Options", {}).get("Allowed") != "true":
                    continue
                uuid = d["Uuid"]
                if configured and uuid not in configured:
                    continue
                displays = d.get("Displays", [])
                w = displays[0]["Width"] if displays else WIDTH
                h = displays[0]["Height"] if displays else HEIGHT
                name = d.get("Options", {}).get("Revision", uuid[:12])
                devices.append({"uuid": uuid, "name": name, "width": w, "height": h})
    except Exception as e:
        print(f"[discover] VSS query failed: {e}")
        # Fallback: use configured UUIDs at canvas resolution
        for u in [u.strip() for u in _DEVICE_UUIDS_RAW.split(",") if u.strip()]:
            devices.append({"uuid": u, "name": u[:12], "width": WIDTH, "height": HEIGHT})
    return devices


_discovered_devices = None


def _get_devices() -> list:
    """Return cached list of target devices (discovered on first call)."""
    global _discovered_devices
    if _discovered_devices is None:
        _discovered_devices = discover_devices()
    return _discovered_devices


def _prepare_device_image(img, target_size):
    """Rotate portrait artwork into the panel's native landscape framebuffer.

    Mount the display 90 degrees to the right from landscape. Set
    PORTRAIT_ROTATION=270 for the opposite mounting direction.
    """
    from PIL import ImageOps
    if not target_size:
        target_size = (1600, 1200)
    # Carry photo coverage alongside the full-tone canvas through all geometry.
    mask = None
    regions = img.info.get('photo_regions', [])
    if regions:
        mask = Image.new('L', img.size, 0)
        md = ImageDraw.Draw(mask)
        for left, top, right, bottom in regions:
            md.rectangle((left,top,right-1,bottom-1),fill=255)
    if (img.width < img.height) != (target_size[0] < target_size[1]):
        rotation = int(os.environ.get("PORTRAIT_ROTATION", "90"))
        if rotation not in (90, 270):
            raise ValueError("PORTRAIT_ROTATION must be 90 or 270")
        img = img.rotate(rotation, expand=True)
        if mask is not None:
            mask = mask.rotate(rotation, expand=True)
    out = ImageOps.pad(img, target_size, method=Image.Resampling.LANCZOS, color=255)
    if mask is not None:
        from photo_renderer import dither_photos
        mask = ImageOps.pad(mask, target_size, method=Image.Resampling.NEAREST, color=0)
        out = dither_photos(out, mask)
    out.info.pop('photo_regions', None)
    return out


def push_image(img: Image.Image, device_uuid: str = None, target_size: tuple = None):
    """Push a PIL Image to a Joan device.

    Saves the rendered image to the local serve directory so the VSS engine's
    WebKit can fetch it via our HTTP server.  Also attempts the legacy
    /backend/ API push as a fallback (works when VSS port 11116 is available).

    If target_size differs from the image dimensions, the image is
    LANCZOS-resized to the device's native resolution before pushing.
    """
    uuid = device_uuid or DEVICE_UUID
    if not uuid:
        print("[push] No device UUID configured")
        return

    # Resize to device native resolution if different from canvas
    out = _prepare_device_image(img, target_size)

    # Convert to RGB PNG
    rgb = out.convert("RGB")

    # Save to serve directory for the HTTP image server
    serve_path = os.path.join(_SERVE_DIR, f"{uuid}.png")
    temp_path = serve_path + ".tmp"
    rgb.save(temp_path, format="PNG")
    os.replace(temp_path, serve_path)
    fsize = os.path.getsize(serve_path)
    print(f"[push] -> {uuid[:12]}... {out.width}x{out.height} ({fsize} bytes)")

    # Also attempt legacy /backend/ push (works if VSS engine port 11116 is up)
    try:
        base_url = f"http://{VSS_HOST}:{VSS_PORT}"
        session = get_session(base_url)
        buf = io.BytesIO()
        rgb.save(buf, format="PNG")
        buf.seek(0)
        r = session.put(
            f"{base_url}/backend/{uuid}",
            files=[("image", ("dashboard.png", buf, "image/png"))],
            timeout=5,
        )
        if r.status_code == 200:
            print(f"[push] (backend ok)")
    except Exception:
        pass  # silently fall back to HTTP serve method


def push_to_all(img: Image.Image):
    """Push a pre-rendered image to every configured device."""
    devices = _get_devices()
    if not devices:
        if DEVICE_UUID:
            push_image(img, DEVICE_UUID)
        else:
            print("[push] No devices configured")
        return
    for dev in devices:
        push_image(img, dev["uuid"], (dev["width"], dev["height"]))


def render_and_push_all(render_fn):
    """Render per-device (for device-specific footer) and push to all.

    Sets _active_device_uuid before each render so fetch_device_status()
    returns the correct battery/temperature for each device's footer.
    """
    global _active_device_uuid
    devices = _get_devices()
    if not devices:
        if DEVICE_UUID:
            _active_device_uuid = DEVICE_UUID
            img = render_fn()
            push_image(img, DEVICE_UUID)
        else:
            print("[push] No devices configured")
        _active_device_uuid = None
        return
    for dev in devices:
        _active_device_uuid = dev["uuid"]
        img = render_fn()
        push_image(img, dev["uuid"], (dev["width"], dev["height"]))
    _active_device_uuid = None


# --- Main ---
def main():
    parser = argparse.ArgumentParser(description="Joan Dashboard")
    parser.add_argument("--loop", type=int, default=0, help="Re-render interval in seconds (0 = once)")
    parser.add_argument("--preview", action="store_true", help="Save preview PNG without pushing")
    parser.add_argument("--playlist", type=str, default="",
                        help="Comma-separated screen names to rotate (e.g. 'dashboard,agenda,quote,art')")
    parser.add_argument("--active-hours", type=str, default="07:00-21:00",
                        help="Only refresh during these hours (default: 07:00-21:00)")
    parser.add_argument("--screen", type=str, default="",
                        help="Render a single screen by name (e.g. 'quote', 'art', 'radar')")
    args = parser.parse_args()

    # Single named screen (for preview/testing)
    if args.screen:
        from joan_screens import ALL_SCREENS
        if args.screen not in ALL_SCREENS:
            print(f"[error] Unknown screen '{args.screen}'. Available: {', '.join(ALL_SCREENS.keys())}")
            return
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Rendering screen: {args.screen}")
        if args.preview:
            img = ALL_SCREENS[args.screen]()
            path = _save_preview_image(img, f"{args.screen}.png")
            print(f"[preview] Saved to {path}")
        else:
            render_and_push_all(ALL_SCREENS[args.screen])
        return

    # Start image-serving HTTP server and configure VSS sessions
    if not args.preview:
        _start_image_server()
        devices = _get_devices()
        for dev in devices:
            _configure_vss_session(dev["uuid"])
        if not devices and DEVICE_UUID:
            _configure_vss_session(DEVICE_UUID)

    # Playlist mode
    if args.playlist:
        from joan_screens import ALL_SCREENS

        PLAYLIST_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "playlist_config.json")

        def _load_playlist():
            """Load screen list from config file or CLI arg. Re-read each cycle."""
            names = []
            cfg_interval = 180
            if args.playlist == "config":
                # Read from playlist_config.json (written by web UI)
                if os.path.exists(PLAYLIST_CONFIG):
                    try:
                        with open(PLAYLIST_CONFIG, "r") as f:
                            cfg = json.load(f)
                        names = cfg.get("enabled", [])
                        cfg_interval = cfg.get("interval", 180)
                    except Exception as e:
                        print(f"[playlist] Failed to read config: {e}")
                if not names:
                    print("[playlist] Config empty or missing, using all screens")
                    names = ["dashboard"] + list(ALL_SCREENS.keys())
            else:
                names = [s.strip() for s in args.playlist.split(",") if s.strip()]
            screens = []
            for name in names:
                if name == "dashboard":
                    screens.append(("dashboard", render_dashboard))
                elif name in ALL_SCREENS:
                    screens.append((name, ALL_SCREENS[name]))
                else:
                    print(f"[warn] Unknown screen '{name}', skipping")
            return screens, cfg_interval

        screens, cfg_interval = _load_playlist()

        if not screens:
            print("[error] No valid screens in playlist")
            return

        interval = max(args.loop, cfg_interval) if args.loop else max(cfg_interval, 180)
        # Parse active hours
        try:
            start_str, end_str = args.active_hours.split("-")
            active_start = int(start_str.split(":")[0]) * 60 + int(start_str.split(":")[1])
            active_end = int(end_str.split(":")[0]) * 60 + int(end_str.split(":")[1])
        except (ValueError, IndexError):
            active_start, active_end = 7 * 60, 21 * 60  # default 07:00-21:00

        devices = _get_devices()
        dev_info = ", ".join(f"{d['name']} {d['width']}x{d['height']}" for d in devices) or "none found"
        print(f"[playlist] Rotating {len(screens)} screens, {interval}s each, active {args.active_hours}: {[s[0] for s in screens]}")
        print(f"[devices] Pushing to {len(devices)} device(s): {dev_info}")

        screen_idx = 0
        _prev_order = None  # track config changes

        while True:
            # Reload config BEFORE each screen (changes take effect immediately)
            if args.playlist == "config":
                screens, cfg_interval = _load_playlist()
                interval = max(args.loop, cfg_interval) if args.loop else max(cfg_interval, 180)
                # Detect config changes and log them
                new_order = [s[0] for s in screens]
                if _prev_order is not None and new_order != _prev_order:
                    print(f"[playlist] Config changed: {new_order}")
                _prev_order = new_order

            if not screens:
                time.sleep(30)
                continue

            # Wrap index if playlist shrank or cycled
            if screen_idx >= len(screens):
                screen_idx = 0

            # Active hours check
            now_mins = datetime.now().hour * 60 + datetime.now().minute
            if now_mins < active_start or now_mins >= active_end:
                # Push sleep screen once
                try:
                    from joan_screens import render_sleep_screen
                    wake_str = f"{active_start // 60:02d}:{active_start % 60:02d}"
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Pushing sleep screen")
                    render_and_push_all(lambda: render_sleep_screen(wake_time=wake_str))
                except Exception as e:
                    print(f"[sleep] Failed to render sleep screen: {e}")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Outside active hours ({args.active_hours}); polling until wake")
                # Poll the wall clock in short increments. A single long time.sleep()
                # is unsafe on macOS because nanosleep doesn't tick while the host is
                # asleep, so an overnight 10h sleep can leave the loop stranded after
                # the Mac wakes. Re-checking every 60s also self-heals against clock
                # changes (DST, manual sync).
                while True:
                    now_m = datetime.now().hour * 60 + datetime.now().minute
                    if active_start <= now_m < active_end:
                        break
                    time.sleep(60)
                screen_idx = 0  # restart from first screen on wake
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Inside active hours, resuming playlist")
                continue

            name, render_fn = screens[screen_idx]
            try:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Rendering: {name} ({screen_idx + 1}/{len(screens)})")
                render_and_push_all(render_fn)
            except Exception as e:
                # Keep the last useful frame; try the next slot immediately.
                print(f"[{name}] Skipping unavailable screen: {e}")
                screen_idx += 1
                time.sleep(min(5, interval))
                continue

            screen_idx += 1
            print(f"[playlist] Next screen in {interval}s")
            time.sleep(interval)
        return

    # Default: dashboard only
    while True:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Rendering dashboard...")

        if args.preview:
            img = render_dashboard()
            path = _save_preview_image(img, "dashboard.png")
            print(f"[preview] Saved to {path}")
            return

        render_and_push_all(render_dashboard)

        if args.loop <= 0:
            break
        print(f"[loop] Next update in {args.loop}s")
        time.sleep(args.loop)


if __name__ == "__main__":
    main()
