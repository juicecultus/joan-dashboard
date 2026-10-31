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

    stock = _select(stocks)
    img, draw = _canvas()
    _poster_text(draw, stock['name'], (40,40,1120,250), 300)
    _poster_text(draw, f"{stock['price']:,.2f}", (40,350,1120,500), 650)
    _poster_text(draw, stock['currency'], (40,880,1120,90), 100, False)
    up = stock['change_pct'] >= 0
    arrow = [(450,1100),(450,1200),(350,1200),(600,1430),(850,1200),(750,1200),(750,1100)]
    if up:
        arrow = [(x,2530-y) for x,y in arrow]
    draw.polygon(arrow, fill=0)
    _poster_text(draw, f"{stock['change_pct']:+.2f}%", (40,1460,1120,110), 150)
    return img
