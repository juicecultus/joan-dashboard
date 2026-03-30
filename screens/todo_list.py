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

    # ── 2-column grid layout ──────────────────────────────────────
    TOP_Y = 195
    BOT_Y = HEIGHT - 70          # leave room for footer
    COL_GAP = 40                 # gap between columns
    COL_W = (WIDTH - 2 * PAD - COL_GAP) // 2
    BOX_SZ = 32                  # checkbox size (scaled with text)
    BOX_PAD = 14                 # space after checkbox
    title_font = get_font(39)
    due_font = get_font(33)

    # Split tasks into two columns (fill left first, then right)
    max_visible = 20             # 10 per column
    visible = tasks[:max_visible]
    mid = (len(visible) + 1) // 2
    col_tasks = [visible[:mid], visible[mid:]]

    # Row height: divide available height evenly per column
    rows_per_col = max(mid, 1)
    avail_h = BOT_Y - TOP_Y
    ROW_H = min(avail_h // rows_per_col, 80)

    # Measure actual text visual height for precise vertical centering
    _title_bbox = title_font.getbbox("Ag")
    _title_h = _title_bbox[3] - _title_bbox[1]
    _due_bbox = due_font.getbbox("Ag")
    _due_h = _due_bbox[3] - _due_bbox[1]
    BOX_Y_OFFSET = -7

    for ci, col in enumerate(col_tasks):
        col_x = PAD + ci * (COL_W + COL_GAP)

        for ri, task in enumerate(col):
            row_y = TOP_Y + ri * ROW_H
            row_cy = row_y + ROW_H // 2   # vertical centre of row

            # Checkbox — aligned to text visual centre
            text_cy = row_cy - _title_h // 2 - _title_bbox[1] + _title_h // 2
            box_top = text_cy - BOX_SZ // 2 + BOX_Y_OFFSET
            draw.rectangle(
                [col_x, box_top, col_x + BOX_SZ, box_top + BOX_SZ],
                outline=60, width=2,
            )

            # Due date (right-aligned in column) — measure first for title truncation
            due_w = 0
            if task["due"]:
                due_w = _text_width(due_font, task["due"]) + 16
                due_top = row_cy - _due_h // 2 - _due_bbox[1]
                draw.text(
                    (col_x + COL_W, due_top),
                    task["due"], fill=140, font=due_font, anchor="rt",
                )

            # Title — vertically centred using measured bbox, not font metrics
            text_x = col_x + BOX_SZ + BOX_PAD
            title_max = COL_W - BOX_SZ - BOX_PAD - due_w
            title_top = text_cy - _title_h // 2 - _title_bbox[1]
            title_str = task["title"].replace("\n", " ").strip()
            draw.text(
                (text_x, title_top),
                _truncate_text(title_font, title_str, title_max),
                fill=20, font=title_font, anchor="lt",
            )

    # Task count overflow
    if len(tasks) > max_visible:
        draw.text(
            (WIDTH // 2, HEIGHT - 70),
            f"+{len(tasks) - max_visible} more tasks",
            fill=160, font=get_font(24), anchor="mm",
        )

    _footer(draw, now_str())
    return img
