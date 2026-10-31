from .shared import *

# ── 9. Dad Joke ─────────────────────────────────────────────────────

# Strip emoji and other pictographic codepoints the bundled font can't render
# (avoids "tofu" □ boxes on the e-ink panel).
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"  # symbols & pictographs, transport, supplemental
    "\U00002600-\U000027BF"  # misc symbols, dingbats
    "\U0001F1E6-\U0001F1FF"  # regional indicators (flags)
    "\U0000FE0F"             # variation selector-16
    "\U0000200D"             # zero-width joiner
    "]",
    flags=re.UNICODE,
)


def _strip_emoji(text: str) -> str:
    return _EMOJI_RE.sub("", text or "").strip()


def render_dad_joke() -> Image.Image:
    """Display a random dad joke from icanhazdadjoke.com."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    def _fetch():
        r = requests.get("https://icanhazdadjoke.com/",
                         headers={"Accept": "application/json"}, timeout=10)
        r.raise_for_status()
        return r.json().get("joke", "")

    result = _cache_fetch("joke", 0, 300, _fetch)  # always try fresh, 5min stale
    joke = result or "I told my wife she was drawing her eyebrows too high. She looked surprised."
    joke = _strip_emoji(joke)

    return _statement(joke)
