from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fontagent.service import FontAgentService
from fontagent.typography_presets import get_seed_presets


def _make_service(root: Path) -> FontAgentService:
    (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
    (root / "fontagent" / "seed" / "fonts.json").write_text(
        '{"fonts": []}', encoding="utf-8"
    )
    return FontAgentService(root)


def _seed_fonts(service: FontAgentService, font_ids: list[str]) -> None:
    service.repository.upsert_many([
        {
            "font_id": fid,
            "family": fid.replace("-", " ").title(),
            "slug": fid,
            "source_site": "fixture",
            "source_page_url": "file://x",
            "license_id": "OFL",
            "license_summary": "OFL",
            "commercial_use_allowed": True,
            "video_use_allowed": True,
            "web_embedding_allowed": True,
            "redistribution_allowed": True,
            "languages": ["ko", "en"],
            "tags": ["serif"],
            "recommended_for": ["title"],
            "download_type": "manual_only",
            "download_url": "",
            "download_source": "fixture",
            "format": "ttf",
            "variable_font": False,
        }
        for fid in font_ids
    ])


class TypographyPresetStorageTests(unittest.TestCase):
    def test_seed_presets_load_on_catalog_ready(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            service = _make_service(root)
            service.ensure_catalog_ready()
            presets = service.list_typography_presets()
            seed_ids = {p["preset_id"] for p in get_seed_presets()}
            stored_ids = {p["preset_id"] for p in presets}
            self.assertEqual(stored_ids, seed_ids)

    def test_seed_presets_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            service = _make_service(root)
            service.ensure_catalog_ready()
            first_count = len(service.list_typography_presets())
            service.ensure_catalog_ready()
            second_count = len(service.list_typography_presets())
            self.assertEqual(first_count, second_count)

    def test_save_and_get_preset_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            service = _make_service(root)
            service.ensure_catalog_ready()
            result = service.save_typography_preset(
                preset_id="test-preset",
                name="Test Preset",
                description="unit test",
                tones=["clean"],
                languages=["ko"],
                mediums=["web"],
                surfaces=["landing"],
                role_assignments={
                    "title": {
                        "font_id": "pretendard",
                        "fallback_font_ids": ["suit"],
                        "pairing_reason": "neutral UI",
                    },
                },
                source="manual",
                confidence=0.77,
            )
            self.assertEqual(result["preset_id"], "test-preset")
            fetched = service.get_typography_preset("test-preset")
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched["role_assignments"]["title"]["font_id"], "pretendard")
            self.assertAlmostEqual(fetched["confidence"], 0.77)


class TypographyPresetRecommendTests(unittest.TestCase):
    def test_recommend_ranks_by_tone_language_medium_surface(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            service = _make_service(root)
            service.ensure_catalog_ready()
            ranked = service.recommend_typography_preset(
                tones=["editorial", "calm"],
                languages=["ko"],
                medium="editorial",
                surface="article",
                count=5,
            )
            self.assertTrue(ranked)
            # editorial-serif-ko should be a top candidate for this brief.
            top_ids = [entry["preset_id"] for entry in ranked[:3]]
            self.assertIn("editorial-serif-ko", top_ids)


class ComposeWithPresetTests(unittest.TestCase):
    def test_compose_honors_preset_when_font_satisfies_constraints(self) -> None:
        try:
            from PIL import Image, ImageDraw, ImageFont  # noqa: WPS433
        except ImportError:
            self.skipTest("Pillow not installed")

        from fontagent.font_identify import build_index
        from fontagent.font_identify.index import FontSource

        # Use whatever TTF we can locate so build_index succeeds.
        system_candidates = [
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ]
        available = [p for p in system_candidates if p.exists()]
        if len(available) < 2:
            self.skipTest("need at least two TTF fonts for the index")

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            service = _make_service(root)
            service.ensure_catalog_ready()

            # Seed font_ids that match the preset's role_assignments.
            _seed_fonts(service, ["pretendard", "suit", "noto-sans-kr"])

            sources = [
                FontSource("pretendard", "Pretendard", available[0], languages=["ko"]),
                FontSource("suit", "SUIT", available[1], languages=["ko"]),
            ]
            build_index(sources, index_dir=service.font_identify_index_dir, language_hint="ko")

            # Render a poster-ish image so compose_text_layers can crop.
            poster = Image.new("RGB", (800, 400), color=(250, 248, 240))
            draw = ImageDraw.Draw(poster)
            draw.text((20, 20), "미니멀", fill=(10, 10, 10),
                      font=ImageFont.truetype(str(available[0]), 80))
            poster_path = root / "poster.png"
            poster.save(poster_path)

            regions = [
                {
                    "bbox": [10, 10, 400, 120],
                    "text": "미니멀",
                    "role": "title",
                    "style_hints": ["sans", "gothic"],
                    "language": "ko",
                }
            ]
            result = service.compose_text_layers(
                image_path=poster_path,
                regions=regions,
                similar_alternatives=2,
                preset_id="modern-ui-ko",
            )
            self.assertEqual(
                result["preset_applied"],
                {"preset_id": "modern-ui-ko", "preset_name": "모던 UI 스택"},
            )
            layer = result["text_layers"][0]
            self.assertEqual(layer["font"]["font_id"], "pretendard")
            self.assertEqual(layer["match_reasoning"]["winner_source"], "preset")
            # Alternatives must not duplicate the preset winner.
            alt_ids = [a.get("font_id") for a in layer["similar_alternatives"]]
            self.assertNotIn("pretendard", alt_ids)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
