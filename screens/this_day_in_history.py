from .shared import *

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
    draw.text((WIDTH // 2, 135), now.strftime("%d %B"), fill=80, font=get_font(48), anchor="mt")
    draw.line([(PAD, 185), (WIDTH - PAD, 185)], fill=180, width=2)

    if not events:
        draw.text((WIDTH // 2, HEIGHT // 2), "Could not load historical events", fill=120, font=get_font(36), anchor="mm")
        return img

    # Pick 4 notable events (spread across centuries)
    events.sort(key=lambda e: e.get("year", 0))
    # Sample evenly from the list
    step = max(1, len(events) // 4)
    selected = events[::step][:4]

    y = 230
    for ev in selected:
        if y > HEIGHT - 120:
            break
        year = ev.get("year", "?")
        text = ev.get("text", "")
        if not text:
            continue

        # Year
        draw.text((PAD + 20, y), str(year), fill=0, font=get_font(60, bold=True), anchor="lt")

        # Event text (wrapped)
        font = get_font(45)
        max_w = WIDTH - PAD - 240
        lines = _wrap_text(font, text, max_w)
        line_h = max(int(_text_height(font, "Ag") * 1.2), 54)

        tx = PAD + 200
        for ln in lines[:3]:  # fewer lines with larger font
            draw.text((tx, y), ln, fill=40, font=font, anchor="lt")
            y += line_h
        y += 24

        # Divider
        draw.line([(PAD + 100, y - 15), (WIDTH - PAD - 100, y - 15)], fill=220, width=1)

    _footer(draw, now_str())
    return img
