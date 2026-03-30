from .shared import *

# ── Flip Clock ───────────────────────────────────────────────────────

def render_flip_clock() -> Image.Image:
    """Render a flip clock screen with 4 digit panels + AM/PM."""
    img = Image.new("L", (WIDTH, HEIGHT), 215)
    draw = ImageDraw.Draw(img)

    now = datetime.now()
    hour_12 = now.hour % 12
    if hour_12 == 0:
        hour_12 = 12
    ampm = "AM" if now.hour < 12 else "PM"
    digits = f"{hour_12:02d}{now.minute:02d}"

    # 4 digit panels + smaller AM/PM panel
    panel_w = 200
    panel_h = 340
    gap = 24
    total_w = panel_w * 4 + gap * 3 + 100  # extra for AM/PM
    start_x = (WIDTH - total_w) // 2
    y = (HEIGHT - panel_h) // 2

    for i, digit in enumerate(digits):
        x = start_x + i * (panel_w + gap)
        # Shadow/border effect
        draw.rounded_rectangle([x - 3, y - 3, x + panel_w + 3, y + panel_h + 3],
                               radius=28, fill=140)
        # Black panel
        draw.rounded_rectangle([x, y, x + panel_w, y + panel_h],
                               radius=24, fill=10, outline=80, width=2)
        # Flip hinge line
        mid_y = y + panel_h // 2
        draw.line([(x, mid_y), (x + panel_w, mid_y)], fill=60, width=2)
        # Digit
        font = get_font(260, bold=True)
        draw.text((x + panel_w // 2, y + panel_h // 2), digit,
                  fill=240, font=font, anchor="mm")

    # AM/PM panel (smaller, to the right of last digit)
    ampm_x = start_x + 4 * (panel_w + gap)
    ampm_w = 90
    ampm_h = 80
    ampm_y = y + panel_h - ampm_h
    draw.rounded_rectangle([ampm_x - 2, ampm_y - 2, ampm_x + ampm_w + 2, ampm_y + ampm_h + 2],
                           radius=14, fill=140)
    draw.rounded_rectangle([ampm_x, ampm_y, ampm_x + ampm_w, ampm_y + ampm_h],
                           radius=12, fill=80)
    draw.text((ampm_x + ampm_w // 2, ampm_y + ampm_h // 2), ampm,
              fill=220, font=get_font(36, bold=True), anchor="mm")

    return img
