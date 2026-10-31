from .shared import *

# ── Element of the Day ────────────────────────────────────────────────

_ELEMENTS_URL = "https://raw.githubusercontent.com/hossain-khan/trmnl-elements-plugin/main/data-all.json"


def _fetch_elements():
    """Fetch periodic table elements JSON from GitHub."""
    r = requests.get(_ELEMENTS_URL, timeout=15)
    r.raise_for_status()
    return r.json().get("elements", [])


def render_element_of_day() -> Image.Image:
    """Render an Element of the Day screen (periodic table style)."""
    img = Image.new("L", (WIDTH, HEIGHT), 225)
    draw = ImageDraw.Draw(img)

    elements = _cache_fetch("periodic_elements", 604800, 2592000, _fetch_elements)

    el = _require(elements)[datetime.now().timetuple().tm_yday % len(elements)]
    img, draw = _canvas()
    draw.rectangle((50,50,1150,1550), outline=0, width=8)
    _fit_block(draw, el.get('atomic_number',''), (100,100,260,220), 140, True)
    _fit_block(draw, el.get('atomic_mass',''), (650,100,450,220), 86)
    _fit_block(draw, el['symbol'], (100,390,1000,610), 420, True)
    _fit_block(draw, el['name'], (100,1120,1000,190), 120, True)
    _fit_block(draw, el.get('category',''), (100,1360,1000,120), 56)
    return img
