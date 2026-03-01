#!/usr/bin/env python3
"""Joan Playlist Manager — web UI to toggle which screens rotate on the devices.

Usage:
    python joan_playlist_manager.py                # start on port 8080
    python joan_playlist_manager.py --port 9090    # custom port

Saves selections to playlist_config.json, which joan_dashboard.py reads
when --playlist=config is used.
"""

import argparse
import json
import os
import signal
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "playlist_config.json")

# All available screens with display names and descriptions
SCREEN_CATALOG = [
    ("dashboard",  "Main Dashboard",       "Clock, calendar, weather, events, tasks"),
    ("agenda",     "Daily Agenda",          "Full-screen schedule for today + week"),
    ("quote",      "Daily Quote",           "Inspirational quote of the day"),
    ("countdown",  "Countdown Timer",       "Days until upcoming events"),
    ("photo",      "Family Photo",          "Random family photo from Google Photos"),
    ("word",       "Word of the Day",       "Vocabulary builder with definition"),
    ("history",    "This Day in History",   "Historical events on today's date"),
    ("art",        "Art Gallery",           "Famous artwork with artist info"),
    ("radar",      "Weather Radar",         "Current weather radar map"),
    ("joke",       "Dad Joke",              "Random dad joke"),
    ("progress",   "Year Progress",         "Year progress bar + stats"),
    ("maths",      "Maths Challenge",       "8 maths problems for kids"),
    ("rss",        "RSS Headlines",         "Latest articles from RSS feed"),
    ("stocks",     "Stock Ticker",          "Live stock prices + daily change"),
    ("todo",       "Todo List",             "Google Tasks full-screen list"),
    ("moon",       "Moon Phase",            "Current moon with phase info"),
    ("airquality", "Air Quality",           "AQI, pollutants, UV index"),
    ("clock",      "Analogue Clock",        "Classic clock face"),
    ("movies",     "Upcoming Movies",       "Featured movie + coming soon list"),
    ("learning",   "Kid Learning Card",     "Spelling, times tables, capitals"),
    ("trains",     "UK Train Departures",   "Live departures via Rail Data Marketplace"),
    ("bins",       "Bin Collection Day",    "Next collection dates for your address (Buckinghamshire)"),
]


def load_config() -> dict:
    """Load playlist config from JSON file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    # Default: all screens enabled
    return {"enabled": [s[0] for s in SCREEN_CATALOG], "interval": 180}


def save_config(config: dict):
    """Save playlist config to JSON file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def render_html(config: dict) -> str:
    """Render the playlist manager page."""
    enabled = set(config.get("enabled", []))
    interval = config.get("interval", 180)

    rows = ""
    for key, name, desc in SCREEN_CATALOG:
        checked = "checked" if key in enabled else ""
        rows += f"""
        <label class="screen-row" for="chk-{key}">
            <input type="checkbox" name="screens" value="{key}" id="chk-{key}" {checked}>
            <div class="screen-info">
                <span class="screen-name">{name}</span>
                <span class="screen-desc">{desc}</span>
            </div>
            <span class="screen-key">{key}</span>
        </label>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Joan Playlist Manager</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f0f0f;
            color: #e0e0e0;
            min-height: 100vh;
        }}
        .container {{
            max-width: 720px;
            margin: 0 auto;
            padding: 24px 16px;
        }}
        header {{
            text-align: center;
            margin-bottom: 32px;
            padding-bottom: 24px;
            border-bottom: 1px solid #2a2a2a;
        }}
        header h1 {{
            font-size: 28px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 6px;
        }}
        header p {{
            font-size: 14px;
            color: #888;
        }}
        .toolbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            gap: 12px;
            flex-wrap: wrap;
        }}
        .toolbar-left {{
            display: flex;
            gap: 8px;
        }}
        .btn-sm {{
            padding: 6px 14px;
            font-size: 13px;
            border: 1px solid #333;
            background: #1a1a1a;
            color: #ccc;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.15s;
        }}
        .btn-sm:hover {{ background: #252525; color: #fff; }}
        .interval-group {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: #888;
        }}
        .interval-group input {{
            width: 70px;
            padding: 6px 10px;
            border: 1px solid #333;
            background: #1a1a1a;
            color: #fff;
            border-radius: 6px;
            font-size: 13px;
            text-align: center;
        }}
        .screen-list {{
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}
        .screen-row {{
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 14px 16px;
            background: #161616;
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.15s;
            user-select: none;
        }}
        .screen-row:hover {{ background: #1e1e1e; }}
        .screen-row input[type="checkbox"] {{
            width: 20px;
            height: 20px;
            accent-color: #4ade80;
            cursor: pointer;
            flex-shrink: 0;
        }}
        .screen-info {{
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}
        .screen-name {{
            font-size: 15px;
            font-weight: 600;
            color: #f0f0f0;
        }}
        .screen-desc {{
            font-size: 12px;
            color: #666;
        }}
        .screen-key {{
            font-family: 'SF Mono', Monaco, Consolas, monospace;
            font-size: 11px;
            color: #555;
            background: #1a1a1a;
            padding: 3px 8px;
            border-radius: 4px;
            border: 1px solid #2a2a2a;
        }}
        .save-bar {{
            position: sticky;
            bottom: 0;
            padding: 16px 0;
            background: linear-gradient(transparent, #0f0f0f 30%);
            text-align: center;
        }}
        .btn-save {{
            padding: 12px 48px;
            font-size: 15px;
            font-weight: 600;
            border: none;
            background: #4ade80;
            color: #000;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.15s;
        }}
        .btn-save:hover {{ background: #22c55e; }}
        .btn-save:active {{ transform: scale(0.97); }}
        .toast {{
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%) translateY(-80px);
            background: #22c55e;
            color: #000;
            padding: 10px 24px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            transition: transform 0.3s ease;
            z-index: 100;
        }}
        .toast.show {{ transform: translateX(-50%) translateY(0); }}
        .count {{
            font-size: 13px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Joan Playlist Manager</h1>
            <p>Select which screens rotate on your Joan devices</p>
        </header>

        <form method="POST" action="/save" id="playlist-form">
            <div class="toolbar">
                <div class="toolbar-left">
                    <button type="button" class="btn-sm" onclick="toggleAll(true)">Select All</button>
                    <button type="button" class="btn-sm" onclick="toggleAll(false)">Deselect All</button>
                    <span class="count" id="count"></span>
                </div>
                <div class="interval-group">
                    <span>Interval</span>
                    <input type="number" name="interval" value="{interval}" min="60" max="3600" step="30">
                    <span>sec</span>
                </div>
            </div>

            <div class="screen-list">
                {rows}
            </div>

            <div class="save-bar">
                <button type="submit" class="btn-save">Save Playlist</button>
            </div>
        </form>
    </div>

    <div class="toast" id="toast">Playlist saved!</div>

    <script>
        function toggleAll(state) {{
            document.querySelectorAll('input[name="screens"]').forEach(cb => cb.checked = state);
            updateCount();
        }}
        function updateCount() {{
            const n = document.querySelectorAll('input[name="screens"]:checked').length;
            const t = document.querySelectorAll('input[name="screens"]').length;
            document.getElementById('count').textContent = n + ' / ' + t + ' enabled';
        }}
        document.querySelectorAll('input[name="screens"]').forEach(cb => cb.addEventListener('change', updateCount));
        updateCount();

        // Show toast if redirected after save
        if (window.location.search.includes('saved=1')) {{
            const toast = document.getElementById('toast');
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2500);
            history.replaceState(null, '', '/');
        }}
    </script>
</body>
</html>"""


class PlaylistHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        config = load_config()
        html = render_html(config)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def do_POST(self):
        if self.path == "/save":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode()
            params = parse_qs(body)
            enabled = params.get("screens", [])
            interval = int(params.get("interval", [180])[0])
            interval = max(60, min(3600, interval))
            save_config({"enabled": enabled, "interval": interval})
            print(f"[playlist] Saved: {len(enabled)} screens, {interval}s interval")
            self.send_response(303)
            self.send_header("Location", "/?saved=1")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        print(f"[web] {args[0]}")


def main():
    parser = argparse.ArgumentParser(description="Joan Playlist Manager")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    args = parser.parse_args()

    server = HTTPServer(("0.0.0.0", args.port), PlaylistHandler)
    print(f"[playlist-manager] Listening on http://0.0.0.0:{args.port}")
    print(f"[playlist-manager] Config file: {CONFIG_FILE}")

    signal.signal(signal.SIGINT, lambda *_: (print("\nShutting down..."), server.shutdown(), sys.exit(0)))

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
