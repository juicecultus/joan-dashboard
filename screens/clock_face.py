from .shared import *

# ── 17. Analogue Clock ──────────────────────────────────────────────

def render_clock_face() -> Image.Image:
    """Beautiful analogue clock face filling the 13\" display."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)
    now = datetime.now()

    cx, cy = WIDTH // 2, HEIGHT // 2 - 30
    radius = 480  # large clock filling the display

    # Outer ring
    draw.ellipse([cx - radius - 8, cy - radius - 8, cx + radius + 8, cy + radius + 8], outline=30, width=6)
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=60, width=3)

    # Hour markers
    for i in range(60):
        angle = math.radians(i * 6 - 90)
        if i % 5 == 0:
            # Hour marker — thick line
            inner = radius - 45
            outer = radius - 10
            w = 4
        else:
            # Minute marker — thin line
            inner = radius - 20
            outer = radius - 10
            w = 1
        x1 = cx + int(inner * math.cos(angle))
        y1 = cy + int(inner * math.sin(angle))
        x2 = cx + int(outer * math.cos(angle))
        y2 = cy + int(outer * math.sin(angle))
        draw.line([(x1, y1), (x2, y2)], fill=40, width=w)

    # Hour numbers
    for h in range(1, 13):
        angle = math.radians(h * 30 - 90)
        nx = cx + int((radius - 75) * math.cos(angle))
        ny = cy + int((radius - 75) * math.sin(angle))
        draw.text((nx, ny), str(h), fill=20, font=get_font(48, bold=True), anchor="mm")

    # Date window at 3 o'clock position
    date_x = cx + int(radius * 0.55)
    date_y = cy
    dw, dh = 60, 36
    draw.rectangle([date_x - dw // 2, date_y - dh // 2, date_x + dw // 2, date_y + dh // 2],
                    outline=140, width=1, fill=245)
    draw.text((date_x, date_y), str(now.day), fill=0, font=get_font(24, bold=True), anchor="mm")

    # Calculate hand angles
    hour = now.hour % 12
    minute = now.minute
    second = now.second

    hour_angle = math.radians((hour + minute / 60) * 30 - 90)
    min_angle = math.radians((minute + second / 60) * 6 - 90)
    sec_angle = math.radians(second * 6 - 90)

    # Hour hand — short and thick
    hour_len = radius * 0.55
    hx = cx + int(hour_len * math.cos(hour_angle))
    hy = cy + int(hour_len * math.sin(hour_angle))
    # Draw thick hand with a polygon
    perp = hour_angle + math.pi / 2
    hw = 10  # half-width
    points = [
        (cx + int(hw * math.cos(perp)), cy + int(hw * math.sin(perp))),
        (hx + int(3 * math.cos(perp)), hy + int(3 * math.sin(perp))),
        (hx - int(3 * math.cos(perp)), hy - int(3 * math.sin(perp))),
        (cx - int(hw * math.cos(perp)), cy - int(hw * math.sin(perp))),
    ]
    draw.polygon(points, fill=20)

    # Minute hand — long and medium
    min_len = radius * 0.8
    mx = cx + int(min_len * math.cos(min_angle))
    my = cy + int(min_len * math.sin(min_angle))
    perp = min_angle + math.pi / 2
    mw = 6
    points = [
        (cx + int(mw * math.cos(perp)), cy + int(mw * math.sin(perp))),
        (mx + int(2 * math.cos(perp)), my + int(2 * math.sin(perp))),
        (mx - int(2 * math.cos(perp)), my - int(2 * math.sin(perp))),
        (cx - int(mw * math.cos(perp)), cy - int(mw * math.sin(perp))),
    ]
    draw.polygon(points, fill=30)

    # Second hand — thin and long
    sec_len = radius * 0.85
    sx = cx + int(sec_len * math.cos(sec_angle))
    sy = cy + int(sec_len * math.sin(sec_angle))
    # Counterweight
    tail_len = radius * 0.15
    tx = cx - int(tail_len * math.cos(sec_angle))
    ty = cy - int(tail_len * math.sin(sec_angle))
    draw.line([(tx, ty), (sx, sy)], fill=60, width=2)

    # Center cap
    draw.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=20)
    draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=60)

    # Branding
    draw.text((cx, cy + radius * 0.3), "JOAN", fill=160, font=get_font(22, bold=True), anchor="mm")

    # Digital time below clock
    draw.text((WIDTH // 2, HEIGHT - 50), now.strftime("%H:%M:%S"), fill=140, font=get_font(30), anchor="mm")

    return img
