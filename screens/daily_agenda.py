from .shared import *

# ── 1. Daily Agenda ──────────────────────────────────────────────────

def render_daily_agenda() -> Image.Image:
    """Large-font view of today's schedule — easy to read across the room."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)
    now = datetime.now()

    # Header: day and date
    day_font = _fit_font_to_width(now.strftime("%A"), WIDTH - 120, 80, min_size=44, bold=True)
    date_font = _fit_font_to_width(now.strftime("%d %B %Y"), WIDTH - 120, 40, min_size=24)
    draw.text((WIDTH // 2, 60), now.strftime("%A"), fill=0, font=day_font, anchor="mt")
    draw.text((WIDTH // 2, 150), now.strftime("%d %B %Y"), fill=80, font=date_font, anchor="mt")

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
                title_font = get_font(44)
                title_max = WIDTH - (PAD + 240) - PAD
                draw.text((PAD + 240, y), _truncate_text(title_font, title, title_max),
                          fill=40, font=title_font, anchor="lt")
            else:
                # All-day event
                title_font = get_font(44)
                _draw_bullet(draw, PAD + 35, y + 22, 10, fill=40)
                draw.text((PAD + 60, y), _truncate_text(title_font, title, WIDTH - PAD * 2 - 60),
                          fill=40, font=title_font, anchor="lt")

            y += 80
            # Subtle separator
            draw.line([(PAD + 20, y - 15), (WIDTH - PAD - 20, y - 15)], fill=220, width=1)

    _footer(draw, f"Today's Agenda — {WEATHER_LOCATION}")
    return img
