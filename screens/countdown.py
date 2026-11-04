from .shared import *

# ── 3. Countdown ─────────────────────────────────────────────────────

def render_countdown() -> Image.Image:
    """Show countdown to next notable upcoming event."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)
    now = datetime.now()

    # Fetch upcoming events and find the next future one
    week_events = fetch_week_events()
    today_key = now.strftime("%Y-%m-%d")
    upcoming = []

    for date_key, events in sorted(week_events.items()):
        if date_key <= today_key:
            continue
        for ev in events:
            try:
                event_date = datetime.strptime(date_key, "%Y-%m-%d")
                delta = (event_date.date() - now.date()).days
                upcoming.append((delta, ev["title"], event_date))
            except ValueError:
                pass

    if not upcoming:
        # Fallback: show days until end of month
        import calendar as cal_mod
        last_day = cal_mod.monthrange(now.year, now.month)[1]
        end_of_month = now.replace(day=last_day)
        delta = (end_of_month.date() - now.date()).days
        upcoming = [(delta, f"End of {now.strftime('%B')}", end_of_month)]

    upcoming.sort(key=lambda x: x[0])

    days, title, event_date = upcoming[0]
    from .flip_date import _draw_flip_panel
    img, draw = _canvas()
    # A physical flip-calendar idiom gives the countdown a recognisable shape.
    _draw_flip_panel(img,draw,40,45,1120,790,str(days),720,radius=36)
    for x in (30,1140):
        draw.rounded_rectangle((x,400,x+30,480),radius=8,fill=255,outline=0,width=4)
    _poster_text(draw,'Today' if days==0 else 'Tomorrow' if days==1 else 'days to go',
                  (70,875,1060,120),130,False)
    _panel(draw,(25,1040,1150,530))
    _poster_text(draw,title,(75,1090,1050,300),210)
    _poster_text(draw,event_date.strftime('%A %-d %B'),(75,1450,1050,80),85,False)
    return img
