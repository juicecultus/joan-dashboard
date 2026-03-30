from .shared import *

# ── 14. Google Tasks Todo ───────────────────────────────────────────

def render_todo_list() -> Image.Image:
    """Full-screen Google Tasks view — large, readable, standalone."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    from joan_dashboard import get_google_creds

    # Header
    draw.text((WIDTH // 2, 70), "To Do", fill=0, font=get_font(56, bold=True), anchor="mm")
    draw.text((WIDTH // 2, 125), datetime.now().strftime("%A %d %B"), fill=140, font=get_font(28), anchor="mm")
    draw.line([(PAD, 160), (WIDTH - PAD, 160)], fill=200, width=2)

    def _fetch():
        creds = get_google_creds()
        if not creds:
            raise ValueError("No Google credentials")
        from googleapiclient.discovery import build
        service = build("tasks", "v1", credentials=creds)
        tasklists = service.tasklists().list(maxResults=10).execute().get("items", [])
        items = []
        for tl in tasklists:
            result = service.tasks().list(
                tasklist=tl["id"], showCompleted=False, maxResults=20
            ).execute()
            for t in result.get("items", []):
                if t.get("title", "").strip():
                    due = ""
                    if t.get("due"):
                        try:
                            due_dt = datetime.fromisoformat(t["due"].rstrip("Z"))
                            due = due_dt.strftime("%d %b")
                        except Exception:
                            pass
                    items.append({"title": t["title"], "due": due, "list": tl.get("title", "")})
        return items

    tasks = _cache_fetch("todo_all", 120, 1800, _fetch) or []  # 2min TTL, 30min stale

    if not tasks:
        draw.text((WIDTH // 2, HEIGHT // 2), "No tasks!", fill=120, font=get_font(44), anchor="mm")
        draw.text((WIDTH // 2, HEIGHT // 2 + 60), "All caught up ✓", fill=160, font=get_font(30), anchor="mm")
        _footer(draw, now_str())
        return img

    dy = 195
    LINE_H = 56
    BX = PAD + 20  # box left edge (same as dashboard B_L)

    for task in tasks[:14]:  # max 14 tasks for screen space
        # Exact same checkbox rendering as main dashboard
        box_top = dy + (LINE_H - 24) // 2
        draw.rectangle([BX, box_top, BX + 24, box_top + 24], outline=60, width=2)
        title = task["title"]
        title_font = get_font(26)
        title_max = WIDTH - (BX + 36) - (PAD + 120)
        draw.text((BX + 36, dy + LINE_H // 2), _truncate_text(title_font, title, title_max),
                  fill=20, font=title_font, anchor="lm")

        if task["due"]:
            draw.text((WIDTH - PAD - 20, dy + LINE_H // 2), task["due"], fill=140, font=get_font(22), anchor="rm")

        dy += LINE_H
        if dy > HEIGHT - 80:
            break

    # Task count footer
    if len(tasks) > 14:
        draw.text((WIDTH // 2, HEIGHT - 70), f"+{len(tasks) - 14} more tasks", fill=160, font=get_font(24), anchor="mm")

    _footer(draw, now_str())
    return img
