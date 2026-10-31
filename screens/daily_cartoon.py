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


def render_daily_cartoon():
    data = _require(_cache_fetch("newyorker_cartoon", 43200, 172800, _fetch_daily_cartoon))
    cartoon = _require(_image_url(data['image_url']))
    # Keep the cartoon and its original lettering intact.
    from PIL import ImageChops
    # Crop only outer whitespace; the original caption is already in the image.
    mask = ImageChops.difference(cartoon, Image.new('L', cartoon.size, 255)).point(lambda v: 255 if v > 45 else 0)
    bounds = mask.getbbox()
    if bounds:
        cartoon = cartoon.crop(bounds)
    return _picture(cartoon, photo=False)
