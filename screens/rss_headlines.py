from .shared import *

# ── 12. RSS Headlines ───────────────────────────────────────────────

RSS_FEED_URL = os.environ.get("RSS_FEED_URL", "https://www.theverge.com/rss/index.xml")
RSS_FEED_NAME = os.environ.get("RSS_FEED_NAME", "The Verge")


def render_rss_headlines() -> Image.Image:
    """Display a single article from an RSS feed (hero image + full summary)."""
    from PIL import ImageOps

    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    def _fetch():
        import feedparser
        feed = feedparser.parse(RSS_FEED_URL)
        if not feed.entries:
            raise ValueError("Empty feed")
        return feed.entries[:12]

    def _wrap_text(font, text, max_width):
        words = text.split()
        lines = []
        line = ""
        for word in words:
            test = f"{line} {word}".strip()
            if font.getlength(test) > max_width:
                if line:
                    lines.append(line)
                line = word
            else:
                line = test
        if line:
            lines.append(line)
        return lines

    def _strip_html(text):
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        return " ".join(text.split()).strip()

    def _extract_img_url(text):
        if not text:
            return ""
        match = re.search(r"<img[^>]+src=\"([^\"]+)\"", text)
        if match:
            return match.group(1)
        match = re.search(r"<img[^>]+src='([^']+)'", text)
        if match:
            return match.group(1)
        return ""

    def _entry_image_url(entry):
        for media in entry.get("media_content", []):
            url = media.get("url")
            if url:
                return url
        for media in entry.get("media_thumbnail", []):
            url = media.get("url")
            if url:
                return url
        for link in entry.get("links", []):
            if link.get("rel") == "enclosure" and str(link.get("type", "")).startswith("image"):
                return link.get("href")
        html_src = _extract_img_url(entry.get("summary", "") or entry.get("description", ""))
        if html_src:
            return html_src
        page_url = entry.get("link")
        if page_url:
            def _load_page():
                r = requests.get(page_url, timeout=8, headers={"User-Agent": "JoanDashboard/1.0"})
                r.raise_for_status()
                return r.text

            page_html = _cache_fetch(f"rss_page:{hashlib.md5(page_url.encode()).hexdigest()}", 21600, 86400, _load_page)
            if page_html:
                match = re.search(r"property=\"og:image\" content=\"([^\"]+)\"", page_html)
                if match:
                    return match.group(1)
                match = re.search(r"property='og:image' content='([^']+)'", page_html)
                if match:
                    return match.group(1)
        return ""

    def _fetch_image(url):
        def _load():
            r = requests.get(url, timeout=8, headers={"User-Agent": "JoanDashboard/1.0"})
            r.raise_for_status()
            return Image.open(BytesIO(r.content)).convert("L")

        return _cache_fetch(f"rss_img:{hashlib.md5(url.encode()).hexdigest()}", 21600, 86400, _load)

    entries = _cache_fetch("rss", 600, 1800, _fetch) or []  # 10min TTL, 30min stale

    if not entries:
        draw.text((WIDTH // 2, HEIGHT // 2), "Could not load feed", fill=120, font=get_font(36), anchor="mm")
        _footer(draw, now_str())
        return img

    day_seed = int(datetime.now().strftime("%Y%m%d"))
    day_rng = random.Random(day_seed)
    entries = entries[:12]
    day_rng.shuffle(entries)
    slot = int(time.time() // 1800)  # rotate article every 30 minutes
    entry = entries[slot % len(entries)]

    title = html.unescape(entry.get("title", "Untitled"))
    summary = _strip_html(entry.get("summary", "") or entry.get("description", ""))
    author = entry.get("author", "")
    published = ""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        from time import mktime
        pub_dt = datetime.fromtimestamp(mktime(entry.published_parsed))
        published = pub_dt.strftime("%a %d %b · %H:%M")

    hero_h = 520
    hero_url = _entry_image_url(entry)
    if hero_url:
        hero = _fetch_image(hero_url)
        if hero:
            pw, ph = hero.size
            scale = max(WIDTH / pw, hero_h / ph)
            new_w, new_h = int(pw * scale), int(ph * scale)
            hero = hero.resize((new_w, new_h), Image.LANCZOS)
            left = (new_w - WIDTH) // 2
            top = (new_h - hero_h) // 2
            hero = hero.crop((left, top, left + WIDTH, top + hero_h))
            hero = ImageOps.autocontrast(hero, cutoff=2)
            img.paste(hero, (0, 0))
            draw.rectangle([(0, hero_h - 80), (WIDTH, hero_h)], fill=20)
            draw.text((PAD, hero_h - 65), RSS_FEED_NAME, fill=220, font=get_font(28, bold=True), anchor="lm")
    else:
        draw.rectangle([(0, 0), (WIDTH, hero_h)], fill=235)
        draw.text((WIDTH // 2, hero_h // 2), RSS_FEED_NAME, fill=120, font=get_font(36, bold=True), anchor="mm")

    y = hero_h + 30
    title_font = get_font(50, bold=True)
    max_w = WIDTH - PAD * 2
    title_lines = _wrap_text(title_font, title, max_w)
    for ln in title_lines[:3]:
        draw.text((PAD, y), ln, fill=0, font=title_font, anchor="lt")
        y += 64

    meta = " · ".join([t for t in [author, published] if t])
    if meta:
        draw.text((PAD, y + 5), meta, fill=120, font=get_font(26), anchor="lt")
        y += 50
    draw.line([(PAD, y), (WIDTH - PAD, y)], fill=210, width=1)
    y += 20

    summary_font = get_font(32)
    summary_lines = _wrap_text(summary_font, summary, max_w)
    for ln in summary_lines:
        if y > HEIGHT - 90:
            break
        draw.text((PAD, y), ln, fill=40, font=summary_font, anchor="lt")
        y += 42

    _footer(draw, now_str())
    return img
