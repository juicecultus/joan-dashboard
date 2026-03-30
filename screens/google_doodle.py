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
    # Parse img tags with class hero-tag-carousel__collage-card-img
    pattern = r'<img\s+class="hero-tag-carousel__collage-card-img"\s+src="([^"]+)"\s+alt="([^"]*)"'
    matches = re.findall(pattern, r.text)
    if not matches:
        return None
    src, alt = matches[0]
    if src.startswith("//"):
        src = "https:" + src
    return {"title": alt, "image_url": src}


def render_google_doodle() -> Image.Image:
    """Render a Google Doodle of the Day screen."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    # Key the cache by local day so the doodle is refreshed once per day.
    # This avoids reusing yesterday's doodle when the screen rotates daily.
    cache_key = f"google_doodle:{datetime.now().strftime('%Y-%m-%d')}"
    doodle = _cache_fetch(cache_key, 86400, 0, _fetch_google_doodle)

    # --- Header ---
    header_h = 90
    draw.rectangle([0, 0, WIDTH, header_h], fill=30)
    draw.text((PAD, header_h // 2), "Google Doodle of the Day",
              fill=240, font=get_font(42, bold=True), anchor="lm")
    today_str = datetime.now().strftime("%A, %-d %B %Y")
    draw.text((WIDTH - PAD, header_h // 2), today_str,
              fill=160, font=get_font(24), anchor="rm")

    if not doodle:
        _centered_text(draw, HEIGHT // 2, "No doodle available today", 38, fill=100)
        _dashboard_footer(draw)
        return img

    title = doodle.get("title", "Google Doodle")
    image_url = doodle.get("image_url", "")

    # --- Fetch and display the doodle image ---
    doodle_img = None
    if image_url:
        try:
            r = requests.get(image_url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            })
            r.raise_for_status()
            doodle_img = Image.open(BytesIO(r.content))
        except Exception as e:
            print(f"[doodle] Failed to fetch image: {e}")

    if doodle_img:
        # Convert to grayscale
        doodle_img = doodle_img.convert("L")

        # Scale to fit in the available area
        avail_w = WIDTH - PAD * 2
        avail_h = HEIGHT - header_h - 200  # room for title and footer
        dw, dh = doodle_img.size
        scale = min(avail_w / dw, avail_h / dh)
        new_w = int(dw * scale)
        new_h = int(dh * scale)
        doodle_img = doodle_img.resize((new_w, new_h), Image.LANCZOS)

        # Center the image
        img_x = (WIDTH - new_w) // 2
        img_y = header_h + 40
        img.paste(doodle_img, (img_x, img_y))
        title_y = img_y + new_h + 30
    else:
        title_y = HEIGHT // 2

    # --- Title ---
    _centered_text(draw, title_y, title, 38, bold=True, fill=30, max_width=WIDTH - PAD * 2)

    # --- Footer ---
    _dashboard_footer(draw)

    return img
