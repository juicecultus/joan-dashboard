from .shared import *

# ── Daily Cartoon (The New Yorker) ────────────────────────────────────

def _fetch_daily_cartoon():
    """Fetch the latest Daily Cartoon from The New Yorker."""
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux) AppleWebKit/537.36"}
    r = requests.get("https://www.newyorker.com/cartoons/daily-cartoon",
                      headers=headers, timeout=15)
    r.raise_for_status()
    page = r.text

    # Extract og:image and convert /photos/ to /cartoons/ endpoint
    # (the /photos/ URL often returns 500, but /cartoons/ works)
    img_url = ""
    img_match = re.search(r'og:image["\s]+content="([^"]+)"', page)
    if img_match:
        raw_url = img_match.group(1)
        photo_id = re.search(r'/photos/([a-f0-9]+)/', raw_url)
        if photo_id:
            img_url = (f"https://media.newyorker.com/cartoons/"
                       f"{photo_id.group(1)}/master/w_1600,c_limit/undefined")
        else:
            img_url = raw_url

    # Extract the first daily cartoon link (for caption)
    link_match = re.search(r'href="(/cartoons/daily-cartoon/[^"]+)"', page)
    detail_url = ""
    if link_match:
        detail_url = "https://www.newyorker.com" + link_match.group(1)

    # Extract caption from the detail page (smart-quoted text)
    caption = ""
    if detail_url:
        try:
            r2 = requests.get(detail_url, headers=headers, timeout=15)
            r2.raise_for_status()
            caps = re.findall(r'\u201c([^\u201d]+)\u201d', r2.text)
            if caps:
                caption = caps[0]
        except Exception:
            pass

    # Extract title
    title_match = re.search(r'og:title["\s]+content="([^"]+)"', page)
    title = title_match.group(1) if title_match else "Daily Cartoon"

    return {"image_url": img_url, "caption": caption, "title": title}


def render_daily_cartoon() -> Image.Image:
    """Render The New Yorker's Daily Cartoon with auto-cropped whitespace."""
    from PIL import ImageOps
    img = Image.new("L", (WIDTH, HEIGHT), 230)
    draw = ImageDraw.Draw(img)

    data = _cache_fetch("newyorker_cartoon", 43200, 172800, _fetch_daily_cartoon)

    if not data:
        _centered_text(draw, HEIGHT // 2, "No cartoon available", 40, fill=80)
        _footer(draw, now_str())
        return img

    caption = data.get("caption", "")
    title = data.get("title", "Daily Cartoon")

    # Reserve space for caption at bottom
    caption_h = 0
    caption_lines = []
    if caption:
        cap_font = get_font(36)
        caption_lines = _wrap_text(cap_font, f'"{caption}"', WIDTH - PAD * 2 - 40)
        caption_h = len(caption_lines) * 48 + 30

    footer_h = 50
    footer_y = HEIGHT - footer_h
    caption_area_top = footer_y - caption_h
    img_area_h = caption_area_top - 20  # image area height

    # Fetch and process the cartoon image
    try:
        img_url = data["image_url"]
        r = requests.get(img_url, timeout=15,
                         headers={"User-Agent": "JoanDashboard/1.0"})
        r.raise_for_status()
        cartoon = Image.open(BytesIO(r.content)).convert("L")

        # Auto-crop whitespace
        bg = cartoon.getpixel((0, 0))
        threshold = 20
        pixels = cartoon.load()
        w, h = cartoon.size
        top, bottom, left, right = h, 0, w, 0
        for y_px in range(h):
            for x_px in range(w):
                if abs(pixels[x_px, y_px] - bg) > threshold:
                    top = min(top, y_px)
                    bottom = max(bottom, y_px)
                    left = min(left, x_px)
                    right = max(right, x_px)
        if bottom > top and right > left:
            margin = 10
            cartoon = cartoon.crop((max(0, left - margin), max(0, top - margin),
                                    min(w, right + margin), min(h, bottom + margin)))

        # Scale to fit the available area
        cw, ch = cartoon.size
        scale = min((WIDTH - PAD * 2) / cw, img_area_h / ch)
        new_w, new_h = int(cw * scale), int(ch * scale)
        cartoon = cartoon.resize((new_w, new_h), Image.LANCZOS)

        # Center the cartoon
        x_off = (WIDTH - new_w) // 2
        y_off = max(10, (img_area_h - new_h) // 2)
        img.paste(cartoon, (x_off, y_off))
    except Exception as e:
        _centered_text(draw, HEIGHT // 3, f"Image load failed: {str(e)[:60]}", 28, fill=100)

    # Draw caption
    if caption_lines:
        cap_font = get_font(36)
        cy = caption_area_top + 15
        for ln in caption_lines:
            draw.text((WIDTH // 2, cy), ln, fill=30, font=cap_font, anchor="mt")
            cy += 48

    # Footer
    draw.rectangle([0, footer_y, WIDTH, HEIGHT], fill=200)
    draw.text((PAD + 10, footer_y + footer_h // 2), "The New Yorker — Daily Cartoon",
              fill=60, font=get_font(24, bold=True), anchor="lm")
    draw.text((WIDTH - PAD - 10, footer_y + footer_h // 2), now_str(),
              fill=80, font=get_font(24), anchor="rm")

    return img
