from .shared import *

# ── Bank Holidays (England & Wales) ─────────────────────────────────

def _fetch_bank_holidays():
    """Fetch UK bank holidays from gov.uk."""
    r = requests.get("https://www.gov.uk/bank-holidays.json", timeout=15)
    r.raise_for_status()
    data = r.json()
    return data.get("england-and-wales", {}).get("events", [])


def render_bank_holidays() -> Image.Image:
    """Render upcoming bank holidays for England & Wales."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    events = _cache_fetch("bank_holidays", 86400, 604800, _fetch_bank_holidays)

    # Header
    header_h = 100
    draw.rectangle([0, 0, WIDTH, header_h], fill=30)
    draw.text((PAD, header_h // 2), "Upcoming Bank Holidays",
              fill=240, font=get_font(48, bold=True), anchor="lm")
    draw.text((WIDTH - PAD, header_h // 2), "England & Wales",
              fill=160, font=get_font(26), anchor="rm")

    if not events:
        _centered_text(draw, HEIGHT // 2, "No bank holiday data available", 36, fill=100)
        _dashboard_footer(draw)
        return img

    today = datetime.now().date()
    upcoming = []
    for e in events:
        try:
            d = datetime.strptime(e["date"], "%Y-%m-%d").date()
            if d >= today:
                days_away = (d - today).days
                upcoming.append({"title": e["title"], "date": d, "days": days_away})
        except (ValueError, KeyError):
            continue

    upcoming.sort(key=lambda x: x["date"])
    upcoming = upcoming[:10]

    y = header_h + 40
    row_h = 85
    for i, hol in enumerate(upcoming):
        is_next = (i == 0)

        # Date column
        date_str = hol["date"].strftime("%a %-d %b %Y")
        date_font = get_font(30, bold=is_next)
        draw.text((PAD + 20, y), date_str, fill=120 if is_next else 140, font=date_font, anchor="lt")

        # Holiday name
        title_font = _fit_font_to_width(hol["title"], WIDTH - (PAD + 260) - PAD, 34, min_size=24, bold=is_next)
        draw.text((PAD + 240, y), _truncate_text(title_font, hol["title"], WIDTH - (PAD + 260) - PAD),
                  fill=0 if is_next else 40, font=title_font, anchor="lt")

        # Days away badge
        if hol["days"] == 0:
            badge = "TODAY"
        elif hol["days"] == 1:
            badge = "TOMORROW"
        else:
            badge = f"{hol['days']} days"
        badge_font = get_font(24, bold=True)
        bw = badge_font.getlength(badge) + 24
        bx = WIDTH - PAD - bw
        if hol["days"] <= 7:
            draw.rounded_rectangle([bx, y + 6, bx + bw, y + 42], radius=8, fill=40)
            draw.text((bx + bw // 2, y + 24), badge, fill=240, font=badge_font, anchor="mm")
        else:
            draw.text((WIDTH - PAD, y + 10), badge, fill=120, font=get_font(24), anchor="rt")

        # Separator
        if i < len(upcoming) - 1:
            draw.line([(PAD, y + row_h - 10), (WIDTH - PAD, y + row_h - 10)], fill=210, width=1)
        y += row_h

    _dashboard_footer(draw)
    return img
