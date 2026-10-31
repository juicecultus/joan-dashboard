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

    movie = _select(_require(movies))
    title = movie.get('title', 'Untitled')
    date = movie.get('release_date', '')
    caption = title
    poster = _image_url("https://image.tmdb.org/t/p/w780" + movie['poster_path']) if movie.get('poster_path') else None
    return _picture(poster, caption, portrait=True) if poster else _statement(title, date)
