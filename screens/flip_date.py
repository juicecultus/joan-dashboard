from .shared import *

# ── Flip Date ────────────────────────────────────────────────────────

def _draw_flip_panel(img, draw, x, y, w, h, text, font_size, radius=24):
    """Draw a single flip-calendar panel: black rounded rect, white text, hinge line."""
    # Black rounded rectangle
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=0, outline=80, width=2)
    # Horizontal hinge line through the middle
    mid_y = y + h // 2
    draw.line([(x, mid_y), (x + w, mid_y)], fill=60, width=2)
    # White text centered
    font = _fit_font_to_width(text, w - 40, font_size, min_size=max(24, font_size // 3), bold=True)
    draw.text((x + w // 2, y + h // 2), _truncate_text(font, text, w - 40), fill=255, font=font, anchor="mm")


def render_flip_date() -> Image.Image:
    """Render a flip-calendar date screen (day name, day number, month)."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    now = datetime.now()
    day_name = now.strftime("%A")      # e.g. "Sunday"
    day_num = str(now.day)             # e.g. "2"
    month_abbr = now.strftime("%b")    # e.g. "Mar"

    # Layout constants
    margin_x = 60
    gap = 30
    top_y = 80
    panel_w = WIDTH - margin_x * 2
    top_h = 540
    bottom_h = 820
    bottom_y = top_y + top_h + gap
    half_w = (panel_w - gap) // 2

    # Top panel: day name (full width)
    _draw_flip_panel(img, draw, margin_x, top_y, panel_w, top_h, day_name, 180)

    # Bottom-left: day number
    _draw_flip_panel(img, draw, margin_x, bottom_y, half_w, bottom_h, day_num, 260)

    # Bottom-right: month abbreviation
    right_x = margin_x + half_w + gap
    _draw_flip_panel(img, draw, right_x, bottom_y, half_w, bottom_h, month_abbr, 200)

    return img
