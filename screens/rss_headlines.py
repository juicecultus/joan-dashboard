from .shared import *

RSS_FEED_URL = os.environ.get("RSS_FEED_URL", "https://www.theverge.com/rss/index.xml")
RSS_FEED_NAME = os.environ.get("RSS_FEED_NAME", "The Verge")


def _fetch_entries():
    import feedparser
    r = requests.get(RSS_FEED_URL, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return _require(feedparser.parse(r.content).entries[:12], "Empty RSS feed")


def render_rss_headlines():
    entry = _select(_cache_fetch("rss_v2", 600, 1800, _fetch_entries))
    title = html.unescape(entry.get('title',''))
    _require(title)
    media = entry.get('media_content') or entry.get('media_thumbnail') or []
    url = media[0].get('url') if media else None
    if not url:
        match = re.search(r'<img[^>]+src=[\'"]([^\'"]+)', entry.get('summary',''))
        url = html.unescape(match.group(1)) if match else None
    image = _image_url(url) if url else None
    return _picture(image, title) if image else _statement(title, RSS_FEED_NAME)
