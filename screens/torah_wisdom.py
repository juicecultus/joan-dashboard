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
    """Render a Daily Torah Wisdom screen with English + Hebrew."""
    img = Image.new("L", (WIDTH, HEIGHT), 225)
    draw = ImageDraw.Draw(img)

    verse = _cache_fetch("torah_wisdom", 43200, 172800, _fetch_torah_verse)

    # Footer bar
    footer_h = 60
    footer_y = HEIGHT - footer_h
    draw.rectangle([0, footer_y, WIDTH, HEIGHT], fill=180)
    draw.text((PAD, footer_y + footer_h // 2), "Daily Torah Wisdom",
              fill=30, font=get_font(28, bold=True), anchor="lm")

    if not verse:
        _centered_text(draw, HEIGHT // 2, "No verse available", 40, fill=80)
        return img

    en_text = verse.get("en", "")
    he_text = verse.get("he", "")
    ref_str = verse.get("ref", "")

    content_top = 28
    content_bottom = footer_y - 18
    content_height = content_bottom - content_top
    split_y = content_top + content_height // 2

    # Divider and language labels
    draw.line([(PAD, split_y), (WIDTH - PAD, split_y)], fill=150, width=2)
    draw.text((WIDTH // 2, content_top), "English", fill=80, font=get_font(24, bold=True), anchor="mt")
    draw.text((WIDTH // 2, split_y + 12), "Hebrew", fill=80, font=get_font(24, bold=True), anchor="mt")

    # English text in the top half
    en_block_top = content_top + 44
    en_block_height = max(20, split_y - en_block_top - 32)
    en_text = re.sub(r"\s+", " ", en_text).strip()
    if len(en_text) > 320:
        en_text = en_text[:317].rstrip() + "..."
    _draw_wrapped_block(
        draw,
        PAD,
        en_block_top,
        WIDTH - PAD * 2,
        en_block_height,
        en_text,
        34,
        bold=True,
        fill=30,
        rtl=False,
        max_lines=6,
    )
    if ref_str:
        draw.text((WIDTH // 2, split_y - 18), f"— {ref_str}", fill=85, font=get_font(22), anchor="mt")

    # Hebrew text in the bottom half
    if he_text:
        he_block_top = split_y + 42
        he_block_height = max(20, content_bottom - he_block_top - 12)
        if len(he_text) > 260:
            he_text = he_text[:257].rstrip() + "..."
        _draw_wrapped_block(
            draw,
            PAD,
            he_block_top,
            WIDTH - PAD * 2,
            he_block_height,
            he_text,
            36,
            bold=False,
            fill=55,
            rtl=True,
            max_lines=6,
        )

    return img
