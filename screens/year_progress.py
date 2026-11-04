from .shared import *

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

    img, draw = _canvas()
    _poster_text(draw, f"{pct*100:.0f}%", (40,30,1120,370), 500)
    # Each dot represents one day of this year.
    for i in range(total_days):
        x, y = 42 + (i % 23)*49, 470 + (i//23)*58
        draw.ellipse((x,y,x+37,y+37), fill=0 if i < day_of_year else 255, outline=0, width=3)
    _panel(draw,(25,1430,1150,145))
    _poster_text(draw, f"{total_days-day_of_year} days left · {now.year}", (40,1460,1120,100), 110)
    return img
