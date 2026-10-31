from .shared import *

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

    days, title, event_date = upcoming[0]
    img, draw = _canvas()
    _fit_block(draw, "Today" if days == 0 else "Tomorrow" if days == 1 else str(days), (60, 107, 1080, 733), 440, True)
    _fit_block(draw, title if days <= 1 else "days until " + title, (90, 867, 1020, 373), 110, True)
    _fit_block(draw, event_date.strftime("%A %d %B"), (90, 1320, 1020, 147), 64)
    return img
