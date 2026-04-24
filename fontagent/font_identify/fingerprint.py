"""Turn a normalized glyph bitmap into a fixed-length fingerprint vector.

The fingerprint combines four cheap features that together are more
discriminative than pixels alone:

1. Downsampled pixel intensity (shape of the ink).
2. Gradient-orientation histogram per cell (captures stroke direction
   — e.g., sans vs. serif).
3. Ink density per cell (robust to small rendering differences).
4. Stroke-width histogram (weight signature — separates thin
   handwriting from heavy display from regular text).

Each block is L2-normalized, concatenated, and the whole vector is
L2-normalized a final time so cosine similarity is a well-defined
[-1, 1] score.
"""

from __future__ import annotations

import numpy as np


PIXEL_GRID = 16
HOG_GRID = 8
HOG_BINS = 9
ZONE_GRID = 8
STROKE_BINS = 10

# Each block is L2-normalized to unit length before concatenation, then
# the combined vector is L2-normalized again. Without weights every
# block contributes equal magnitude, which buries the stroke signature
# under pixel/HOG noise — that's how a thin handwriting query ends up
# closest to a serif book face on shape/orientation alone. Up-weighting
# the stroke block before concatenation gives it ~1.8x the magnitude of
# a shape block, so fonts with the wrong stroke distribution (heavy
# display vs. hairline handwriting) are penalized correctly.
STROKE_BLOCK_WEIGHT = 1.3
FINGERPRINT_VERSION = 2

_PIXEL_DIM = PIXEL_GRID * PIXEL_GRID
_HOG_DIM = HOG_GRID * HOG_GRID * HOG_BINS
_ZONE_DIM = ZONE_GRID * ZONE_GRID
_STROKE_DIM = STROKE_BINS

FINGERPRINT_DIM = _PIXEL_DIM + _HOG_DIM + _ZONE_DIM + _STROKE_DIM


def _l2_normalize(vec: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    if norm <= 1e-8:
        return vec.astype(np.float32)
    return (vec / norm).astype(np.float32)


def _downsample(bitmap: np.ndarray, grid: int) -> np.ndarray:
    # Average pooling into `grid x grid` cells without SciPy.
    image = bitmap.astype(np.float32) / 255.0
    height, width = image.shape
    row_edges = np.linspace(0, height, grid + 1, dtype=int)
    col_edges = np.linspace(0, width, grid + 1, dtype=int)
    out = np.zeros((grid, grid), dtype=np.float32)
    for r in range(grid):
        r0, r1 = row_edges[r], max(row_edges[r] + 1, row_edges[r + 1])
        for c in range(grid):
            c0, c1 = col_edges[c], max(col_edges[c] + 1, col_edges[c + 1])
            out[r, c] = float(image[r0:r1, c0:c1].mean())
    return out


def _gradient_orientation_histogram(bitmap: np.ndarray) -> np.ndarray:
    image = bitmap.astype(np.float32) / 255.0
    gx = np.zeros_like(image)
    gy = np.zeros_like(image)
    gx[:, 1:-1] = image[:, 2:] - image[:, :-2]
    gy[1:-1, :] = image[2:, :] - image[:-2, :]
    magnitude = np.sqrt(gx * gx + gy * gy)
    # Unsigned orientation so opposite-direction strokes share a bin.
    angle = (np.arctan2(gy, gx) + np.pi) % np.pi
    bin_width = np.pi / HOG_BINS
    bin_idx = np.clip((angle / bin_width).astype(int), 0, HOG_BINS - 1)

    height, width = image.shape
    row_edges = np.linspace(0, height, HOG_GRID + 1, dtype=int)
    col_edges = np.linspace(0, width, HOG_GRID + 1, dtype=int)
    hog = np.zeros((HOG_GRID, HOG_GRID, HOG_BINS), dtype=np.float32)
    for r in range(HOG_GRID):
        r0, r1 = row_edges[r], max(row_edges[r] + 1, row_edges[r + 1])
        for c in range(HOG_GRID):
            c0, c1 = col_edges[c], max(col_edges[c] + 1, col_edges[c + 1])
            cell_mag = magnitude[r0:r1, c0:c1]
            cell_bin = bin_idx[r0:r1, c0:c1]
            if cell_mag.size == 0:
                continue
            for b in range(HOG_BINS):
                hog[r, c, b] = float(cell_mag[cell_bin == b].sum())
    return hog.reshape(-1)


def _ink_density(bitmap: np.ndarray) -> np.ndarray:
    return _downsample((bitmap > 96).astype(np.uint8) * 255, ZONE_GRID).reshape(-1)


def _distance_transform(ink: np.ndarray) -> np.ndarray:
    """L∞ distance from each ink pixel to the nearest non-ink pixel.

    Iterative 4-connected erosion; pixels that survive the k-th erosion
    are at least k pixels away from any background. Implemented with
    numpy array shifts so it stays fast even at 64x64.
    """
    surviving = ink.astype(np.uint8)
    height, width = surviving.shape
    result = np.zeros(surviving.shape, dtype=np.int32)
    step = 1
    max_steps = max(height, width)
    while surviving.any() and step <= max_steps:
        result[surviving > 0] = step
        left = np.zeros_like(surviving)
        right = np.zeros_like(surviving)
        up = np.zeros_like(surviving)
        down = np.zeros_like(surviving)
        left[:, 1:] = surviving[:, :-1]
        right[:, :-1] = surviving[:, 1:]
        up[1:, :] = surviving[:-1, :]
        down[:-1, :] = surviving[1:, :]
        surviving = surviving & left & right & up & down
        step += 1
    return result


def _stroke_width_histogram(bitmap: np.ndarray) -> np.ndarray:
    """Histogram of per-pixel stroke half-widths, normalized by the em.

    A heavy display font (Black Han Sans) piles every ink pixel into
    the high-width bins; a thin handwriting font (Gaegu) piles them
    into the low bins; a regular Gothic lands in the middle. This is
    the feature that breaks ties like Hahmlet-serif vs. Noto-Sans-KR
    where ink shape and orientation alone look near-identical.
    """
    ink = (bitmap > 96).astype(np.uint8)
    if ink.sum() == 0:
        return np.zeros(STROKE_BINS, dtype=np.float32)
    distances = _distance_transform(ink)
    em = float(max(bitmap.shape))
    normalized = distances[ink > 0].astype(np.float32) / em
    # Half-widths past ~0.35 em are vanishingly rare; the upper bound
    # keeps bins packed around the informative range.
    hist, _ = np.histogram(normalized, bins=STROKE_BINS, range=(0.0, 0.35))
    total = float(hist.sum())
    if total <= 0:
        return np.zeros(STROKE_BINS, dtype=np.float32)
    return (hist.astype(np.float32) / total)


def compute_fingerprint(bitmap: np.ndarray) -> np.ndarray:
    """Return an L2-normalized float32 fingerprint of shape (FINGERPRINT_DIM,)."""
    if bitmap.ndim != 2:
        raise ValueError("compute_fingerprint expects a 2-D bitmap")

    pixel_block = _l2_normalize(_downsample(bitmap, PIXEL_GRID).reshape(-1))
    hog_block = _l2_normalize(_gradient_orientation_histogram(bitmap))
    zone_block = _l2_normalize(_ink_density(bitmap))
    stroke_block = _l2_normalize(_stroke_width_histogram(bitmap)) * STROKE_BLOCK_WEIGHT
    combined = np.concatenate([pixel_block, hog_block, zone_block, stroke_block])
    return _l2_normalize(combined)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity assuming both inputs are already L2-normalized."""
    return float(np.dot(a, b))


def cosine_similarity_matrix(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Row-wise cosine similarity between `query` (D,) and `matrix` (N, D)."""
    return matrix @ query
