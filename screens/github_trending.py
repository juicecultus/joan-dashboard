from .shared import *

# ── GitHub Trending Repos ────────────────────────────────────────────

def _fetch_github_trending():
    """Fetch daily trending repos from GitHub Trending API."""
    r = requests.get(
        "https://trend.doforce.dpdns.org/repo",
        params={"since": "daily"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def render_github_trending() -> Image.Image:
    """Render a GitHub Trending Repos screen (two-column layout, e-ink)."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    repos = _cache_fetch("github_trending", 3600, 43200, _fetch_github_trending)

    # --- Footer bar ---
    footer_h = 60
    footer_y = HEIGHT - footer_h
    draw.rectangle([0, footer_y, WIDTH, HEIGHT], fill=20)
    # GitHub icon (simple octocat silhouette text)
    draw.text((PAD, footer_y + footer_h // 2), "GitHub Trending Repos",
              fill=220, font=get_font(28, bold=True), anchor="lm")
    draw.text((WIDTH - PAD, footer_y + footer_h // 2), "Daily",
              fill=160, font=get_font(26), anchor="rm")

    if not repos:
        _centered_text(draw, HEIGHT // 2 - 30, "No trending data available", 36, fill=100)
        return img

    # Two-column layout matching the reference image
    repos = repos[:10]
    col_w = (WIDTH - PAD * 2 - 40) // 2
    left_x = PAD
    right_x = PAD + col_w + 40
    start_y = 30

    for i, repo in enumerate(repos):
        col_x = left_x if i < 5 else right_x
        idx = i % 5
        y = start_y + idx * (footer_y - start_y - 20) // 5

        # Rank number
        rank_font = get_font(36, bold=True)
        draw.text((col_x, y + 2), str(i + 1), fill=120, font=rank_font, anchor="lt")

        # Repo name: owner / name
        repo_name = repo.get("repo", "/unknown").lstrip("/")
        parts = repo_name.split("/", 1)
        name_x = col_x + 45
        if len(parts) == 2:
            owner_font = get_font(28)
            name_font = get_font(30, bold=True)
            owner_text = parts[0] + " / "
            owner_text = _truncate_text(owner_font, owner_text, col_w - 120)
            draw.text((name_x, y), owner_text, fill=80, font=owner_font, anchor="lt")
            owner_w = _text_width(owner_font, owner_text)
            repo_max = col_w - 50 - owner_w
            draw.text((name_x + owner_w, y), _truncate_text(name_font, parts[1], repo_max), fill=0, font=name_font, anchor="lt")
        else:
            repo_font = get_font(30, bold=True)
            draw.text((name_x, y), _truncate_text(repo_font, repo_name, col_w - 50), fill=0, font=repo_font, anchor="lt")

        # Description (truncated)
        desc = repo.get("desc", "")
        if desc:
            max_desc_w = col_w - 50
            desc_font = get_font(24)
            # Truncate desc to fit
            if desc_font.getlength(desc) > max_desc_w:
                while len(desc) > 10 and desc_font.getlength(desc + "...") > max_desc_w:
                    desc = desc[:-1]
                desc = desc.rstrip() + "..."
            draw.text((name_x, y + 38), desc, fill=100, font=desc_font, anchor="lt")

        # Stats line: language, stars, forks, change
        stats_y = y + 68
        sx = name_x
        stats_font = get_font(22)
        stats_bold = get_font(22, bold=True)

        lang = repo.get("lang", "")
        if lang:
            # Language dot
            draw.ellipse([sx, stats_y + 4, sx + 14, stats_y + 18], fill=80)
            sx += 18
            draw.text((sx, stats_y), lang, fill=80, font=stats_font, anchor="lt")
            sx += stats_font.getlength(lang) + 16

        stars = repo.get("stars", 0)
        if stars:
            star_str = f"{stars:,}" if stars < 100000 else f"{stars // 1000}k"
            draw.text((sx, stats_y), "*", fill=80, font=stats_bold, anchor="lt")
            sx += 16
            draw.text((sx, stats_y), star_str, fill=80, font=stats_font, anchor="lt")
            sx += stats_font.getlength(star_str) + 16

        forks = repo.get("forks", 0)
        if forks:
            fork_str = f"{forks:,}" if forks < 100000 else f"{forks // 1000}k"
            draw.text((sx, stats_y), "Y", fill=80, font=stats_bold, anchor="lt")
            sx += 18
            draw.text((sx, stats_y), fork_str, fill=80, font=stats_font, anchor="lt")
            sx += stats_font.getlength(fork_str) + 20

        change = repo.get("change", 0)
        if change:
            change_str = f"* {change:,} today"
            # Right-align the change in the column
            draw.text((col_x + col_w - 5, stats_y), _truncate_text(stats_bold, change_str, col_w - 20),
                      fill=40, font=stats_bold, anchor="rt")

        # Separator line (except last in column)
        if idx < 4:
            sep_y = y + 100
            draw.line([(name_x, sep_y), (col_x + col_w, sep_y)], fill=210, width=1)

    return img
