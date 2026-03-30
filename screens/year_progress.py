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

    # Title
    draw.text((WIDTH // 2, 140), str(now.year), fill=0, font=get_font(80, bold=True), anchor="mm")

    # Subtitle
    draw.text((WIDTH // 2, 220), f"Day {day_of_year} of {total_days}", fill=80, font=get_font(40), anchor="mm")

    # Big percentage
    draw.text((WIDTH // 2, 360), f"{pct * 100:.1f}%", fill=0, font=get_font(120, bold=True), anchor="mm")

    # Progress bar
    bar_x = 160
    bar_w = WIDTH - 320
    bar_y = 480
    bar_h = 60
    # Background
    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=bar_h // 2, fill=220)
    # Filled portion
    fill_w = int(bar_w * pct)
    if fill_w > bar_h:  # only draw if enough for rounded rect
        draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=bar_h // 2, fill=60)

    # Month markers below bar
    month_names = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
    for i, m in enumerate(month_names):
        mx = bar_x + int(bar_w * (i + 0.5) / 12)
        draw.text((mx, bar_y + bar_h + 25), m, fill=140, font=get_font(20), anchor="mt")

    # Days remaining
    days_left = total_days - day_of_year
    draw.text((WIDTH // 2, 640), f"{days_left} days remaining", fill=100, font=get_font(36), anchor="mm")

    # Weeks remaining
    weeks_left = days_left // 7
    draw.text((WIDTH // 2, 700), f"({weeks_left} weeks)", fill=140, font=get_font(28), anchor="mm")

    # Quarter info
    quarter = (now.month - 1) // 3 + 1
    quarter_start = datetime(now.year, (quarter - 1) * 3 + 1, 1)
    if quarter < 4:
        quarter_end = datetime(now.year, quarter * 3 + 1, 1)
    else:
        quarter_end = datetime(now.year + 1, 1, 1)
    q_pct = (now - quarter_start).days / (quarter_end - quarter_start).days * 100
    draw.text((WIDTH // 2, 800), f"Q{quarter}: {q_pct:.0f}% complete", fill=120, font=get_font(30), anchor="mm")

    _footer(draw, now_str())
    return img
