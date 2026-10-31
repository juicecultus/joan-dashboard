from .shared import *
import xml.etree.ElementTree as ET


def _fetch_bbc_news():
    r = requests.get("https://feeds.bbci.co.uk/news/rss.xml", timeout=12)
    r.raise_for_status()
    articles = []
    for item in ET.fromstring(r.content).findall("./channel/item"):
        title = item.findtext("title")
        thumbnail = item.find("{http://search.yahoo.com/mrss/}thumbnail")
        if title:
            articles.append({"title": html.unescape(title), "image_link": thumbnail.get("url", "") if thumbnail is not None else ""})
    return _require(articles, "BBC feed empty")


def render_bbc_news():
    article = _select(_cache_fetch("bbc_rss", 900, 3600, _fetch_bbc_news))
    image = _image_url(article['image_link']) if article['image_link'] else None
    return _picture(image, article['title']) if image else _statement(article['title'])
