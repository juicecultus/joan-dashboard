from .shared import *

# ── 1. Daily Agenda ──────────────────────────────────────────────────

def render_daily_agenda() -> Image.Image:
    """Large-font view of today's schedule — easy to read across the room."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)
    now = datetime.now()

    events = fetch_week_events().get(now.strftime("%Y-%m-%d"), [])
    future = [e for e in events if not e.get("time") or e["time"] >= now.strftime("%H:%M")]
    if not future:
        return _statement("Time to yourself", "No more events today")
    event = future[0]
    return _statement(event["title"], "Today " + (event.get("time") or "All day"))
