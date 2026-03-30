from .shared import *

# ── 4. Family Photo ──────────────────────────────────────────────────

PHOTOS_DIR = os.environ.get("PHOTOS_DIR", os.path.join(os.path.dirname(__file__), "photos"))


def render_family_photo() -> Image.Image:
    """Display a random photo from PHOTOS_DIR — new photo each rotation.

    Set PHOTOS_DIR env var or drop images into the photos/ folder.
    On Pi, mount a network share (e.g. SMB) to /mnt/joan_photos.
    """
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    if not os.path.isdir(PHOTOS_DIR):
        os.makedirs(PHOTOS_DIR, exist_ok=True)

    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    photos = [f for f in os.listdir(PHOTOS_DIR) if os.path.splitext(f)[1].lower() in exts]
    print(f"[photo] PHOTOS_DIR={PHOTOS_DIR}  found {len(photos)} photos")

    if not photos:
        draw.text((WIDTH // 2, HEIGHT // 2 - 40), "Family Photos", fill=0, font=get_font(50, bold=True), anchor="mm")
        draw.text((WIDTH // 2, HEIGHT // 2 + 20), "Add photos to:", fill=120, font=get_font(30), anchor="mm")
        draw.text((WIDTH // 2, HEIGHT // 2 + 60), PHOTOS_DIR, fill=160, font=get_font(22), anchor="mm")
        return img

    photo_file = random.choice(photos)

    try:
        photo = Image.open(os.path.join(PHOTOS_DIR, photo_file))
        photo = photo.convert("L")

        # Resize to fill, maintaining aspect ratio, then center-crop
        pw, ph = photo.size
        scale = max(WIDTH / pw, HEIGHT / ph)
        new_w = int(pw * scale)
        new_h = int(ph * scale)
        photo = photo.resize((new_w, new_h), Image.LANCZOS)

        # Center crop
        left = (new_w - WIDTH) // 2
        top = (new_h - HEIGHT) // 2
        photo = photo.crop((left, top, left + WIDTH, top + HEIGHT))

        # Enhance contrast for e-ink
        from PIL import ImageOps
        photo = ImageOps.autocontrast(photo, cutoff=1)

        print(f"[photo] Rendered: {photo_file}")
        return photo
    except Exception as e:
        print(f"[photo] Failed to load {photo_file}: {e}")
        draw.text((WIDTH // 2, HEIGHT // 2), "Error loading photo", fill=80, font=get_font(40), anchor="mm")
        return img
