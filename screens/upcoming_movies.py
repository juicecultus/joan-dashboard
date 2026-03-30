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
    if poster_path:
        try:
            poster_url = f"https://image.tmdb.org/t/p/w342{poster_path}"
            r = requests.get(poster_url, timeout=10)
            if r.status_code == 200:
                poster = Image.open(BytesIO(r.content)).convert("L")
                # Scale poster to fit left side
                pw, ph = poster.size
                target_h = 500
                scale = target_h / ph
                poster = poster.resize((int(pw * scale), target_h), Image.LANCZOS)
                from PIL import ImageOps
                poster = ImageOps.autocontrast(poster, cutoff=2)
                img.paste(poster, (PAD + 20, 180))
                poster_loaded = True
                poster_w = int(pw * scale)
        except Exception as e:
            print(f"[movies] Poster failed: {e}")

    # First movie details
    text_x = PAD + poster_w + 40 if poster_loaded else PAD + 40
    text_max = WIDTH - text_x - PAD

    title = first.get("title", "Untitled")
    release = first.get("release_date", "")
    overview = first.get("overview", "")
    vote = first.get("vote_average", 0)

    y = 190
    # Title
    title_font = get_font(38, bold=True)
    title_lines = _wrap_text(title_font, title, text_max)
    for ln in title_lines[:2]:
        draw.text((text_x, y), ln, fill=0, font=title_font, anchor="lt")
        y += 50

    y += 10
    if release:
        try:
            rd = datetime.strptime(release, "%Y-%m-%d")
            draw.text((text_x if poster_loaded else PAD + 40, y), rd.strftime("%d %B %Y"), fill=80, font=get_font(28), anchor="lt")
            y += 40
        except ValueError:
            pass

    if vote:
        draw.text((text_x if poster_loaded else PAD + 40, y), f"★ {vote:.1f}/10", fill=60, font=get_font(28, bold=True), anchor="lt")
        y += 40

    # Overview (short)
    if overview:
        y += 10
        ox = text_x if poster_loaded else PAD + 40
        o_max = text_max if poster_loaded else WIDTH - PAD * 2 - 40
        font = get_font(24)
        words = overview.split()
        lines, line = [], ""
        for w in words:
            test = f"{line} {w}".strip()
            if font.getlength(test) > o_max:
                if line:
                    lines.append(line)
                line = w
            else:
                line = test
        if line:
            lines.append(line)
        max_lines = 6 if poster_loaded else 4
        for ln in lines[:max_lines]:
            draw.text((ox, y), ln, fill=100, font=font, anchor="lt")
            y += 30

    # Other upcoming movies list
    list_y = max(700, y + 20)
    draw.line([(PAD, list_y - 10), (WIDTH - PAD, list_y - 10)], fill=200, width=1)
    draw.text((PAD + 20, list_y + 5), "Also coming soon:", fill=140, font=get_font(24), anchor="lt")
    list_y += 45

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
        draw.text((PAD + 40, list_y), f"• {_truncate_text(list_font, t, WIDTH - PAD * 2 - 140)}",
                  fill=40, font=list_font, anchor="lt")
        if date_str:
            draw.text((WIDTH - PAD - 20, list_y), date_str, fill=140, font=get_font(22), anchor="rt")
        list_y += 45

    _footer(draw, now_str())
    return img
