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
    img, draw = _canvas()
    draw.rounded_rectangle((410,40,790,420),radius=25,outline=0,width=12)
    _panel(draw,(25,475,1150,1100))
    _poster_text(draw,task['title'],(45,500,1110,900),500)
    _poster_text(draw,'By '+task['due'] if task.get('due') else 'To do',(45,1480,1110,80),100,False)
    return img
