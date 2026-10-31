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
    _require(proverbs)

    # Pick a proverb based on day-of-year so it rotates daily
    idx = datetime.now().timetuple().tm_yday % len(proverbs)
    proverb = proverbs[idx]
    english = proverb.get("translation", "")
    chinese = proverb.get("chinese", "")
    num = proverb.get("id", idx + 1)

    img, draw = _canvas()
    # Allow CJK characters to wrap into a large calligraphic block.
    _poster_text(draw, ' '.join(chinese), (50,40,WIDTH-100,830), 350, font_fn=_get_cjk_font)
    _poster_text(draw, english, (50,940,WIDTH-100,610), 230, False)
    return img
