from .shared import *

# ── Buddha Quotes ────────────────────────────────────────────────────

def _fetch_buddha_quote():
    """Fetch a random Buddha quote from buddha-api.com."""
    r = requests.get("https://buddha-api.com/api/random", timeout=10)
    r.raise_for_status()
    data = r.json()
    return {"text": data.get("text", ""), "by": data.get("byName", "Buddha")}


def render_buddha_quote() -> Image.Image:
    """Render a Buddha quote in a serene, minimalist layout."""
    img = Image.new("L", (WIDTH, HEIGHT), 240)
    draw = ImageDraw.Draw(img)
    scale = 2

    quote = _cache_fetch("buddha_quote", 43200, 172800, _fetch_buddha_quote)

    # Decorative top line
    line_y = 60 * scale
    draw.line([(PAD + 80, line_y), (WIDTH - PAD - 80, line_y)], fill=180, width=2 * scale)

    if not quote:
        _centered_text(draw, HEIGHT // 2, "No quote available", 36 * scale, fill=100)
        draw.text((WIDTH // 2, HEIGHT - 34 * scale), "Source: buddha-ai.com",
                  fill=120, font=get_font(18 * scale), anchor="mm")
        _footer(draw, now_str())
        return img

    text = quote.get("text", "")
    by = quote.get("by", "Buddha")

    # Large opening quote mark
    draw.text((PAD + 40 * scale, 150 * scale), "\u201c", fill=180, font=get_font(120 * scale), anchor="lt")

    # Quote text — centered, large
    quote_font = get_font(44 * scale)
    max_w = WIDTH - PAD * 2 - 120 * scale
    lines = _wrap_text(quote_font, text, max_w)
    lines = lines[:8]  # cap at 8 lines

    line_h = max(int(_text_height(quote_font, "Ag") * 1.25), 56 * scale)
    total_h = len(lines) * line_h
    start_y = max(200 * scale // 2, (HEIGHT - 100 * scale - total_h) // 2)
    for ln in lines:
        draw.text((WIDTH // 2, start_y), ln, fill=20, font=quote_font, anchor="mt")
        start_y += line_h

    # Closing quote + attribution
    draw.text((WIDTH // 2, start_y + 20 * scale), f"— {by}", fill=100,
              font=get_font(30 * scale), anchor="mt")

    # Decorative bottom line
    draw.line([(PAD + 80, HEIGHT - 80 * scale), (WIDTH - PAD - 80, HEIGHT - 80 * scale)],
              fill=180, width=2 * scale)

    # Footer source label
    draw.text((WIDTH // 2, HEIGHT - 34 * scale), "Source: buddha-ai.com",
              fill=120, font=get_font(18 * scale), anchor="mm")

    return img
