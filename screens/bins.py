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


def _bin_pictogram(name, width, height):
    """Oversampled geometry: a food caddy or a wheeled collection bin."""
    import math
    scale = 3
    icon = Image.new('L', (1000*scale, 650*scale), 255)
    d = ImageDraw.Draw(icon)
    def polygon(points, fill=0):
        d.polygon([(int(x*scale), int(y*scale)) for x,y in points], fill=fill)
    def line(points, width=16):
        d.line([(int(x*scale), int(y*scale)) for x,y in points], fill=0, width=width*scale, joint='curve')
    def ellipse(box, fill=0):
        d.ellipse(tuple(int(v*scale) for v in box), fill=fill)
    food = 'food' in name.lower()
    recycling = 'recycl' in name.lower()
    label = 'Food' if food else 'Recycling' if recycling else 'Garden' if 'garden' in name.lower() else 'General waste' if 'general' in name.lower() else name
    if food:
        # Broad kitchen caddy with a raised carrying handle.
        d.arc((270*scale, 15*scale, 730*scale, 420*scale), 180, 360, fill=0, width=20*scale)
        polygon([(150,155),(850,155),(800,605),(200,605)])
        polygon([(174,177),(826,177),(780,583),(220,583)],255)
        line([(130,150),(870,150)],24)
        ellipse((407,233,520,368)); ellipse((480,233,593,368))
        polygon([(425,292),(575,292),(550,392),(450,392)])
        line([(500,249),(510,208)],12)
        ellipse((520,192,578,220))
    else:
        # Tapered outdoor bin, broad lid, pull handle and two wheels.
        line([(680,100),(680,45),(810,45),(810,140)],18)
        polygon([(170,125),(830,125),(770,570),(230,570)])
        polygon([(194,148),(806,148),(750,548),(250,548)],255)
        line([(140,124),(860,124)],26)
        ellipse((230,555,315,640)); ellipse((685,555,770,640))
        if recycling:
            # Three separate chasing arrows; no font/emoji dependency.
            for angle in (0,120,240):
                pts=[(-85,-110),(52,-110),(52,-145),(135,-90),(52,-35),(52,-70),(-85,-70)]
                r=math.radians(angle)
                polygon([(500+.78*(x*math.cos(r)-y*math.sin(r)),290+.78*(x*math.sin(r)+y*math.cos(r))) for x,y in pts])
        else:
            line([(430,225),(570,225)],18)
            line([(450,265),(450,380)],14); line([(500,265),(500,380)],14); line([(550,265),(550,380)],14)
    size=112
    while get_font(size*scale,bold=True).getlength(label)>460*scale:
        size-=2
    d.text((500*scale,485*scale),label,font=get_font(size*scale,bold=True),fill=0,anchor='mm')
    from PIL import ImageOps
    return ImageOps.contain(icon,(width,height),Image.Resampling.LANCZOS)


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
    date_label = urgency if days < 2 else next_date.strftime('%A %-d %b')
    _fit_block(draw, date_label, (60,20,WIDTH-120,160), 110, True)
    # Stack the large pictograms in portrait; keep every bin due visible.
    count = len(types)
    row_height = (HEIGHT-210)//count
    for i, name in enumerate(types):
        icon = _bin_pictogram(name, WIDTH-60, row_height-12)
        img.paste(icon, ((WIDTH-icon.width)//2, 190+i*row_height+(row_height-icon.height)//2))
    return img
