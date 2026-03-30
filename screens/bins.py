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


def _fetch_bins():
    """Fetch bin collection dates from Buckinghamshire Council API."""
    if not BIN_UPRN:
        return None
    payload = json.dumps({
        "P_CLIENT_ID": 152,
        "P_COUNCIL_ID": 34505,
        "P_LANG_CODE": "EN",
        "P_UPRN": BIN_UPRN,
    })
    encrypted = _bin_encrypt(payload)
    headers = {
        "P_PARAMETER": encrypted,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    r = requests.get(
        "https://itouchvision.app/portal/itouchvision/kmbd/collectionDay",
        headers=headers, timeout=15,
    )
    r.raise_for_status()
    raw = r.text.strip()
    if not all(c in "0123456789ABCDEFabcdef" for c in raw):
        raise ValueError(f"Non-hex response: {raw[:100]}")
    decoded = _bin_decrypt(raw)
    return decoded.get("collectionDay", [])


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

    # --- Header ---
    header_h = 100
    draw.rectangle([0, 0, WIDTH, header_h], fill=30)
    draw.text((PAD, header_h // 2), "Bin Collection Day",
              fill=240, font=get_font(48, bold=True), anchor="lm")
    draw.text((WIDTH - PAD, header_h // 2), "Waddesdon",
              fill=180, font=get_font(30), anchor="rm")

    if not collections or not BIN_UPRN:
        if not BIN_UPRN:
            msg = "BIN_UPRN not set -- add your UPRN to .env"
        else:
            msg = "No collection data available"
        _centered_text(draw, HEIGHT // 2 - 20, msg, 36, fill=100)
        _dashboard_footer(draw)
        return img

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
        bins.append({"type": bin_type, "date": dt})

    bins.sort(key=lambda b: b["date"])

    # Group by date
    from collections import OrderedDict
    by_date = OrderedDict()
    for b in bins:
        by_date.setdefault(b["date"], []).append(b["type"])

    if not by_date:
        _centered_text(draw, HEIGHT // 2, "No upcoming collections found", 38, fill=100)
        _dashboard_footer(draw)
        return img

    # --- Render the next collection prominently ---
    next_date = list(by_date.keys())[0]
    next_bins = by_date[next_date]
    days_until = (next_date - today).days

    if days_until == 0:
        urgency = "TODAY"
        urgency_fill = 0
    elif days_until == 1:
        urgency = "TOMORROW"
        urgency_fill = 40
    elif days_until < 0:
        urgency = f"{abs(days_until)} day{'s' if abs(days_until) != 1 else ''} ago"
        urgency_fill = 120
    else:
        urgency = f"In {days_until} days"
        urgency_fill = 80

    # Big urgency text
    y = header_h + 50
    draw.text((WIDTH // 2, y), urgency, fill=urgency_fill,
              font=get_font(72, bold=True), anchor="mt")
    y += 90

    # Date line
    date_display = next_date.strftime("%A, %-d %B %Y")
    draw.text((WIDTH // 2, y), date_display, fill=60,
              font=get_font(38), anchor="mt")
    y += 70

    # --- Draw bin icons for next collection ---
    bin_count = len(next_bins)
    icon_size = min(140, (WIDTH - PAD * 2) // max(bin_count, 1) - 60)
    total_width = bin_count * (icon_size + 80) - 80
    start_x = (WIDTH - total_width) // 2 + icon_size // 2

    for i, bt in enumerate(next_bins):
        cx = start_x + i * (icon_size + 80)
        cy = y + icon_size // 2 + 20

        # Match style
        key = bt.lower()
        style = None
        for k, v in _BIN_STYLES.items():
            if k in key:
                style = v
                break
        if not style:
            style = (bt, 90)
        name, fill = style
        label = name[0].upper()

        _draw_bin_icon(draw, cx, cy, icon_size, fill, label)
        # Label below icon
        name_font = get_font(24, bold=True)
        draw.text((cx, cy + icon_size // 2 + 40), _truncate_text(name_font, name, icon_size + 30),
                  fill=40, font=name_font, anchor="mt")

    y = cy + icon_size // 2 + 80

    # --- Subsequent collections ---
    remaining = list(by_date.items())[1:4]  # next 3 after the first
    if remaining:
        y += 20
        draw.line([(PAD + 40, y), (WIDTH - PAD - 40, y)], fill=200, width=1)
        y += 30
        draw.text((PAD + 40, y), "Coming up", fill=100,
                  font=get_font(28, bold=True), anchor="lt")
        y += 45

        row_font = get_font(30)
        row_font_bold = get_font(30, bold=True)
        for dt, bin_types in remaining:
            days = (dt - today).days
            if days == 0:
                day_label = "Today"
            elif days == 1:
                day_label = "Tomorrow"
            else:
                day_label = dt.strftime("%a %-d %b")

            types_str = ", ".join(bin_types)
            draw.text((PAD + 60, y), day_label, fill=40, font=row_font_bold, anchor="lt")
            types_max = WIDTH - 450 - PAD - 90
            draw.text((450, y), _truncate_text(row_font, types_str, types_max), fill=80, font=row_font, anchor="lt")

            if days >= 0:
                tag = f"{days}d"
                draw.text((WIDTH - PAD - 40, y), tag, fill=140, font=row_font, anchor="rt")

            y += 50

    # --- Footer ---
    _dashboard_footer(draw)

    return img
