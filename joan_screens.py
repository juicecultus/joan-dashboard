#!/usr/bin/env python3
"""Additional screens for Joan display playlist rotation.

Each render_* function returns a 1600x1200 grayscale PIL Image.
"""

import hashlib
import html
import json
import math
import os
import random
import re
import textwrap
import time
from datetime import datetime, timedelta
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFilter

# Reuse from main dashboard
from joan_dashboard import (
    WIDTH, HEIGHT, get_font, fetch_weather, fetch_week_events,
    WEATHER_LAT, WEATHER_LON, WEATHER_LOCATION,
)

PAD = 60  # generous padding for full-screen layouts


# ── Cache layer ──────────────────────────────────────────────────────
# Fresh-first: within TTL return cached; after TTL try fresh;
# on failure serve stale (up to max_stale). Never serve beyond max_stale.

_cache = {}  # key -> {"data": ..., "ts": float}


def _cache_fetch(key, ttl, max_stale, fetch_fn):
    """Cached fetch with stale fallback. Returns None if nothing available."""
    now = time.time()
    entry = _cache.get(key)
    if entry and (now - entry["ts"]) < ttl:
        return entry["data"]
    try:
        data = fetch_fn()
        _cache[key] = {"data": data, "ts": now}
        return data
    except Exception as e:
        print(f"[cache] '{key}' fetch failed: {e}")
        if entry and max_stale > 0 and (now - entry["ts"]) < max_stale:
            print(f"[cache] Serving stale '{key}' (age {int(now - entry['ts'])}s)")
            return entry["data"]
        return None


# ── Helpers ──────────────────────────────────────────────────────────

def _centered_text(draw, y, text, size, bold=False, fill=0, max_width=WIDTH - 120):
    """Draw text centered at y, wrapping if needed. Returns new y."""
    font = get_font(size, bold=bold)
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        line = ""
        for word in words:
            test = f"{line} {word}".strip()
            if font.getlength(test) > max_width:
                if line:
                    lines.append(line)
                line = word
            else:
                line = test
        if line:
            lines.append(line)
    line_h = int(size * 1.4)
    for line in lines:
        draw.text((WIDTH // 2, y), line, fill=fill, font=font, anchor="mt")
        y += line_h
    return y


def _footer(draw, text=""):
    """Draw a subtle footer at the bottom."""
    if text:
        draw.text((WIDTH // 2, HEIGHT - 36), text, fill=160, font=get_font(22), anchor="mm")


# ── 1. Daily Agenda ──────────────────────────────────────────────────

def render_daily_agenda() -> Image.Image:
    """Large-font view of today's schedule — easy to read across the room."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)
    now = datetime.now()

    # Header: day and date
    draw.text((WIDTH // 2, 60), now.strftime("%A"), fill=0, font=get_font(80, bold=True), anchor="mt")
    draw.text((WIDTH // 2, 150), now.strftime("%d %B %Y"), fill=80, font=get_font(40), anchor="mt")

    # Divider
    draw.line([(PAD, 210), (WIDTH - PAD, 210)], fill=180, width=2)

    # Fetch today's events
    week_events = fetch_week_events()
    today_key = now.strftime("%Y-%m-%d")
    events = week_events.get(today_key, [])

    y = 240
    if not events:
        draw.text((WIDTH // 2, HEIGHT // 2), "No events today", fill=120, font=get_font(50), anchor="mm")
    else:
        for ev in events:
            if y > HEIGHT - 100:
                break
            t = ev["time"] or ""
            title = ev["title"]

            if t:
                # Time in large bold
                draw.text((PAD + 20, y), t, fill=0, font=get_font(48, bold=True), anchor="lt")
                # Title next to time
                draw.text((PAD + 240, y), title[:50], fill=40, font=get_font(44), anchor="lt")
            else:
                # All-day event
                draw.text((PAD + 20, y), f"• {title[:55]}", fill=40, font=get_font(44), anchor="lt")

            y += 80
            # Subtle separator
            draw.line([(PAD + 20, y - 15), (WIDTH - PAD - 20, y - 15)], fill=220, width=1)

    _footer(draw, f"Today's Agenda — {WEATHER_LOCATION}")
    return img


# ── 2. Motivational Quote ────────────────────────────────────────────

def render_quote() -> Image.Image:
    """Daily motivational quote — centered, elegant layout."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    quote_text = "The only way to do great work is to love what you do."
    author = "Steve Jobs"

    def _fetch():
        r = requests.get("https://zenquotes.io/api/today", timeout=5)
        r.raise_for_status()
        data = r.json()
        if data and isinstance(data, list):
            return {"q": data[0].get("q", ""), "a": data[0].get("a", "")}
        raise ValueError("No quote data")

    result = _cache_fetch("quote", 21600, 86400, _fetch)  # 6h TTL, 24h stale
    if result:
        quote_text = result.get("q") or quote_text
        author = result.get("a") or author

    # Large opening quotation mark
    draw.text((PAD + 20, 200), "\u201c", fill=200, font=get_font(200), anchor="lt")

    # Quote text — centered
    y = _centered_text(draw, 350, quote_text, size=52, fill=20, max_width=WIDTH - 200)

    # Author
    draw.text((WIDTH // 2, y + 40), f"— {author}", fill=100, font=get_font(36, bold=True), anchor="mt")

    _footer(draw, now_str())
    return img


# ── 3. Countdown ─────────────────────────────────────────────────────

def render_countdown() -> Image.Image:
    """Show countdown to next notable upcoming event."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)
    now = datetime.now()

    # Fetch upcoming events and find the next future one
    week_events = fetch_week_events()
    today_key = now.strftime("%Y-%m-%d")
    upcoming = []

    for date_key, events in sorted(week_events.items()):
        if date_key <= today_key:
            continue
        for ev in events:
            try:
                event_date = datetime.strptime(date_key, "%Y-%m-%d")
                delta = (event_date.date() - now.date()).days
                upcoming.append((delta, ev["title"], event_date))
            except ValueError:
                pass

    if not upcoming:
        # Fallback: show days until end of month
        import calendar as cal_mod
        last_day = cal_mod.monthrange(now.year, now.month)[1]
        end_of_month = now.replace(day=last_day)
        delta = (end_of_month.date() - now.date()).days
        upcoming = [(delta, f"End of {now.strftime('%B')}", end_of_month)]

    upcoming.sort(key=lambda x: x[0])

    # Show up to 3 countdowns
    y = 120
    for i, (days, title, event_date) in enumerate(upcoming[:3]):
        if i == 0:
            # Main countdown — big
            if days == 1:
                day_text = "Tomorrow"
            else:
                day_text = f"{days} days"

            draw.text((WIDTH // 2, y), title[:40], fill=0, font=get_font(50, bold=True), anchor="mt")
            y += 80
            draw.text((WIDTH // 2, y), day_text, fill=0, font=get_font(160, bold=True), anchor="mt")
            y += 220
            draw.text((WIDTH // 2, y), event_date.strftime("%A, %d %B"), fill=100, font=get_font(36), anchor="mt")
            y += 80
            draw.line([(PAD, y), (WIDTH - PAD, y)], fill=180, width=2)
            y += 40
        else:
            # Secondary countdowns — smaller
            label = "Tomorrow" if days == 1 else f"in {days} days"
            draw.text((PAD + 40, y), f"{title[:45]}", fill=40, font=get_font(36), anchor="lt")
            draw.text((WIDTH - PAD - 40, y), label, fill=0, font=get_font(36, bold=True), anchor="rt")
            y += 60

    _footer(draw, now_str())
    return img


# ── 4. Family Photo ──────────────────────────────────────────────────

PHOTOS_DIR = os.environ.get("PHOTOS_DIR", os.path.join(os.path.dirname(__file__), "photos"))


def render_family_photo() -> Image.Image:
    """Display a random photo from PHOTOS_DIR — new photo each rotation.

    Set PHOTOS_DIR env var or drop images into the photos/ folder.
    On Pi, mount a network share (e.g. SMB) to /mnt/joan_photos.
    """
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    if not os.path.isdir(PHOTOS_DIR):
        os.makedirs(PHOTOS_DIR, exist_ok=True)

    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    photos = [f for f in os.listdir(PHOTOS_DIR) if os.path.splitext(f)[1].lower() in exts]
    print(f"[photo] PHOTOS_DIR={PHOTOS_DIR}  found {len(photos)} photos")

    if not photos:
        draw.text((WIDTH // 2, HEIGHT // 2 - 40), "Family Photos", fill=0, font=get_font(50, bold=True), anchor="mm")
        draw.text((WIDTH // 2, HEIGHT // 2 + 20), "Add photos to:", fill=120, font=get_font(30), anchor="mm")
        draw.text((WIDTH // 2, HEIGHT // 2 + 60), PHOTOS_DIR, fill=160, font=get_font(22), anchor="mm")
        return img

    photo_file = random.choice(photos)

    try:
        photo = Image.open(os.path.join(PHOTOS_DIR, photo_file))
        photo = photo.convert("L")

        # Resize to fill, maintaining aspect ratio, then center-crop
        pw, ph = photo.size
        scale = max(WIDTH / pw, HEIGHT / ph)
        new_w = int(pw * scale)
        new_h = int(ph * scale)
        photo = photo.resize((new_w, new_h), Image.LANCZOS)

        # Center crop
        left = (new_w - WIDTH) // 2
        top = (new_h - HEIGHT) // 2
        photo = photo.crop((left, top, left + WIDTH, top + HEIGHT))

        # Enhance contrast for e-ink
        from PIL import ImageOps
        photo = ImageOps.autocontrast(photo, cutoff=1)

        print(f"[photo] Rendered: {photo_file}")
        return photo
    except Exception as e:
        print(f"[photo] Failed to load {photo_file}: {e}")
        draw.text((WIDTH // 2, HEIGHT // 2), "Error loading photo", fill=80, font=get_font(40), anchor="mm")
        return img


# ── 5. Word of the Day ───────────────────────────────────────────────

# Curated list of interesting words for kids/family
WORD_LIST = [
    "ephemeral", "serendipity", "eloquent", "resilient", "benevolent",
    "ubiquitous", "pristine", "ambiguous", "diligent", "empathy",
    "tenacious", "vivacious", "whimsical", "zealous", "pragmatic",
    "luminous", "gregarious", "meticulous", "audacious", "candid",
    "enigma", "jubilant", "serene", "tenacity", "plethora",
    "conundrum", "ethereal", "magnanimous", "perspicacious", "sanguine",
    "idyllic", "quintessential", "fortuitous", "loquacious", "voracious",
    "ingenious", "pertinent", "sagacious", "effervescent", "intrepid",
    "cogent", "mellifluous", "panacea", "veracity", "aplomb",
    "ebullient", "fastidious", "halcyon", "incandescent", "juxtapose",
    "kaleidoscope", "labyrinth", "mercurial", "nonchalant", "oblivion",
    "paradox", "quixotic", "ravenous", "sublime", "transcend",
    "cacophony", "euphoria", "harbinger", "indelible", "kinetic",
    "languid", "mosaic", "nebulous", "oscillate", "pedagogy",
]


def render_word_of_day() -> Image.Image:
    """Word of the day with definition — vocabulary builder."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    # Pick word based on day of year (consistent all day)
    day_of_year = datetime.now().timetuple().tm_yday
    word = WORD_LIST[day_of_year % len(WORD_LIST)]

    definition = ""
    part_of_speech = ""
    phonetic = ""
    example = ""

    def _fetch():
        r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=5)
        r.raise_for_status()
        data = r.json()
        if data and isinstance(data, list):
            e = data[0]
            ph = e.get("phonetic", "")
            if not ph:
                for p in e.get("phonetics", []):
                    if p.get("text"):
                        ph = p["text"]
                        break
            pos, defn, ex = "", "", ""
            meanings = e.get("meanings", [])
            if meanings:
                pos = meanings[0].get("partOfSpeech", "")
                defs = meanings[0].get("definitions", [])
                if defs:
                    defn = defs[0].get("definition", "")
                    ex = defs[0].get("example", "")
            return {"phonetic": ph, "pos": pos, "definition": defn, "example": ex}
        raise ValueError("No word data")

    result = _cache_fetch(f"word:{word}", 43200, 86400, _fetch)  # 12h TTL, 24h stale
    if result:
        phonetic = result.get("phonetic", "")
        part_of_speech = result.get("pos", "")
        definition = result.get("definition", "")
        example = result.get("example", "")

    # Header
    draw.text((WIDTH // 2, 80), "Word of the Day", fill=120, font=get_font(32), anchor="mt")
    draw.line([(PAD, 130), (WIDTH - PAD, 130)], fill=200, width=1)

    # Word — large
    draw.text((WIDTH // 2, 220), word.capitalize(), fill=0, font=get_font(100, bold=True), anchor="mt")

    # Phonetic
    if phonetic:
        draw.text((WIDTH // 2, 340), phonetic, fill=120, font=get_font(36), anchor="mt")

    # Part of speech
    y = 400
    if part_of_speech:
        draw.text((WIDTH // 2, y), part_of_speech.lower(), fill=100, font=get_font(30, bold=True), anchor="mt")
        y += 50

    # Definition
    draw.line([(PAD + 100, y), (WIDTH - PAD - 100, y)], fill=200, width=1)
    y += 30
    if definition:
        y = _centered_text(draw, y, definition, size=38, fill=30, max_width=WIDTH - 200)

    # Example sentence
    if example:
        y += 30
        y = _centered_text(draw, y, f'"{example}"', size=30, fill=100, max_width=WIDTH - 240)

    _footer(draw, now_str())
    return img


# ── 6. This Day in History ───────────────────────────────────────────

def render_this_day_in_history() -> Image.Image:
    """Show notable events that happened on this date in history."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)
    now = datetime.now()

    def _fetch():
        url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{now.month}/{now.day}"
        r = requests.get(url, headers={"User-Agent": "JoanDashboard/1.0"}, timeout=8)
        r.raise_for_status()
        evts = r.json().get("events", [])
        if not evts:
            raise ValueError("No events")
        return evts

    events = _cache_fetch(f"history:{now.month}/{now.day}", 43200, 86400, _fetch) or []

    # Header
    draw.text((WIDTH // 2, 60), "On This Day", fill=0, font=get_font(60, bold=True), anchor="mt")
    draw.text((WIDTH // 2, 135), now.strftime("%d %B"), fill=80, font=get_font(36), anchor="mt")
    draw.line([(PAD, 185), (WIDTH - PAD, 185)], fill=180, width=2)

    if not events:
        draw.text((WIDTH // 2, HEIGHT // 2), "Could not load historical events", fill=120, font=get_font(36), anchor="mm")
        return img

    # Pick 4 notable events (spread across centuries)
    events.sort(key=lambda e: e.get("year", 0))
    # Sample evenly from the list
    step = max(1, len(events) // 4)
    selected = events[::step][:4]

    y = 220
    for ev in selected:
        if y > HEIGHT - 120:
            break
        year = ev.get("year", "?")
        text = ev.get("text", "")
        if not text:
            continue

        # Year
        draw.text((PAD + 20, y), str(year), fill=0, font=get_font(40, bold=True), anchor="lt")

        # Event text (wrapped)
        font = get_font(30)
        max_w = WIDTH - PAD - 240
        words = text.split()
        lines = []
        line = ""
        for w in words:
            test = f"{line} {w}".strip()
            if font.getlength(test) > max_w:
                if line:
                    lines.append(line)
                line = w
            else:
                line = test
        if line:
            lines.append(line)

        tx = PAD + 200
        for ln in lines[:4]:  # max 4 lines per event
            draw.text((tx, y), ln, fill=40, font=font, anchor="lt")
            y += 38
        y += 30

        # Divider
        draw.line([(PAD + 100, y - 15), (WIDTH - PAD - 100, y - 15)], fill=220, width=1)

    _footer(draw, now_str())
    return img


# ── 7. Art Gallery ───────────────────────────────────────────────────

def render_art_gallery() -> Image.Image:
    """Display a random artwork from the Metropolitan Museum of Art."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    def _fetch():
        search_url = "https://collectionapi.metmuseum.org/public/collection/v1/search"
        r = requests.get(search_url, params={"hasImages": "true", "q": "painting portrait landscape"}, timeout=8)
        r.raise_for_status()
        ids = r.json().get("objectIDs", [])
        if not ids:
            raise ValueError("No artworks found")
        day_seed = int(datetime.now().strftime("%Y%m%d")) + 42
        random.seed(day_seed)
        obj_id = random.choice(ids[:500])
        random.seed()
        obj_url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{obj_id}"
        r = requests.get(obj_url, timeout=8)
        r.raise_for_status()
        obj = r.json()
        image_url = obj.get("primaryImageSmall") or obj.get("primaryImage")
        if not image_url:
            raise ValueError("No image available")
        r = requests.get(image_url, timeout=15)
        r.raise_for_status()
        return {
            "image_bytes": r.content,
            "title": obj.get("title", "Untitled"),
            "artist": obj.get("artistDisplayName", "Unknown artist"),
            "date": obj.get("objectDate", ""),
            "medium": obj.get("medium", ""),
        }

    data = _cache_fetch("art", 3600, 21600, _fetch)  # 1h TTL, 6h stale

    if data:
        art = Image.open(BytesIO(data["image_bytes"])).convert("L")
        title = data["title"]
        artist = data["artist"]
        date = data["date"]
        medium = data["medium"]

        art_area_h = HEIGHT - 200
        art_area_w = WIDTH - 120
        aw, ah = art.size
        scale = min(art_area_w / aw, art_area_h / ah)
        new_w = int(aw * scale)
        new_h = int(ah * scale)
        art = art.resize((new_w, new_h), Image.LANCZOS)

        x = (WIDTH - new_w) // 2
        y = (art_area_h - new_h) // 2 + 20
        img.paste(art, (x, y))

        cap_y = HEIGHT - 170
        draw.line([(PAD, cap_y - 10), (WIDTH - PAD, cap_y - 10)], fill=200, width=1)
        draw.text((WIDTH // 2, cap_y), title[:60], fill=0, font=get_font(32, bold=True), anchor="mt")
        caption_line2 = artist
        if date:
            caption_line2 += f", {date}"
        draw.text((WIDTH // 2, cap_y + 42), caption_line2[:70], fill=80, font=get_font(26), anchor="mt")
        if medium:
            draw.text((WIDTH // 2, cap_y + 74), medium[:80], fill=120, font=get_font(22), anchor="mt")
        draw.text((WIDTH // 2, HEIGHT - 30), "The Metropolitan Museum of Art", fill=180, font=get_font(18), anchor="mm")
    else:
        draw.text((WIDTH // 2, HEIGHT // 2 - 20), "Art Gallery", fill=0, font=get_font(50, bold=True), anchor="mm")
        draw.text((WIDTH // 2, HEIGHT // 2 + 40), "Could not load artwork", fill=120, font=get_font(30), anchor="mm")

    return img


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
        for y in range(HEIGHT - 50, HEIGHT):
            for x in range(WIDTH):
                px = img.getpixel((x, y))
                img.putpixel((x, y), min(255, px + 80))
        draw.text((WIDTH // 2, HEIGHT - 25), now_str(), fill=60, font=get_font(22), anchor="mm")
    else:
        draw.text((WIDTH // 2, HEIGHT // 2 - 20), "Weather Radar", fill=0, font=get_font(50, bold=True), anchor="mm")
        draw.text((WIDTH // 2, HEIGHT // 2 + 40), "Could not load radar data", fill=120, font=get_font(30), anchor="mm")

    return img


# ── 9. Dad Joke ─────────────────────────────────────────────────────

def render_dad_joke() -> Image.Image:
    """Display a random dad joke from icanhazdadjoke.com."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    def _fetch():
        r = requests.get("https://icanhazdadjoke.com/",
                         headers={"Accept": "application/json"}, timeout=10)
        r.raise_for_status()
        return r.json().get("joke", "")

    result = _cache_fetch("joke", 0, 300, _fetch)  # always try fresh, 5min stale
    joke = result or "I told my wife she was drawing her eyebrows too high. She looked surprised."

    # Title
    draw.text((WIDTH // 2, 120), "Dad Joke", fill=160, font=get_font(36), anchor="mm")

    # Draw a small divider
    div_w = 200
    draw.line([(WIDTH // 2 - div_w // 2, 160), (WIDTH // 2 + div_w // 2, 160)], fill=180, width=2)

    # Joke text — large and centered
    y = _centered_text(draw, 240, joke, size=52, bold=False, fill=20, max_width=WIDTH - 200)

    # Emoji-style decoration at bottom
    draw.text((WIDTH // 2, HEIGHT - 100), "😄", fill=160, font=get_font(60), anchor="mm")

    _footer(draw, now_str())
    return img


# ── 10. Year Progress ───────────────────────────────────────────────

def render_year_progress() -> Image.Image:
    """Visual progress bar showing how far through the year we are."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)
    now = datetime.now()

    year_start = datetime(now.year, 1, 1)
    year_end = datetime(now.year + 1, 1, 1)
    total_days = (year_end - year_start).days
    day_of_year = (now - year_start).days + 1
    pct = day_of_year / total_days

    # Title
    draw.text((WIDTH // 2, 140), str(now.year), fill=0, font=get_font(80, bold=True), anchor="mm")

    # Subtitle
    draw.text((WIDTH // 2, 220), f"Day {day_of_year} of {total_days}", fill=80, font=get_font(40), anchor="mm")

    # Big percentage
    draw.text((WIDTH // 2, 360), f"{pct * 100:.1f}%", fill=0, font=get_font(120, bold=True), anchor="mm")

    # Progress bar
    bar_x = 160
    bar_w = WIDTH - 320
    bar_y = 480
    bar_h = 60
    # Background
    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=bar_h // 2, fill=220)
    # Filled portion
    fill_w = int(bar_w * pct)
    if fill_w > bar_h:  # only draw if enough for rounded rect
        draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=bar_h // 2, fill=60)

    # Month markers below bar
    month_names = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
    for i, m in enumerate(month_names):
        mx = bar_x + int(bar_w * (i + 0.5) / 12)
        draw.text((mx, bar_y + bar_h + 25), m, fill=140, font=get_font(20), anchor="mt")

    # Days remaining
    days_left = total_days - day_of_year
    draw.text((WIDTH // 2, 640), f"{days_left} days remaining", fill=100, font=get_font(36), anchor="mm")

    # Weeks remaining
    weeks_left = days_left // 7
    draw.text((WIDTH // 2, 700), f"({weeks_left} weeks)", fill=140, font=get_font(28), anchor="mm")

    # Quarter info
    quarter = (now.month - 1) // 3 + 1
    quarter_start = datetime(now.year, (quarter - 1) * 3 + 1, 1)
    if quarter < 4:
        quarter_end = datetime(now.year, quarter * 3 + 1, 1)
    else:
        quarter_end = datetime(now.year + 1, 1, 1)
    q_pct = (now - quarter_start).days / (quarter_end - quarter_start).days * 100
    draw.text((WIDTH // 2, 800), f"Q{quarter}: {q_pct:.0f}% complete", fill=120, font=get_font(30), anchor="mm")

    _footer(draw, now_str())
    return img


# ── 11. Maths Challenge ─────────────────────────────────────────────

def render_maths_challenge() -> Image.Image:
    """Daily maths puzzles for the kids — mix of operations and difficulty."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    # Title
    draw.text((WIDTH // 2, 80), "Maths Challenge", fill=0, font=get_font(50, bold=True), anchor="mm")
    draw.text((WIDTH // 2, 130), datetime.now().strftime("%A %d %B"), fill=120, font=get_font(28), anchor="mm")

    # Generate 8 problems of varying difficulty
    problems = []
    # Easy: addition/subtraction
    a, b = random.randint(10, 99), random.randint(10, 99)
    problems.append(f"{a} + {b} = ?")
    a, b = random.randint(30, 99), random.randint(10, 49)
    problems.append(f"{a} − {b} = ?")
    # Medium: multiplication
    a, b = random.randint(3, 12), random.randint(3, 12)
    problems.append(f"{a} × {b} = ?")
    a, b = random.randint(6, 15), random.randint(4, 9)
    problems.append(f"{a} × {b} = ?")
    # Harder: division (ensure clean division)
    b = random.randint(3, 12)
    a = b * random.randint(3, 15)
    problems.append(f"{a} ÷ {b} = ?")
    # Fractions
    n = random.randint(1, 5)
    d = random.choice([2, 3, 4, 5, 8, 10])
    n2 = random.randint(1, 5)
    problems.append(f"{n}/{d} + {n2}/{d} = ?")
    # Percentage
    pct = random.choice([10, 20, 25, 50, 75])
    val = random.choice([40, 60, 80, 100, 120, 200, 500])
    problems.append(f"{pct}% of {val} = ?")
    # Squared
    sq = random.randint(4, 15)
    problems.append(f"{sq}² = ?")

    random.shuffle(problems)

    # Draw problems in two columns
    col_x = [320, 960]
    start_y = 220
    row_h = 110

    for i, problem in enumerate(problems):
        col = i % 2
        row = i // 2
        x = col_x[col]
        y = start_y + row * row_h

        # Number circle
        draw.ellipse([x - 180, y - 20, x - 140, y + 20], outline=80, width=2)
        draw.text((x - 160, y), str(i + 1), fill=80, font=get_font(22, bold=True), anchor="mm")

        # Problem text
        draw.text((x - 110, y), problem, fill=20, font=get_font(40), anchor="lm")

    # Footer encouragement
    encouragements = [
        "Can you solve them all?", "No calculators allowed!",
        "Show your working!", "Time yourself!",
        "Beat yesterday's time!", "You've got this!",
    ]
    draw.text((WIDTH // 2, HEIGHT - 100), random.choice(encouragements), fill=140, font=get_font(30), anchor="mm")

    _footer(draw, now_str())
    return img


# ── 12. RSS Headlines ───────────────────────────────────────────────

RSS_FEED_URL = os.environ.get("RSS_FEED_URL", "https://www.theverge.com/rss/index.xml")
RSS_FEED_NAME = os.environ.get("RSS_FEED_NAME", "The Verge")


def render_rss_headlines() -> Image.Image:
    """Display a single article from an RSS feed (hero image + full summary)."""
    from PIL import ImageOps

    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    def _fetch():
        import feedparser
        feed = feedparser.parse(RSS_FEED_URL)
        if not feed.entries:
            raise ValueError("Empty feed")
        return feed.entries[:12]

    def _wrap_text(font, text, max_width):
        words = text.split()
        lines = []
        line = ""
        for word in words:
            test = f"{line} {word}".strip()
            if font.getlength(test) > max_width:
                if line:
                    lines.append(line)
                line = word
            else:
                line = test
        if line:
            lines.append(line)
        return lines

    def _strip_html(text):
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        return " ".join(text.split()).strip()

    def _extract_img_url(text):
        if not text:
            return ""
        match = re.search(r"<img[^>]+src=\"([^\"]+)\"", text)
        if match:
            return match.group(1)
        match = re.search(r"<img[^>]+src='([^']+)'", text)
        if match:
            return match.group(1)
        return ""

    def _entry_image_url(entry):
        for media in entry.get("media_content", []):
            url = media.get("url")
            if url:
                return url
        for media in entry.get("media_thumbnail", []):
            url = media.get("url")
            if url:
                return url
        for link in entry.get("links", []):
            if link.get("rel") == "enclosure" and str(link.get("type", "")).startswith("image"):
                return link.get("href")
        html_src = _extract_img_url(entry.get("summary", "") or entry.get("description", ""))
        if html_src:
            return html_src
        page_url = entry.get("link")
        if page_url:
            def _load_page():
                r = requests.get(page_url, timeout=8, headers={"User-Agent": "JoanDashboard/1.0"})
                r.raise_for_status()
                return r.text

            page_html = _cache_fetch(f"rss_page:{hashlib.md5(page_url.encode()).hexdigest()}", 21600, 86400, _load_page)
            if page_html:
                match = re.search(r"property=\"og:image\" content=\"([^\"]+)\"", page_html)
                if match:
                    return match.group(1)
                match = re.search(r"property='og:image' content='([^']+)'", page_html)
                if match:
                    return match.group(1)
        return ""

    def _fetch_image(url):
        def _load():
            r = requests.get(url, timeout=8, headers={"User-Agent": "JoanDashboard/1.0"})
            r.raise_for_status()
            return Image.open(BytesIO(r.content)).convert("L")

        return _cache_fetch(f"rss_img:{hashlib.md5(url.encode()).hexdigest()}", 21600, 86400, _load)

    entries = _cache_fetch("rss", 600, 1800, _fetch) or []  # 10min TTL, 30min stale

    if not entries:
        draw.text((WIDTH // 2, HEIGHT // 2), "Could not load feed", fill=120, font=get_font(36), anchor="mm")
        _footer(draw, now_str())
        return img

    slot = int(time.time() // 1800)  # rotate article every 30 minutes
    entry = entries[slot % len(entries)]

    title = html.unescape(entry.get("title", "Untitled"))
    summary = _strip_html(entry.get("summary", "") or entry.get("description", ""))
    author = entry.get("author", "")
    published = ""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        from time import mktime
        pub_dt = datetime.fromtimestamp(mktime(entry.published_parsed))
        published = pub_dt.strftime("%a %d %b · %H:%M")

    hero_h = 520
    hero_url = _entry_image_url(entry)
    if hero_url:
        hero = _fetch_image(hero_url)
        if hero:
            pw, ph = hero.size
            scale = max(WIDTH / pw, hero_h / ph)
            new_w, new_h = int(pw * scale), int(ph * scale)
            hero = hero.resize((new_w, new_h), Image.LANCZOS)
            left = (new_w - WIDTH) // 2
            top = (new_h - hero_h) // 2
            hero = hero.crop((left, top, left + WIDTH, top + hero_h))
            hero = ImageOps.autocontrast(hero, cutoff=2)
            img.paste(hero, (0, 0))
            draw.rectangle([(0, hero_h - 80), (WIDTH, hero_h)], fill=20)
            draw.text((PAD, hero_h - 65), RSS_FEED_NAME, fill=220, font=get_font(28, bold=True), anchor="lm")
    else:
        draw.rectangle([(0, 0), (WIDTH, hero_h)], fill=235)
        draw.text((WIDTH // 2, hero_h // 2), RSS_FEED_NAME, fill=120, font=get_font(36, bold=True), anchor="mm")

    y = hero_h + 30
    title_font = get_font(50, bold=True)
    max_w = WIDTH - PAD * 2
    title_lines = _wrap_text(title_font, title, max_w)
    for ln in title_lines[:3]:
        draw.text((PAD, y), ln, fill=0, font=title_font, anchor="lt")
        y += 64

    meta = " · ".join([t for t in [author, published] if t])
    if meta:
        draw.text((PAD, y + 5), meta, fill=120, font=get_font(26), anchor="lt")
        y += 50
    draw.line([(PAD, y), (WIDTH - PAD, y)], fill=210, width=1)
    y += 20

    summary_font = get_font(32)
    summary_lines = _wrap_text(summary_font, summary, max_w)
    for ln in summary_lines:
        if y > HEIGHT - 90:
            break
        draw.text((PAD, y), ln, fill=40, font=summary_font, anchor="lt")
        y += 42

    _footer(draw, now_str())
    return img


# ── 13. Stock Ticker ────────────────────────────────────────────────

STOCK_TICKERS = os.environ.get("STOCK_TICKERS", "^FTSE,^GSPC,AAPL,MSFT,GOOGL,AMZN").split(",")


def _fetch_stock_data(ticker):
    """Fetch current price and change from Yahoo Finance."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=1d"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        meta = data["chart"]["result"][0]["meta"]
        price = meta["regularMarketPrice"]
        prev_close = meta.get("chartPreviousClose", meta.get("previousClose", price))
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
        return {
            "ticker": ticker,
            "name": _ticker_name(ticker),
            "price": price,
            "change": change,
            "change_pct": change_pct,
            "currency": meta.get("currency", "USD"),
        }
    except Exception as e:
        print(f"[stock] Failed to fetch {ticker}: {e}")
        return None


def _ticker_name(ticker):
    """Friendly names for common tickers."""
    names = {
        "^FTSE": "FTSE 100", "^GSPC": "S&P 500", "^DJI": "Dow Jones",
        "^IXIC": "NASDAQ", "^N225": "Nikkei 225",
        "AAPL": "Apple", "MSFT": "Microsoft", "GOOGL": "Alphabet",
        "AMZN": "Amazon", "TSLA": "Tesla", "META": "Meta",
        "NVDA": "NVIDIA", "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum",
    }
    return names.get(ticker, ticker)


def render_stock_ticker() -> Image.Image:
    """Display stock prices and daily changes."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    # Header
    draw.text((WIDTH // 2, 70), "Markets", fill=0, font=get_font(50, bold=True), anchor="mm")
    draw.text((WIDTH // 2, 120), datetime.now().strftime("%A %d %B %H:%M"), fill=140, font=get_font(26), anchor="mm")
    draw.line([(PAD, 155), (WIDTH - PAD, 155)], fill=200, width=2)

    def _fetch_all():
        results = []
        for ticker in STOCK_TICKERS:
            d = _fetch_stock_data(ticker.strip())
            if d:
                results.append(d)
        if not results:
            raise ValueError("No stock data")
        return results

    stocks = _cache_fetch("stocks", 300, 1800, _fetch_all) or []  # 5min TTL, 30min stale

    if not stocks:
        draw.text((WIDTH // 2, HEIGHT // 2), "Could not load market data", fill=120, font=get_font(36), anchor="mm")
        _footer(draw, now_str())
        return img

    y = 190
    row_h = (HEIGHT - 280) // min(len(stocks), 8)
    row_h = min(row_h, 120)

    for s in stocks:
        # Ticker name
        draw.text((PAD + 20, y), s["name"], fill=0, font=get_font(34, bold=True), anchor="lt")

        # Price
        if s["currency"] == "GBp":
            price_str = f"{s['price']:,.0f}p"
        elif s["currency"] == "GBP":
            price_str = f"£{s['price']:,.2f}"
        elif s["currency"] == "USD":
            price_str = f"${s['price']:,.2f}"
        elif s["currency"] == "EUR":
            price_str = f"€{s['price']:,.2f}"
        else:
            price_str = f"{s['price']:,.2f}"

        draw.text((WIDTH - PAD - 20, y), price_str, fill=0, font=get_font(34, bold=True), anchor="rt")

        # Change line
        arrow = "▲" if s["change"] >= 0 else "▼"
        change_str = f"{arrow} {abs(s['change']):,.2f} ({abs(s['change_pct']):.2f}%)"
        fill = 40 if s["change"] >= 0 else 80
        draw.text((PAD + 20, y + 42), s["ticker"], fill=160, font=get_font(22), anchor="lt")
        draw.text((WIDTH - PAD - 20, y + 42), change_str, fill=fill, font=get_font(26), anchor="rt")

        y += row_h

        if y > HEIGHT - 80:
            break

    _footer(draw, now_str())
    return img


# ── 14. Google Tasks Todo ───────────────────────────────────────────

def render_todo_list() -> Image.Image:
    """Full-screen Google Tasks view — large, readable, standalone."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    from joan_dashboard import get_google_creds

    # Header
    draw.text((WIDTH // 2, 70), "To Do", fill=0, font=get_font(56, bold=True), anchor="mm")
    draw.text((WIDTH // 2, 125), datetime.now().strftime("%A %d %B"), fill=140, font=get_font(28), anchor="mm")
    draw.line([(PAD, 160), (WIDTH - PAD, 160)], fill=200, width=2)

    def _fetch():
        creds = get_google_creds()
        if not creds:
            raise ValueError("No Google credentials")
        from googleapiclient.discovery import build
        service = build("tasks", "v1", credentials=creds)
        tasklists = service.tasklists().list(maxResults=10).execute().get("items", [])
        items = []
        for tl in tasklists:
            result = service.tasks().list(
                tasklist=tl["id"], showCompleted=False, maxResults=20
            ).execute()
            for t in result.get("items", []):
                if t.get("title", "").strip():
                    due = ""
                    if t.get("due"):
                        try:
                            due_dt = datetime.fromisoformat(t["due"].rstrip("Z"))
                            due = due_dt.strftime("%d %b")
                        except Exception:
                            pass
                    items.append({"title": t["title"], "due": due, "list": tl.get("title", "")})
        return items

    tasks = _cache_fetch("todo_all", 120, 1800, _fetch) or []  # 2min TTL, 30min stale

    if not tasks:
        draw.text((WIDTH // 2, HEIGHT // 2), "No tasks!", fill=120, font=get_font(44), anchor="mm")
        draw.text((WIDTH // 2, HEIGHT // 2 + 60), "All caught up ✓", fill=160, font=get_font(30), anchor="mm")
        _footer(draw, now_str())
        return img

    dy = 195
    LINE_H = 56
    BX = PAD + 20  # box left edge (same as dashboard B_L)

    for task in tasks[:14]:  # max 14 tasks for screen space
        # Exact same checkbox rendering as main dashboard
        box_top = dy + (LINE_H - 24) // 2
        draw.rectangle([BX, box_top, BX + 24, box_top + 24], outline=60, width=2)
        title = task["title"]
        if len(title) > 55:
            title = title[:52] + "..."
        draw.text((BX + 36, dy + LINE_H // 2), title, fill=20, font=get_font(26), anchor="lm")

        if task["due"]:
            draw.text((WIDTH - PAD - 20, dy + LINE_H // 2), task["due"], fill=140, font=get_font(22), anchor="rm")

        dy += LINE_H
        if dy > HEIGHT - 80:
            break

    # Task count footer
    if len(tasks) > 14:
        draw.text((WIDTH // 2, HEIGHT - 70), f"+{len(tasks) - 14} more tasks", fill=160, font=get_font(24), anchor="mm")

    _footer(draw, now_str())
    return img


# ── 15. Moon Phase ──────────────────────────────────────────────────

def _moon_phase(dt):
    """Calculate moon phase (0-29.53) using Conway's method.
    0 = new moon, ~7.4 = first quarter, ~14.8 = full moon, ~22.1 = last quarter."""
    year = dt.year
    month = dt.month
    day = dt.day
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = a // 4
    c = 2 - a + b
    e = int(365.25 * (year + 4716))
    f = int(30.6001 * (month + 1))
    jd = c + day + e + f - 1524.5
    days_since_new = (jd - 2451550.1) % 29.530588853
    return days_since_new


def _draw_moon(draw, cx, cy, radius, phase_days):
    """Draw a realistic moon at (cx, cy) with given radius and phase."""
    # phase_days: 0=new, ~14.8=full
    phase_pct = phase_days / 29.530588853  # 0 to 1

    # Draw the dark circle (base)
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=40)

    # Calculate illumination
    # 0 = new (dark), 0.5 = full (bright), 1 = new again
    if phase_pct <= 0.5:
        illumination = phase_pct * 2  # 0 to 1 (waxing)
    else:
        illumination = (1 - phase_pct) * 2  # 1 to 0 (waning)

    # Draw lit portion using vertical slices
    for y_off in range(-radius, radius + 1):
        # Width of the circle at this y
        x_half = math.sqrt(max(0, radius * radius - y_off * y_off))
        if x_half < 1:
            continue

        # Terminator x position
        term_x = x_half * (2 * illumination - 1)

        if phase_pct <= 0.5:
            # Waxing: lit from right
            x_start = int(cx + term_x)
            x_end = int(cx + x_half)
        else:
            # Waning: lit from left
            x_start = int(cx - x_half)
            x_end = int(cx + term_x)

        if x_end > x_start:
            draw.line([(x_start, cy + y_off), (x_end, cy + y_off)], fill=230, width=1)


def render_moon_phase() -> Image.Image:
    """Display current moon phase with a beautiful drawn moon."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)
    now = datetime.now()

    phase_days = _moon_phase(now)
    phase_pct = phase_days / 29.530588853

    # Phase name
    if phase_days < 1.85:
        name = "New Moon"
    elif phase_days < 5.53:
        name = "Waxing Crescent"
    elif phase_days < 9.22:
        name = "First Quarter"
    elif phase_days < 12.91:
        name = "Waxing Gibbous"
    elif phase_days < 16.61:
        name = "Full Moon"
    elif phase_days < 20.30:
        name = "Waning Gibbous"
    elif phase_days < 23.99:
        name = "Last Quarter"
    elif phase_days < 27.68:
        name = "Waning Crescent"
    else:
        name = "New Moon"

    illumination = abs(1 - 2 * phase_pct) if phase_pct > 0.5 else phase_pct * 2

    # Draw the moon — large and centered
    moon_r = 250
    moon_cy = 420
    _draw_moon(draw, WIDTH // 2, moon_cy, moon_r, phase_days)

    # Add subtle crater circles for realism
    craters = [(0.15, -0.3, 30), (-0.25, 0.1, 20), (0.1, 0.2, 25),
               (-0.15, -0.15, 15), (0.3, 0.05, 18), (-0.05, 0.35, 22)]
    for cx_f, cy_f, cr in craters:
        ccx = int(WIDTH // 2 + cx_f * moon_r)
        ccy = int(moon_cy + cy_f * moon_r)
        # Only draw craters on lit portion
        dist = math.sqrt(cx_f**2 + cy_f**2)
        if dist < 0.85:
            draw.ellipse([ccx - cr, ccy - cr, ccx + cr, ccy + cr], outline=200, width=1)

    # Title
    draw.text((WIDTH // 2, 80), "Moon Phase", fill=160, font=get_font(32), anchor="mm")

    # Phase name — large
    draw.text((WIDTH // 2, 760), name, fill=0, font=get_font(56, bold=True), anchor="mm")

    # Illumination percentage
    draw.text((WIDTH // 2, 830), f"{illumination * 100:.0f}% illuminated", fill=100, font=get_font(32), anchor="mm")

    # Day in cycle
    draw.text((WIDTH // 2, 880), f"Day {phase_days:.1f} of 29.5", fill=140, font=get_font(26), anchor="mm")

    # Next full/new moon
    if phase_days < 14.765:
        days_to_full = 14.765 - phase_days
        draw.text((WIDTH // 2, 940), f"Full moon in {days_to_full:.0f} days", fill=120, font=get_font(28), anchor="mm")
    else:
        days_to_new = 29.53 - phase_days
        draw.text((WIDTH // 2, 940), f"New moon in {days_to_new:.0f} days", fill=120, font=get_font(28), anchor="mm")

    _footer(draw, now.strftime("%A %d %B"))
    return img


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


# ── 17. Analogue Clock ──────────────────────────────────────────────

def render_clock_face() -> Image.Image:
    """Beautiful analogue clock face filling the 13\" display."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)
    now = datetime.now()

    cx, cy = WIDTH // 2, HEIGHT // 2 - 30
    radius = 480  # large clock filling the display

    # Outer ring
    draw.ellipse([cx - radius - 8, cy - radius - 8, cx + radius + 8, cy + radius + 8], outline=30, width=6)
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=60, width=3)

    # Hour markers
    for i in range(60):
        angle = math.radians(i * 6 - 90)
        if i % 5 == 0:
            # Hour marker — thick line
            inner = radius - 45
            outer = radius - 10
            w = 4
        else:
            # Minute marker — thin line
            inner = radius - 20
            outer = radius - 10
            w = 1
        x1 = cx + int(inner * math.cos(angle))
        y1 = cy + int(inner * math.sin(angle))
        x2 = cx + int(outer * math.cos(angle))
        y2 = cy + int(outer * math.sin(angle))
        draw.line([(x1, y1), (x2, y2)], fill=40, width=w)

    # Hour numbers
    for h in range(1, 13):
        angle = math.radians(h * 30 - 90)
        nx = cx + int((radius - 75) * math.cos(angle))
        ny = cy + int((radius - 75) * math.sin(angle))
        draw.text((nx, ny), str(h), fill=20, font=get_font(48, bold=True), anchor="mm")

    # Date window at 3 o'clock position
    date_x = cx + int(radius * 0.55)
    date_y = cy
    dw, dh = 60, 36
    draw.rectangle([date_x - dw // 2, date_y - dh // 2, date_x + dw // 2, date_y + dh // 2],
                    outline=140, width=1, fill=245)
    draw.text((date_x, date_y), str(now.day), fill=0, font=get_font(24, bold=True), anchor="mm")

    # Calculate hand angles
    hour = now.hour % 12
    minute = now.minute
    second = now.second

    hour_angle = math.radians((hour + minute / 60) * 30 - 90)
    min_angle = math.radians((minute + second / 60) * 6 - 90)
    sec_angle = math.radians(second * 6 - 90)

    # Hour hand — short and thick
    hour_len = radius * 0.55
    hx = cx + int(hour_len * math.cos(hour_angle))
    hy = cy + int(hour_len * math.sin(hour_angle))
    # Draw thick hand with a polygon
    perp = hour_angle + math.pi / 2
    hw = 10  # half-width
    points = [
        (cx + int(hw * math.cos(perp)), cy + int(hw * math.sin(perp))),
        (hx + int(3 * math.cos(perp)), hy + int(3 * math.sin(perp))),
        (hx - int(3 * math.cos(perp)), hy - int(3 * math.sin(perp))),
        (cx - int(hw * math.cos(perp)), cy - int(hw * math.sin(perp))),
    ]
    draw.polygon(points, fill=20)

    # Minute hand — long and medium
    min_len = radius * 0.8
    mx = cx + int(min_len * math.cos(min_angle))
    my = cy + int(min_len * math.sin(min_angle))
    perp = min_angle + math.pi / 2
    mw = 6
    points = [
        (cx + int(mw * math.cos(perp)), cy + int(mw * math.sin(perp))),
        (mx + int(2 * math.cos(perp)), my + int(2 * math.sin(perp))),
        (mx - int(2 * math.cos(perp)), my - int(2 * math.sin(perp))),
        (cx - int(mw * math.cos(perp)), cy - int(mw * math.sin(perp))),
    ]
    draw.polygon(points, fill=30)

    # Second hand — thin and long
    sec_len = radius * 0.85
    sx = cx + int(sec_len * math.cos(sec_angle))
    sy = cy + int(sec_len * math.sin(sec_angle))
    # Counterweight
    tail_len = radius * 0.15
    tx = cx - int(tail_len * math.cos(sec_angle))
    ty = cy - int(tail_len * math.sin(sec_angle))
    draw.line([(tx, ty), (sx, sy)], fill=60, width=2)

    # Center cap
    draw.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=20)
    draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=60)

    # Branding
    draw.text((cx, cy + radius * 0.3), "JOAN", fill=160, font=get_font(22, bold=True), anchor="mm")

    # Digital time below clock
    draw.text((WIDTH // 2, HEIGHT - 50), now.strftime("%H:%M:%S"), fill=140, font=get_font(30), anchor="mm")

    return img


# ── 18. Upcoming Movies ────────────────────────────────────────────

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")


def render_upcoming_movies() -> Image.Image:
    """Display upcoming movies from The Movie Database (TMDB)."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    def _fetch():
        if not TMDB_API_KEY:
            # Use the discover endpoint with no auth for trending (v3 needs key)
            raise ValueError("Set TMDB_API_KEY env var (free at themoviedb.org)")
        url = "https://api.themoviedb.org/3/movie/upcoming"
        params = {"api_key": TMDB_API_KEY, "language": "en-GB", "region": "GB", "page": 1}
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        results = r.json().get("results", [])
        if not results:
            raise ValueError("No upcoming movies")
        return results[:6]

    movies = _cache_fetch("movies", 3600, 21600, _fetch)  # 1h TTL, 6h stale

    # Header
    draw.text((WIDTH // 2, 70), "Upcoming Movies", fill=0, font=get_font(50, bold=True), anchor="mm")
    draw.text((WIDTH // 2, 120), "In Cinemas Soon", fill=140, font=get_font(26), anchor="mm")
    draw.line([(PAD, 150), (WIDTH - PAD, 150)], fill=200, width=2)

    if not movies:
        msg = "Set TMDB_API_KEY for movie listings" if not TMDB_API_KEY else "Could not load movies"
        draw.text((WIDTH // 2, HEIGHT // 2 - 20), msg, fill=120, font=get_font(30), anchor="mm")
        if not TMDB_API_KEY:
            draw.text((WIDTH // 2, HEIGHT // 2 + 30), "Free key at themoviedb.org", fill=160, font=get_font(24), anchor="mm")
        _footer(draw, now_str())
        return img

    # Try to load poster for the first movie
    poster_loaded = False
    first = movies[0]
    poster_path = first.get("poster_path", "")
    if poster_path:
        try:
            poster_url = f"https://image.tmdb.org/t/p/w342{poster_path}"
            r = requests.get(poster_url, timeout=10)
            if r.status_code == 200:
                poster = Image.open(BytesIO(r.content)).convert("L")
                # Scale poster to fit left side
                pw, ph = poster.size
                target_h = 500
                scale = target_h / ph
                poster = poster.resize((int(pw * scale), target_h), Image.LANCZOS)
                from PIL import ImageOps
                poster = ImageOps.autocontrast(poster, cutoff=2)
                img.paste(poster, (PAD + 20, 180))
                poster_loaded = True
                poster_w = int(pw * scale)
        except Exception as e:
            print(f"[movies] Poster failed: {e}")

    # First movie details
    text_x = PAD + poster_w + 40 if poster_loaded else PAD + 40
    text_max = WIDTH - text_x - PAD

    title = first.get("title", "Untitled")
    release = first.get("release_date", "")
    overview = first.get("overview", "")
    vote = first.get("vote_average", 0)

    y = 190
    # Title
    y = _centered_text(draw, y, title, size=38, bold=True, fill=0, max_width=text_max) if not poster_loaded else y
    if poster_loaded:
        font = get_font(38, bold=True)
        words = title.split()
        lines, line = [], ""
        for w in words:
            test = f"{line} {w}".strip()
            if font.getlength(test) > text_max:
                if line:
                    lines.append(line)
                line = w
            else:
                line = test
        if line:
            lines.append(line)
        for ln in lines[:2]:
            draw.text((text_x, y), ln, fill=0, font=font, anchor="lt")
            y += 50

    y += 10
    if release:
        try:
            rd = datetime.strptime(release, "%Y-%m-%d")
            draw.text((text_x if poster_loaded else PAD + 40, y), rd.strftime("%d %B %Y"), fill=80, font=get_font(28), anchor="lt")
            y += 40
        except ValueError:
            pass

    if vote:
        draw.text((text_x if poster_loaded else PAD + 40, y), f"★ {vote:.1f}/10", fill=60, font=get_font(28, bold=True), anchor="lt")
        y += 40

    # Overview (short)
    if overview:
        y += 10
        ox = text_x if poster_loaded else PAD + 40
        o_max = text_max if poster_loaded else WIDTH - PAD * 2 - 40
        font = get_font(24)
        words = overview.split()
        lines, line = [], ""
        for w in words:
            test = f"{line} {w}".strip()
            if font.getlength(test) > o_max:
                if line:
                    lines.append(line)
                line = w
            else:
                line = test
        if line:
            lines.append(line)
        max_lines = 6 if poster_loaded else 4
        for ln in lines[:max_lines]:
            draw.text((ox, y), ln, fill=100, font=font, anchor="lt")
            y += 30

    # Other upcoming movies list
    list_y = max(700, y + 20)
    draw.line([(PAD, list_y - 10), (WIDTH - PAD, list_y - 10)], fill=200, width=1)
    draw.text((PAD + 20, list_y + 5), "Also coming soon:", fill=140, font=get_font(24), anchor="lt")
    list_y += 45

    for m in movies[1:5]:
        t = m.get("title", "")
        rd = m.get("release_date", "")
        date_str = ""
        if rd:
            try:
                date_str = datetime.strptime(rd, "%Y-%m-%d").strftime("%d %b")
            except ValueError:
                pass
        draw.text((PAD + 40, list_y), f"• {t[:50]}", fill=40, font=get_font(26), anchor="lt")
        if date_str:
            draw.text((WIDTH - PAD - 20, list_y), date_str, fill=140, font=get_font(22), anchor="rt")
        list_y += 45

    _footer(draw, now_str())
    return img


# ── 19. Sleep Screen ────────────────────────────────────────────────

def render_sleep_screen(wake_time="07:00") -> Image.Image:
    """Beautiful sleep screen shown outside active hours — moon, stars, Zzz."""
    img = Image.new("L", (WIDTH, HEIGHT), 15)  # near-black background
    draw = ImageDraw.Draw(img)

    # Stars — scattered small dots and crosses
    rng = random.Random(42)  # fixed seed so stars don't flicker each render
    for _ in range(120):
        sx = rng.randint(40, WIDTH - 40)
        sy = rng.randint(40, HEIGHT - 40)
        brightness = rng.randint(60, 180)
        size = rng.choice([1, 1, 1, 2, 2, 3])
        if size <= 2:
            draw.ellipse([sx - size, sy - size, sx + size, sy + size], fill=brightness)
        else:
            # Cross-shaped star
            draw.line([(sx - size, sy), (sx + size, sy)], fill=brightness, width=1)
            draw.line([(sx, sy - size), (sx, sy + size)], fill=brightness, width=1)

    # A few brighter stars with rays
    for _ in range(8):
        sx = rng.randint(100, WIDTH - 100)
        sy = rng.randint(60, HEIGHT - 100)
        draw.ellipse([sx - 3, sy - 3, sx + 3, sy + 3], fill=220)
        for angle in [0, 45, 90, 135]:
            rad = math.radians(angle)
            ray = rng.randint(6, 12)
            draw.line([(sx - int(ray * math.cos(rad)), sy - int(ray * math.sin(rad))),
                       (sx + int(ray * math.cos(rad)), sy + int(ray * math.sin(rad)))],
                      fill=140, width=1)

    # Crescent moon — upper right area
    moon_cx, moon_cy, moon_r = WIDTH - 320, 250, 120
    draw.ellipse([moon_cx - moon_r, moon_cy - moon_r, moon_cx + moon_r, moon_cy + moon_r], fill=210)
    # Cut out crescent with overlapping dark circle
    cut_cx = moon_cx + 50
    cut_cy = moon_cy - 30
    draw.ellipse([cut_cx - moon_r, cut_cy - moon_r, cut_cx + moon_r, cut_cy + moon_r], fill=15)

    # Soft glow around moon
    for i in range(3):
        gr = moon_r + 15 + i * 12
        draw.ellipse([moon_cx - gr, moon_cy - gr, moon_cx + gr, moon_cy + gr], outline=25 + i * 3, width=1)

    # "Zzz" floating upward from center
    zzz_data = [
        (WIDTH // 2 + 60, HEIGHT // 2 - 80, 90, 100),
        (WIDTH // 2 + 140, HEIGHT // 2 - 180, 65, 130),
        (WIDTH // 2 + 200, HEIGHT // 2 - 260, 46, 155),
    ]
    for zx, zy, size, fill in zzz_data:
        draw.text((zx, zy), "Z", fill=fill, font=get_font(size, bold=True), anchor="mm")

    # Main text
    draw.text((WIDTH // 2, HEIGHT // 2 + 60), "Sleeping", fill=120, font=get_font(72, bold=True), anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 130), "Good night", fill=70, font=get_font(36), anchor="mm")

    # Subtle footer
    draw.text((WIDTH // 2, HEIGHT - 50), f"Back at {wake_time} · {datetime.now().strftime('%H:%M')}",
              fill=50, font=get_font(22), anchor="mm")

    return img


# ── Utility ──────────────────────────────────────────────────────────

def now_str():
    return datetime.now().strftime("%H:%M")


# ── Screen registry ──────────────────────────────────────────────────

ALL_SCREENS = {
    "agenda": render_daily_agenda,
    "quote": render_quote,
    "countdown": render_countdown,
    "photo": render_family_photo,
    "word": render_word_of_day,
    "history": render_this_day_in_history,
    "art": render_art_gallery,
    "radar": render_weather_radar,
    "joke": render_dad_joke,
    "progress": render_year_progress,
    "maths": render_maths_challenge,
    "rss": render_rss_headlines,
    "stocks": render_stock_ticker,
    "todo": render_todo_list,
    "moon": render_moon_phase,
    "airquality": render_air_quality,
    "clock": render_clock_face,
    "movies": render_upcoming_movies,
}
