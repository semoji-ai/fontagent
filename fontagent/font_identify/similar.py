"""Rank fonts in the fingerprint index by similarity to a reference font.

The identify pipeline tells you which font an image most resembles. A
user who needs a commercially safe alternative (common for AI-generated
slides where the "detected" font may not even be a real font, or may
have a restrictive license) wants a second query: "given that the
closest match is font X, which other fonts in the index look most like
X?" This module answers that — the scoring stays in the same per-
character cosine space as the main matcher.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np

from .index import FontFingerprintIndex


def _mean_shared_similarity(
    ref_matrix: np.ndarray,
    ref_chars: list[str],
    other_matrix: np.ndarray,
    other_chars: list[str],
) -> float | None:
    if ref_matrix.size == 0 or other_matrix.size == 0:
        return None
    ref_index = {ch: idx for idx, ch in enumerate(ref_chars)}
    shared_scores: list[float] = []
    for ch_idx, ch in enumerate(other_chars):
        if ch not in ref_index:
            continue
        ref_vec = ref_matrix[ref_index[ch]]
        other_vec = other_matrix[ch_idx]
        shared_scores.append(float(np.dot(ref_vec, other_vec)))
    if not shared_scores:
        return None
    return float(np.mean(shared_scores))


def find_similar_fonts(
    index: FontFingerprintIndex,
    reference_font_id: str,
    *,
    top_k: int = 5,
    exclude_font_ids: Iterable[str] | None = None,
) -> list[tuple[str, float]]:
    """Return (font_id, similarity) pairs most similar to `reference_font_id`.

    Similarity is the mean cosine of per-character fingerprints over
    the characters both fonts indexed. Fonts with no shared characters
    are omitted. The reference font is always excluded from the
    result, even if not passed in `exclude_font_ids`.
    """
    ref_entry = index.font_entry(reference_font_id)
    if ref_entry is None:
        return []
    ref_matrix = index.vectors.get(reference_font_id)
    if ref_matrix is None:
        return []

    excluded = set(exclude_font_ids or ())
    excluded.add(reference_font_id)

    scored: list[tuple[str, float]] = []
    for entry in index.manifest.get("fonts", []):
        font_id = entry.get("font_id", "")
        if not font_id or font_id in excluded:
            continue
        matrix = index.vectors.get(font_id)
        if matrix is None:
            continue
        similarity = _mean_shared_similarity(
            ref_matrix,
            ref_entry.characters,
            matrix,
            entry.get("characters", []),
        )
        if similarity is None:
            continue
        scored.append((font_id, similarity))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:top_k]
