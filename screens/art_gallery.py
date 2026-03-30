from .shared import *

# ── 7. Art Gallery ───────────────────────────────────────────────────

def render_art_gallery() -> Image.Image:
    """Display a random artwork from the Metropolitan Museum of Art."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    def _fetch():
        search_url = "https://collectionapi.metmuseum.org/public/collection/v1/search"
        r = requests.get(search_url, params={"hasImages": "true", "q": "painting portrait landscape"}, timeout=8)
        r.raise_for_status()
        ids = r.json().get("objectIDs", [])
        if not ids:
            raise ValueError("No artworks found")
        day_seed = int(datetime.now().strftime("%Y%m%d")) + 42
        random.seed(day_seed)
        obj_id = random.choice(ids[:500])
        random.seed()
        obj_url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{obj_id}"
        r = requests.get(obj_url, timeout=8)
        r.raise_for_status()
        obj = r.json()
        image_url = obj.get("primaryImageSmall") or obj.get("primaryImage")
        if not image_url:
            raise ValueError("No image available")
        r = requests.get(image_url, timeout=15)
        r.raise_for_status()
        return {
            "image_bytes": r.content,
            "title": obj.get("title", "Untitled"),
            "artist": obj.get("artistDisplayName", "Unknown artist"),
            "date": obj.get("objectDate", ""),
            "medium": obj.get("medium", ""),
        }

    data = _cache_fetch("art", 3600, 21600, _fetch)  # 1h TTL, 6h stale

    if data:
        art = Image.open(BytesIO(data["image_bytes"])).convert("L")
        title = data["title"]
        artist = data["artist"]
        date = data["date"]
        medium = data["medium"]

        art_area_h = HEIGHT - 200
        art_area_w = WIDTH - 120
        aw, ah = art.size
        scale = min(art_area_w / aw, art_area_h / ah)
        new_w = int(aw * scale)
        new_h = int(ah * scale)
        art = art.resize((new_w, new_h), Image.LANCZOS)

        x = (WIDTH - new_w) // 2
        y = (art_area_h - new_h) // 2 + 20
        img.paste(art, (x, y))

        cap_y = HEIGHT - 170
        draw.line([(PAD, cap_y - 10), (WIDTH - PAD, cap_y - 10)], fill=200, width=1)
        draw.text((WIDTH // 2, cap_y), title[:60], fill=0, font=get_font(32, bold=True), anchor="mt")
        caption_line2 = artist
        if date:
            caption_line2 += f", {date}"
        draw.text((WIDTH // 2, cap_y + 42), caption_line2[:70], fill=80, font=get_font(26), anchor="mt")
        if medium:
            draw.text((WIDTH // 2, cap_y + 74), medium[:80], fill=120, font=get_font(22), anchor="mt")
        draw.text((WIDTH // 2, HEIGHT - 30), "The Metropolitan Museum of Art", fill=180, font=get_font(18), anchor="mm")
    else:
        draw.text((WIDTH // 2, HEIGHT // 2 - 20), "Art Gallery", fill=0, font=get_font(50, bold=True), anchor="mm")
        draw.text((WIDTH // 2, HEIGHT // 2 + 40), "Could not load artwork", fill=120, font=get_font(30), anchor="mm")

    return img
