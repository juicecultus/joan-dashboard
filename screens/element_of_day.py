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

    # --- Header ---
    title_font = _fit_font_to_width(name.upper(), WIDTH - PAD * 2, 76, min_size=50, bold=True)
    draw.text((WIDTH // 2, 72), _truncate_text(title_font, name.upper(), WIDTH - PAD * 2),
              fill=20, font=title_font, anchor="mt")
    draw.line([(PAD, 166), (WIDTH - PAD, 166)], fill=120, width=3)

    # --- Element card (left column) ---
    card_x = 60
    gap = 48
    card_w = int((WIDTH - PAD * 2 - gap) / 2)
    card_h = int(HEIGHT * 0.7)
    content_top = 194
    card_y = content_top + max(0, ((HEIGHT - footer_h - content_top - 20) - card_h) // 2)
    draw.rectangle([card_x, card_y, card_x + card_w, card_y + card_h],
                   fill=255, outline=20, width=3)

    # Atomic number (top-left of card)
    draw.text((card_x + 22, card_y + 22), str(num),
              fill=30, font=get_font(82, bold=True), anchor="lt")
    # Atomic mass (top-right of card)
    draw.text((card_x + card_w - 22, card_y + 30), str(mass),
              fill=60, font=get_font(42), anchor="rt")
    # Symbol (large, centered)
    draw.text((card_x + card_w // 2, card_y + int(card_h * 0.43)), symbol,
              fill=10, font=get_font(190, bold=True), anchor="mm")
    # Name below symbol
    draw.text((card_x + card_w // 2, card_y + int(card_h * 0.67)), name,
              fill=30, font=get_font(40), anchor="mt")
    # Category badge
    if category:
        cat_font = get_font(26, bold=True)
        cw = cat_font.getlength(category) + 28
        cx = card_x + (card_w - cw) // 2
        cy = card_y + int(card_h * 0.77)
        draw.rounded_rectangle([cx, cy, cx + cw, cy + 44], radius=8, fill=60)
        draw.text((cx + cw // 2, cy + 22), category, fill=230, font=cat_font, anchor="mm")

    # --- Properties list (right column) ---
    right_x = card_x + card_w + gap
    right_w = card_w
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

    label_font = get_font(28, bold=True)
    value_font = get_font(34)
    row_h = 70

    props = props_left + props_right
    block_h = max(0, (len(props) - 1) * row_h + 42)
    row_y = content_top + max(0, ((footer_y - content_top) - block_h) // 2)
    for label, value in props:
        if not value:
            continue
        label_text = _truncate_text(label_font, label, 240)
        lw = label_font.getlength(label_text) + 18
        draw.rounded_rectangle([right_x, row_y, right_x + lw, row_y + 42], radius=7, outline=40, width=1)
        draw.text((right_x + 8, row_y + 21), label_text, fill=40, font=label_font, anchor="lm")
        value_max = WIDTH - (right_x + lw + 18) - PAD
        draw.text((right_x + lw + 14, row_y + 21), _truncate_text(value_font, value, value_max),
                  fill=20, font=value_font, anchor="lm")
        row_y += row_h

    return img
