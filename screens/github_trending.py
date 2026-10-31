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
    img, draw = _canvas()
    # A large branch diagram identifies the repository without a page heading.
    draw.line((400,170,400,760),fill=0,width=30)
    draw.line([(400,620),(800,370),(800,170)],fill=0,width=30,joint='curve')
    for x,y in [(400,170),(400,760),(800,170)]:
        draw.ellipse((x-70,y-70,x+70,y+70),fill=255,outline=0,width=26)
    _poster_text(draw,name.replace('-', ' '),(40,930,1120,450),420)
    _poster_text(draw,owner+' / GitHub',(40,1470,1120,100),110,False)
    return img
