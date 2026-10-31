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
    _fit_block(draw, stock['name'], (75, 133, 1050, 307), 140, True)
    _fit_block(draw, f"{stock['price']:,.2f}", (75, 493, 1050, 467), 260, True)
    _fit_block(draw, f"{stock['currency']}   {stock['change_pct']:+.2f}%", (75, 1067, 1050, 267), 100)
    return img
