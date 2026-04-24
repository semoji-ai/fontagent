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


@unittest.skipUnless(DEPENDENCIES_AVAILABLE, "Pillow/fontTools/numpy not installed")
class ComposeTextLayersTests(unittest.TestCase):
    def test_compose_text_layers_end_to_end(self) -> None:
        fonts = _available_fonts()
        if len(fonts) < 2:
            self.skipTest("need at least two TTF fonts for the index")

        from fontagent.service import FontAgentService

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                '{"fonts": []}', encoding="utf-8"
            )
            service = FontAgentService(root)
            service.ensure_catalog_ready()

            # Build an index from the fixture fonts so compose_text_layers
            # has something to match against.
            from fontagent.font_identify import build_index
            from fontagent.font_identify.index import FontSource

            sources = [
                FontSource(fid, family, path, languages=["en"])
                for fid, family, path in fonts
            ]
            build_index(
                sources,
                index_dir=service.font_identify_index_dir,
                language_hint="en",
            )
            # Register matching FontRecords so profile enrichment works.
            for fid, family, path in fonts:
                service.repository.upsert_many(
                    [
                        {
                            "font_id": fid,
                            "family": family,
                            "slug": fid,
                            "source_site": "fixture",
                            "source_page_url": f"file://{path}",
                            "license_id": "OFL",
                            "license_summary": "Fixture OFL",
                            "commercial_use_allowed": True,
                            "video_use_allowed": True,
                            "web_embedding_allowed": True,
                            "redistribution_allowed": True,
                            "languages": ["en"],
                            "tags": ["serif"],
                            "recommended_for": ["title"],
                            "download_type": "manual_only",
                            "download_url": "",
                            "download_source": "fixture",
                            "format": "ttf",
                            "variable_font": False,
                        }
                    ]
                )

            # Render a poster-ish image and build two regions against it.
            target_id, _, target_path = fonts[0]
            poster = Image.new("RGB", (800, 400), color=(250, 248, 240))
            draw = ImageDraw.Draw(poster)
            draw.text(
                (20, 20), "HELLO",
                fill=(10, 10, 10),
                font=ImageFont.truetype(str(target_path), 96),
            )
            draw.text(
                (20, 200), "WORLD",
                fill=(10, 10, 10),
                font=ImageFont.truetype(str(target_path), 72),
            )
            poster_path = root / "poster.png"
            poster.save(poster_path)

            regions = [
                {
                    "bbox": [10, 10, 500, 140],
                    "text": "HELLO",
                    "role": "title",
                    "style_hints": ["serif"],
                    "language": "en",
                },
                {
                    "bbox": [10, 190, 500, 300],
                    "text": "WORLD",
                    "role": "body",
                    "style_hints": ["serif"],
                    "language": "en",
                },
            ]

            svg_path = root / "preview.svg"
            result = service.compose_text_layers(
                image_path=poster_path,
                regions=regions,
                similar_alternatives=2,
                svg_output_path=svg_path,
            )

            self.assertEqual(len(result["text_layers"]), 2)
            self.assertTrue(svg_path.exists())
            for layer in result["text_layers"]:
                self.assertIsNotNone(layer.get("font"))
                font = layer["font"]
                self.assertIn("license", font)
                self.assertIn("source", font)
                self.assertIn("install", font)
                self.assertIn("match_sources", font)
                self.assertIn("hybrid_score", font)
                self.assertIn(layer["match_reasoning"]["winner_source"],
                              {"identify_only", "recommend_only", "identify+recommend"})

    def test_compose_text_layers_emits_confidence_handoff_and_exports(self) -> None:
        fonts = _available_fonts()
        if len(fonts) < 2:
            self.skipTest("need at least two TTF fonts")
        from fontagent.service import FontAgentService

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                '{"fonts": []}', encoding="utf-8"
            )
            service = FontAgentService(root)
            service.ensure_catalog_ready()

            from fontagent.font_identify import build_index
            from fontagent.font_identify.index import FontSource

            sources = [
                FontSource(fid, family, path, languages=["en"])
                for fid, family, path in fonts
            ]
            build_index(
                sources,
                index_dir=service.font_identify_index_dir,
                language_hint="en",
            )
            for fid, family, path in fonts:
                service.repository.upsert_many([
                    {
                        "font_id": fid,
                        "family": family,
                        "slug": fid,
                        "source_site": "fixture",
                        "source_page_url": f"file://{path}",
                        "license_id": "OFL",
                        "license_summary": "Fixture OFL",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["en"],
                        "tags": ["serif"],
                        "recommended_for": ["title"],
                        "download_type": "manual_only",
                        "download_url": "",
                        "download_source": "fixture",
                        "format": "ttf",
                        "variable_font": False,
                    }
                ])

            # Simulate a successful install for every font so the CSS /
            # Remotion exports have paths to embed.
            def fake_install(font_id, output_dir, persist_result=True):
                installed_path = Path(output_dir) / f"{font_id}.ttf"
                installed_path.parent.mkdir(parents=True, exist_ok=True)
                installed_path.write_bytes(b"fake")
                return {
                    "status": "installed",
                    "font_id": font_id,
                    "installed_files": [str(installed_path)],
                }

            service.install = fake_install  # type: ignore[assignment]

            _, _, target_path = fonts[0]
            poster = Image.new("RGB", (800, 300), color=(250, 248, 240))
            draw = ImageDraw.Draw(poster)
            draw.text(
                (20, 20), "HELLO",
                fill=(10, 10, 10),
                font=ImageFont.truetype(str(target_path), 96),
            )
            poster_path = root / "poster.png"
            poster.save(poster_path)

            regions = [
                {
                    "bbox": [10, 10, 500, 140],
                    "text": "HELLO",
                    "role": "title",
                    "style_hints": ["serif"],
                    "language": "en",
                }
            ]

            result = service.compose_text_layers(
                image_path=poster_path,
                regions=regions,
                similar_alternatives=1,
                install_to=root / "assets" / "fonts",
                handoff_output_path=root / "handoff.json",
                css_output_path=root / "fonts.css",
                remotion_output_path=root / "remotionFonts.ts",
            )

            # Every layer has a populated confidence in (0, 1] plus a tier.
            layer = result["text_layers"][0]
            self.assertIn("confidence", layer)
            self.assertGreater(layer["confidence"], 0.0)
            self.assertLessEqual(layer["confidence"], 1.0)
            self.assertIn(layer["confidence_tier"], {"low", "medium", "high"})

            # Install block should carry the installed_files and status.
            install_block = layer["font"]["install"]
            self.assertEqual(install_block["install_status"], "installed")
            self.assertTrue(install_block["installed_files"])

            # Exports produced both CSS and Remotion content.
            self.assertTrue((root / "fonts.css").exists())
            self.assertTrue((root / "remotionFonts.ts").exists())
            css_body = (root / "fonts.css").read_text(encoding="utf-8")
            self.assertIn("@font-face", css_body)
            remotion_body = (root / "remotionFonts.ts").read_text(encoding="utf-8")
            self.assertIn("fontAgentTextLayerFonts", remotion_body)

            # Handoff contract has the right shape.
            handoff_path = root / "handoff.json"
            self.assertTrue(handoff_path.exists())
            import json

            contract = json.loads(handoff_path.read_text(encoding="utf-8"))
            self.assertEqual(contract["contract"], "fontagent.text-layer-handoff.v1")
            self.assertEqual(len(contract["layers"]), 1)
            self.assertIn("confidence", contract["layers"][0])
            self.assertEqual(contract["layers"][0]["font"]["install"], install_block)

            # installation_summary is attached to the response.
            summary = result["installation_summary"]
            self.assertEqual(summary["unique_fonts"], 1)
            self.assertEqual(summary["status_counts"]["installed"], 1)

    def test_compose_text_layers_applies_license_constraints(self) -> None:
        fonts = _available_fonts()
        if len(fonts) < 2:
            self.skipTest("need at least two TTF fonts")
        from fontagent.service import FontAgentService

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                '{"fonts": []}', encoding="utf-8"
            )
            service = FontAgentService(root)
            service.ensure_catalog_ready()

            from fontagent.font_identify import build_index
            from fontagent.font_identify.index import FontSource

            sources = [
                FontSource(fid, family, path, languages=["en"])
                for fid, family, path in fonts
            ]
            build_index(
                sources,
                index_dir=service.font_identify_index_dir,
                language_hint="en",
            )
            # Mark every fixture font as non-commercial so the filter has
            # something to reject.
            for fid, family, path in fonts:
                service.repository.upsert_many(
                    [
                        {
                            "font_id": fid,
                            "family": family,
                            "slug": fid,
                            "source_site": "fixture",
                            "source_page_url": f"file://{path}",
                            "license_id": "restricted",
                            "license_summary": "not for commercial use",
                            "commercial_use_allowed": False,
                            "video_use_allowed": False,
                            "web_embedding_allowed": False,
                            "redistribution_allowed": False,
                            "languages": ["en"],
                            "tags": ["serif"],
                            "recommended_for": ["title"],
                            "download_type": "manual_only",
                            "download_url": "",
                            "download_source": "fixture",
                            "format": "ttf",
                            "variable_font": False,
                        }
                    ]
                )

            _, _, target_path = fonts[0]
            poster = Image.new("RGB", (600, 200), color=(250, 248, 240))
            draw = ImageDraw.Draw(poster)
            draw.text(
                (20, 20), "HELLO",
                fill=(10, 10, 10),
                font=ImageFont.truetype(str(target_path), 80),
            )
            poster_path = root / "poster.png"
            poster.save(poster_path)

            regions = [
                {
                    "bbox": [10, 10, 400, 140],
                    "text": "HELLO",
                    "role": "title",
                    "style_hints": ["serif"],
                    "language": "en",
                }
            ]
            result = service.compose_text_layers(
                image_path=poster_path,
                regions=regions,
                license_constraints={"commercial_use": True},
                similar_alternatives=2,
            )
            self.assertEqual(len(result["text_layers"]), 1)
            # Every fixture font is marked non-commercial, so no font
            # should pass the filter.
            self.assertIsNone(result["text_layers"][0]["font"])
            self.assertEqual(result["text_layers"][0]["similar_alternatives"], [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
