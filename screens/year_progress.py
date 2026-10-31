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
    _fit_block(draw, f"{pct*100:.0f}%", (60, 40, 1080, 533), 330, True)
    # Each dot represents one day of this year.
    for i in range(total_days):
        x, y = 88 + (i % 23)*45, 600 + (i//23)*42
        draw.ellipse((x,y,x+24,y+24), fill=0 if i < day_of_year else 255, outline=0, width=2)
    _fit_block(draw, f"{total_days-day_of_year} days left in {now.year}", (60, 1360, 1080, 147), 70)
    return img
