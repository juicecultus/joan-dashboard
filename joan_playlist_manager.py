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
    ("flipdate",   "Flip Date",             "Flip-calendar style date display"),
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
    """Render the playlist manager page with drag-and-drop reordering."""
    enabled_list = config.get("enabled", [])
    interval = config.get("interval", 180)

    # Build lookup for catalog info
    catalog = {key: (name, desc) for key, name, desc in SCREEN_CATALOG}

    # Enabled screens in their saved order
    enabled_rows = ""
    for idx, key in enumerate(enabled_list):
        if key not in catalog:
            continue
        name, desc = catalog[key]
        enabled_rows += f"""
        <div class="screen-row" draggable="true" data-key="{key}" data-enabled="1">
            <span class="drag-handle" title="Drag to reorder">&#9776;</span>
            <input type="checkbox" checked data-key="{key}">
            <div class="screen-info">
                <span class="screen-name">{name}</span>
                <span class="screen-desc">{desc}</span>
            </div>
            <span class="screen-key">{key}</span>
            <div class="move-btns">
                <button type="button" class="btn-move" onclick="moveUp(this)" title="Move up">&uarr;</button>
                <button type="button" class="btn-move" onclick="moveDown(this)" title="Move down">&darr;</button>
            </div>
        </div>"""

    # Disabled screens (not in enabled list)
    enabled_set = set(enabled_list)
    disabled_rows = ""
    for key, name, desc in SCREEN_CATALOG:
        if key in enabled_set:
            continue
        disabled_rows += f"""
        <div class="screen-row disabled" data-key="{key}" data-enabled="0">
            <span class="drag-handle dim">&#9776;</span>
            <input type="checkbox" data-key="{key}">
            <div class="screen-info">
                <span class="screen-name">{name}</span>
                <span class="screen-desc">{desc}</span>
            </div>
            <span class="screen-key">{key}</span>
            <div class="move-btns"></div>
        </div>"""

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
            align-items: center;
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
        .section-label {{
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #555;
            margin: 20px 0 8px 4px;
        }}
        .screen-list {{
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}
        .screen-row {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 14px;
            background: #161616;
            border-radius: 8px;
            transition: background 0.15s, opacity 0.15s, transform 0.15s;
            user-select: none;
        }}
        .screen-row:hover {{ background: #1e1e1e; }}
        .screen-row.disabled {{ opacity: 0.45; }}
        .screen-row.drag-over {{
            border-top: 2px solid #4ade80;
            margin-top: -2px;
        }}
        .screen-row.dragging {{
            opacity: 0.3;
        }}
        .drag-handle {{
            cursor: grab;
            font-size: 18px;
            color: #555;
            padding: 0 4px;
            flex-shrink: 0;
        }}
        .drag-handle:active {{ cursor: grabbing; }}
        .drag-handle.dim {{ color: #333; }}
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
            min-width: 0;
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
            flex-shrink: 0;
        }}
        .move-btns {{
            display: flex;
            flex-direction: column;
            gap: 2px;
            flex-shrink: 0;
        }}
        .btn-move {{
            width: 28px;
            height: 22px;
            font-size: 14px;
            border: 1px solid #333;
            background: #1a1a1a;
            color: #888;
            border-radius: 4px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 0;
            line-height: 1;
            transition: all 0.15s;
        }}
        .btn-move:hover {{ background: #252525; color: #fff; border-color: #4ade80; }}
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
        .order-num {{
            font-size: 12px;
            font-weight: 700;
            color: #4ade80;
            width: 20px;
            text-align: center;
            flex-shrink: 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Joan Playlist Manager</h1>
            <p>Drag to reorder, tick to enable. Order = rotation order.</p>
        </header>

        <div class="toolbar">
            <div class="toolbar-left">
                <button type="button" class="btn-sm" onclick="toggleAll(true)">Select All</button>
                <button type="button" class="btn-sm" onclick="toggleAll(false)">Deselect All</button>
                <span class="count" id="count"></span>
            </div>
            <div class="interval-group">
                <span>Interval</span>
                <input type="number" id="interval" value="{interval}" min="60" max="3600" step="30">
                <span>sec</span>
            </div>
        </div>

        <div class="section-label">Enabled (rotation order)</div>
        <div class="screen-list" id="enabled-list">
            {enabled_rows}
        </div>

        <div class="section-label">Disabled</div>
        <div class="screen-list" id="disabled-list">
            {disabled_rows}
        </div>

        <div class="save-bar">
            <button type="button" class="btn-save" onclick="savePlaylist()">Save Playlist</button>
        </div>
    </div>

    <div class="toast" id="toast">Playlist saved!</div>

    <script>
        // --- Move up/down ---
        function moveUp(btn) {{
            const row = btn.closest('.screen-row');
            const prev = row.previousElementSibling;
            if (prev) row.parentNode.insertBefore(row, prev);
            renumber();
        }}
        function moveDown(btn) {{
            const row = btn.closest('.screen-row');
            const next = row.nextElementSibling;
            if (next) row.parentNode.insertBefore(next, row);
            renumber();
        }}

        // --- Checkbox toggle: move between enabled/disabled ---
        document.addEventListener('change', function(e) {{
            if (e.target.type !== 'checkbox') return;
            const row = e.target.closest('.screen-row');
            if (e.target.checked) {{
                // Move to enabled list
                row.classList.remove('disabled');
                row.dataset.enabled = '1';
                row.querySelector('.move-btns').innerHTML =
                    '<button type="button" class="btn-move" onclick="moveUp(this)" title="Move up">&uarr;</button>' +
                    '<button type="button" class="btn-move" onclick="moveDown(this)" title="Move down">&darr;</button>';
                row.querySelector('.drag-handle').classList.remove('dim');
                document.getElementById('enabled-list').appendChild(row);
            }} else {{
                // Move to disabled list
                row.classList.add('disabled');
                row.dataset.enabled = '0';
                row.querySelector('.move-btns').innerHTML = '';
                row.querySelector('.drag-handle').classList.add('dim');
                document.getElementById('disabled-list').appendChild(row);
            }}
            renumber();
        }});

        // --- Drag and drop (enabled list only) ---
        let dragEl = null;
        const enabledList = document.getElementById('enabled-list');

        enabledList.addEventListener('dragstart', function(e) {{
            dragEl = e.target.closest('.screen-row');
            if (!dragEl || dragEl.dataset.enabled !== '1') {{ e.preventDefault(); return; }}
            dragEl.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
        }});
        enabledList.addEventListener('dragend', function() {{
            if (dragEl) dragEl.classList.remove('dragging');
            enabledList.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
            dragEl = null;
            renumber();
        }});
        enabledList.addEventListener('dragover', function(e) {{
            e.preventDefault();
            const target = e.target.closest('.screen-row');
            enabledList.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
            if (target && target !== dragEl && target.dataset.enabled === '1') {{
                target.classList.add('drag-over');
            }}
        }});
        enabledList.addEventListener('drop', function(e) {{
            e.preventDefault();
            const target = e.target.closest('.screen-row');
            if (target && target !== dragEl && target.dataset.enabled === '1') {{
                const rect = target.getBoundingClientRect();
                const midY = rect.top + rect.height / 2;
                if (e.clientY < midY) {{
                    enabledList.insertBefore(dragEl, target);
                }} else {{
                    enabledList.insertBefore(dragEl, target.nextSibling);
                }}
            }}
            enabledList.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
            renumber();
        }});

        // --- Touch drag for mobile ---
        let touchEl = null, touchClone = null, touchStartY = 0;
        enabledList.addEventListener('touchstart', function(e) {{
            const handle = e.target.closest('.drag-handle');
            if (!handle) return;
            touchEl = handle.closest('.screen-row');
            if (!touchEl || touchEl.dataset.enabled !== '1') return;
            touchStartY = e.touches[0].clientY;
            touchEl.classList.add('dragging');
        }}, {{passive: true}});
        document.addEventListener('touchmove', function(e) {{
            if (!touchEl) return;
            e.preventDefault();
            const y = e.touches[0].clientY;
            const rows = [...enabledList.querySelectorAll('.screen-row:not(.dragging)')];
            let target = null;
            for (const row of rows) {{
                const rect = row.getBoundingClientRect();
                if (y > rect.top && y < rect.bottom) {{ target = row; break; }}
            }}
            enabledList.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
            if (target) target.classList.add('drag-over');
        }}, {{passive: false}});
        document.addEventListener('touchend', function() {{
            if (!touchEl) return;
            const over = enabledList.querySelector('.drag-over');
            if (over) {{
                enabledList.insertBefore(touchEl, over);
            }}
            touchEl.classList.remove('dragging');
            enabledList.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
            touchEl = null;
            renumber();
        }});

        // --- Helpers ---
        function toggleAll(state) {{
            document.querySelectorAll('.screen-row input[type="checkbox"]').forEach(cb => {{
                if (cb.checked !== state) {{ cb.checked = state; cb.dispatchEvent(new Event('change', {{bubbles:true}})); }}
            }});
        }}

        function renumber() {{
            const rows = enabledList.querySelectorAll('.screen-row');
            rows.forEach((row, i) => {{
                let num = row.querySelector('.order-num');
                if (!num) {{
                    num = document.createElement('span');
                    num.className = 'order-num';
                    row.insertBefore(num, row.querySelector('.drag-handle').nextSibling);
                }}
                num.textContent = i + 1;
            }});
            updateCount();
        }}

        function updateCount() {{
            const n = enabledList.querySelectorAll('.screen-row').length;
            const t = document.querySelectorAll('.screen-row').length;
            document.getElementById('count').textContent = n + ' / ' + t + ' enabled';
        }}

        function savePlaylist() {{
            const enabled = [...enabledList.querySelectorAll('.screen-row')].map(r => r.dataset.key);
            const interval = parseInt(document.getElementById('interval').value) || 180;
            fetch('/save', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{enabled, interval}})
            }}).then(r => r.json()).then(d => {{
                const toast = document.getElementById('toast');
                toast.textContent = d.message || 'Playlist saved!';
                toast.classList.add('show');
                setTimeout(() => toast.classList.remove('show'), 2500);
            }}).catch(() => alert('Save failed'));
        }}

        // Init numbering
        renumber();

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
            content_type = self.headers.get("Content-Type", "")
            if "json" in content_type:
                data = json.loads(body)
                enabled = data.get("enabled", [])
                interval = data.get("interval", 180)
            else:
                params = parse_qs(body)
                enabled = params.get("screens", [])
                interval = int(params.get("interval", [180])[0])
            interval = max(60, min(3600, int(interval)))
            save_config({"enabled": enabled, "interval": interval})
            print(f"[playlist] Saved: {len(enabled)} screens, {interval}s interval, order: {enabled}")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "message": f"Saved {len(enabled)} screens, {interval}s interval"}).encode())
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
