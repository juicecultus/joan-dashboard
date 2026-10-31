from .shared import *

# ── 20. Sleep Screen ────────────────────────────────────────────────

def render_sleep_screen(wake_time="07:00") -> Image.Image:
    """Beautiful sleep screen shown outside active hours — moon, stars, Zzz."""
    img = Image.new("L", (WIDTH, HEIGHT), 15)  # near-black background
    draw = ImageDraw.Draw(img)

    # Stars — scattered small dots and crosses
    rng = random.Random(42)  # fixed seed so stars don't flicker each render
    for _ in range(120):
        sx = rng.randint(40, WIDTH - 40)
        sy = rng.randint(40, HEIGHT - 40)
        brightness = rng.randint(60, 180)
        size = rng.choice([1, 1, 1, 2, 2, 3])
        if size <= 2:
            draw.ellipse([sx - size, sy - size, sx + size, sy + size], fill=brightness)
        else:
            # Cross-shaped star
            draw.line([(sx - size, sy), (sx + size, sy)], fill=brightness, width=1)
            draw.line([(sx, sy - size), (sx, sy + size)], fill=brightness, width=1)

    # A few brighter stars with rays
    for _ in range(8):
        sx = rng.randint(100, WIDTH - 100)
        sy = rng.randint(60, HEIGHT - 100)
        draw.ellipse([sx - 3, sy - 3, sx + 3, sy + 3], fill=220)
        for angle in [0, 45, 90, 135]:
            rad = math.radians(angle)
            ray = rng.randint(6, 12)
            draw.line([(sx - int(ray * math.cos(rad)), sy - int(ray * math.sin(rad))),
                       (sx + int(ray * math.cos(rad)), sy + int(ray * math.sin(rad)))],
                      fill=140, width=1)

    # Crescent moon — upper right area
    moon_cx, moon_cy, moon_r = WIDTH - 320, 250, 120
    draw.ellipse([moon_cx - moon_r, moon_cy - moon_r, moon_cx + moon_r, moon_cy + moon_r], fill=210)
    # Cut out crescent with overlapping dark circle
    cut_cx = moon_cx + 50
    cut_cy = moon_cy - 30
    draw.ellipse([cut_cx - moon_r, cut_cy - moon_r, cut_cx + moon_r, cut_cy + moon_r], fill=15)

    # Soft glow around moon
    for i in range(3):
        gr = moon_r + 15 + i * 12
        draw.ellipse([moon_cx - gr, moon_cy - gr, moon_cx + gr, moon_cy + gr], outline=25 + i * 3, width=1)

    # "Zzz" floating upward from center
    zzz_data = [
        (WIDTH // 2 + 60, HEIGHT // 2 - 80, 90, 100),
        (WIDTH // 2 + 140, HEIGHT // 2 - 180, 65, 130),
        (WIDTH // 2 + 200, HEIGHT // 2 - 260, 46, 155),
    ]
    for zx, zy, size, fill in zzz_data:
        draw.text((zx, zy), "Z", fill=fill, font=get_font(size, bold=True), anchor="mm")

    # Main text
    draw.text((WIDTH // 2, HEIGHT // 2 + 60), "Sleeping", fill=120, font=get_font(72, bold=True), anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 130), "Good night", fill=70, font=get_font(36), anchor="mm")

    return img
