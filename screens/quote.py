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

    return _statement(quote_text, author)
