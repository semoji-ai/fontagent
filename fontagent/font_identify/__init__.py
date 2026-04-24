"""Font-from-image identification.

Phase 1 MVP: render installed fonts into glyph fingerprints, compare
fingerprints extracted from an input image, and rank candidate fonts.

The dependencies (Pillow, fontTools, numpy) are optional for FontAgent
as a whole and are declared as the `identify` extra in pyproject.toml.
Import sites in `service.py` must load this package lazily so the core
`FontAgent` keeps working when the extra is not installed.
"""

from __future__ import annotations

from .glyph_renderer import (
    DEFAULT_INDEX_SAMPLES_KO,
    DEFAULT_INDEX_SAMPLES_EN,
    default_index_samples,
    normalize_glyph_bitmap,
    render_glyph_bitmap,
)
from .fingerprint import (
    FINGERPRINT_DIM,
    compute_fingerprint,
    cosine_similarity,
)
from .index import (
    FontFingerprintIndex,
    IndexedFont,
    build_index,
    load_index,
)
from .detect import GlyphCrop, extract_glyph_crops
from .match import IdentificationResult, identify_from_image, identify_from_glyph
from .similar import find_similar_fonts

__all__ = [
    "DEFAULT_INDEX_SAMPLES_KO",
    "DEFAULT_INDEX_SAMPLES_EN",
    "default_index_samples",
    "normalize_glyph_bitmap",
    "render_glyph_bitmap",
    "FINGERPRINT_DIM",
    "compute_fingerprint",
    "cosine_similarity",
    "FontFingerprintIndex",
    "IndexedFont",
    "build_index",
    "load_index",
    "GlyphCrop",
    "extract_glyph_crops",
    "IdentificationResult",
    "identify_from_image",
    "identify_from_glyph",
    "find_similar_fonts",
]
