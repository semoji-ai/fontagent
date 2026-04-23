"""Render single glyphs from font files into normalized bitmaps.

The identify pipeline reduces every character — whether it came from an
image crop or from a font file — to the same canonical representation:
a square grayscale array, tightly cropped to the glyph's ink box, then
resized and centered. That canonical form is what the fingerprint layer
turns into a vector, so keeping this module deterministic is important.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageFont


DEFAULT_RENDER_SIZE = 256
DEFAULT_NORMALIZED_SIZE = 64
DEFAULT_PAD_RATIO = 0.08

# Korean samples: a handful of common Hangul syllables that exercise
# ㅇ/ㅁ/ㅅ bowls, vertical/horizontal finals, and complex jongseong.
DEFAULT_INDEX_SAMPLES_KO = (
    "가", "나", "다", "라", "마",
    "바", "사", "아", "자", "차",
    "카", "타", "파", "하",
    "강", "글", "꽃", "밝", "읽",
    "를", "은", "이", "요", "의",
)

# Latin samples: lowercase & uppercase forms with distinctive curves
# and stems, plus digits for display fonts.
DEFAULT_INDEX_SAMPLES_EN = (
    "A", "B", "C", "D", "E", "G", "M", "Q", "R", "S",
    "a", "b", "e", "g", "k", "n", "o", "r", "s", "t",
    "0", "1", "2", "5", "7", "8", "9",
)


def default_index_samples(language: str | None = None) -> tuple[str, ...]:
    """Return the per-character sample set used when indexing fonts."""
    language = (language or "").lower()
    if language in {"ko", "kr", "korean"}:
        return DEFAULT_INDEX_SAMPLES_KO
    if language in {"en", "us", "english", "latin"}:
        return DEFAULT_INDEX_SAMPLES_EN
    return DEFAULT_INDEX_SAMPLES_KO + DEFAULT_INDEX_SAMPLES_EN


def _load_font(font_path: Path, size: int) -> ImageFont.FreeTypeFont:
    # Collection files (ttc/otc) may contain several faces; PIL picks the
    # first by default which is what we want for a family-level fingerprint.
    return ImageFont.truetype(str(font_path), size=size)


def render_glyph_bitmap(
    font_path: Path | str,
    char: str,
    *,
    render_size: int = DEFAULT_RENDER_SIZE,
    normalized_size: int = DEFAULT_NORMALIZED_SIZE,
) -> np.ndarray | None:
    """Render `char` from `font_path` and return a normalized grayscale array.

    Returns None when the font does not contain a glyph for the character
    (PIL raises or produces an empty ink box in that case).
    """
    font_path = Path(font_path)
    if not font_path.exists():
        return None
    try:
        font = _load_font(font_path, render_size)
    except (OSError, IOError):
        return None

    canvas_size = render_size * 2
    canvas = Image.new("L", (canvas_size, canvas_size), color=0)
    draw = ImageDraw.Draw(canvas)
    try:
        draw.text((render_size // 2, render_size // 2), char, fill=255, font=font)
    except (OSError, ValueError):
        return None

    bbox = canvas.getbbox()
    if bbox is None:
        return None

    left, top, right, bottom = bbox
    if right - left < 2 or bottom - top < 2:
        return None

    cropped = canvas.crop(bbox)
    array = np.asarray(cropped, dtype=np.uint8)
    return normalize_glyph_bitmap(array, target_size=normalized_size)


def normalize_glyph_bitmap(
    bitmap: np.ndarray,
    *,
    target_size: int = DEFAULT_NORMALIZED_SIZE,
    pad_ratio: float = DEFAULT_PAD_RATIO,
) -> np.ndarray:
    """Center a glyph crop in a square canvas and resize to target_size.

    Input must be a 2-D uint8 array where higher values indicate ink.
    Output is a (target_size, target_size) uint8 array with the glyph
    scaled to preserve aspect ratio and padded with a small margin.
    """
    if bitmap.ndim != 2:
        raise ValueError("normalize_glyph_bitmap expects a 2-D bitmap")

    height, width = bitmap.shape
    inner = max(1, int(round(target_size * (1.0 - 2.0 * pad_ratio))))
    scale = inner / max(height, width)
    new_height = max(1, int(round(height * scale)))
    new_width = max(1, int(round(width * scale)))

    resized = Image.fromarray(bitmap).resize((new_width, new_height), Image.BILINEAR)
    canvas = Image.new("L", (target_size, target_size), color=0)
    offset_x = (target_size - new_width) // 2
    offset_y = (target_size - new_height) // 2
    canvas.paste(resized, (offset_x, offset_y))
    return np.asarray(canvas, dtype=np.uint8)


def render_many(
    font_path: Path | str,
    chars: Iterable[str],
    *,
    render_size: int = DEFAULT_RENDER_SIZE,
    normalized_size: int = DEFAULT_NORMALIZED_SIZE,
) -> dict[str, np.ndarray]:
    """Render several characters from one font file.

    Missing glyphs are silently skipped — the caller sees only the chars
    for which a bitmap could be produced.
    """
    output: dict[str, np.ndarray] = {}
    for char in chars:
        bitmap = render_glyph_bitmap(
            font_path,
            char,
            render_size=render_size,
            normalized_size=normalized_size,
        )
        if bitmap is not None:
            output[char] = bitmap
    return output
