#!/usr/bin/env python3
"""Additional screens for Joan display playlist rotation.

Each render_* function returns a 1600x1200 grayscale PIL Image.
"""

import hashlib
import json
import os
import random
import textwrap
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

    try:
        r = requests.get("https://zenquotes.io/api/today", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data and isinstance(data, list):
                quote_text = data[0].get("q", quote_text)
                author = data[0].get("a", author)
    except Exception as e:
        print(f"[quote] API failed, using fallback: {e}")

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

    try:
        r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data and isinstance(data, list):
                entry = data[0]
                phonetic = entry.get("phonetic", "")
                if not phonetic:
                    for p in entry.get("phonetics", []):
                        if p.get("text"):
                            phonetic = p["text"]
                            break
                meanings = entry.get("meanings", [])
                if meanings:
                    part_of_speech = meanings[0].get("partOfSpeech", "")
                    defs = meanings[0].get("definitions", [])
                    if defs:
                        definition = defs[0].get("definition", "")
                        example = defs[0].get("example", "")
    except Exception as e:
        print(f"[word] API failed: {e}")

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

    events = []
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{now.month}/{now.day}"
        r = requests.get(url, headers={"User-Agent": "JoanDashboard/1.0"}, timeout=8)
        if r.status_code == 200:
            data = r.json()
            events = data.get("events", [])
    except Exception as e:
        print(f"[history] API failed: {e}")

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

    try:
        # Get a random artwork with an image
        # Use a curated search for paintings with images
        search_url = "https://collectionapi.metmuseum.org/public/collection/v1/search"
        r = requests.get(search_url, params={"hasImages": "true", "q": "painting portrait landscape"}, timeout=8)
        if r.status_code != 200:
            raise Exception(f"Search failed: {r.status_code}")

        ids = r.json().get("objectIDs", [])
        if not ids:
            raise Exception("No artworks found")

        # Pick based on day
        day_seed = int(datetime.now().strftime("%Y%m%d")) + 42
        random.seed(day_seed)
        obj_id = random.choice(ids[:500])  # top 500 results
        random.seed()

        # Fetch artwork details
        obj_url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{obj_id}"
        r = requests.get(obj_url, timeout=8)
        if r.status_code != 200:
            raise Exception(f"Object fetch failed: {r.status_code}")

        obj = r.json()
        image_url = obj.get("primaryImageSmall") or obj.get("primaryImage")
        title = obj.get("title", "Untitled")
        artist = obj.get("artistDisplayName", "Unknown artist")
        date = obj.get("objectDate", "")
        medium = obj.get("medium", "")

        if not image_url:
            raise Exception("No image available")

        # Download and process image
        r = requests.get(image_url, timeout=15)
        art = Image.open(BytesIO(r.content)).convert("L")

        # Scale to fit within the frame (leave room for caption)
        art_area_h = HEIGHT - 200  # bottom 200px for caption
        art_area_w = WIDTH - 120

        aw, ah = art.size
        scale = min(art_area_w / aw, art_area_h / ah)
        new_w = int(aw * scale)
        new_h = int(ah * scale)
        art = art.resize((new_w, new_h), Image.LANCZOS)

        # Center the artwork
        x = (WIDTH - new_w) // 2
        y = (art_area_h - new_h) // 2 + 20
        img.paste(art, (x, y))

        # Caption area
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
        return img

    except Exception as e:
        print(f"[art] Failed: {e}")
        draw.text((WIDTH // 2, HEIGHT // 2 - 20), "Art Gallery", fill=0, font=get_font(50, bold=True), anchor="mm")
        draw.text((WIDTH // 2, HEIGHT // 2 + 40), "Could not load artwork", fill=120, font=get_font(30), anchor="mm")
        return img


# ── 8. Weather Radar ─────────────────────────────────────────────────

def render_weather_radar() -> Image.Image:
    """Display weather radar map for your area from RainViewer."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    try:
        # Get latest radar timestamp
        r = requests.get("https://api.rainviewer.com/public/weather-maps.json", timeout=8)
        if r.status_code != 200:
            raise Exception(f"RainViewer API failed: {r.status_code}")

        data = r.json()
        radar = data.get("radar", {}).get("past", [])
        if not radar:
            raise Exception("No radar data available")

        latest = radar[-1]
        ts_path = latest["path"]

        # Build tile URL for our location
        # RainViewer uses standard web map tiles (z/x/y)
        lat = float(WEATHER_LAT)
        lon = float(WEATHER_LON)

        # Zoom level 7 gives a good regional view (~150km)
        zoom = 7
        import math as _math
        n = 2 ** zoom
        x_tile = int((lon + 180.0) / 360.0 * n)
        lat_rad = _math.radians(lat)
        y_tile = int((1.0 - _math.asinh(_math.tan(lat_rad)) / _math.pi) / 2.0 * n)

        # Download a 3x3 grid of tiles for a wider view
        tiles_img = Image.new("RGBA", (256 * 3, 256 * 3), (0, 0, 0, 0))

        for dx in range(-1, 2):
            for dy in range(-1, 2):
                tx = x_tile + dx
                ty = y_tile + dy
                tile_url = f"https://tilecache.rainviewer.com{ts_path}/256/{zoom}/{tx}/{ty}/2/1_1.png"
                try:
                    tr = requests.get(tile_url, timeout=5)
                    if tr.status_code == 200:
                        tile = Image.open(BytesIO(tr.content)).convert("RGBA")
                        tiles_img.paste(tile, ((dx + 1) * 256, (dy + 1) * 256))
                except Exception:
                    pass

        # Also get base map tiles (OpenStreetMap)
        base_img = Image.new("RGB", (256 * 3, 256 * 3), (240, 240, 240))
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                tx = x_tile + dx
                ty = y_tile + dy
                osm_url = f"https://tile.openstreetmap.org/{zoom}/{tx}/{ty}.png"
                try:
                    tr = requests.get(osm_url, headers={"User-Agent": "JoanDashboard/1.0"}, timeout=5)
                    if tr.status_code == 200:
                        tile = Image.open(BytesIO(tr.content)).convert("RGB")
                        base_img.paste(tile, ((dx + 1) * 256, (dy + 1) * 256))
                except Exception:
                    pass

        # Composite radar over base map
        base_img = base_img.convert("RGBA")
        base_img = Image.alpha_composite(base_img, tiles_img)

        # Convert to grayscale and resize to fill display
        radar_gray = base_img.convert("L")

        # Scale to fit display
        rw, rh = radar_gray.size
        scale = max(WIDTH / rw, HEIGHT / rh)
        new_w = int(rw * scale)
        new_h = int(rh * scale)
        radar_gray = radar_gray.resize((new_w, new_h), Image.LANCZOS)

        # Center crop
        left = (new_w - WIDTH) // 2
        top = (new_h - HEIGHT) // 2
        radar_gray = radar_gray.crop((left, top, left + WIDTH, top + HEIGHT))

        img = radar_gray

        # Overlay text
        draw = ImageDraw.Draw(img)
        # Semi-transparent header bar
        for y in range(60):
            for x in range(WIDTH):
                px = img.getpixel((x, y))
                img.putpixel((x, y), min(255, px + 80))

        draw.text((WIDTH // 2, 30), f"Weather Radar — {WEATHER_LOCATION}", fill=0, font=get_font(30, bold=True), anchor="mm")

        # Footer bar
        for y in range(HEIGHT - 50, HEIGHT):
            for x in range(WIDTH):
                px = img.getpixel((x, y))
                img.putpixel((x, y), min(255, px + 80))

        draw.text((WIDTH // 2, HEIGHT - 25), now_str(), fill=60, font=get_font(22), anchor="mm")
        return img

    except Exception as e:
        print(f"[radar] Failed: {e}")
        draw.text((WIDTH // 2, HEIGHT // 2 - 20), "Weather Radar", fill=0, font=get_font(50, bold=True), anchor="mm")
        draw.text((WIDTH // 2, HEIGHT // 2 + 40), "Could not load radar data", fill=120, font=get_font(30), anchor="mm")
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
}
