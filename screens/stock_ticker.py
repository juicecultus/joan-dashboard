from .shared import *

# ── 13. Stock Ticker ────────────────────────────────────────────────

STOCK_TICKERS = os.environ.get(
    "STOCK_TICKERS",
    "^FTSE,^GSPC,AAPL,MSFT,GOOGL,AMZN,TSLA,NVDA,META,ARM",
).split(",")


def _quote_symbol(ticker):
    """Resolve aliases to a live Yahoo Finance symbol when needed."""
    aliases = {}
    return aliases.get(ticker, ticker)


def _fetch_stock_data(ticker):
    """Fetch current price and change from Yahoo Finance."""
    try:
        quote_symbol = _quote_symbol(ticker)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote_symbol}?range=1d&interval=1d"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        meta = data["chart"]["result"][0]["meta"]
        price = meta["regularMarketPrice"]
        prev_close = meta.get("chartPreviousClose", meta.get("previousClose", price))
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
        return {
            "ticker": ticker,
            "name": _ticker_name(ticker),
            "price": price,
            "change": change,
            "change_pct": change_pct,
            "currency": meta.get("currency", "USD"),
        }
    except Exception as e:
        print(f"[stock] Failed to fetch {ticker}: {e}")
        return None


def _ticker_name(ticker):
    """Friendly names for common tickers."""
    names = {
        "^FTSE": "FTSE 100", "^GSPC": "S&P 500", "^DJI": "Dow Jones",
        "^IXIC": "NASDAQ", "^N225": "Nikkei 225",
        "AAPL": "Apple", "MSFT": "Microsoft", "GOOGL": "Alphabet",
        "AMZN": "Amazon", "TSLA": "Tesla",
        "META": "Meta", "ARM": "Arm",
        "NVDA": "NVIDIA", "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum",
    }
    return names.get(ticker, ticker)


def render_stock_ticker() -> Image.Image:
    """Display stock prices and daily changes."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    # Header
    draw.text((WIDTH // 2, 70), "Markets", fill=0, font=get_font(50, bold=True), anchor="mm")
    draw.text((WIDTH // 2, 120), datetime.now().strftime("%A %d %B %H:%M"), fill=140, font=get_font(26), anchor="mm")
    draw.line([(PAD, 155), (WIDTH - PAD, 155)], fill=200, width=2)

    def _fetch_all():
        results = []
        for ticker in STOCK_TICKERS:
            d = _fetch_stock_data(ticker.strip())
            if d:
                results.append(d)
        if not results:
            raise ValueError("No stock data")
        return results

    stocks = _cache_fetch("stocks", 300, 1800, _fetch_all) or []  # 5min TTL, 30min stale

    if not stocks:
        draw.text((WIDTH // 2, HEIGHT // 2), "Could not load market data", fill=120, font=get_font(36), anchor="mm")
        _footer(draw, now_str())
        return img

    # Two-column grid of stock cards
    content_top = 185
    footer_y = HEIGHT - 70
    gap = 40
    col_w = int((WIDTH - PAD * 2 - gap) / 2)
    row_h = 125
    rows = (len(stocks) + 1) // 2
    grid_h = rows * row_h
    start_y = content_top + max(0, ((footer_y - content_top) - grid_h) // 2)

    for idx, s in enumerate(stocks):
        col = idx % 2
        row = idx // 2
        x = PAD + col * (col_w + gap)
        y = start_y + row * row_h

        # Optional card background for readability
        draw.rounded_rectangle([x, y, x + col_w, y + row_h - 10], radius=10, fill=248, outline=220, width=1)

        # Top line: name + price
        name_font = get_font(30, bold=True)
        name_max = col_w - 20
        draw.text((x + 12, y + 10), _truncate_text(name_font, s["name"], name_max),
                  fill=0, font=name_font, anchor="lt")

        if s["currency"] == "GBp":
            price_str = f"{s['price']:,.0f}p"
        elif s["currency"] == "GBP":
            price_str = f"£{s['price']:,.2f}"
        elif s["currency"] == "USD":
            price_str = f"${s['price']:,.2f}"
        elif s["currency"] == "EUR":
            price_str = f"€{s['price']:,.2f}"
        else:
            price_str = f"{s['price']:,.2f}"

        draw.text((x + col_w - 12, y + 10), price_str, fill=0, font=get_font(30, bold=True), anchor="rt")

        # Bottom line: ticker + change
        fill = 40 if s["change"] >= 0 else 80
        draw.text((x + 12, y + 58), s["ticker"], fill=160, font=get_font(22), anchor="lt")

        change_text = f"{abs(s['change']):,.2f} ({abs(s['change_pct']):.2f}%)"
        change_font = get_font(24)
        tw = _text_width(change_font, change_text)

        # Draw arrow then text
        arrow_x = x + col_w - 12 - tw - 25
        arrow_y = y + 58 + 14
        _draw_arrow(draw, arrow_x, arrow_y, 18, direction="up" if s["change"] >= 0 else "down", fill=fill)
        draw.text((x + col_w - 12, y + 58), change_text, fill=fill, font=change_font, anchor="rt")

    _footer(draw, now_str())
    return img
