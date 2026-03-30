from .shared import *

# ── Element of the Day ────────────────────────────────────────────────

_ELEMENTS_URL = "https://raw.githubusercontent.com/hossain-khan/trmnl-elements-plugin/main/data-all.json"


def _fetch_elements():
    """Fetch periodic table elements JSON from GitHub."""
    r = requests.get(_ELEMENTS_URL, timeout=15)
    r.raise_for_status()
    return r.json().get("elements", [])


def render_element_of_day() -> Image.Image:
    """Render an Element of the Day screen (periodic table style)."""
    img = Image.new("L", (WIDTH, HEIGHT), 225)
    draw = ImageDraw.Draw(img)

    elements = _cache_fetch("periodic_elements", 604800, 2592000, _fetch_elements)

    # Footer bar
    footer_h = 60
    footer_y = HEIGHT - footer_h
    draw.rectangle([0, footer_y, WIDTH, HEIGHT], fill=180)
    draw.text((PAD, footer_y + footer_h // 2), "Element of the Day",
              fill=30, font=get_font(28, bold=True), anchor="lm")

    if not elements:
        _centered_text(draw, HEIGHT // 2, "No element data available", 40, fill=80)
        return img

    # Pick element based on day of year
    idx = datetime.now().timetuple().tm_yday % len(elements)
    el = elements[idx]

    num = el.get("atomic_number", "?")
    symbol = el.get("symbol", "?")
    name = el.get("name", "Unknown")
    mass = el.get("atomic_mass", "?")
    category = el.get("category", "")
    state = el.get("standard_state", "")
    config = el.get("electron_configuration", "")
    melting = el.get("melting_point", "")
    boiling = el.get("boiling_point", "")
    density = el.get("density", "")
    discovered = el.get("year_discovered", "")
    electronegativity = el.get("electronegativity", "")
    oxidation = el.get("oxidation_states", "")
    radius = el.get("atomic_radius", "")
    affinity = el.get("electron_affinity", "")
    ionization = el.get("ionization_energy", "")

    # --- Element card (left side) ---
    card_x, card_y = 60, 80
    card_w, card_h = 300, 420
    draw.rectangle([card_x, card_y, card_x + card_w, card_y + card_h],
                   fill=255, outline=20, width=3)

    # Atomic number (top-left of card)
    draw.text((card_x + 20, card_y + 20), str(num),
              fill=30, font=get_font(64, bold=True), anchor="lt")
    # Atomic mass (top-right of card)
    draw.text((card_x + card_w - 20, card_y + 30), str(mass),
              fill=60, font=get_font(36), anchor="rt")
    # Symbol (large, centered)
    draw.text((card_x + card_w // 2, card_y + 200), symbol,
              fill=10, font=get_font(160, bold=True), anchor="mm")
    # Name below symbol
    draw.text((card_x + card_w // 2, card_y + 310), name,
              fill=30, font=get_font(32), anchor="mt")
    # Category badge
    if category:
        cat_font = get_font(22, bold=True)
        cw = cat_font.getlength(category) + 20
        cx = card_x + (card_w - cw) // 2
        cy = card_y + 360
        draw.rounded_rectangle([cx, cy, cx + cw, cy + 34], radius=6, fill=60)
        draw.text((cx + cw // 2, cy + 17), category, fill=230, font=cat_font, anchor="mm")

    # --- Element name header (right side) ---
    header_font = _fit_font_to_width(name.upper(), WIDTH - 420 - PAD, 56, min_size=30, bold=True)
    draw.text((420, 90), _truncate_text(header_font, name.upper(), WIDTH - 420 - PAD),
              fill=20, font=header_font, anchor="lt")
    draw.line([(420, 155), (WIDTH - PAD, 155)], fill=120, width=2)

    # --- Properties grid (right side, two columns) ---
    props_left = [
        ("State", state),
        ("Electronegativity", str(electronegativity) if electronegativity else ""),
        ("Boiling Point", str(boiling) if boiling else ""),
        ("Oxidation States", str(oxidation) if oxidation else ""),
        ("Atomic Radius", f"{radius} pm" if radius else ""),
        ("Electron Affinity", f"{affinity} eV" if affinity else ""),
    ]
    props_right = [
        ("Electron Config", str(config) if config else ""),
        ("Melting Point", str(melting) if melting else ""),
        ("Density", f"{density} g/cm³" if density else ""),
        ("Discovered", str(discovered) if discovered else ""),
        ("Ionization Energy", f"{ionization} eV" if ionization else ""),
        ("Group", str(category) if category else ""),
    ]

    label_font = get_font(22, bold=True)
    value_font = get_font(26)
    row_h = 58
    ly = 180
    ry = 180

    for label, value in props_left:
        if not value:
            continue
        # Label in rounded box
        label_text = _truncate_text(label_font, label, 200)
        lw = label_font.getlength(label_text) + 12
        draw.rounded_rectangle([420, ly, 420 + lw, ly + 30], radius=4, outline=40, width=1)
        draw.text((426, ly + 15), label_text, fill=40, font=label_font, anchor="lm")
        # Value next to it
        value_max = WIDTH - (430 + lw) - PAD
        draw.text((430 + lw, ly + 15), _truncate_text(value_font, value, value_max), fill=20, font=value_font, anchor="lm")
        ly += row_h

    for label, value in props_right:
        if not value:
            continue
        label_text = _truncate_text(label_font, label, 200)
        lw = label_font.getlength(label_text) + 12
        rx = 720
        draw.rounded_rectangle([rx, ry, rx + lw, ry + 30], radius=4, outline=40, width=1)
        draw.text((rx + 6, ry + 15), label_text, fill=40, font=label_font, anchor="lm")
        value_max = WIDTH - (rx + lw + 10) - PAD
        draw.text((rx + lw + 10, ry + 15), _truncate_text(value_font, value, value_max),
                  fill=20, font=value_font, anchor="lm")
        ry += row_h

    return img
