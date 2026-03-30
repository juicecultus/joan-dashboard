from .shared import *

# ── 15. Moon Phase ──────────────────────────────────────────────────

def _moon_phase(dt):
    """Calculate moon phase (0-29.53) using Conway's method.
    0 = new moon, ~7.4 = first quarter, ~14.8 = full moon, ~22.1 = last quarter."""
    year = dt.year
    month = dt.month
    day = dt.day
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = a // 4
    c = 2 - a + b
    e = int(365.25 * (year + 4716))
    f = int(30.6001 * (month + 1))
    jd = c + day + e + f - 1524.5
    days_since_new = (jd - 2451550.1) % 29.530588853
    return days_since_new


def _draw_moon(draw, cx, cy, radius, phase_days):
    """Draw a realistic moon at (cx, cy) with given radius and phase."""
    # phase_days: 0=new, ~14.8=full
    phase_pct = phase_days / 29.530588853  # 0 to 1

    # Draw the dark circle (base)
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=40)

    # Calculate illumination
    # 0 = new (dark), 0.5 = full (bright), 1 = new again
    if phase_pct <= 0.5:
        illumination = phase_pct * 2  # 0 to 1 (waxing)
    else:
        illumination = (1 - phase_pct) * 2  # 1 to 0 (waning)

    # Draw lit portion using vertical slices
    for y_off in range(-radius, radius + 1):
        # Width of the circle at this y
        x_half = math.sqrt(max(0, radius * radius - y_off * y_off))
        if x_half < 1:
            continue

        # Terminator x position
        term_x = x_half * (2 * illumination - 1)

        if phase_pct <= 0.5:
            # Waxing: lit from right
            x_start = int(cx + term_x)
            x_end = int(cx + x_half)
        else:
            # Waning: lit from left
            x_start = int(cx - x_half)
            x_end = int(cx + term_x)

        if x_end > x_start:
            draw.line([(x_start, cy + y_off), (x_end, cy + y_off)], fill=230, width=1)


def render_moon_phase() -> Image.Image:
    """Display current moon phase with a beautiful drawn moon."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)
    now = datetime.now()

    phase_days = _moon_phase(now)
    phase_pct = phase_days / 29.530588853

    # Phase name
    if phase_days < 1.85:
        name = "New Moon"
    elif phase_days < 5.53:
        name = "Waxing Crescent"
    elif phase_days < 9.22:
        name = "First Quarter"
    elif phase_days < 12.91:
        name = "Waxing Gibbous"
    elif phase_days < 16.61:
        name = "Full Moon"
    elif phase_days < 20.30:
        name = "Waning Gibbous"
    elif phase_days < 23.99:
        name = "Last Quarter"
    elif phase_days < 27.68:
        name = "Waning Crescent"
    else:
        name = "New Moon"

    illumination = abs(1 - 2 * phase_pct) if phase_pct > 0.5 else phase_pct * 2

    # Draw the moon — large and centered
    moon_r = 250
    moon_cy = 420
    _draw_moon(draw, WIDTH // 2, moon_cy, moon_r, phase_days)

    # Add subtle crater circles for realism
    craters = [(0.15, -0.3, 30), (-0.25, 0.1, 20), (0.1, 0.2, 25),
               (-0.15, -0.15, 15), (0.3, 0.05, 18), (-0.05, 0.35, 22)]
    for cx_f, cy_f, cr in craters:
        ccx = int(WIDTH // 2 + cx_f * moon_r)
        ccy = int(moon_cy + cy_f * moon_r)
        # Only draw craters on lit portion
        dist = math.sqrt(cx_f**2 + cy_f**2)
        if dist < 0.85:
            draw.ellipse([ccx - cr, ccy - cr, ccx + cr, ccy + cr], outline=200, width=1)

    # Title
    draw.text((WIDTH // 2, 80), "Moon Phase", fill=160, font=get_font(32), anchor="mm")

    # Phase name — large
    draw.text((WIDTH // 2, 760), name, fill=0, font=get_font(56, bold=True), anchor="mm")

    # Illumination percentage
    draw.text((WIDTH // 2, 830), f"{illumination * 100:.0f}% illuminated", fill=100, font=get_font(32), anchor="mm")

    # Day in cycle
    draw.text((WIDTH // 2, 880), f"Day {phase_days:.1f} of 29.5", fill=140, font=get_font(26), anchor="mm")

    # Next full/new moon
    if phase_days < 14.765:
        days_to_full = 14.765 - phase_days
        draw.text((WIDTH // 2, 940), f"Full moon in {days_to_full:.0f} days", fill=120, font=get_font(28), anchor="mm")
    else:
        days_to_new = 29.53 - phase_days
        draw.text((WIDTH // 2, 940), f"New moon in {days_to_new:.0f} days", fill=120, font=get_font(28), anchor="mm")

    _footer(draw, now.strftime("%A %d %B"))
    return img
