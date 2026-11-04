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


def _fetch_trains(station=None, extra_params=None):
    """Fetch live departures from the configured station via LDBWS API."""
    if not TRAINS_API_KEY:
        return None
    headers = {
        "x-apikey": TRAINS_API_KEY,
        "User-Agent": "JoanDashboard/1.0",
        "Accept": "application/json, text/xml;q=0.9, application/xml;q=0.8, */*;q=0.1",
    }
    station = station or TRAINS_STATION
    params = {"numRows": 10, **(extra_params or {})}
    urls = [
        f"https://api1.raildata.org.uk/1010-live-departure-board-dep1_2/LDBWS/api/20220120/GetDepBoardWithDetails/{station}",
        f"https://api1.raildata.org.uk/1010-live-departure-board-dep/LDBWS/api/20220120/GetDepBoardWithDetails/{station}",
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


def _incoming_services(board):
    """Use AVP's own live calling time, never the origin's departure/platform."""
    incoming=[]
    for service in _service_list(board):
        groups=service.get('subsequentCallingPoints') or []
        if isinstance(groups,dict): groups=[groups]
        for group in groups:
            points=group.get('callingPoint') or []
            if isinstance(points,dict): points=[points]
            for point in points:
                if point.get('crs') != TRAINS_STATION or point.get('at'):
                    continue
                scheduled=point.get('st')
                expected=point.get('et') or 'Time pending'
                effective=expected if len(expected)==5 and expected[2]==':' else scheduled
                minutes=_minutes_until(effective or '')
                if minutes is None or minutes < 0:
                    continue
                incoming.append({'sta':scheduled,'eta':expected,
                    'origin':{'location':{'crs':board.get('crs') or TRAINS_DESTINATION,
                        'locationName':board.get('locationName') or _CRS_NAMES.get(TRAINS_DESTINATION,TRAINS_DESTINATION)}},
                    'platform':point.get('platform'),
                    'isCancelled':str(service.get('isCancelled','')).lower()=='true' or str(point.get('isCancelled','')).lower()=='true',
                    'serviceID':service.get('serviceID') or scheduled})
    return incoming


def _fetch_arrivals():
    _require(TRAINS_DESTINATION,'Arrival origin not configured')
    rows=[]
    # Include trains already en route as well as those yet to depart the origin.
    for offset in (-90,30):
        data=_fetch_trains(TRAINS_DESTINATION,{'filterCrs':TRAINS_STATION,
            'filterType':'to','timeOffset':offset,'timeWindow':120})
        rows.extend(_incoming_services(_board_payload(_require(data))))
    unique={row['serviceID']:row for row in rows}
    return {'services':sorted(unique.values(),key=lambda s:_minutes_until(s['sta']) or 0)}


def _rail_card(draw,title,services,box,arrival=False,shared_platform=None,unavailable=False):
    x,y,w,h=box
    _panel(draw,box,32)
    _poster_text(draw,title,(x+40,y+25,w-80,75),80)
    draw.line((x+40,y+120,x+w-40,y+120),fill=0,width=2)
    if not services:
        _poster_text(draw,'Live times unavailable' if unavailable else 'No upcoming trains',
            (x+60,y+200,w-120,220),95,False)
        return
    rows=services[:3]
    step=(h-155)//len(rows)
    for i,service in enumerate(rows):
        top=y+145+i*step
        time=service.get('sta' if arrival else 'std') or '—'
        places=_locations(service.get('origin' if arrival else 'destination'))
        place=' / '.join(p.get('locationName') or _CRS_NAMES.get(p.get('crs'),p.get('crs','')) for p in places)
        status='Cancelled' if str(service.get('isCancelled','')).lower()=='true' else str(service.get('eta' if arrival else 'etd') or 'Time pending')
        if len(status)==5 and status[2]==':': status='Expected '+status
        platform=service.get('platform')
        if platform and status!='Cancelled' and str(platform)!=shared_platform: status+=' · Platform '+str(platform)
        _poster_text(draw,time,(x+35,top+10,290,step-30),110)
        _poster_text(draw,place or 'Route pending',(x+360,top+5,w-400,(step-20)//2),76)
        _poster_text(draw,status,(x+360,top+step//2,w-400,step//2-20),54,False)
        if i<len(rows)-1: draw.line((x+40,top+step-6,x+w-40,top+step-6),fill=0,width=2)


def render_trains():
    # Never present old train times as live during a feed outage.
    data=_cache_fetch('trains',60,0,_fetch_trains)
    board=_board_payload(data)
    departures=[s for s in _service_list(board) if isinstance(s,dict)]
    if TRAINS_DESTINATION:
        departures=[s for s in departures if any(d.get('crs')==TRAINS_DESTINATION for d in _locations(s.get('destination')))]
    arrivals_data=_cache_fetch('train_arrivals',60,0,_fetch_arrivals)
    arrivals=(arrivals_data or {}).get('services',[])
    _require(data or arrivals_data,'Live rail boards unavailable')
    known=[str(s.get('platform') or '') for s in departures[:3]+arrivals[:3]]
    platforms={p for p in known if p}
    shared=next(iter(platforms)) if len(platforms)==1 else None
    img,draw=_canvas()
    station=board.get('locationName') or _CRS_NAMES.get(TRAINS_STATION,TRAINS_STATION)
    _poster_text(draw,station,(45,25,1110,115),100)
    _poster_text(draw,'Platform '+shared if shared else 'Platforms pending' if not platforms else 'Platforms vary',
                  (45,150,1110,70),70,False)
    _rail_card(draw,'Departures',departures,(25,260,1150,640),shared_platform=shared,unavailable=data is None)
    _rail_card(draw,'Arrivals',arrivals,(25,930,1150,640),arrival=True,shared_platform=shared,unavailable=arrivals_data is None)
    return img
