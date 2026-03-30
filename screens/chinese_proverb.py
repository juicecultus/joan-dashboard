from .shared import *

# ── Chinese Proverbs ─────────────────────────────────────────────────

_PROVERBS_URL = "https://raw.githubusercontent.com/SteveBloX/trmnl-recipes/master/chinese-proverbs/proverbs-en.json"


def _fetch_proverbs():
    """Fetch Chinese proverbs JSON from GitHub."""
    r = requests.get(_PROVERBS_URL, timeout=15)
    r.raise_for_status()
    return r.json()


def _fit_wrapped_text(text, max_width, max_height, start_size, min_size, bold=False):
    """Fit wrapped English text within a bounding box."""
    for size in range(start_size, min_size - 1, -2):
        font = get_font(size, bold=bold)
        lines = []
        for paragraph in text.split("\n"):
            lines.extend(_wrap_text(font, paragraph, max_width) or [""])
        line_h = max(int(_text_height(font, "Ag") * 1.2), size + 4)
        if len(lines) * line_h <= max_height:
            return font, lines, line_h
    font = get_font(min_size, bold=bold)
    lines = []
    for paragraph in text.split("\n"):
        lines.extend(_wrap_text(font, paragraph, max_width) or [""])
    line_h = max(int(_text_height(font, "Ag") * 1.2), min_size + 4)
    return font, lines, line_h


def _fit_cjk_line(text, max_width, start_size, min_size):
    """Fit a single-line CJK string within a max width."""
    for size in range(start_size, min_size - 1, -2):
        font = _get_cjk_font(size)
        if _text_width(font, text) <= max_width:
            return font
    return _get_cjk_font(min_size)


def _fit_cjk_wrapped_text(text, max_width, max_height, start_size, min_size):
    """Fit wrapped CJK/Latin mixed text within a bounding box using a CJK font."""
    for size in range(start_size, min_size - 1, -2):
        font = _get_cjk_font(size)
        lines = []
        for paragraph in text.split("\n"):
            lines.extend(_wrap_text(font, paragraph, max_width) or [""])
        line_h = max(int(_text_height(font, "Ag") * 1.15), size + 2)
        if len(lines) * line_h <= max_height:
            return font, lines, line_h
    font = _get_cjk_font(min_size)
    lines = []
    for paragraph in text.split("\n"):
        lines.extend(_wrap_text(font, paragraph, max_width) or [""])
    line_h = max(int(_text_height(font, "Ag") * 1.15), min_size + 2)
    return font, lines, line_h


def render_chinese_proverb() -> Image.Image:
    """Render a Chinese Proverb screen following the Word of the Day layout."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    proverbs = _cache_fetch("chinese_proverbs", 86400, 604800, _fetch_proverbs)
    if not proverbs:
        _centered_text(draw, HEIGHT // 2, "No proverbs available", 40, fill=80)
        _footer(draw, now_str())
        return img

    # Pick a proverb based on day-of-year so it rotates daily
    idx = datetime.now().timetuple().tm_yday % len(proverbs)
    proverb = proverbs[idx]
    english = proverb.get("translation", "")
    chinese = proverb.get("chinese", "")
    num = proverb.get("id", idx + 1)

    # Header
    draw.text((WIDTH // 2, 80), "Chinese Proverb", fill=120, font=get_font(32), anchor="mt")
    draw.line([(PAD, 130), (WIDTH - PAD, 130)], fill=200, width=1)

    # English Translation — large (like the 'Word' in Word of Day)
    eng_font = _fit_font_to_width(english, WIDTH - 200, 80, min_size=44, bold=True)
    # We use a wrapped block here if it's long, but keep it centered around y=220
    eng_lines = _wrap_text(eng_font, english, WIDTH - 200)
    eng_line_h = int(eng_font.size * 1.2)
    eng_y = 220 - (len(eng_lines) * eng_line_h // 2) + 40
    for ln in eng_lines:
        draw.text((WIDTH // 2, eng_y), ln, fill=0, font=eng_font, anchor="mt")
        eng_y += eng_line_h

    # Divider line for Chinese text
    y = max(450, eng_y + 40)
    draw.line([(PAD + 100, y), (WIDTH - PAD - 100, y)], fill=200, width=1)
    y += 40

    # Chinese text — centered vertically in remaining space
    if chinese:
        ch_font, ch_lines, ch_line_h = _fit_cjk_wrapped_text(
            chinese,
            WIDTH - 240,
            HEIGHT - y - 120,
            56,
            24
        )
        
        total_ch_h = len(ch_lines) * ch_line_h
        content_top = y
        content_bottom = HEIGHT - 120
        ch_y = content_top + max(0, (content_bottom - content_top - total_ch_h) // 2)
        
        for ln in ch_lines:
            draw.text((WIDTH // 2, ch_y), ln, fill=60, font=ch_font, anchor="mt")
            ch_y += ch_line_h

    _footer(draw, f"Chinese Proverbs — #{num}")
    return img
