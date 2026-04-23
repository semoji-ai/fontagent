"""Very lightweight glyph crop extraction from an image.

This is a deliberately small baseline so the identify pipeline can run
with nothing but Pillow + numpy. A proper OCR model (PaddleOCR/CRAFT)
can replace this later without changing the matcher interface — the
caller only needs to return a list of GlyphCrop.

Assumptions the baseline relies on:

- Text is roughly horizontal.
- Background is substantially lighter or darker than the text.
- The image is reasonably clean (clipart/presentation/screenshot).

When the heuristics fail, callers should fall back to providing an
already-cropped glyph via identify_from_glyph().
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


MIN_GLYPH_PIXELS = 16
MIN_GLYPH_HEIGHT = 8
MIN_GLYPH_WIDTH = 3
MAX_ASPECT_RATIO = 6.0


@dataclass
class GlyphCrop:
    bbox: tuple[int, int, int, int]
    bitmap: np.ndarray
    char_hint: str | None = None


def _auto_threshold(image: np.ndarray) -> np.ndarray:
    """Return a 0/255 mask where ink is 255 regardless of polarity."""
    values = image.astype(np.int32)
    threshold = int(values.mean())
    foreground = (values < threshold - 8).astype(np.uint8)
    background = (values > threshold + 8).astype(np.uint8)
    # Pick whichever polarity produced less area — text is usually
    # the smaller of the two classes on presentation imagery.
    if foreground.sum() > background.sum():
        mask = background
    else:
        mask = foreground
    return mask * 255


def _connected_components(mask: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Iterative 4-connected component labelling, returns bounding boxes."""
    visited = np.zeros_like(mask, dtype=bool)
    height, width = mask.shape
    boxes: list[tuple[int, int, int, int]] = []
    for y in range(height):
        row = mask[y]
        for x in range(width):
            if row[x] == 0 or visited[y, x]:
                continue
            stack = [(y, x)]
            visited[y, x] = True
            min_x = max_x = x
            min_y = max_y = y
            pixel_count = 0
            while stack:
                cy, cx = stack.pop()
                pixel_count += 1
                if cx < min_x:
                    min_x = cx
                if cx > max_x:
                    max_x = cx
                if cy < min_y:
                    min_y = cy
                if cy > max_y:
                    max_y = cy
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < height and 0 <= nx < width and not visited[ny, nx] and mask[ny, nx] > 0:
                        visited[ny, nx] = True
                        stack.append((ny, nx))
            if pixel_count < MIN_GLYPH_PIXELS:
                continue
            glyph_h = max_y - min_y + 1
            glyph_w = max_x - min_x + 1
            if glyph_h < MIN_GLYPH_HEIGHT or glyph_w < MIN_GLYPH_WIDTH:
                continue
            aspect = max(glyph_h, glyph_w) / max(1, min(glyph_h, glyph_w))
            if aspect > MAX_ASPECT_RATIO:
                continue
            boxes.append((min_x, min_y, max_x + 1, max_y + 1))
    return boxes


def _estimate_em_square(boxes: list[tuple[int, int, int, int]]) -> int:
    """Approximate one em-square in pixels from the detected boxes.

    For a script like Latin where each letter is its own component, the
    tallest components approximate the em. For Hangul where a syllable
    decomposes into jamo, the widest/tallest fragment (often ㅏ/ㅣ or
    the outer ㅁ/ㅇ bowl) still spans close to the full em.
    """
    if not boxes:
        return 0
    max_dims = sorted(max(box[2] - box[0], box[3] - box[1]) for box in boxes)
    q75 = max_dims[int(len(max_dims) * 0.75)]
    return int(q75 * 1.2)


def _group_into_syllables(boxes: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    """Merge connected components that fit together inside one em-square.

    Latin scripts usually produce one component per letter; Hangul
    syllables like '한' decompose into two or three disconnected jamo.
    Heuristic: cluster components greedily left-to-right, adding the
    next component to the current cluster if the resulting bounding box
    still fits within a single em-square. Hangul jamo rejoin into a
    syllable; Latin letters stay separate because their combined box
    exceeds the em-square once you concatenate two characters.
    """
    if not boxes:
        return boxes

    em_square = _estimate_em_square(boxes)
    if em_square <= 0:
        return boxes

    ordered = sorted(boxes, key=lambda b: (b[0], b[1]))
    unused = list(ordered)
    merged: list[tuple[int, int, int, int]] = []

    while unused:
        cluster = [unused.pop(0)]
        changed = True
        while changed:
            changed = False
            for candidate in list(unused):
                cx0 = min(b[0] for b in cluster)
                cy0 = min(b[1] for b in cluster)
                cx1 = max(b[2] for b in cluster)
                cy1 = max(b[3] for b in cluster)
                nx0 = min(cx0, candidate[0])
                ny0 = min(cy0, candidate[1])
                nx1 = max(cx1, candidate[2])
                ny1 = max(cy1, candidate[3])
                if (nx1 - nx0) <= em_square and (ny1 - ny0) <= em_square:
                    cluster.append(candidate)
                    unused.remove(candidate)
                    changed = True
        x0 = min(b[0] for b in cluster)
        y0 = min(b[1] for b in cluster)
        x1 = max(b[2] for b in cluster)
        y1 = max(b[3] for b in cluster)
        merged.append((x0, y0, x1, y1))

    merged.sort(key=lambda b: (b[1] // max(1, em_square // 2), b[0]))
    return merged


def extract_glyph_crops(
    image_path: Path | str,
    *,
    max_glyphs: int = 32,
) -> list[GlyphCrop]:
    """Return glyph crops detected in the image, ordered left-to-right."""
    image = Image.open(image_path).convert("L")
    array = np.asarray(image, dtype=np.uint8)
    mask = _auto_threshold(array)
    boxes = _connected_components(mask)
    boxes = _group_into_syllables(boxes)

    crops: list[GlyphCrop] = []
    for bbox in boxes[:max_glyphs]:
        x0, y0, x1, y1 = bbox
        crop = mask[y0:y1, x0:x1]
        if crop.size == 0:
            continue
        crops.append(GlyphCrop(bbox=bbox, bitmap=crop.astype(np.uint8)))
    return crops
