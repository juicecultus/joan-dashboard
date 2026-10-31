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
    img, draw = _canvas()
    draw.rounded_rectangle((130,50,1070,800),radius=35,outline=0,width=16)
    for x in (340,860):
        draw.line((x,25,x,160),fill=0,width=22)
    _poster_text(draw, event.get('time') or 'All day', (170,230,860,390), 350)
    _poster_text(draw,event['title'],(45,900,1110,650),500)
    return img
