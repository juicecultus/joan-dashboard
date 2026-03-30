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

    # Show up to 3 countdowns
    y = 120
    for i, (days, title, event_date) in enumerate(upcoming[:3]):
        if i == 0:
            # Main countdown — big
            if days == 1:
                day_text = "Tomorrow"
            else:
                day_text = f"{days} days"

            title_font = _fit_font_to_width(title, WIDTH - 200, 50, min_size=30, bold=True)
            draw.text((WIDTH // 2, y), _truncate_text(title_font, title, WIDTH - 200),
                      fill=0, font=title_font, anchor="mt")
            y += 80
            day_font = _fit_font_to_width(day_text, WIDTH - 200, 160, min_size=92, bold=True)
            draw.text((WIDTH // 2, y), day_text, fill=0, font=day_font, anchor="mt")
            y += 220
            date_font = _fit_font_to_width(event_date.strftime("%A, %d %B"), WIDTH - 200, 36, min_size=24)
            draw.text((WIDTH // 2, y), event_date.strftime("%A, %d %B"), fill=100, font=date_font, anchor="mt")
            y += 80
            draw.line([(PAD, y), (WIDTH - PAD, y)], fill=180, width=2)
            y += 40
        else:
            # Secondary countdowns — smaller
            label = "Tomorrow" if days == 1 else f"in {days} days"
            title_font = _fit_font_to_width(title, WIDTH - PAD * 2 - 180, 36, min_size=24)
            draw.text((PAD + 40, y), _truncate_text(title_font, title, WIDTH - PAD * 2 - 180),
                      fill=40, font=title_font, anchor="lt")
            label_font = _fit_font_to_width(label, 160, 36, min_size=24, bold=True)
            draw.text((WIDTH - PAD - 40, y), label, fill=0, font=label_font, anchor="rt")
            y += 60

    _footer(draw, now_str())
    return img
