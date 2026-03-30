from .shared import *

# ── 2. Motivational Quote ────────────────────────────────────────────

def render_quote() -> Image.Image:
    """Daily motivational quote — centered, elegant layout."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    quote_text = "The only way to do great work is to love what you do."
    author = "Steve Jobs"

    def _fetch():
        r = requests.get("https://zenquotes.io/api/today", timeout=5)
        r.raise_for_status()
        data = r.json()
        if data and isinstance(data, list):
            return {"q": data[0].get("q", ""), "a": data[0].get("a", "")}
        raise ValueError("No quote data")

    result = _cache_fetch("quote", 21600, 86400, _fetch)  # 6h TTL, 24h stale
    if result:
        quote_text = result.get("q") or quote_text
        author = result.get("a") or author

    # Large opening quotation mark
    draw.text((PAD + 20, 200), "\u201c", fill=200, font=get_font(200), anchor="lt")

    # Quote text — centered
    quote_font = get_font(78)
    quote_lines = []
    for paragraph in quote_text.split("\n"):
        quote_lines.extend(_wrap_text(quote_font, paragraph, WIDTH - 200) or [""])
    line_h = max(int(_text_height(quote_font, "Ag") * 1.25), 88)
    block_h = line_h * len(quote_lines)
    start_y = max(280, (HEIGHT - block_h) // 2 - 40)
    y = start_y
    for line in quote_lines:
        draw.text((WIDTH // 2, y), line, fill=20, font=quote_font, anchor="mt")
        y += line_h

    # Author
    draw.text((WIDTH // 2, y + 40), f"— {author}", fill=100, font=get_font(48, bold=True), anchor="mt")

    _dashboard_footer(draw)
    return img
