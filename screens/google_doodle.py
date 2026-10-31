from .shared import *

# ── Google Doodle of the Day ─────────────────────────────────────────

def _fetch_google_doodle():
    """Fetch the latest Google Doodle by scraping doodles.google."""
    r = requests.get("https://doodles.google/", timeout=15, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    })
    r.raise_for_status()
    from html.parser import HTMLParser
    class Parser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.images = []
        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if tag == 'img' and 'hero-tag-carousel__collage-card-img' in a.get('class',''):
                self.images.append(a)
    parser = Parser()
    parser.feed(r.text)
    if not parser.images:
        raise ScreenUnavailable("Doodle markup changed")
    item = parser.images[0]
    from urllib.parse import urljoin
    return {'title': item.get('alt',''), 'image_url': urljoin(r.url, item.get('src') or item.get('data-src',''))}


def render_google_doodle() -> Image.Image:
    """Render a Google Doodle of the Day screen."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    # Key the cache by local day so the doodle is refreshed once per day.
    # This avoids reusing yesterday's doodle when the screen rotates daily.
    cache_key = f"google_doodle:{datetime.now().strftime('%Y-%m-%d')}"
    doodle = _cache_fetch(cache_key, 86400, 0, _fetch_google_doodle)

    _require(doodle)
    return _picture(_require(_image_url(doodle['image_url'])), doodle['title'])
