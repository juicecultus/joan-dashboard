from .shared import *
import xml.etree.ElementTree as ET

# ── UK Train Departures ──────────────────────────────────────────────

# CRS code → human-readable station name (common stations)
_CRS_NAMES = {
    "AVP": "Aylesbury Vale Parkway",
    "MYB": "London Marylebone",
    "AYS": "Aylesbury",
    "AMR": "Amersham",
    "BCS": "Bicester North",
    "HDM": "High Wycombe",
    "BAN": "Banbury",
    "KGX": "Kings Cross",
    "PAD": "London Paddington",
    "EUS": "London Euston",
    "WAT": "London Waterloo",
    "VXH": "Vauxhall",
    "EDB": "Edinburgh Waverley",
}


def _xml_to_dict(node):
    """Convert a minimal XML tree into nested dict/list structures."""
    children = list(node)
    if not children:
        return (node.text or "").strip()

    result = {}
    for child in children:
        key = child.tag.split("}")[-1]
        value = _xml_to_dict(child)
        if key in result:
            if not isinstance(result[key], list):
                result[key] = [result[key]]
            result[key].append(value)
        else:
            result[key] = value
    return result


def _board_payload(data):
    """Return the board payload regardless of JSON proxy or SOAP-style nesting."""
    if not isinstance(data, dict):
        return {}
    for key in ("GetStationBoardResult", "GetDepBoardWithDetailsResult", "GetArrivalBoardResult"):
        nested = data.get(key)
        if isinstance(nested, dict):
            return nested
    return data


def _service_list(board):
    """Normalize service containers into a flat list of service dicts."""
    services = board.get("trainServices") or board.get("services") or []
    if isinstance(services, dict):
        services = services.get("service") or services.get("Service") or []
    if isinstance(services, dict):
        services = [services]
    return services or []


def _message_list(board):
    """Normalize disruption messages into a flat list."""
    messages = board.get("nrccMessages") or board.get("messages") or []
    if isinstance(messages, dict):
        messages = messages.get("msg") or messages.get("message") or messages.get("value") or []
    if isinstance(messages, dict):
        messages = [messages]
    return messages or []


def _fetch_trains():
    """Fetch live departures from the configured station via LDBWS API."""
    if not TRAINS_API_KEY:
        return None
    headers = {
        "x-apikey": TRAINS_API_KEY,
        "User-Agent": "JoanDashboard/1.0",
        "Accept": "application/json, text/xml;q=0.9, application/xml;q=0.8, */*;q=0.1",
    }
    params = {"numRows": 10}
    urls = [
        f"https://api1.raildata.org.uk/1010-live-departure-board-dep1_2/LDBWS/api/20220120/GetDepBoardWithDetails/{TRAINS_STATION}",
        f"https://api1.raildata.org.uk/1010-live-departure-board-dep/LDBWS/api/20220120/GetDepBoardWithDetails/{TRAINS_STATION}",
    ]
    last_error = None
    for url in urls:
        try:
            r = requests.get(url, params=params, headers=headers, timeout=10)
            r.raise_for_status()
            try:
                return r.json()
            except ValueError:
                root = ET.fromstring(r.text)
                return _xml_to_dict(root)
        except Exception as exc:
            last_error = exc
            print(f"[trains] fetch failed from {url}: {exc}")
    if last_error:
        raise last_error
    return None


def _minutes_until(time_str):
    """Return minutes from now until HH:MM, or None on parse error."""
    try:
        now = datetime.now()
        h, m = int(time_str.split(":")[0]), int(time_str.split(":")[1])
        dep = now.replace(hour=h, minute=m, second=0, microsecond=0)
        diff = (dep - now).total_seconds() / 60
        if diff < -60:
            diff += 1440  # next day
        return int(diff)
    except Exception:
        return None


def _locations(value):
    if isinstance(value, dict):
        value = value.get('location', value)
    return value if isinstance(value, list) else [value] if isinstance(value, dict) else []


def render_trains():
    # Live departures must not be shown from a half-hour-old cache.
    data = _require(_cache_fetch("trains", 60, 0, _fetch_trains))
    board = _board_payload(data)
    services = [s for s in _service_list(board) if isinstance(s,dict)]
    if TRAINS_DESTINATION:
        services = [s for s in services if any(d.get('crs') == TRAINS_DESTINATION for d in _locations(s.get('destination')))]
    if not services:
        return _statement('No departures', _CRS_NAMES.get(TRAINS_STATION,TRAINS_STATION) + ' to ' + _CRS_NAMES.get(TRAINS_DESTINATION,TRAINS_DESTINATION))
    service = services[0]
    destinations = _locations(service.get('destination'))
    destination = destinations[0].get('locationName','') if destinations else ''
    status = 'Cancelled' if str(service.get('isCancelled','')).lower() == 'true' else service.get('etd','')
    img, draw = _canvas()
    _fit_block(draw, service.get('std',''), (60,80,WIDTH-120,430), 310, True)
    _fit_block(draw, destination, (80,570,WIDTH-160,300), 120, True)
    _fit_block(draw, status, (80,940,WIDTH-160,200), 110, True)
    platform = service.get('platform')
    _fit_block(draw, 'Platform ' + str(platform) if platform else 'Platform to be announced', (80,1240,WIDTH-160,220), 85)
    return img
