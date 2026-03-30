from .shared import *

# ── Chinese Proverbs ─────────────────────────────────────────────────

_PROVERBS_URL = "https://raw.githubusercontent.com/SteveBloX/trmnl-recipes/master/chinese-proverbs/proverbs-en.json"


def _fetch_proverbs():
    """Fetch Chinese proverbs JSON from GitHub."""
    r = requests.get(_PROVERBS_URL, timeout=15)
    r.raise_for_status()
    return r.json()


def render_chinese_proverb() -> Image.Image:
    """Render a Chinese Proverb screen (English + Chinese, footer bar)."""
    img = Image.new("L", (WIDTH, HEIGHT), 225)
    draw = ImageDraw.Draw(img)

    proverbs = _cache_fetch("chinese_proverbs", 86400, 604800, _fetch_proverbs)
    if not proverbs:
        _centered_text(draw, HEIGHT // 2, "No proverbs available", 40, fill=80)
        return img

    # Pick a proverb based on day-of-year so it rotates daily
    idx = datetime.now().timetuple().tm_yday % len(proverbs)
    proverb = proverbs[idx]
    english = proverb.get("translation", "")
    chinese = proverb.get("chinese", "")
    num = proverb.get("id", idx + 1)

    # English text — large, centered
    _centered_text(draw, HEIGHT // 2 - 80, english, 64, bold=True, fill=30, max_width=WIDTH - 200)

    # Chinese text — below English (needs CJK font)
    if chinese:
        ch_font = _get_cjk_font(42)
        draw.text((WIDTH // 2, HEIGHT // 2 + 40), chinese, fill=60, font=ch_font, anchor="mt")

    # Footer bar
    footer_h = 60
    footer_y = HEIGHT - footer_h
    draw.rectangle([0, footer_y, WIDTH, HEIGHT], fill=180)
    draw.text((PAD, footer_y + footer_h // 2), "Chinese Proverbs (Translated)",
              fill=40, font=get_font(26, bold=True), anchor="lm")
    draw.text((WIDTH - PAD, footer_y + footer_h // 2), f"#{num}",
              fill=40, font=get_font(26, bold=True), anchor="rm")

    return img
