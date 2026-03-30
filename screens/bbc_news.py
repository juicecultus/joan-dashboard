from .shared import *

# ── BBC News ─────────────────────────────────────────────────────────

def _fetch_bbc_news():
    """Fetch BBC News articles."""
    r = requests.get("https://bbc-news-api.vercel.app/news?lang=english", timeout=15)
    r.raise_for_status()
    data = r.json()
    # Collect articles from multiple categories, dedup by title
    articles = []
    seen = set()
    for cat in ["Latest", "Watch", "Must watch", "More world news", "US & Canada news"]:
        for item in data.get(cat, []):
            title = item.get("title")
            if title and title not in seen:
                seen.add(title)
                articles.append(item)
    return articles


def render_bbc_news() -> Image.Image:
    """Render a BBC News screen with top stories and images."""
    img = Image.new("L", (WIDTH, HEIGHT), 245)
    draw = ImageDraw.Draw(img)

    articles = _cache_fetch("bbc_news", 1800, 7200, _fetch_bbc_news)

    # BBC NEWS header
    header_h = 90
    draw.rectangle([0, 0, WIDTH, header_h], fill=255)
    # BBC blocks
    bbc_font = get_font(52, bold=True)
    bx = PAD
    for letter in ["B", "B", "C"]:
        lw = bbc_font.getlength(letter) + 20
        draw.rectangle([bx, 14, bx + lw, 74], fill=0)
        draw.text((bx + lw // 2, 44), letter, fill=255, font=bbc_font, anchor="mm")
        bx += lw + 8
    draw.text((bx + 12, 44), "NEWS", fill=0, font=get_font(54, bold=True), anchor="lm")

    if not articles:
        _centered_text(draw, HEIGHT // 2, "No BBC News available", 48, fill=100)
        return img

    # Top 2 stories with images (side by side, 50% taller)
    top_y = header_h + 10
    img_h = 450
    img_w = (WIDTH - PAD * 2 - 20) // 2

    for i in range(min(2, len(articles))):
        art = articles[i]
        ax = PAD + i * (img_w + 20)

        # Fetch thumbnail
        thumb_url = art.get("image_link", "")
        if thumb_url:
            try:
                # Get higher res version
                thumb_url = thumb_url.replace("/240/", "/960/").replace("/160x90/", "/960x540/")
                tr = requests.get(thumb_url, timeout=10)
                tr.raise_for_status()
                thumb = Image.open(BytesIO(tr.content)).convert("L")
                thumb = thumb.resize((img_w, img_h), Image.LANCZOS)
                img.paste(thumb, (ax, top_y))
            except Exception:
                draw.rectangle([ax, top_y, ax + img_w, top_y + img_h], fill=180)

        # Title overlay at bottom of image
        title = art.get("title", "")
        if title:
            # Dark gradient overlay area
            overlay_h = 140
            oy = top_y + img_h - overlay_h
            for row in range(overlay_h):
                alpha = int(200 * (row / overlay_h))
                draw.line([(ax, oy + row), (ax + img_w, oy + row)], fill=max(0, 40 - alpha // 3))

            # Truncate title to fit
            title_font = get_font(36, bold=True)
            max_tw = img_w - 30
            lines = _wrap_text(title_font, title, max_tw)
            lines = lines[:3]
            line_h = max(int(_text_height(title_font, "Ag") * 1.15), 40)
            ty = top_y + img_h - 24 - len(lines) * line_h
            for ln in lines:
                draw.text((ax + 14, ty), ln, fill=240, font=title_font, anchor="lt")
                ty += line_h

    # Remaining headlines as text list
    list_y = top_y + img_h + 30
    remaining = articles[2:7]
    for art in remaining:
        title = art.get("title", "")
        if not title:
            continue
        if list_y > HEIGHT - 40:
            break

        # Truncate
        h_font = get_font(36)
        max_w = WIDTH - PAD * 2
        title = _truncate_text(h_font, title, max_w)

        draw.text((PAD, list_y + 2), title, fill=20, font=h_font, anchor="lt")
        list_y += 56

    return img
