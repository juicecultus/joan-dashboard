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

    event = _select(events, 3600)
    img, draw = _canvas()
    _fit_block(draw, event['year'], (75, 93, 1050, 440), 280, True)
    _fit_block(draw, event['text'], (75, 587, 1050, 747), 106)
    _fit_block(draw, now.strftime("On %d %B"), (75, 1387, 1050, 133), 56)
    return img
