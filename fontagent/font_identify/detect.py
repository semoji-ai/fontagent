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
    """Return a 0/255 ink mask, auto-detecting polarity and threshold.

    Uses Otsu's method to pick the inter-class-variance-maximizing cut,
    then treats the minority class as ink. The previous heuristic
    failed on thin handwriting fonts where "pixels darker than mean-8"
    captured almost nothing, leaving an empty mask.
    """
    hist, _ = np.histogram(image, bins=256, range=(0, 256))
    total = int(image.size)
    if total == 0:
        return np.zeros_like(image, dtype=np.uint8)
    cumulative = np.cumsum(hist).astype(np.float64)
    cumulative_mean = np.cumsum(hist * np.arange(256)).astype(np.float64)
    global_mean = cumulative_mean[-1] / total

    best_variance = 0.0
    best_threshold = 128
    for t in range(256):
        w_bg = cumulative[t]
        if w_bg == 0 or w_bg == total:
            continue
        mu_bg = cumulative_mean[t] / w_bg
        mu_fg = (cumulative_mean[-1] - cumulative_mean[t]) / (total - w_bg)
        variance = (w_bg * (total - w_bg)) * (mu_bg - mu_fg) ** 2
        if variance > best_variance:
            best_variance = variance
            best_threshold = t

    if global_mean > best_threshold:
        ink = image <= best_threshold
    else:
        ink = image >= best_threshold
    return (ink.astype(np.uint8)) * 255


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

    For a script like Latin where each letter is its own component the
    tallest components already approximate the em. Hangul syllables
    decompose into jamo, but at least one fragment usually spans close
    to the full em. Handwriting fonts break that assumption — a cursive
    '가' can produce only short thin strokes of similar size — so we
    also take the overall line height (the vertical span of all boxes)
    and use whichever is larger. The line-height fallback requires
    single-line text input, which is what the CLI/service target.
    """
    if not boxes:
        return 0
    max_dims = sorted(max(box[2] - box[0], box[3] - box[1]) for box in boxes)
    q75 = max_dims[int(len(max_dims) * 0.75)]
    line_height = max(box[3] for box in boxes) - min(box[1] for box in boxes)
    return int(max(q75, line_height) * 1.15)


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


def _dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    """3x3 dilation applied `radius` times, no SciPy dependency.

    Thin handwriting strokes often break into several connected
    components after thresholding. A small morphological dilation
    bridges pixel-level gaps so a single stroke turns into a single
    component, without merging characters that have a visible gap
    between them.
    """
    if radius <= 0:
        return mask
    output = mask.copy()
    for _ in range(radius):
        shifted = np.maximum.reduce([
            output,
            np.roll(output, 1, axis=0),
            np.roll(output, -1, axis=0),
            np.roll(output, 1, axis=1),
            np.roll(output, -1, axis=1),
        ])
        output = shifted
    return output


def extract_glyph_crops(
    image_path: Path | str,
    *,
    max_glyphs: int = 32,
    dilation_radius: int = 2,
) -> list[GlyphCrop]:
    """Return glyph crops detected in the image, ordered left-to-right."""
    image = Image.open(image_path).convert("L")
    array = np.asarray(image, dtype=np.uint8)
    mask = _auto_threshold(array)
    dilated = _dilate(mask, dilation_radius)
    boxes = _connected_components(dilated)
    boxes = _group_into_syllables(boxes)

    crops: list[GlyphCrop] = []
    for bbox in boxes[:max_glyphs]:
        x0, y0, x1, y1 = bbox
        # Use the original un-dilated mask for the crop so the glyph
        # shape stays faithful for fingerprinting.
        crop = mask[y0:y1, x0:x1]
        if crop.size == 0:
            continue
        crops.append(GlyphCrop(bbox=bbox, bitmap=crop.astype(np.uint8)))
    return crops
