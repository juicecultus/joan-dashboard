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
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=0)

    # Draw lit portion using vertical slices
    for y_off in range(-radius, radius + 1):
        # Width of the circle at this y
        x_half = math.sqrt(max(0, radius * radius - y_off * y_off))
        if x_half < 1:
            continue

        # Terminator x position
        term_x = x_half * math.cos(2 * math.pi * phase_pct)

        if phase_pct <= 0.5:
            # Waxing: lit from right
            x_start = int(cx + term_x)
            x_end = int(cx + x_half)
        else:
            # Waning: lit from left
            x_start = int(cx - x_half)
            x_end = int(cx - term_x)

        if x_end > x_start:
            draw.line([(x_start, cy + y_off), (x_end, cy + y_off)], fill=255, width=1)


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

    illumination = (1-math.cos(2*math.pi*phase_pct))/2
    _draw_moon(draw, WIDTH//2, 610, 570, phase_days)
    draw.ellipse((30,40,1170,1180), outline=0, width=6)
    _poster_text(draw, name, (40,1240,WIDTH-80,210), 180)
    _poster_text(draw, f"{illumination*100:.0f}% lit", (40,1490,WIDTH-80,80), 90, False)
    return img
