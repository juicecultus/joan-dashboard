from .shared import *

# ── 9. Dad Joke ─────────────────────────────────────────────────────

def render_dad_joke() -> Image.Image:
    """Display a random dad joke from icanhazdadjoke.com."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    def _fetch():
        r = requests.get("https://icanhazdadjoke.com/",
                         headers={"Accept": "application/json"}, timeout=10)
        r.raise_for_status()
        return r.json().get("joke", "")

    result = _cache_fetch("joke", 0, 300, _fetch)  # always try fresh, 5min stale
    joke = result or "I told my wife she was drawing her eyebrows too high. She looked surprised."

    # Title
    draw.text((WIDTH // 2, 120), "Dad Joke", fill=160, font=get_font(48), anchor="mm")

    # Draw a small divider
    div_w = 200
    draw.line([(WIDTH // 2 - div_w // 2, 160), (WIDTH // 2 + div_w // 2, 160)], fill=180, width=2)

    # Joke text — larger and vertically centered
    joke_font = get_font(78)
    lines = _wrap_text(joke_font, joke, WIDTH - 200)
    line_h = max(int(_text_height(joke_font, "Ag") * 1.25), 96)
    block_h = line_h * len(lines)
    start_y = max(240, (HEIGHT - block_h) // 2 - 40)
    y = start_y
    for ln in lines:
        draw.text((WIDTH // 2, y), ln, fill=20, font=joke_font, anchor="mt")
        y += line_h

    # Emoji-style decoration at bottom
    draw.text((WIDTH // 2, HEIGHT - 100), "😄", fill=160, font=get_font(60), anchor="mm")

    _footer(draw, now_str())
    return img
