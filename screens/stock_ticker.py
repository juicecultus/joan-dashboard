from .shared import *

# ── 13. Stock Ticker ────────────────────────────────────────────────

STOCK_TICKERS = os.environ.get("STOCK_TICKERS", "^FTSE,^GSPC,AAPL,MSFT,GOOGL,AMZN").split(",")


def _fetch_stock_data(ticker):
    """Fetch current price and change from Yahoo Finance."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=1d"
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
        "AMZN": "Amazon", "TSLA": "Tesla", "META": "Meta",
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

    y = 190
    row_h = (HEIGHT - 280) // min(len(stocks), 8)
    row_h = min(row_h, 120)

    for s in stocks:
        # Ticker name
        name_font = get_font(34, bold=True)
        name_max = WIDTH // 2 - PAD - 40
        draw.text((PAD + 20, y), _truncate_text(name_font, s["name"], name_max),
                  fill=0, font=name_font, anchor="lt")

        # Price
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

        draw.text((WIDTH - PAD - 20, y), price_str, fill=0, font=get_font(34, bold=True), anchor="rt")

        # Change line
        arrow = "▲" if s["change"] >= 0 else "▼"
        change_str = f"{arrow} {abs(s['change']):,.2f} ({abs(s['change_pct']):.2f}%)"
        fill = 40 if s["change"] >= 0 else 80
        draw.text((PAD + 20, y + 42), s["ticker"], fill=160, font=get_font(22), anchor="lt")
        draw.text((WIDTH - PAD - 20, y + 42), change_str, fill=fill, font=get_font(26), anchor="rt")

        y += row_h

        if y > HEIGHT - 80:
            break

    _footer(draw, now_str())
    return img
