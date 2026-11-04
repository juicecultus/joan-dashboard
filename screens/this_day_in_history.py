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
    _poster_text(draw, event['year'], (40,40,WIDTH-80,340), 420)
    _panel(draw,(25,410,1150,1165))
    _poster_text(draw, event['text'], (75,460,WIDTH-150,930), 190, False)
    _poster_text(draw, now.strftime("On %-d %B"), (50,1480,WIDTH-100,80), 85, False)
    return img
