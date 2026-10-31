from .shared import *

# ── Literate Movies (Letterboxd) ─────────────────────────────────────

LETTERBOXD_LIST_URL = "https://letterboxd.com/shawn_stubbs/list/literate-movies/"


def _fetch_literate_movies():
    """Fetch the full list of movie slugs from the Letterboxd list."""
    headers = {"User-Agent": "JoanDashboard/1.0"}
    all_slugs = []
    # Fetch page 1 to discover total pages
    r = requests.get(LETTERBOXD_LIST_URL, headers=headers, timeout=15)
    r.raise_for_status()
    slugs = re.findall(r'data-target-link="/film/([^/]+)/"', r.text)
    all_slugs.extend(slugs)
    pages = re.findall(r'/page/(\d+)/', r.text)
    max_page = max(int(p) for p in pages) if pages else 1
    # Fetch remaining pages (cap at 5 pages = 500 movies to keep it fast)
    for pg in range(2, min(max_page + 1, 6)):
        try:
            r2 = requests.get(f"{LETTERBOXD_LIST_URL}page/{pg}/",
                              headers=headers, timeout=10)
            r2.raise_for_status()
            all_slugs.extend(re.findall(r'data-target-link="/film/([^/]+)/"', r2.text))
        except Exception:
            break
    return all_slugs


def _fetch_movie_details(slug):
    """Fetch movie details from Letterboxd film page + TMDB poster."""
    headers = {"User-Agent": "JoanDashboard/1.0"}
    url = f"https://letterboxd.com/film/{slug}/"
    import html as html_mod
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    page = r.text

    # Title + year
    title = ""
    year = ""
    # Title is in <h1><span class="name ...">Title</span></h1>
    tm = re.search(r'<h1[^>]*>\s*<span[^>]*class="name[^"]*"[^>]*>([^<]+)</span>', page)
    if not tm:
        tm = re.search(r'<h1[^>]*>(.*?)</h1>', page, re.DOTALL)
    if tm:
        title = html_mod.unescape(re.sub(r'<[^>]+>', '', tm.group(1)).strip())
    ym = re.search(r'href="/films/year/(\d{4})/"', page)
    if ym:
        year = ym.group(1)

    # Director
    director = ""
    dm = re.search(r'<a[^>]*href="/director/[^"]*"[^>]*><span[^>]*>([^<]+)</span></a>', page)
    if dm:
        director = html_mod.unescape(dm.group(1))

    # Poster image (portrait crop, not the landscape og:image)
    poster_url = ""
    pm = re.search(r'(https://a\.ltrbxd\.com/resized/[^"\s]*0-230-0-345[^"\s]*)', page)
    if pm:
        # Upscale from 230x345 to 500x750 for better quality
        poster_url = pm.group(1).replace('0-230-0-345', '0-500-0-750')
    else:
        # Fallback to og:image
        pm2 = re.search(r'og:image["\s]+content="([^"]+)"', page)
        if pm2:
            poster_url = pm2.group(1)

    # Description/tagline
    desc = ""
    desc_m = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', page)
    if desc_m:
        desc = html_mod.unescape(desc_m.group(1).strip())
        # Trim to reasonable length
        if len(desc) > 200:
            desc = desc[:197].rstrip() + "..."

    # Cast
    cast = []
    cast_matches = re.findall(r'<a[^>]*href="/actor/[^"]*"[^>]*>([^<]+)</a>', page)
    cast = [html_mod.unescape(c.strip()) for c in cast_matches[:5]]

    return {
        "title": title, "year": year, "director": director,
        "poster_url": poster_url, "desc": desc, "cast": cast,
        "slug": slug,
    }


def render_literate_movies() -> Image.Image:
    """Show a movie from the Literate Movies Letterboxd list, rotating daily."""
    img = Image.new("L", (WIDTH, HEIGHT), 230)
    draw = ImageDraw.Draw(img)

    # Get list of all movie slugs (cached 24h)
    slugs = _cache_fetch("literate_movies_list", 86400, 604800, _fetch_literate_movies)
    _require(slugs)

    # Pick movie based on day of year
    day = datetime.now().timetuple().tm_yday
    slug = slugs[day % len(slugs)]

    # Get movie details (cached 7 days)
    movie = _cache_fetch(f"litmovie:{slug}", 604800, 2592000,
                         lambda: _fetch_movie_details(slug))
    _require(movie)

    title = movie.get("title", slug.replace("-", " ").title())
    year = movie.get("year", "")
    director = movie.get("director", "")
    desc = movie.get("desc", "")
    cast = movie.get("cast", [])
    poster_url = movie.get("poster_url", "")

    poster = _image_url(poster_url) if poster_url else None
    caption = title
    return _picture(poster, caption, portrait=True, credit=" · ".join(v for v in (director,year) if v)) if poster else _statement(title, year)
