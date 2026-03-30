from .shared import *

# ── 18. Upcoming Movies ────────────────────────────────────────────

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")


def render_upcoming_movies() -> Image.Image:
    """Display upcoming movies from The Movie Database (TMDB)."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    def _fetch():
        if not TMDB_API_KEY:
            # Use the discover endpoint with no auth for trending (v3 needs key)
            raise ValueError("Set TMDB_API_KEY env var (free at themoviedb.org)")
        url = "https://api.themoviedb.org/3/movie/upcoming"
        params = {"api_key": TMDB_API_KEY, "language": "en-GB", "region": "GB", "page": 1}
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        results = r.json().get("results", [])
        if not results:
            raise ValueError("No upcoming movies")
        return results[:6]

    movies = _cache_fetch("movies", 3600, 21600, _fetch)  # 1h TTL, 6h stale

    # Header
    draw.text((WIDTH // 2, 70), "Upcoming Movies", fill=0, font=get_font(50, bold=True), anchor="mm")
    draw.text((WIDTH // 2, 120), "In Cinemas Soon", fill=140, font=get_font(26), anchor="mm")
    draw.line([(PAD, 150), (WIDTH - PAD, 150)], fill=200, width=2)

    if not movies:
        msg = "Set TMDB_API_KEY for movie listings" if not TMDB_API_KEY else "Could not load movies"
        draw.text((WIDTH // 2, HEIGHT // 2 - 20), msg, fill=120, font=get_font(30), anchor="mm")
        if not TMDB_API_KEY:
            draw.text((WIDTH // 2, HEIGHT // 2 + 30), "Free key at themoviedb.org", fill=160, font=get_font(24), anchor="mm")
        _footer(draw, now_str())
        return img

    # Try to load poster for the first movie
    poster_loaded = False
    first = movies[0]
    poster_path = first.get("poster_path", "")

    footer_h = 60
    footer_y = HEIGHT - footer_h
    content_top = 170
    gap = 36
    col_w = int((WIDTH - PAD * 2 - gap) / 2)
    col_h = footer_y - content_top
    left_x = PAD + 20
    right_x = left_x + col_w + gap

    if poster_path:
        try:
            poster_url = f"https://image.tmdb.org/t/p/w342{poster_path}"
            r = requests.get(poster_url, timeout=10)
            if r.status_code == 200:
                poster = Image.open(BytesIO(r.content)).convert("L")
                # Scale poster to fill the entire left column while preserving aspect ratio
                pw, ph = poster.size
                scale = min(col_w / pw, col_h / ph)
                new_w, new_h = int(pw * scale), int(ph * scale)
                poster = poster.resize((new_w, new_h), Image.LANCZOS)
                from PIL import ImageOps
                poster = ImageOps.autocontrast(poster, cutoff=2)
                poster_x = left_x + (col_w - new_w) // 2
                poster_y = content_top + (col_h - new_h) // 2
                img.paste(poster, (poster_x, poster_y))
                draw.rectangle([left_x, content_top, left_x + col_w, content_top + col_h], outline=180, width=2)
                poster_loaded = True
        except Exception as e:
            print(f"[movies] Poster failed: {e}")

    if not poster_loaded:
        draw.rectangle([left_x, content_top, left_x + col_w, content_top + col_h], fill=235, outline=180, width=2)
        draw.text((left_x + col_w // 2, content_top + col_h // 2), "Poster unavailable",
                  fill=110, font=get_font(32, bold=True), anchor="mm")

    title = first.get("title", "Untitled")
    release = first.get("release_date", "")
    overview = first.get("overview", "")
    vote = first.get("vote_average", 0)

    # Right column split into movie context (top) and list (bottom)
    right_top_h = int(col_h * 0.56)
    right_bottom_h = col_h - right_top_h
    right_top_y = content_top
    right_bottom_y = content_top + right_top_h

    # Movie context in the top-right block
    title_font = get_font(38, bold=True)
    title_lines = _wrap_text(title_font, title, col_w)
    y = right_top_y + 10
    for ln in title_lines[:2]:
        draw.text((right_x, y), ln, fill=0, font=title_font, anchor="lt")
        y += 48

    if release:
        try:
            rd = datetime.strptime(release, "%Y-%m-%d")
            draw.text((right_x, y), rd.strftime("%d %B %Y"), fill=80, font=get_font(28), anchor="lt")
            y += 38
        except ValueError:
            pass

    if vote:
        star_size = 12
        _draw_star(draw, right_x + star_size, y + 18, star_size, fill=60)
        draw.text((right_x + star_size * 2 + 8, y), f"{vote:.1f}/10", fill=60, font=get_font(28, bold=True), anchor="lt")
        y += 38

    if overview:
        y += 8
        font = get_font(24)
        lines = _wrap_text(font, overview, col_w)
        for ln in lines[:max(3, (right_top_h - (y - right_top_y)) // 30)]:
            draw.text((right_x, y), ln, fill=100, font=font, anchor="lt")
            y += 30

    # Other upcoming movies list in the bottom-right block
    draw.line([(right_x, right_bottom_y + 10), (right_x + col_w, right_bottom_y + 10)], fill=200, width=1)
    draw.text((right_x, right_bottom_y + 22), "Also coming soon:", fill=140, font=get_font(24), anchor="lt")

    list_y = right_bottom_y + 58
    for m in movies[1:5]:
        t = m.get("title", "")
        rd = m.get("release_date", "")
        date_str = ""
        if rd:
            try:
                date_str = datetime.strptime(rd, "%Y-%m-%d").strftime("%d %b")
            except ValueError:
                pass
        list_font = get_font(26)
        _draw_bullet(draw, right_x + 15, list_y + 14, 8, fill=40)
        draw.text((right_x + 35, list_y), _truncate_text(list_font, t, col_w - 145),
                  fill=40, font=list_font, anchor="lt")
        if date_str:
            draw.text((right_x + col_w - 10, list_y), date_str, fill=140, font=get_font(22), anchor="rt")
        list_y += 42

    _footer(draw, now_str())
    return img
