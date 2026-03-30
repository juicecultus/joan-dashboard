#!/usr/bin/env python3
"""Additional screens for Joan display playlist rotation.

Each render_* function returns a 1600x1200 grayscale PIL Image.
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
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/Supplemental/Songti.ttc",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
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
    """Get a font that supports Hebrew characters."""
    key = ("he", size)
    if key not in _INTL_FONT_CACHE:
        candidates = [
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
        _cache[key] = {"data": data, "ts": now}
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
    """Best-effort RTL shaping for Hebrew text."""
    if not text:
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
        measured = _shape_rtl_text(test) if rtl else test
        if _text_width(font, measured) > max_width:
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
        draw.text((WIDTH // 2, y), line, fill=fill, font=font, anchor="mt")
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
            draw.text((x + width - 8, top), line, fill=fill, font=font, anchor="rt")
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
    """Match the main dashboard footer: location + update time + room/battery."""
    footer_left = f"{WEATHER_LOCATION}  ·  Updated {datetime.now().strftime('%H:%M')}"
    draw.text((PAD, HEIGHT - 28), footer_left, fill=160, font=get_font(26), anchor="lm")
    dev = fetch_device_status()
    footer_parts = []
    if dev.get("temperature"):
        footer_parts.append(f"Room {dev['temperature']}°C")
    if dev.get("battery"):
        footer_parts.append(f"Batt {dev['battery']}%")
    if footer_parts:
        draw.text((WIDTH - PAD, HEIGHT - 28), "  ·  ".join(footer_parts), fill=160, font=get_font(26), anchor="rm")


def _footer(draw, text=""):
    """Legacy footer wrapper; now matches dashboard footer style."""
    _dashboard_footer(draw)



def now_str():
    return datetime.now().strftime("%H:%M")
