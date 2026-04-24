from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:  # pragma: no cover - exercised by CI when extras are missing
    from PIL import Image, ImageDraw, ImageFont

    from fontagent.font_identify import (
        FontFingerprintIndex,
        build_index,
        compute_fingerprint,
        cosine_similarity,
        find_similar_fonts,
        identify_from_glyph,
        identify_from_image,
        load_index,
        render_glyph_bitmap,
    )
    from fontagent.font_identify.index import FontSource

    DEPENDENCIES_AVAILABLE = True
except ImportError:  # pragma: no cover
    DEPENDENCIES_AVAILABLE = False


CANDIDATE_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]

CANDIDATE_KOREAN_FONT_PATHS = [
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/unifont/unifont.otf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]


def _available_fonts() -> list[tuple[str, str, Path]]:
    available: list[tuple[str, str, Path]] = []
    for path_str in CANDIDATE_FONT_PATHS:
        path = Path(path_str)
        if path.exists():
            available.append((f"fixture-{path.stem.lower()}", path.stem, path))
    return available


def _available_korean_fonts() -> list[tuple[str, str, Path]]:
    available: list[tuple[str, str, Path]] = []
    for path_str in CANDIDATE_KOREAN_FONT_PATHS:
        path = Path(path_str)
        if path.exists():
            available.append((f"fixture-ko-{path.stem.lower()}", path.stem, path))
    return available


@unittest.skipUnless(DEPENDENCIES_AVAILABLE, "Pillow/fontTools/numpy not installed")
class FingerprintTests(unittest.TestCase):
    def test_fingerprint_dim_is_stable(self) -> None:
        # Pin the contract so a change to block layout has to be made
        # deliberately and accompanied by an index rebuild.
        from fontagent.font_identify import FINGERPRINT_DIM

        self.assertEqual(FINGERPRINT_DIM, 906)

    def test_self_similarity_is_one(self) -> None:
        fonts = _available_fonts()
        if not fonts:
            self.skipTest("no system TTF fonts available")
        _, _, path = fonts[0]
        bitmap = render_glyph_bitmap(path, "A")
        self.assertIsNotNone(bitmap)
        fp = compute_fingerprint(bitmap)
        self.assertAlmostEqual(cosine_similarity(fp, fp), 1.0, places=5)

    def test_different_fonts_have_less_than_perfect_similarity(self) -> None:
        fonts = _available_fonts()
        if len(fonts) < 2:
            self.skipTest("need at least two TTF fonts to compare")
        fp_a = compute_fingerprint(render_glyph_bitmap(fonts[0][2], "A"))
        fp_b = compute_fingerprint(render_glyph_bitmap(fonts[1][2], "A"))
        self.assertLess(cosine_similarity(fp_a, fp_b), 0.999)


@unittest.skipUnless(DEPENDENCIES_AVAILABLE, "Pillow/fontTools/numpy not installed")
class IndexRoundTripTests(unittest.TestCase):
    def test_index_build_and_self_identify(self) -> None:
        fonts = _available_fonts()
        if len(fonts) < 2:
            self.skipTest("need at least two TTF fonts to build a useful index")

        sources = [FontSource(fid, family, path) for fid, family, path in fonts]
        with tempfile.TemporaryDirectory() as td:
            index_dir = Path(td) / "index"
            summary = build_index(sources, index_dir=index_dir, language_hint="en")
            self.assertEqual(summary["indexed_fonts"], len(sources))
            self.assertGreater(summary["total_glyphs"], 0)

            index = load_index(index_dir)
            self.assertIsInstance(index, FontFingerprintIndex)
            self.assertEqual(len(index.manifest["fonts"]), len(sources))

            # Round-trip: render a glyph from the first font and confirm
            # that the same font is in the top candidates. A strict top-1
            # assertion is unreliable here because system indexes often
            # contain near-identical family clones (DejaVu Serif vs.
            # LiberationSerif both being Times clones).
            first_id, _, first_path = fonts[0]
            bitmap = render_glyph_bitmap(first_path, "A")
            result = identify_from_glyph(bitmap, index, char_hint="A", top_k=3)
            self.assertTrue(result.top_matches, "expected at least one match")
            top_ids = [match["font_id"] for match in result.top_matches]
            self.assertIn(first_id, top_ids)


@unittest.skipUnless(DEPENDENCIES_AVAILABLE, "Pillow/fontTools/numpy not installed")
class ImageIdentificationTests(unittest.TestCase):
    def test_identify_from_rendered_image_round_trips(self) -> None:
        fonts = _available_fonts()
        if len(fonts) < 2:
            self.skipTest("need at least two TTF fonts")
        sources = [FontSource(fid, family, path) for fid, family, path in fonts]

        with tempfile.TemporaryDirectory() as td:
            index_dir = Path(td) / "index"
            build_index(sources, index_dir=index_dir, language_hint="en")
            index = load_index(index_dir)

            target_id, _, target_path = fonts[0]
            image = Image.new("L", (640, 180), color=255)
            draw = ImageDraw.Draw(image)
            draw.text((20, 20), "HELLO", fill=0, font=ImageFont.truetype(str(target_path), 96))
            image_path = Path(td) / "sample.png"
            image.save(image_path)

            result = identify_from_image(
                image_path,
                index,
                top_k=3,
                char_hints=["H", "E", "L", "L", "O"],
            )
            self.assertGreater(result.glyph_count, 0)
            self.assertTrue(result.top_matches)
            # When the target font is unique in the tiny index, it should be
            # the top match. When there are near-identical families (e.g.,
            # DejaVu Serif vs. Liberation Serif), accept any in top-3.
            top_ids = [match["font_id"] for match in result.top_matches]
            self.assertIn(target_id, top_ids)


@unittest.skipUnless(DEPENDENCIES_AVAILABLE, "Pillow/fontTools/numpy not installed")
class KoreanIdentificationTests(unittest.TestCase):
    def test_hangul_syllables_detect_as_single_glyphs(self) -> None:
        fonts = _available_korean_fonts()
        if not fonts:
            self.skipTest("no Korean-capable TTF/TTC fonts available")
        _, _, target_path = fonts[0]
        from fontagent.font_identify.detect import extract_glyph_crops

        with tempfile.TemporaryDirectory() as td:
            image = Image.new("L", (500, 140), color=255)
            draw = ImageDraw.Draw(image)
            draw.text((10, 10), "한글 가나다", fill=0, font=ImageFont.truetype(str(target_path), 80))
            image_path = Path(td) / "ko_sample.png"
            image.save(image_path)

            crops = extract_glyph_crops(image_path)
            # '한글 가나다' has five syllables; the em-square merge should
            # collapse each syllable's jamo into one glyph. Allow some
            # slack for fonts (e.g. Unifont) that produce tiny stray
            # fragments, but demand the majority of crops be syllables.
            self.assertGreaterEqual(len(crops), 5)
            self.assertLessEqual(len(crops), 6)

    def test_korean_identify_round_trips_against_same_font(self) -> None:
        fonts = _available_korean_fonts()
        if len(fonts) < 2:
            self.skipTest("need at least two Korean-capable fonts to compare")
        sources = [FontSource(fid, family, path) for fid, family, path in fonts]

        with tempfile.TemporaryDirectory() as td:
            index_dir = Path(td) / "index"
            build_index(sources, index_dir=index_dir, language_hint="ko")
            index = load_index(index_dir)

            target_id, _, target_path = fonts[0]
            image = Image.new("L", (500, 140), color=255)
            draw = ImageDraw.Draw(image)
            draw.text((10, 10), "한글 가나다", fill=0, font=ImageFont.truetype(str(target_path), 80))
            image_path = Path(td) / "ko_sample.png"
            image.save(image_path)

            result = identify_from_image(
                image_path,
                index,
                top_k=3,
                char_hints=["한", "글", "가", "나", "다"],
            )
            self.assertGreater(result.glyph_count, 0)
            self.assertTrue(result.top_matches)
            top_ids = [match["font_id"] for match in result.top_matches]
            self.assertIn(target_id, top_ids)


@unittest.skipUnless(DEPENDENCIES_AVAILABLE, "Pillow/fontTools/numpy not installed")
class SimilarFontTests(unittest.TestCase):
    def test_find_similar_fonts_excludes_reference_and_sorts_descending(self) -> None:
        fonts = _available_fonts()
        if len(fonts) < 3:
            self.skipTest("need at least three TTF fonts to rank similarities")
        sources = [FontSource(fid, family, path) for fid, family, path in fonts]
        with tempfile.TemporaryDirectory() as td:
            index_dir = Path(td) / "index"
            build_index(sources, index_dir=index_dir, language_hint="en")
            index = load_index(index_dir)

            ref_id = fonts[0][0]
            results = find_similar_fonts(index, ref_id, top_k=5)

            self.assertTrue(results)
            self.assertLessEqual(len(results), len(fonts) - 1)
            # Reference must never appear in its own similarity list.
            self.assertFalse(any(fid == ref_id for fid, _ in results))
            # Scores must be sorted highest first.
            scores = [score for _, score in results]
            self.assertEqual(scores, sorted(scores, reverse=True))

    def test_find_similar_fonts_respects_exclusion(self) -> None:
        fonts = _available_fonts()
        if len(fonts) < 3:
            self.skipTest("need at least three TTF fonts")
        sources = [FontSource(fid, family, path) for fid, family, path in fonts]
        with tempfile.TemporaryDirectory() as td:
            index_dir = Path(td) / "index"
            build_index(sources, index_dir=index_dir, language_hint="en")
            index = load_index(index_dir)

            ref_id = fonts[0][0]
            excluded_id = fonts[1][0]
            results = find_similar_fonts(
                index,
                ref_id,
                top_k=len(fonts),
                exclude_font_ids={excluded_id},
            )
            returned_ids = {fid for fid, _ in results}
            self.assertNotIn(ref_id, returned_ids)
            self.assertNotIn(excluded_id, returned_ids)


@unittest.skipUnless(DEPENDENCIES_AVAILABLE, "Pillow/fontTools/numpy not installed")
class DetectorRobustnessTests(unittest.TestCase):
    def test_otsu_threshold_handles_thin_ink(self) -> None:
        """Regression: an earlier heuristic produced an empty mask on
        images whose ink pixels covered only a few percent of the area.
        Ensure a synthetic thin-line image still yields a non-empty mask
        and detects at least one component."""
        import numpy as np

        from fontagent.font_identify.detect import (
            _auto_threshold,
            _connected_components,
        )

        array = np.full((120, 600), 250, dtype=np.uint8)
        # Four roughly square blobs of ink, thin enough that the old
        # mean-based heuristic produced an empty mask.
        for x in (40, 160, 320, 480):
            array[40:80, x : x + 30] = 20

        mask = _auto_threshold(array)
        self.assertGreater(int((mask > 0).sum()), 0)
        boxes = _connected_components(mask)
        self.assertGreaterEqual(len(boxes), 4)

    def test_dilation_reconnects_broken_strokes(self) -> None:
        """A stroke split by a 1-pixel gap must rejoin after dilation so
        the syllable merger sees a single component, not two."""
        import numpy as np

        from fontagent.font_identify.detect import _connected_components, _dilate

        mask = np.zeros((40, 80), dtype=np.uint8)
        mask[10:30, 10:30] = 255
        mask[10:30, 33:50] = 255  # 3-pixel gap

        before = _connected_components(mask)
        self.assertEqual(len(before), 2)

        after = _connected_components(_dilate(mask, radius=2))
        self.assertEqual(len(after), 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
