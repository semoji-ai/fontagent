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


def _merge_vertical_parts(boxes: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    """Merge boxes that sit above/below one another (dotted 'i', 'ㅎ', '한')."""
    if not boxes:
        return boxes
    merged = list(boxes)
    changed = True
    while changed:
        changed = False
        merged.sort(key=lambda b: (b[0], b[1]))
        new_boxes: list[tuple[int, int, int, int]] = []
        skip = set()
        for i, box in enumerate(merged):
            if i in skip:
                continue
            x0, y0, x1, y1 = box
            for j in range(i + 1, len(merged)):
                if j in skip:
                    continue
                bx0, by0, bx1, by1 = merged[j]
                horizontal_overlap = min(x1, bx1) - max(x0, bx0)
                width = min(x1 - x0, bx1 - bx0)
                if horizontal_overlap >= 0.5 * width:
                    x0 = min(x0, bx0)
                    y0 = min(y0, by0)
                    x1 = max(x1, bx1)
                    y1 = max(y1, by1)
                    skip.add(j)
                    changed = True
            new_boxes.append((x0, y0, x1, y1))
        merged = new_boxes
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
    boxes = _merge_vertical_parts(boxes)
    boxes.sort(key=lambda b: (b[1] // max(1, (boxes[0][3] - boxes[0][1]) // 2 or 1) if boxes else 0, b[0]))

    crops: list[GlyphCrop] = []
    for bbox in boxes[:max_glyphs]:
        x0, y0, x1, y1 = bbox
        crop = mask[y0:y1, x0:x1]
        if crop.size == 0:
            continue
        crops.append(GlyphCrop(bbox=bbox, bitmap=crop.astype(np.uint8)))
    return crops
