from .shared import *
from html.parser import HTMLParser


class _TrendingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.repos = []
        self.in_heading = False
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h2":
            self.in_heading = True
        if tag == "a" and self.in_heading:
            path = attrs.get("href", "").strip("/")
            if path.count("/") == 1:
                self.repos.append(path)
    def handle_endtag(self, tag):
        if tag == "h2":
            self.in_heading = False


def _fetch_github_trending():
    r = requests.get("https://github.com/trending", timeout=12)
    r.raise_for_status()
    parser = _TrendingParser()
    parser.feed(r.text)
    return _require(parser.repos)


def render_github_trending():
    repo = _select(_cache_fetch("github_v2", 3600, 43200, _fetch_github_trending))
    owner, name = repo.split("/", 1)
    return _statement(name.replace('-', ' '), owner + " / " + name + "\nTrending on GitHub")
