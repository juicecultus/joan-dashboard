from .shared import *

# ── 5. Word of the Day ───────────────────────────────────────────────

# Curated list of interesting words for kids/family
WORD_LIST = [
    "ephemeral", "serendipity", "eloquent", "resilient", "benevolent",
    "ubiquitous", "pristine", "ambiguous", "diligent", "empathy",
    "tenacious", "vivacious", "whimsical", "zealous", "pragmatic",
    "luminous", "gregarious", "meticulous", "audacious", "candid",
    "enigma", "jubilant", "serene", "tenacity", "plethora",
    "conundrum", "ethereal", "magnanimous", "perspicacious", "sanguine",
    "idyllic", "quintessential", "fortuitous", "loquacious", "voracious",
    "ingenious", "pertinent", "sagacious", "effervescent", "intrepid",
    "cogent", "mellifluous", "panacea", "veracity", "aplomb",
    "ebullient", "fastidious", "halcyon", "incandescent", "juxtapose",
    "kaleidoscope", "labyrinth", "mercurial", "nonchalant", "oblivion",
    "paradox", "quixotic", "ravenous", "sublime", "transcend",
    "cacophony", "euphoria", "harbinger", "indelible", "kinetic",
    "languid", "mosaic", "nebulous", "oscillate", "pedagogy",
]


def render_word_of_day() -> Image.Image:
    """Word of the day with definition — vocabulary builder."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    # Pick word based on day of year (consistent all day)
    day_of_year = datetime.now().timetuple().tm_yday
    word = WORD_LIST[day_of_year % len(WORD_LIST)]

    definition = ""
    part_of_speech = ""
    phonetic = ""
    example = ""

    def _fetch():
        r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=5)
        r.raise_for_status()
        data = r.json()
        if data and isinstance(data, list):
            e = data[0]
            ph = e.get("phonetic", "")
            if not ph:
                for p in e.get("phonetics", []):
                    if p.get("text"):
                        ph = p["text"]
                        break
            pos, defn, ex = "", "", ""
            meanings = e.get("meanings", [])
            if meanings:
                pos = meanings[0].get("partOfSpeech", "")
                defs = meanings[0].get("definitions", [])
                if defs:
                    defn = defs[0].get("definition", "")
                    ex = defs[0].get("example", "")
            return {"phonetic": ph, "pos": pos, "definition": defn, "example": ex}
        raise ValueError("No word data")

    result = _cache_fetch(f"word:{word}", 43200, 86400, _fetch)  # 12h TTL, 24h stale
    if result:
        phonetic = result.get("phonetic", "")
        part_of_speech = result.get("pos", "")
        definition = result.get("definition", "")
        example = result.get("example", "")

    # Header
    draw.text((WIDTH // 2, 80), "Word of the Day", fill=120, font=get_font(32), anchor="mt")
    draw.line([(PAD, 130), (WIDTH - PAD, 130)], fill=200, width=1)

    # Word — large
    word_font = _fit_font_to_width(word.capitalize(), WIDTH - 200, 100, min_size=56, bold=True)
    draw.text((WIDTH // 2, 220), _truncate_text(word_font, word.capitalize(), WIDTH - 200),
              fill=0, font=word_font, anchor="mt")

    # Phonetic
    if phonetic:
        draw.text((WIDTH // 2, 340), phonetic, fill=120, font=get_font(36), anchor="mt")

    # Part of speech
    y = 400
    if part_of_speech:
        draw.text((WIDTH // 2, y), part_of_speech.lower(), fill=100, font=get_font(30, bold=True), anchor="mt")
        y += 50

    # Definition + example (larger + vertically centered block)
    draw.line([(PAD + 100, y), (WIDTH - PAD - 100, y)], fill=200, width=1)
    y += 30

    def_font = get_font(57)
    ex_font = get_font(45)
    max_def_w = WIDTH - 200
    max_ex_w = WIDTH - 240

    def_lines = _wrap_text(def_font, definition, max_def_w) if definition else []
    ex_lines = _wrap_text(ex_font, f'"{example}"', max_ex_w) if example else []

    def_h = int(57 * 1.35) * len(def_lines)
    ex_h = int(45 * 1.35) * len(ex_lines)
    total_h = def_h + (40 if def_lines and ex_lines else 0) + ex_h
    content_top = y
    content_bottom = HEIGHT - 120
    y = content_top + max(0, (content_bottom - content_top - total_h) // 2)

    for ln in def_lines:
        draw.text((WIDTH // 2, y), ln, fill=30, font=def_font, anchor="mt")
        y += int(57 * 1.35)

    if ex_lines:
        y += 40
        for ln in ex_lines:
            draw.text((WIDTH // 2, y), ln, fill=100, font=ex_font, anchor="mt")
            y += int(45 * 1.35)

    _footer(draw, now_str())
    return img
