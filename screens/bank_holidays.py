from .shared import *

# ── Bank Holidays (England & Wales) ─────────────────────────────────

def _fetch_bank_holidays():
    """Fetch UK bank holidays from gov.uk."""
    r = requests.get("https://www.gov.uk/bank-holidays.json", timeout=15)
    r.raise_for_status()
    data = r.json()
    return data.get("england-and-wales", {}).get("events", [])


def render_bank_holidays() -> Image.Image:
    """Render upcoming bank holidays for England & Wales."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    events = _cache_fetch("bank_holidays", 86400, 604800, _fetch_bank_holidays)

    today = datetime.now().date()
    upcoming = sorted((e for e in _require(events) if e.get('date','') >= today.isoformat()), key=lambda e:e['date'])
    event = _require(upcoming, "No upcoming holidays")[0]
    date = datetime.fromisoformat(event['date'])
    days = (date.date()-today).days
    return _calendar_page(str(date.day), date.strftime('%B'), event['title'],
                          'Today' if days == 0 else f'In {days} days')
