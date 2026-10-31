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

    _require(definition, "Dictionary definition unavailable")
    img, draw = _canvas()
    _fit_block(draw, word.capitalize(), (60, 160, 1080, 400), 190, True)
    _fit_block(draw, definition, (90, 653, 1020, 773), 100)
    return img
