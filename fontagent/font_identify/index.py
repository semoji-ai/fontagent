"""Persisted per-character fingerprint index over known fonts.

Layout on disk::

    <index_dir>/manifest.json
    <index_dir>/vectors/<font_id>.npy   # shape: (num_chars, FINGERPRINT_DIM)

`manifest.json` maps every font to the characters it covers so that
lookups can either narrow to a single character (when the query glyph
is OCR'd) or fall back to the full per-font matrix.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

import numpy as np

from .fingerprint import (
    FINGERPRINT_DIM,
    FINGERPRINT_VERSION,
    compute_fingerprint,
    cosine_similarity_matrix,
)
from .glyph_renderer import default_index_samples, render_many


MANIFEST_NAME = "manifest.json"
VECTORS_DIR = "vectors"


@dataclass
class IndexedFont:
    """One font entry as stored in the manifest."""

    font_id: str
    family: str
    font_path: str
    characters: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)


@dataclass
class FontSource:
    """Input to the indexer: where to find a font file on disk."""

    font_id: str
    family: str
    font_path: Path
    tags: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)


def _vectors_path(index_dir: Path, font_id: str) -> Path:
    safe = "".join(ch if (ch.isalnum() or ch in "-_.") else "-" for ch in font_id)
    return index_dir / VECTORS_DIR / f"{safe}.npy"


def build_index(
    sources: Iterable[FontSource],
    *,
    index_dir: Path,
    characters: Iterable[str] | None = None,
    language_hint: str | None = None,
    render_size: int = 256,
    normalized_size: int = 64,
) -> dict:
    """Render glyphs for every (font, character) pair and persist fingerprints.

    Returns a summary dict the CLI/service layer can print back to the user.
    """
    index_dir = Path(index_dir)
    (index_dir / VECTORS_DIR).mkdir(parents=True, exist_ok=True)

    char_list = list(characters) if characters else list(default_index_samples(language_hint))
    if not char_list:
        raise ValueError("characters must not be empty")

    indexed: list[IndexedFont] = []
    skipped: list[dict] = []
    total_glyphs = 0

    for source in sources:
        bitmaps = render_many(
            source.font_path,
            char_list,
            render_size=render_size,
            normalized_size=normalized_size,
        )
        if not bitmaps:
            skipped.append({"font_id": source.font_id, "reason": "no_renderable_glyphs"})
            continue

        covered_chars = [ch for ch in char_list if ch in bitmaps]
        matrix = np.stack(
            [compute_fingerprint(bitmaps[ch]) for ch in covered_chars]
        ).astype(np.float32)
        np.save(_vectors_path(index_dir, source.font_id), matrix)
        total_glyphs += matrix.shape[0]

        indexed.append(
            IndexedFont(
                font_id=source.font_id,
                family=source.family,
                font_path=str(Path(source.font_path)),
                characters=covered_chars,
                tags=list(source.tags),
                languages=list(source.languages),
            )
        )

    character_variance = _character_variance_weights(indexed, char_list, index_dir)
    manifest = {
        "version": 1,
        "fingerprint_dim": FINGERPRINT_DIM,
        "fingerprint_version": FINGERPRINT_VERSION,
        "normalized_size": normalized_size,
        "render_size": render_size,
        "character_set": char_list,
        "language_hint": language_hint or "",
        "character_weights": character_variance,
        "fonts": [entry.__dict__ for entry in indexed],
    }
    (index_dir / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "index_dir": str(index_dir),
        "indexed_fonts": len(indexed),
        "skipped_fonts": skipped,
        "total_glyphs": total_glyphs,
        "character_set_size": len(char_list),
    }


class FontFingerprintIndex:
    """Loaded-in-memory view of a fingerprint index on disk."""

    def __init__(self, index_dir: Path, manifest: dict, vectors: dict[str, np.ndarray]):
        self.index_dir = index_dir
        self.manifest = manifest
        self.vectors = vectors

    @property
    def fingerprint_dim(self) -> int:
        return int(self.manifest.get("fingerprint_dim", FINGERPRINT_DIM))

    @property
    def normalized_size(self) -> int:
        return int(self.manifest.get("normalized_size", 64))

    @property
    def fonts(self) -> list[IndexedFont]:
        return [IndexedFont(**entry) for entry in self.manifest.get("fonts", [])]

    @property
    def character_weights(self) -> dict[str, float]:
        return dict(self.manifest.get("character_weights", {}))

    def weight_for_char(self, char: str) -> float:
        weights = self.manifest.get("character_weights") or {}
        return float(weights.get(char, 1.0))

    def font_entry(self, font_id: str) -> Optional[IndexedFont]:
        for entry in self.manifest.get("fonts", []):
            if entry.get("font_id") == font_id:
                return IndexedFont(**entry)
        return None

    def query_for_char_all(self, query_fp: np.ndarray, char: str) -> dict[str, float]:
        """Full per-font similarity distribution for a single character.

        Returns an empty dict when no font in the index covers `char`.
        The distribution over all indexed fonts is what the matcher
        needs to compute a z-score and reward fonts that are notably
        more similar than the per-glyph average.
        """
        scored: dict[str, float] = {}
        for entry in self.manifest.get("fonts", []):
            chars: list[str] = entry.get("characters", [])
            if char not in chars:
                continue
            matrix = self.vectors.get(entry["font_id"])
            if matrix is None:
                continue
            row = matrix[chars.index(char)]
            scored[entry["font_id"]] = float(np.dot(row, query_fp))
        return scored

    def query_unknown_char_all(self, query_fp: np.ndarray) -> dict[str, tuple[float, str]]:
        """Full per-font best-match distribution without a character hint."""
        scored: dict[str, tuple[float, str]] = {}
        for entry in self.manifest.get("fonts", []):
            matrix = self.vectors.get(entry["font_id"])
            if matrix is None or matrix.size == 0:
                continue
            scores = cosine_similarity_matrix(query_fp, matrix)
            best_idx = int(np.argmax(scores))
            scored[entry["font_id"]] = (
                float(scores[best_idx]),
                entry["characters"][best_idx],
            )
        return scored

    def query_for_char(
        self,
        query_fp: np.ndarray,
        char: str,
        *,
        top_k: int = 5,
    ) -> list[tuple[str, float]]:
        """Match against every font that indexed this particular character."""
        scored = sorted(
            self.query_for_char_all(query_fp, char).items(),
            key=lambda item: item[1],
            reverse=True,
        )
        return scored[:top_k]

    def query_unknown_char(
        self,
        query_fp: np.ndarray,
        *,
        top_k: int = 5,
    ) -> list[tuple[str, float, str]]:
        """Match against every stored fingerprint; return (font_id, score, char)."""
        all_scores = self.query_unknown_char_all(query_fp)
        ranked = sorted(
            ((fid, score, char) for fid, (score, char) in all_scores.items()),
            key=lambda item: item[1],
            reverse=True,
        )
        return ranked[:top_k]


def _character_variance_weights(
    indexed: list[IndexedFont],
    char_list: list[str],
    index_dir: Path,
) -> dict[str, float]:
    """A discriminativeness score in [0.5, 2.0] per indexed character.

    For each character, we measure how much the stored fingerprints for
    that character vary across fonts — computed as the mean pairwise
    cosine distance. Characters that look similar across many fonts
    (like ".", "I", "l", "ㅡ") produce weak votes in matching; ones
    that vary wildly ("g", "Q", "R", "한", "꽃") cast strong votes. We
    persist these weights so the matcher can weight per-glyph
    contributions during hybrid ranking without re-scanning the index.
    """
    if not indexed:
        return {char: 1.0 for char in char_list}

    # Build per-char matrix of fingerprints across fonts that cover it.
    char_fingerprints: dict[str, list[np.ndarray]] = {char: [] for char in char_list}
    for entry in indexed:
        path = _vectors_path(index_dir, entry.font_id)
        if not path.exists():
            continue
        matrix = np.load(path)
        for ch_idx, char in enumerate(entry.characters):
            if char in char_fingerprints and ch_idx < matrix.shape[0]:
                char_fingerprints[char].append(matrix[ch_idx])

    variances: dict[str, float] = {}
    for char, vectors in char_fingerprints.items():
        if len(vectors) < 2:
            variances[char] = 1.0
            continue
        stacked = np.stack(vectors)
        # Cosine distance between every pair; variance is the mean.
        sims = stacked @ stacked.T
        np.fill_diagonal(sims, 1.0)
        # Lower similarity = more discriminative.
        mean_sim = float(sims[np.triu_indices_from(sims, k=1)].mean())
        # Squash mean similarity ∈ [0, 1] to a weight ∈ [0.5, 2.0]:
        # highly similar chars (mean_sim ≈ 1) → 0.5, highly distinct
        # chars (mean_sim ≈ 0) → 2.0.
        weight = max(0.5, min(2.0, 2.0 - 1.5 * mean_sim))
        variances[char] = float(weight)
    return variances


def load_index(index_dir: Path) -> FontFingerprintIndex:
    index_dir = Path(index_dir)
    manifest_path = index_dir / MANIFEST_NAME
    if not manifest_path.exists():
        raise FileNotFoundError(f"missing manifest at {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    vectors: dict[str, np.ndarray] = {}
    for entry in manifest.get("fonts", []):
        path = _vectors_path(index_dir, entry["font_id"])
        if path.exists():
            vectors[entry["font_id"]] = np.load(path)
    return FontFingerprintIndex(index_dir=index_dir, manifest=manifest, vectors=vectors)
