"""Top-level identification pipeline.

The matcher votes across every glyph we extract from an input image:
each glyph independently produces a top-k list of candidate fonts, and
votes are summed across glyphs (weighted by similarity) so that a font
which scores well on several glyphs rises above a font that happens to
match one glyph well. This is the equivalent of the "ensemble across
characters" step in the README roadmap.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

from .detect import GlyphCrop, extract_glyph_crops
from .fingerprint import compute_fingerprint
from .glyph_renderer import normalize_glyph_bitmap
from .index import FontFingerprintIndex


DEFAULT_TOP_K = 5
PER_GLYPH_CANDIDATES = 8


@dataclass
class IdentificationResult:
    top_matches: list[dict]
    per_glyph: list[dict]
    glyph_count: int
    index_fonts: int
    used_character_hints: bool


def _prepare_query(bitmap: np.ndarray, normalized_size: int) -> np.ndarray:
    normalized = normalize_glyph_bitmap(bitmap, target_size=normalized_size)
    return compute_fingerprint(normalized)


def _aggregate_votes(
    per_glyph_results: Iterable[list[tuple[str, float]]],
    *,
    top_k: int,
) -> list[dict]:
    scores: dict[str, float] = {}
    hits: dict[str, int] = {}
    for glyph_scores in per_glyph_results:
        for font_id, score in glyph_scores:
            scores[font_id] = scores.get(font_id, 0.0) + max(0.0, score)
            hits[font_id] = hits.get(font_id, 0) + 1
    ranked = sorted(
        scores.items(),
        key=lambda item: (item[1], hits.get(item[0], 0)),
        reverse=True,
    )
    return [
        {"font_id": font_id, "score": round(score, 6), "glyph_hits": hits[font_id]}
        for font_id, score in ranked[:top_k]
    ]


def identify_from_glyph(
    glyph: np.ndarray,
    index: FontFingerprintIndex,
    *,
    char_hint: str | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> IdentificationResult:
    """Identify a font from a single glyph bitmap."""
    query_fp = _prepare_query(glyph, index.normalized_size)
    if char_hint:
        matches = index.query_for_char(query_fp, char_hint, top_k=top_k)
        used_hint = bool(matches)
        if used_hint:
            return IdentificationResult(
                top_matches=[
                    {"font_id": font_id, "score": round(score, 6), "glyph_hits": 1}
                    for font_id, score in matches
                ],
                per_glyph=[
                    {
                        "bbox": None,
                        "char_hint": char_hint,
                        "candidates": [
                            {"font_id": font_id, "score": round(score, 6)}
                            for font_id, score in matches
                        ],
                    }
                ],
                glyph_count=1,
                index_fonts=len(index.manifest.get("fonts", [])),
                used_character_hints=True,
            )

    raw = index.query_unknown_char(query_fp, top_k=top_k)
    return IdentificationResult(
        top_matches=[
            {
                "font_id": font_id,
                "score": round(score, 6),
                "matched_char": matched_char,
                "glyph_hits": 1,
            }
            for font_id, score, matched_char in raw
        ],
        per_glyph=[
            {
                "bbox": None,
                "char_hint": None,
                "candidates": [
                    {"font_id": font_id, "score": round(score, 6), "matched_char": ch}
                    for font_id, score, ch in raw
                ],
            }
        ],
        glyph_count=1,
        index_fonts=len(index.manifest.get("fonts", [])),
        used_character_hints=False,
    )


def identify_from_image(
    image_path: Path | str,
    index: FontFingerprintIndex,
    *,
    top_k: int = DEFAULT_TOP_K,
    max_glyphs: int = 32,
    char_hints: list[str] | None = None,
) -> IdentificationResult:
    """Identify the font used in an image by voting across detected glyphs.

    `char_hints`, when provided, must align positionally with the glyphs
    that detection returns (left-to-right, top-to-bottom). Any slot may
    be None to fall back to unknown-char matching for that glyph.
    """
    crops = extract_glyph_crops(image_path, max_glyphs=max_glyphs)
    if not crops:
        return IdentificationResult(
            top_matches=[],
            per_glyph=[],
            glyph_count=0,
            index_fonts=len(index.manifest.get("fonts", [])),
            used_character_hints=False,
        )

    per_glyph_report: list[dict] = []
    per_glyph_votes: list[list[tuple[str, float]]] = []
    used_hints = False

    for idx, crop in enumerate(crops):
        hint = None
        if char_hints and idx < len(char_hints):
            hint = char_hints[idx]
        query_fp = _prepare_query(crop.bitmap, index.normalized_size)
        if hint:
            scored = index.query_for_char(query_fp, hint, top_k=PER_GLYPH_CANDIDATES)
            if scored:
                used_hints = True
                per_glyph_report.append(
                    {
                        "bbox": list(crop.bbox),
                        "char_hint": hint,
                        "candidates": [
                            {"font_id": font_id, "score": round(score, 6)}
                            for font_id, score in scored
                        ],
                    }
                )
                per_glyph_votes.append(scored)
                continue
        raw = index.query_unknown_char(query_fp, top_k=PER_GLYPH_CANDIDATES)
        per_glyph_report.append(
            {
                "bbox": list(crop.bbox),
                "char_hint": hint,
                "candidates": [
                    {"font_id": font_id, "score": round(score, 6), "matched_char": ch}
                    for font_id, score, ch in raw
                ],
            }
        )
        per_glyph_votes.append([(font_id, score) for font_id, score, _ in raw])

    top_matches = _aggregate_votes(per_glyph_votes, top_k=top_k)
    return IdentificationResult(
        top_matches=top_matches,
        per_glyph=per_glyph_report,
        glyph_count=len(crops),
        index_fonts=len(index.manifest.get("fonts", [])),
        used_character_hints=used_hints,
    )
