from .shared import *
from .flip_date import _draw_flip_panel


def render_flip_clock():
    img, draw = _canvas()
    now = datetime.now()
    for y, text in [(70, now.strftime("%H")), (830, now.strftime("%M"))]:
        _draw_flip_panel(img, draw, 70, y, WIDTH-140, 700, text, 540)
    return img
