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


def render_trains() -> Image.Image:
    """Render a UK train departure board for e-ink display."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    station_name = _CRS_NAMES.get(TRAINS_STATION, TRAINS_STATION)
    destination_name = _CRS_NAMES.get(TRAINS_DESTINATION, TRAINS_DESTINATION)

    # Fetch departures (cached 2min, stale up to 30min)
    data = _cache_fetch("trains", 120, 1800, _fetch_trains)
    board = _board_payload(data) if isinstance(data, dict) else {}

    # --- Header bar ---
    header_h = 90
    draw.rectangle([0, 0, WIDTH, header_h], fill=30)
    draw.text((PAD, header_h // 2), f"Live Departures — {station_name} > {destination_name}",
              fill=240, font=get_font(42, bold=True), anchor="lm")
    now_str = datetime.now().strftime("%H:%M")
    draw.text((WIDTH - PAD, header_h // 2), now_str,
              fill=200, font=get_font(38, bold=True), anchor="rm")

    y = header_h + 15

    if not data or not TRAINS_API_KEY:
        if not TRAINS_API_KEY:
            msg = "TRAINS_API_KEY not set — add your Rail Data Marketplace key to .env"
        else:
            msg = "No departure data available"
        _centered_text(draw, HEIGHT // 2 - 40, msg, 36, fill=100)
        _dashboard_footer(draw)
        return img

    # --- NRCC disruption messages ---
    nrcc = _message_list(board)
    for msg_obj in nrcc[:2]:
        msg_val = msg_obj.get("value", "") if isinstance(msg_obj, dict) else str(msg_obj)
        # Strip HTML tags
        import re
        msg_clean = re.sub(r"<[^>]+>", "", msg_val).strip()
        if msg_clean:
            draw.rectangle([PAD, y, WIDTH - PAD, y + 50], fill=240)
            draw.text((PAD + 15, y + 25), f"! {msg_clean[:100]}", fill=30,
                      font=get_font(24), anchor="lm")
            y += 55

    # Parse services
    services = []
    train_services = _service_list(board)
    for svc in train_services[:10]:
        if not isinstance(svc, dict):
            continue
        std = svc.get("std", "")
        etd = svc.get("etd", "")
        platform = svc.get("platform", "-")
        operator = svc.get("operator", "")
        operator_code = svc.get("operatorCode", "")
        length = svc.get("length", 0)
        is_cancelled = svc.get("isCancelled", False)
        # Destination
        dest_list = svc.get("destination", [])
        dest_name = dest_list[0].get("locationName", "") if dest_list else ""
        via = dest_list[0].get("via", "") if dest_list else ""
        # Calling points
        calling_points = []
        for cp_group in svc.get("subsequentCallingPoints", []):
            for cp in cp_group.get("callingPoint", []):
                calling_points.append({
                    "name": cp.get("locationName", ""),
                    "st": cp.get("st", ""),
                    "et": cp.get("et", ""),
                })
        # Arrival time at final destination
        arr_time = calling_points[-1]["st"] if calling_points else ""
        # Minutes until departure
        dep_time = etd if etd not in ("On time", "Cancelled", "Delayed", "") else std
        mins = _minutes_until(dep_time)
        services.append({
            "time": std, "due": etd, "platform": platform,
            "destination": dest_name, "via": via,
            "operator": operator, "operator_code": operator_code,
            "length": length, "cancelled": is_cancelled,
            "calling_points": calling_points, "arrival": arr_time,
            "mins": mins,
        })

    if not services:
        _centered_text(draw, HEIGHT // 2, "No departures scheduled", 42, fill=80)
        _dashboard_footer(draw)
        return img

    # --- Render services ---
    # Adaptive layout: detailed cards when <=4 services, compact rows for more
    footer_y = HEIGHT - 60
    avail_h = footer_y - y - 10

    if len(services) <= 4:
        # ── Detailed card layout ──
        card_h = min(avail_h // len(services), 250)
        card_gap = 10

        for i, svc in enumerate(services):
            cy = y + i * (card_h + card_gap)

            # Card background
            if svc["cancelled"]:
                draw.rectangle([PAD, cy, WIDTH - PAD, cy + card_h], fill=230)
            elif i % 2 == 1:
                draw.rectangle([PAD, cy, WIDTH - PAD, cy + card_h], fill=248)

            # Row 1: Time + status + platform badge + destination
            tx = PAD + 20
            r1y = cy + 20

            # Departure time (large)
            draw.text((tx, r1y), svc["time"], fill=0, font=get_font(52, bold=True), anchor="lt")
            tx += 160

            # "in X min" or status
            if svc["cancelled"]:
                draw.text((tx, r1y + 8), "CANCELLED", fill=0, font=get_font(34, bold=True), anchor="lt")
            elif svc["due"].lower() == "on time":
                if svc["mins"] is not None and svc["mins"] >= 0:
                    min_label = "now" if svc["mins"] == 0 else f"in {svc['mins']} min"
                    draw.text((tx, r1y + 8), min_label, fill=60, font=get_font(34), anchor="lt")
                else:
                    draw.text((tx, r1y + 8), "On time", fill=60, font=get_font(34), anchor="lt")
            elif svc["due"].lower() == "delayed":
                draw.text((tx, r1y + 8), "DELAYED", fill=0, font=get_font(34, bold=True), anchor="lt")
            else:
                # Specific expected time
                draw.text((tx, r1y + 8), f"Exp {svc['due']}", fill=0, font=get_font(34, bold=True), anchor="lt")

            # Platform badge (right side)
            plat = svc["platform"]
            if plat and plat != "-":
                px = WIDTH - PAD - 120
                draw.rectangle([px, r1y, px + 90, r1y + 52], fill=30)
                draw.text((px + 45, r1y + 26), f"P{plat}", fill=240, font=get_font(32, bold=True), anchor="mm")

            # Row 2: Destination + via + operator + coaches
            r2y = r1y + 60
            dest_str = svc["destination"]
            if svc["via"]:
                dest_str += f"  {svc['via']}"
            dest_font = get_font(34, bold=True)
            dest_max = WIDTH - (PAD + 20) - 360
            draw.text((PAD + 20, r2y), _truncate_text(dest_font, dest_str, dest_max), fill=0, font=dest_font, anchor="lt")

            # Operator + coaches (right-aligned)
            info_parts = []
            if svc["operator"]:
                info_parts.append(svc["operator"])
            if svc["length"] and svc["length"] > 0:
                info_parts.append(f"{svc['length']} coaches")
            if svc["arrival"]:
                info_parts.append(f"Arr {svc['arrival']}")
            if info_parts:
                info_font = get_font(26)
                info_str = "  |  ".join(info_parts)
                draw.text((WIDTH - PAD - 20, r2y + 5), _truncate_text(info_font, info_str, 320),
                          fill=100, font=info_font, anchor="rt")

            # Row 3: Calling points
            r3y = r2y + 45
            if svc["calling_points"]:
                stops = [cp["name"] for cp in svc["calling_points"]]
                stops_str = " > ".join(stops)
                # Truncate if too long
                max_w = WIDTH - PAD * 2 - 40
                font_cp = get_font(24)
                while font_cp.getlength(stops_str) > max_w and len(stops) > 2:
                    stops = stops[:-1]
                    stops_str = " > ".join(stops) + " > ..."
                draw.text((PAD + 20, r3y), stops_str, fill=120, font=font_cp, anchor="lt")

            # Separator
            if i < len(services) - 1:
                sep_y = cy + card_h + card_gap // 2
                draw.line([(PAD + 20, sep_y), (WIDTH - PAD - 20, sep_y)], fill=200, width=1)
    else:
        # ── Compact row layout for busy periods ──
        row_h = min(avail_h // len(services), 95)
        for i, svc in enumerate(services):
            ry = y + i * row_h
            if i % 2 == 1:
                draw.rectangle([PAD - 10, ry, WIDTH - PAD + 10, ry + row_h - 5], fill=245)
            cy_r = ry + row_h // 2 - 5
            # Time
            draw.text((PAD + 10, cy_r), svc["time"], fill=0, font=get_font(36, bold=True), anchor="lm")
            # Status
            due = svc["due"]
            if svc["cancelled"]:
                due = "CANCELLED"
            due_fill = 60 if due.lower() == "on time" else 0
            draw.text((PAD + 180, cy_r), due, fill=due_fill, font=get_font(32), anchor="lm")
            # Platform
            plat = svc["platform"]
            if plat and plat != "-":
                draw.text((PAD + 440, cy_r), f"P{plat}", fill=0, font=get_font(32, bold=True), anchor="lm")
            # Destination + via
            dest_str = svc["destination"]
            if svc["via"]:
                dest_str += f" {svc['via']}"
            dest_font = get_font(32, bold=True)
            draw.text((PAD + 540, cy_r), _truncate_text(dest_font, dest_str, WIDTH - (PAD + 540) - 140),
                      fill=0, font=dest_font, anchor="lm")
            # Operator code
            draw.text((WIDTH - PAD - 10, cy_r), svc["operator_code"], fill=100, font=get_font(28), anchor="rm")
            # Row separator
            if i < len(services) - 1:
                sep_y = ry + row_h - 3
                for dx in range(PAD, WIDTH - PAD, 8):
                    draw.point((dx, sep_y), fill=180)

    # --- Footer ---
    _dashboard_footer(draw)

    return img
