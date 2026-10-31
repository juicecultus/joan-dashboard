from .shared import *

# ── 14. Google Tasks Todo ───────────────────────────────────────────

def render_todo_list() -> Image.Image:
    """Full-screen Google Tasks view — large, readable, standalone."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    from joan_dashboard import get_google_creds

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

    tasks = _cache_fetch("todo_all", 120, 1800, lambda: {"items": _fetch()})  # 2min TTL, 30min stale

    tasks = _require(tasks)["items"]
    if not tasks:
        return _statement("All caught up", "No tasks to do")
    task = _select(tasks)
    return _statement(task['title'], "To do" + (" by " + task['due'] if task.get('due') else ""))
