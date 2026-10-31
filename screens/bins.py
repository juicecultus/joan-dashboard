from .shared import *

# ── Bin Collection Day ───────────────────────────────────────────────

_BIN_KEY_HEX = "F57E76482EE3DC3336495DEDEEF3962671B054FE353E815145E29C5689F72FEC"
_BIN_IV_HEX = "2CBF4FC35C69B82362D393A4F0B9971A"

# Bin type → (display name, grayscale fill for the bin icon)
_BIN_STYLES = {
    "general waste":   ("General Waste",   60),
    "recycling":       ("Recycling",       140),
    "food waste":      ("Food Waste",      100),
    "garden waste":    ("Garden Waste",    120),
}


def _bin_encrypt(data: str) -> str:
    """AES-CBC encrypt + PKCS7 pad → hex string (Buckinghamshire API)."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding as sym_padding
    key = bytes.fromhex(_BIN_KEY_HEX)
    iv = bytes.fromhex(_BIN_IV_HEX)
    padder = sym_padding.PKCS7(128).padder()
    padded = padder.update(data.encode("utf-8")) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    enc = cipher.encryptor()
    return (enc.update(padded) + enc.finalize()).hex()


def _bin_decrypt(hex_str: str) -> dict:
    """Hex string → AES-CBC decrypt + PKCS7 unpad → JSON dict."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding as sym_padding
    key = bytes.fromhex(_BIN_KEY_HEX)
    iv = bytes.fromhex(_BIN_IV_HEX)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    dec = cipher.decryptor()
    padded = dec.update(bytes.fromhex(hex_str)) + dec.finalize()
    unpadder = sym_padding.PKCS7(128).unpadder()
    plain = unpadder.update(padded) + unpadder.finalize()
    return json.loads(plain.decode("utf-8"))


# Form-engine protocol adapted from UKBinCollectionData's Buckinghamshire adapter.
# See docs/third-party/UKBinCollectionData-LICENSE.txt (MIT).
_BIN_BASE = "https://itouchvision.app/portal/itouchvision/gdsv5/"
_BIN_ACCESS = "FA353FC740600CCE617BE0534D090A8C09AD3DCC"
_BIN_BEARER = "SOcNAeuNQh/A6lmc6dd69Q=="  # Public form client value, not a user credential.


def _parse_collection_table(markup, today=None):
    from html.parser import HTMLParser
    class Table(HTMLParser):
        def __init__(self):
            super().__init__()
            self.rows, self.row, self.cell = [], [], None
        def handle_starttag(self, tag, attrs):
            if tag == 'tr': self.row = []
            if tag == 'td': self.cell = []
            if tag == 'br' and self.cell is not None: self.cell.append(' ')
        def handle_data(self, data):
            if self.cell is not None: self.cell.append(data)
        def handle_endtag(self, tag):
            if tag == 'td' and self.cell is not None:
                self.row.append(' '.join(''.join(self.cell).split()))
                self.cell = None
            if tag == 'tr' and self.row: self.rows.append(self.row)
    parser = Table()
    parser.feed(markup)
    today = today or datetime.now().date()
    result = []
    for cells in parser.rows:
        if len(cells) < 2: continue
        raw, name = cells[:2]
        match = re.search(r"(\d{1,2})\s+([A-Za-z]+)(?:\s+(\d{4}))?", raw)
        if not match: continue
        # The council omits the year. Restrict inferred dates to the next 90 days,
        # preventing an old collection from silently becoming next year's date.
        years = [int(match[3])] if match[3] else [today.year, today.year+1]
        for year in years:
            try:
                date = datetime.strptime(f"{match[1]} {match[2]} {year}", "%d %B %Y").date()
            except ValueError:
                continue
            delta = (date-today).days
            if 0 <= delta <= 90:
                result.append({'binType': name, 'collectionDay': date.isoformat()})
                break
    return _require(result, 'Council returned no upcoming collection dates')


def _fetch_bins():
    """Read the replacement council form; the retired kmbd feed returns null."""
    import secrets
    _require(BIN_UPRN, 'Bin address not configured')
    with requests.Session() as session:
        session.headers.update({'Accept':'application/json',
            'Content-Type':'application/json; charset=UTF-8',
            'Origin':'https://connect.buckinghamshire.gov.uk',
            'sessionid':secrets.token_hex(16), 'User-Agent':'Mozilla/5.0'})
        common = {'P_CLIENT_ID':152, 'P_ACCESS_KEY':_BIN_ACCESS, 'LANG_CODE':'EN'}
        def plugin(name, payload):
            response = session.get(_BIN_BASE+'plugin/'+name,
                headers={'authorization':'Bearer '+_BIN_BEARER,
                         'P_PARAMETER':_bin_encrypt(json.dumps(payload))}, timeout=12)
            response.raise_for_status()
            return _bin_decrypt(response.text.strip())
        fields = [
            {'ANSWER':{'ID':''}, 'QUESTION':{'VALUE':'honeypot'}},
            {'ANSWER':{'ID':'','VALUE':{'LOCATION_DATA':{'REPORT_UPRN':int(BIN_UPRN)}}},
             'QUESTION':{'ID':'666224','VALUE':' Your address'}},
            {'ANSWER':{'ID':'','VALUE':"UPRN='#REPORT_UPRN#'"},
             'QUESTION':{'ID':'666227','VALUE':'-Hidden- Selected UPRN'}},
        ]
        payload = dict(common, P_APP_ID=0, P_REPORT_ID=None, P_USER_ID=None,
            P_CATEGORY_ID=18428, P_COUNCIL_ID=34505, P_FORM_ID=2299,
            P_ALLOW_START_PAGE=0, P_SKIPPED_PAGE_ID='', P_PAGE_ID=52742,
            P_REPORT_DATA={'REPORT_DATA':fields})
        response = session.post(_BIN_BASE+'service/saveqadata',
            data=_bin_encrypt(json.dumps(payload)), timeout=12)
        response.raise_for_status()
        report = _require(_bin_decrypt(response.text.strip()).get('P_REPORT_ID'), 'Council lookup session unavailable')
        form = plugin('getformdata', dict(common, P_CATEGORY_ID=18428, P_REPORT_ID=report, P_USER_ID=None))
        items = [item for page in form.get('PAGES',[]) for region in page.get('REGIONS',[])
                 for item in region.get('ITEMS',[]) if item.get('I_TYPE') == 'WEB_SERVICE_REF']
        item = _require(items, 'Council collection form changed')[0]
        params = dict(common, P_ITEM_ID=item['I_ID'], P_WS_ID=item['I_WS_ID'], P_REPORT_ID=report)
        mapping = plugin('getWSRInputMapping', dict(params, P_USER_ID=None))
        inputs = {i['name']:i['inSource'] for i in mapping.get('WS_INPUTS',[])
                  if i.get('name') and i.get('inSource') is not None}
        result = plugin('getWSRResult', dict(params, P_INPUT_DATA=inputs or {'uprn':str(BIN_UPRN)}))
        outputs = result.get('WSR_VALUE',{}).get('OUTPUT_DATA',[])
        markup = '\n'.join(o.get('VAL','') for o in outputs)
        return _parse_collection_table(markup)


def _draw_bin_icon(draw, cx, cy, size, fill, label_char):
    """Draw a simple bin icon (rounded rectangle with lid) at center (cx, cy)."""
    w = size
    h = int(size * 1.3)
    # Body
    draw.rounded_rectangle(
        [cx - w // 2, cy - h // 2 + 8, cx + w // 2, cy + h // 2],
        radius=8, fill=fill, outline=0, width=2,
    )
    # Lid (wider top bar)
    lid_w = w + 12
    draw.rounded_rectangle(
        [cx - lid_w // 2, cy - h // 2 - 4, cx + lid_w // 2, cy - h // 2 + 12],
        radius=4, fill=fill, outline=0, width=2,
    )
    # Handle
    draw.rectangle([cx - 8, cy - h // 2 - 14, cx + 8, cy - h // 2 - 4], fill=fill)
    # Label character inside bin
    draw.text((cx, cy + 6), label_char, fill=255, font=get_font(int(size * 0.5), bold=True), anchor="mm")


def render_bins() -> Image.Image:
    """Render a Bin Collection Day screen for e-ink display."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    # Fetch collection data (cached 4 hours, stale up to 24h)
    collections = _cache_fetch("bins", 14400, 86400, _fetch_bins)

    _require(collections)

    # Parse and sort by date
    today = datetime.now().date()
    bins = []
    for c in collections:
        bin_type = c.get("binType", "Unknown").strip()
        date_str = c.get("collectionDay", "")
        try:
            # Normalise separators then parse
            norm = date_str.replace("/", "-").strip()
            parts = norm.split("-")
            if len(parts) == 3:
                if len(parts[0]) == 4:        # YYYY-MM-DD
                    dt = datetime(int(parts[0]), int(parts[1]), int(parts[2])).date()
                else:                          # DD-MM-YYYY
                    dt = datetime(int(parts[2]), int(parts[1]), int(parts[0])).date()
            else:
                continue
        except (ValueError, IndexError):
            continue
        if dt >= today:
            bins.append({"type": bin_type, "date": dt})

    bins.sort(key=lambda b: b["date"])

    # Group by date
    from collections import OrderedDict
    by_date = OrderedDict()
    for b in bins:
        by_date.setdefault(b["date"], []).append(b["type"])

    _require(list(by_date))
    next_date = next(iter(by_date))
    types = by_date[next_date]
    days = (next_date-today).days
    urgency = 'Today' if days == 0 else 'Tomorrow' if days == 1 else f'In {days} days'
    img, draw = _canvas()
    _fit_block(draw, urgency, (80,80,WIDTH-160,250), 160, True)
    # One collection day; all bins due on that day remain visible.
    count = len(types)
    size = min(240, (WIDTH-160)//count-30)
    for i, name in enumerate(types):
        x = 80 + (i+.5)*(WIDTH-160)/count
        _draw_bin_icon(draw, int(x), 680, size, 0, name[:1].upper())
    _fit_block(draw, ' + '.join(types), (80,980,WIDTH-160,300), 105, True)
    _fit_block(draw, next_date.strftime('%A %d %B'), (80,1390,WIDTH-160,130), 64)
    return img
