from .shared import *

# ── Daily Torah Wisdom ───────────────────────────────────────────────

# Books of wisdom/proverbs in Tanakh for daily rotation
_TORAH_REFS = [
    "Proverbs.1", "Proverbs.2", "Proverbs.3", "Proverbs.4", "Proverbs.5",
    "Proverbs.6", "Proverbs.7", "Proverbs.8", "Proverbs.9", "Proverbs.10",
    "Proverbs.11", "Proverbs.12", "Proverbs.13", "Proverbs.14", "Proverbs.15",
    "Proverbs.16", "Proverbs.17", "Proverbs.18", "Proverbs.19", "Proverbs.20",
    "Proverbs.21", "Proverbs.22", "Proverbs.23", "Proverbs.24", "Proverbs.25",
    "Proverbs.26", "Proverbs.27", "Proverbs.28", "Proverbs.29", "Proverbs.30",
    "Proverbs.31",
    "Ecclesiastes.1", "Ecclesiastes.2", "Ecclesiastes.3", "Ecclesiastes.4",
    "Ecclesiastes.5", "Ecclesiastes.6", "Ecclesiastes.7", "Ecclesiastes.8",
    "Ecclesiastes.9", "Ecclesiastes.10", "Ecclesiastes.11", "Ecclesiastes.12",
    "Psalms.1", "Psalms.19", "Psalms.23", "Psalms.27", "Psalms.34",
    "Psalms.37", "Psalms.90", "Psalms.91", "Psalms.100", "Psalms.103",
    "Psalms.119", "Psalms.121", "Psalms.127", "Psalms.139", "Psalms.145",
    "Pirkei_Avot.1", "Pirkei_Avot.2", "Pirkei_Avot.3", "Pirkei_Avot.4",
    "Pirkei_Avot.5", "Pirkei_Avot.6",
]


def _fetch_torah_verse():
    """Fetch a daily Torah verse from Sefaria API."""
    # Pick chapter based on day of year
    day = datetime.now().timetuple().tm_yday
    chapter_ref = _TORAH_REFS[day % len(_TORAH_REFS)]
    # Pick a specific verse from the chapter
    url = f"https://www.sefaria.org/api/texts/{chapter_ref}?context=0"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()

    texts = data.get("text", [])
    he_texts = data.get("he", [])
    ref_base = data.get("ref", chapter_ref)

    if isinstance(texts, str):
        texts = [texts]
    if isinstance(he_texts, str):
        he_texts = [he_texts]

    if not texts:
        return None

    # Pick a verse based on day
    vidx = day % len(texts)

    def _clean_sefaria_text(raw_text: str) -> str:
        text = str(raw_text or "")
        text = re.sub(r"<sup class=\"footnote-marker\">.*?</sup><i class=\"footnote\">.*?</i>", "", text, flags=re.S)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
        text = re.sub(r"</span>\s*<span[^>]*>", " ", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        text = re.sub(r"[ \t\xa0]+", " ", text)
        text = re.sub(r"\s*\n\s*", "\n", text)
        text = re.sub(r"\n{2,}", "\n", text)
        return text.strip()

    en_text = _clean_sefaria_text(texts[vidx])
    he_text = _clean_sefaria_text(he_texts[vidx]) if vidx < len(he_texts) else ""
    verse_ref = f"{ref_base.rsplit('.', 1)[0] if '.' in ref_base else ref_base}:{vidx + 1}"

    return {"en": en_text, "he": he_text, "ref": verse_ref}


def render_torah_wisdom() -> Image.Image:
    """Render a Daily Torah Wisdom screen following the Word of the Day layout."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    verse = _cache_fetch("torah_wisdom", 43200, 172800, _fetch_torah_verse)

    if not verse:
        _centered_text(draw, HEIGHT // 2, "No verse available", 40, fill=80)
        _footer(draw, now_str())
        return img

    en_text = verse.get("en", "")
    he_text = verse.get("he", "")
    ref_str = verse.get("ref", "")

    # Header
    draw.text((WIDTH // 2, 80), "Daily Torah Wisdom", fill=120, font=get_font(32), anchor="mt")
    draw.line([(PAD, 130), (WIDTH - PAD, 130)], fill=200, width=1)

    # Reference — large (like the 'Word' in Word of Day)
    ref_font = _fit_font_to_width(ref_str, WIDTH - 200, 100, min_size=56, bold=True)
    draw.text((WIDTH // 2, 220), _truncate_text(ref_font, ref_str, WIDTH - 200),
              fill=0, font=ref_font, anchor="mt")

    # Divider line for content
    y = 360
    draw.line([(PAD + 100, y), (WIDTH - PAD - 100, y)], fill=200, width=1)
    y += 40

    # Content: English + Hebrew centered vertically in remaining space
    en_font = get_font(52, bold=True)
    he_font = _get_hebrew_font(56)
    
    max_w = WIDTH - 240
    en_lines = _wrap_text(en_font, en_text, max_w) if en_text else []
    he_lines = _wrap_text(he_font, he_text, max_w, rtl=True) if he_text else []

    en_h = int(52 * 1.3) * len(en_lines)
    he_h = int(56 * 1.3) * len(he_lines)
    gap = 60 if en_lines and he_lines else 0
    total_h = en_h + gap + he_h

    content_top = y
    content_bottom = HEIGHT - 120
    y = content_top + max(0, (content_bottom - content_top - total_h) // 2)

    # Draw English
    for ln in en_lines:
        draw.text((WIDTH // 2, y), ln, fill=30, font=en_font, anchor="mt")
        y += int(52 * 1.3)

    # Draw Hebrew (raqm shapes niqqud/cantillation when available)
    if he_lines:
        y += gap
        for ln in he_lines:
            _draw_text_intl(draw, (WIDTH // 2, y), ln, font=he_font, fill=60, anchor="mt", rtl=True)
            y += int(56 * 1.3)

    _footer(draw, now_str())
    return img
