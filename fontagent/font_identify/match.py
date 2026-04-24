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
    identify_confidence: float = 0.0


def _prepare_query(bitmap: np.ndarray, normalized_size: int) -> np.ndarray:
    normalized = normalize_glyph_bitmap(bitmap, target_size=normalized_size)
    return compute_fingerprint(normalized)


def _compute_identify_confidence(top_matches: list[dict]) -> float:
    """A 0..1 confidence score based on the separation of the ranked list.

    When the top match scores well clear of the runners-up, confidence
    is high. When everything clusters together (common for noisy crops
    or index pools full of visually similar fonts), confidence is low
    so the downstream hybrid can trust the keyword-based recommend
    channel more.
    """
    if not top_matches:
        return 0.0
    scores = [float(match.get("score", 0.0)) for match in top_matches]
    top = scores[0]
    if top <= 0:
        return 0.0
    if len(scores) == 1:
        return 1.0
    runner_up = scores[1]
    gap = (top - runner_up) / max(abs(top), 1e-6)
    # Squash to [0, 1]; a 25% lead over #2 maps to ~0.75 confidence.
    return float(max(0.0, min(1.0, gap * 3.0)))


def _zscore_aggregate(
    per_glyph_full_scores: Iterable[dict[str, float]],
    *,
    top_k: int,
    per_glyph_weights: Iterable[float] | None = None,
) -> list[dict]:
    """Sum per-glyph z-scores across glyphs and rank fonts.

    For each glyph we convert the full per-font similarity distribution
    into z-scores, so a font that is `1σ` above the mean contributes
    `+1` regardless of the absolute similarity scale. This rewards
    fonts that are notably more similar than the crowd on a given
    glyph, which is what separates the correct font from a generic
    "roughly looks like ink" baseline.

    `per_glyph_weights` lets callers upweight visually discriminative
    characters ("g", "Q", "한") and downweight near-uniform ones
    ("I", "l", "ㅡ"). Weights default to 1.0 when omitted.
    """
    accumulated: dict[str, float] = {}
    hits: dict[str, int] = {}
    weights_list = list(per_glyph_weights) if per_glyph_weights is not None else None
    for idx, glyph_scores in enumerate(per_glyph_full_scores):
        if not glyph_scores:
            continue
        values = np.fromiter(glyph_scores.values(), dtype=np.float32)
        if values.size == 0:
            continue
        weight = 1.0
        if weights_list is not None and idx < len(weights_list):
            weight = float(weights_list[idx])
        mean = float(values.mean())
        std = float(values.std()) or 1e-6
        for font_id, score in glyph_scores.items():
            z = (float(score) - mean) / std
            accumulated[font_id] = accumulated.get(font_id, 0.0) + weight * z
            hits[font_id] = hits.get(font_id, 0) + 1
    ranked = sorted(
        accumulated.items(),
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
        scores = index.query_for_char_all(query_fp, char_hint)
        if scores:
            aggregated = _zscore_aggregate([scores], top_k=top_k)
            return IdentificationResult(
                top_matches=aggregated,
                per_glyph=[
                    {
                        "bbox": None,
                        "char_hint": char_hint,
                        "candidates": [
                            {"font_id": font_id, "score": round(score, 6)}
                            for font_id, score in sorted(
                                scores.items(), key=lambda p: p[1], reverse=True
                            )[:PER_GLYPH_CANDIDATES]
                        ],
                    }
                ],
                glyph_count=1,
                index_fonts=len(index.manifest.get("fonts", [])),
                used_character_hints=True,
                identify_confidence=_compute_identify_confidence(aggregated),
            )

    raw = index.query_unknown_char_all(query_fp)
    score_only = {font_id: score for font_id, (score, _) in raw.items()}
    aggregated = _zscore_aggregate([score_only], top_k=top_k)
    # Attach matched_char for readability.
    for match in aggregated:
        if match["font_id"] in raw:
            match["matched_char"] = raw[match["font_id"]][1]
    return IdentificationResult(
        top_matches=aggregated,
        per_glyph=[
            {
                "bbox": None,
                "char_hint": None,
                "candidates": [
                    {
                        "font_id": font_id,
                        "score": round(score, 6),
                        "matched_char": ch,
                    }
                    for font_id, (score, ch) in sorted(
                        raw.items(), key=lambda p: p[1][0], reverse=True
                    )[:PER_GLYPH_CANDIDATES]
                ],
            }
        ],
        glyph_count=1,
        index_fonts=len(index.manifest.get("fonts", [])),
        used_character_hints=False,
        identify_confidence=_compute_identify_confidence(aggregated),
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
    per_glyph_full_scores: list[dict[str, float]] = []
    per_glyph_weights: list[float] = []
    used_hints = False

    for idx, crop in enumerate(crops):
        hint = None
        if char_hints and idx < len(char_hints):
            hint = char_hints[idx]
        query_fp = _prepare_query(crop.bitmap, index.normalized_size)
        if hint:
            scored = index.query_for_char_all(query_fp, hint)
            if scored:
                used_hints = True
                ranked = sorted(scored.items(), key=lambda p: p[1], reverse=True)
                per_glyph_report.append(
                    {
                        "bbox": list(crop.bbox),
                        "char_hint": hint,
                        "candidates": [
                            {"font_id": font_id, "score": round(score, 6)}
                            for font_id, score in ranked[:PER_GLYPH_CANDIDATES]
                        ],
                    }
                )
                per_glyph_full_scores.append(scored)
                per_glyph_weights.append(index.weight_for_char(hint))
                continue
        raw = index.query_unknown_char_all(query_fp)
        ranked = sorted(raw.items(), key=lambda p: p[1][0], reverse=True)
        per_glyph_report.append(
            {
                "bbox": list(crop.bbox),
                "char_hint": hint,
                "candidates": [
                    {"font_id": font_id, "score": round(score, 6), "matched_char": ch}
                    for font_id, (score, ch) in ranked[:PER_GLYPH_CANDIDATES]
                ],
            }
        )
        per_glyph_full_scores.append(
            {font_id: score for font_id, (score, _) in raw.items()}
        )
        per_glyph_weights.append(1.0)

    top_matches = _zscore_aggregate(
        per_glyph_full_scores,
        top_k=top_k,
        per_glyph_weights=per_glyph_weights,
    )
    return IdentificationResult(
        top_matches=top_matches,
        per_glyph=per_glyph_report,
        glyph_count=len(crops),
        index_fonts=len(index.manifest.get("fonts", [])),
        used_character_hints=used_hints,
        identify_confidence=_compute_identify_confidence(top_matches),
    )
