#!/usr/bin/env python3
"""Additional screens for Joan display playlist rotation.

Each render_* function returns a 1200x1600 portrait grayscale PIL Image.
"""

import hashlib
import html
import json
import math
import os
import random
import re
import textwrap
import time
from datetime import datetime, timedelta
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

try:
    from bidi.algorithm import get_display as _bidi_get_display
except Exception:
    _bidi_get_display = None

# Pillow with libraqm support handles bidi + complex shaping (mark/mkmk) natively.
# When available, we skip manual visual-order reordering and pass direction="rtl"
# to draw.text() so HarfBuzz positions niqqud/cantillation marks correctly.
try:
    from PIL import features as _PIL_features
    _HAS_RAQM = bool(_PIL_features.check("raqm"))
except Exception:
    _HAS_RAQM = False

_RTL_FEATURES = ["rlig", "liga", "mark", "mkmk", "ccmp"]

# Reuse from main dashboard
from joan_dashboard import (
    WIDTH, HEIGHT, get_font, fetch_weather, fetch_week_events,
    WEATHER_LAT, WEATHER_LON, WEATHER_LOCATION, fetch_device_status,
    TRAINS_API_KEY, TRAINS_STATION, TRAINS_DESTINATION,
    BIN_UPRN,
)

PAD = 60  # generous padding for full-screen layouts

# --- CJK / Hebrew font helpers ---
_INTL_FONT_CACHE = {}

def _get_cjk_font(size: int) -> ImageFont.FreeTypeFont:
    """Get a font that supports CJK (Chinese/Japanese/Korean) characters."""
    key = ("cjk", size)
    if key not in _INTL_FONT_CACHE:
        candidates = [
            "/Library/Fonts/Arial Unicode.ttf",
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/PingFang SC.ttc",
            "/System/Library/Fonts/PingFang TC.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/System/Library/Fonts/Hiragino Sans GB W3.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/STSong Medium.ttc",
            "/System/Library/Fonts/Supplemental/PingFang.ttc",
            "/System/Library/Fonts/Supplemental/Hiragino Sans GB.ttc",
            "/System/Library/Fonts/Supplemental/Songti.ttc",
            "/System/Library/Fonts/Supplemental/SimHei.ttf",
            "/System/Library/Fonts/Supplemental/SimSun.ttf",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
            "/usr/share/fonts/truetype/noto/NotoSansSC-Regular.otf",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        ]
        for path in candidates:
            try:
                _INTL_FONT_CACHE[key] = ImageFont.truetype(path, size)
                return _INTL_FONT_CACHE[key]
            except OSError:
                continue
        _INTL_FONT_CACHE[key] = get_font(size)
    return _INTL_FONT_CACHE[key]


def _get_hebrew_font(size: int) -> ImageFont.FreeTypeFont:
    """Get a font that supports Hebrew characters with full niqqud + cantillation coverage."""
    key = ("he", size)
    if key not in _INTL_FONT_CACHE:
        # Bundled Noto Hebrew has full Biblical Hebrew block coverage
        # (base letters, niqqud U+05B0–U+05BC, cantillation U+0591–U+05AF, maqaf, etc).
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates = [
            os.path.join(repo_root, "fonts", "NotoSerifHebrew-Regular.ttf"),
            os.path.join(repo_root, "fonts", "NotoSansHebrew-Regular.ttf"),
            "/Library/Fonts/Arial Unicode.ttf",
            "/System/Library/Fonts/Supplemental/Arial Hebrew.ttf",
            "/System/Library/Fonts/Supplemental/Raanana.ttc",
            "/System/Library/Fonts/Supplemental/Geeza Pro.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansHebrew-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansHebrew-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        ]
        for path in candidates:
            try:
                _INTL_FONT_CACHE[key] = ImageFont.truetype(path, size)
                return _INTL_FONT_CACHE[key]
            except OSError:
                continue
        _INTL_FONT_CACHE[key] = get_font(size)
    return _INTL_FONT_CACHE[key]


# ── Cache layer ──────────────────────────────────────────────────────
# Fresh-first: within TTL return cached; after TTL try fresh;
# on failure serve stale (up to max_stale). Never serve beyond max_stale.

_cache = {}  # key -> {"data": ..., "ts": float}


def _cache_fetch(key, ttl, max_stale, fetch_fn):
    """Cached fetch with stale fallback. Returns None if nothing available."""
    now = time.time()
    entry = _cache.get(key)
    if entry and (now - entry["ts"]) < ttl:
        return entry["data"]
    try:
        data = fetch_fn()
        if data is None or data == [] or data == "":
            raise ValueError("Empty response")
        _cache[key] = {"data": data, "ts": now}
        while len(_cache) > 128:
            oldest = min(_cache, key=lambda k: _cache[k]["ts"])
            del _cache[oldest]
        return data
    except Exception as e:
        print(f"[cache] '{key}' fetch failed: {e}")
        if entry and max_stale > 0 and (now - entry["ts"]) < max_stale:
            print(f"[cache] Serving stale '{key}' (age {int(now - entry['ts'])}s)")
            return entry["data"]
        return None


# ── Helpers ──────────────────────────────────────────────────────────

def _text_width(font, text: str) -> int:
    """Measure text width using the font's bounding box for stable layout."""
    bbox = font.getbbox(text or " ")
    return bbox[2] - bbox[0]


def _text_height(font, text: str) -> int:
    """Measure text height using the font's bounding box for stable layout."""
    bbox = font.getbbox(text or " ")
    return bbox[3] - bbox[1]


def _shape_rtl_text(text: str) -> str:
    """Best-effort RTL shaping for Hebrew text.

    With libraqm-enabled Pillow we leave the string in logical order and let
    HarfBuzz handle bidi + mark positioning at draw time. Without raqm, fall
    back to python-bidi (or naïve word reversal) so widths/output are at least
    legible.
    """
    if not text:
        return text
    if _HAS_RAQM:
        return text
    if _bidi_get_display is not None:
        try:
            return "\n".join(_bidi_get_display(line) for line in text.splitlines())
        except Exception:
            pass

    shaped_lines = []
    for line in text.splitlines():
        words = line.split()
        if not words:
            shaped_lines.append(line)
            continue
        shaped_words = [word[::-1] for word in reversed(words)]
        shaped_lines.append(" ".join(shaped_words))
    return "\n".join(shaped_lines)


def _draw_text_intl(draw, xy, text, *, font, fill=0, anchor=None, rtl=False):
    """Draw text with proper bidi/shaping when the text is RTL and raqm is available."""
    if rtl and _HAS_RAQM:
        draw.text(xy, text, fill=fill, font=font, anchor=anchor,
                  direction="rtl", features=_RTL_FEATURES)
    else:
        draw.text(xy, text, fill=fill, font=font, anchor=anchor)


def _measure_text_intl(font, text: str, rtl: bool = False) -> int:
    """Measure shaped text width when raqm is available, else use bbox."""
    if rtl and _HAS_RAQM:
        try:
            length = font.getlength(text, direction="rtl", features=_RTL_FEATURES)
            return int(length)
        except Exception:
            pass
    return _text_width(font, text)


def _is_rtl_text(text: str) -> bool:
    """Return True when a string contains Hebrew/RTL characters."""
    return any("\u0590" <= ch <= "\u08FF" for ch in text)


def _wrap_text(font, text, max_width, rtl=False):
    """Wrap text to fit within max_width using the given font."""
    words = text.split()
    lines = []
    line = ""
    for word in words:
        test = f"{line} {word}".strip()
        if rtl:
            width = _measure_text_intl(font, test, rtl=True)
        else:
            width = _text_width(font, test)
        if width > max_width:
            if line:
                lines.append(_shape_rtl_text(line) if rtl else line)
            line = word
        else:
            line = test
    if line:
        lines.append(_shape_rtl_text(line) if rtl else line)
    return lines


def _centered_text(draw, y, text, size, bold=False, fill=0, max_width=WIDTH - 120, rtl=False):
    """Draw text centered at y, wrapping if needed. Returns new y."""
    rtl = rtl or _is_rtl_text(text)
    font = _get_hebrew_font(size) if rtl else get_font(size, bold=bold)
    lines = []
    for paragraph in text.split("\n"):
        lines.extend(_wrap_text(font, paragraph, max_width, rtl=rtl) or [""])
    line_h = max(int(_text_height(font, "Ag") * 1.25), size + 6)
    for line in lines:
        _draw_text_intl(draw, (WIDTH // 2, y), line, font=font, fill=fill, anchor="mt", rtl=rtl)
        y += line_h
    return y


def _draw_wrapped_block(draw, x, y, width, height, text, size, bold=False, fill=0, rtl=False, max_lines=None):
    """Draw wrapped text inside a rectangular block."""
    rtl = rtl or _is_rtl_text(text)
    font = _get_hebrew_font(size) if rtl else get_font(size, bold=bold)
    lines = []
    for paragraph in text.split("\n"):
        lines.extend(_wrap_text(font, paragraph, width, rtl=rtl) or [""])
    if max_lines is not None:
        lines = lines[:max_lines]

    line_h = max(int(_text_height(font, "Ag") * 1.22), size + 4)
    block_h = line_h * len(lines)
    top = y + max(0, (height - block_h) // 2)

    for line in lines:
        if rtl:
            _draw_text_intl(draw, (x + width - 8, top), line, font=font, fill=fill, anchor="rt", rtl=True)
        else:
            draw.text((x + width // 2, top), line, fill=fill, font=font, anchor="mt")
        top += line_h

    return top


def _fit_font_to_width(text: str, max_width: int, start_size: int, min_size: int = 12,
                       bold: bool = False) -> ImageFont.FreeTypeFont:
    """Return the largest font that fits the supplied width."""
    for size in range(start_size, min_size - 1, -1):
        font = get_font(size, bold=bold)
        if _text_width(font, text) <= max_width:
            return font
    return get_font(min_size, bold=bold)


def _truncate_text(font, text: str, max_width: int) -> str:
    """Trim text to fit max_width with an ellipsis."""
    if _text_width(font, text) <= max_width:
        return text
    if max_width <= _text_width(font, "…"):
        return "…"
    trimmed = text
    while trimmed and _text_width(font, trimmed + "…") > max_width:
        trimmed = trimmed[:-1]
    return trimmed.rstrip() + "…"


def _dashboard_footer(draw):
    """Display chrome intentionally omitted on the room display."""
    pass


def _footer(draw, text=""):
    pass


def now_str():
    return datetime.now().strftime("%H:%M")


def _draw_arrow(draw, x, y, size, direction="up", fill=0):
    """Draw a robust vector arrow (triangle) at (x, y)."""
    half = size // 2
    if direction == "up":
        points = [(x, y - half), (x - half, y + half), (x + half, y + half)]
    else:
        points = [(x, y + half), (x - half, y - half), (x + half, y - half)]
    draw.polygon(points, fill=fill)


def _draw_star(draw, x, y, size, fill=0):
    """Draw a simple 5-pointed star centered at (x, y)."""
    points = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        r = size if i % 2 == 0 else size // 2.5
        points.append((x + r * math.cos(angle), y + r * math.sin(angle)))
    draw.polygon(points, fill=fill)


def _draw_bullet(draw, x, y, size, fill=0):
    """Draw a simple circular bullet centered at (x, y)."""
    r = size // 2
    draw.ellipse([x - r, y - r, x + r, y + r], fill=fill)


class ScreenUnavailable(RuntimeError):
    """No useful content: skip this playlist slot instead of publishing an error."""


def _require(data, message="Content unavailable"):
    if data is None or data == [] or data == "":
        raise ScreenUnavailable(message)
    return data


def _canvas():
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    return img, ImageDraw.Draw(img)


def _fit_block(draw, text, box, size=120, bold=False, font_fn=None, tight=False):
    """Fit complete text to a rectangle, including long tokens and CJK."""
    text = str(text or "")
    if not text:
        return
    x, y, w, h = box
    if x < 0 or y < 0 or x+w > WIDTH or y+h > HEIGHT:
        raise ValueError(f"Text region outside canvas: {box}")
    rtl = _is_rtl_text(text)
    factory = font_fn or (_get_hebrew_font if rtl else lambda n: get_font(n, bold))
    for n in range(size, 27, -2):
        font = factory(n)
        # Preserve ordinary words (especially spelling cards); shrink before wrapping.
        if any(len(word) <= 40 and _measure_text_intl(font, word, rtl) > w for word in text.split()):
            continue
        lines = []
        for para in text.split("\n"):
            line = ""
            for word in para.split():
                candidate = (line + " " + word).strip()
                if _measure_text_intl(font, candidate, rtl) <= w:
                    line = candidate
                    continue
                if line:
                    lines.append(line)
                line = ""
                for char in word:
                    if line and _measure_text_intl(font, line + char, rtl) > w:
                        lines.append(line)
                        line = ""
                    line += char
            lines.append(line)
        line_h = int(n * 1.3)
        if tight:
            bounds = [draw.textbbox((0,0), line or ' ', font=font, anchor='mt',
                      **({'direction':'rtl'} if rtl and _HAS_RAQM else {})) for line in lines]
            gap = max(8, int(n*.16))
            block_h = sum(b[3]-b[1] for b in bounds) + gap*(len(lines)-1)
        else:
            block_h = len(lines)*line_h
        if block_h <= h:
            break
    else:
        raise ScreenUnavailable("Text too long for the display")
    top = y + (h - block_h) // 2
    for index, line in enumerate(lines):
        if rtl:
            line = _shape_rtl_text(line)
        baseline = top - bounds[index][1] if tight else top
        _draw_text_intl(draw, (x + w // 2, baseline), line, font=font, fill=0, anchor="mt", rtl=rtl)
        top += bounds[index][3]-bounds[index][1]+gap if tight else line_h


def _poster_text(draw, text, box, size=500, bold=True, font_fn=None):
    """Size the ink itself to its box; used by poster layouts, never clocks."""
    return _fit_block(draw,text,box,size,bold,font_fn,tight=True)


def _calendar_page(day, month, title, detail=''):
    img, draw = _canvas()
    draw.rounded_rectangle((40,90,WIDTH-40,HEIGHT-40),radius=40,outline=0,width=14)
    for x in (270,WIDTH-270):
        draw.rounded_rectangle((x-20,30,x+20,155),radius=20,fill=0)
    _poster_text(draw,month,(80,190,WIDTH-160,140),160)
    _poster_text(draw,day,(80,370,WIDTH-160,630),850)
    _poster_text(draw,title,(85,1050,WIDTH-170,310),220)
    if detail:
        _poster_text(draw,detail,(85,1410,WIDTH-170,90),90,False)
    return img


def _statement(text, detail="", size=140):
    img, draw = _canvas()
    _poster_text(draw, text, (50, 50, WIDTH-100, 1280 if detail else HEIGHT-100), max(size, 500))
    if detail:
        _poster_text(draw, detail, (60, 1390, WIDTH-120, 150), 110, False)
    return img


def _select(items, seconds=1800):
    return _require(items)[int(time.time() // seconds) % len(items)]


def _image_url(url):
    from PIL import ImageOps
    def fetch():
        r = requests.get(url, timeout=12, headers={"User-Agent": "JoanDashboard/2.0"})
        r.raise_for_status()
        source = ImageOps.exif_transpose(Image.open(BytesIO(r.content))).convert("RGBA")
        bg = Image.new("RGBA", source.size, "white")
        bg.alpha_composite(source)
        return bg.convert("L")
    return _cache_fetch("image:" + url, 3600, 86400, fetch)


def _picture(image, caption="", portrait=False, photo=True):
    from PIL import ImageOps
    _require(image)
    img, draw = _canvas()
    fitted = ImageOps.contain(image.convert("L"), (WIDTH-40, HEIGHT-(180 if portrait and caption else 390 if caption else 40)), Image.Resampling.LANCZOS)
    if caption:
        # Give a landscape picture's unused height to its headline instead of
        # leaving a large fixed gap between the image and a small caption.
        img.paste(fitted, ((WIDTH-fitted.width)//2,20))
        top = fitted.height+50
        _poster_text(draw, caption, (40,top,WIDTH-80,HEIGHT-top-30), 260)
    else:
        img.paste(fitted, ((WIDTH-fitted.width)//2,(HEIGHT-fitted.height)//2))
    if photo:
        left = (WIDTH-fitted.width)//2
        top = 20 if caption else (HEIGHT-fitted.height)//2
        img.info['photo_regions'] = [(left,top,left+fitted.width,top+fitted.height)]
    return img


__all__ = [
    name
    for name in globals()
    if not name.startswith("__")
]
