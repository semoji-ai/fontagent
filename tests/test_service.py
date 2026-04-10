from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
import zipfile
import gzip
import io
from pathlib import Path
from unittest import mock

from fontagent.curated_candidates import CURATED_CANDIDATE_SETS
from fontagent.discovery import classify_candidate_status, get_discovery_queries, parse_duckduckgo_results
from fontagent.font_system import pick_preferred_file
from fontagent.interviews import build_interview_plan
from fontagent.noonnu import fetch_noonnu_snapshot, parse_detail_html, parse_listing_html
from fontagent.official_sources import (
    fetch_cafe24_fonts,
    fetch_fontshare_fonts,
    fetch_google_display_fonts,
    parse_cafe24_catalog,
    parse_gmarket_design_system_html,
    parse_goodchoice_jalnan_css,
    parse_gongu_download_popup_html,
    parse_gongu_list_html,
    parse_fonco_detail_html,
    parse_fonco_free_font_list_html,
    parse_hancom_fonts_html,
    parse_jeju_font_info_html,
    parse_league_font_page,
    parse_nexon_brand_bundle,
    parse_naver_fonts_html,
    parse_woowahan_font_bundle,
)
from fontagent.resolver import ResolutionResult, resolve_download, write_browser_download_task
from fontagent.service import FontAgentService
from fontagent.use_cases import UseCaseRequest, preview_preset_for_use_case


class FontAgentServiceTests(unittest.TestCase):
    def test_ensure_catalog_ready_bootstraps_seed_and_system_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            seed = {
                "fonts": [
                    {
                        "font_id": "fixture-seed",
                        "family": "Fixture Seed",
                        "slug": "fixture-seed",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["title"],
                        "recommended_for": ["title"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "manual_only",
                        "download_url": "",
                        "download_source": "",
                        "format": "ttf",
                        "variable_font": False,
                    }
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            with mock.patch(
                "fontagent.service.scan_system_font_records",
                return_value=[
                    {
                        "font_id": "system-apple-sd-gothic-neo",
                        "family": "Apple SD Gothic Neo",
                        "slug": "apple-sd-gothic-neo",
                        "source_site": "system_local",
                        "source_page_url": "file:///System/Library/Fonts/AppleSDGothicNeo.ttc",
                        "homepage_url": "",
                        "license_id": "system_local",
                        "license_summary": "시스템 폰트",
                        "commercial_use_allowed": False,
                        "video_use_allowed": False,
                        "web_embedding_allowed": False,
                        "redistribution_allowed": False,
                        "languages": ["ko", "en"],
                        "tags": ["system", "installed", "local"],
                        "recommended_for": ["local_preview"],
                        "preview_text_ko": "시스템",
                        "preview_text_en": "System",
                        "download_type": "manual_only",
                        "download_url": "",
                        "download_source": "installed_system",
                        "format": "ttc",
                        "variable_font": False,
                        "installed_file_count": 2,
                    }
                ],
            ):
                summary = service.ensure_catalog_ready(auto_scan_system=True)
            self.assertEqual(summary["seeded"], 1)
            self.assertEqual(summary["system_scanned"], 1)
            status = service.catalog_status()
            self.assertEqual(status["total_fonts"], 2)
            self.assertEqual(status["installed_fonts"], 1)
            self.assertIn("system_local", status["sources"])

    def test_import_official_sources_aggregates_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = FontAgentService(root)
            with mock.patch.object(service, "import_naver_fonts", return_value={"source": "naver_hangeul", "imported": 3}), mock.patch.object(
                service,
                "import_google_display_fonts",
                return_value={"source": "google_display", "imported": 2},
            ):
                result = service.import_official_sources(sources=["naver_hangeul", "google_display"])
            self.assertEqual(result["succeeded"], 2)
            self.assertEqual(result["failed"], 0)
            self.assertEqual([item["source"] for item in result["results"]], ["naver_hangeul", "google_display"])

    def test_init_and_search(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            seeded = service.init()
            self.assertGreaterEqual(seeded, 5)

            results = service.search(query="subtitle", language="ko", commercial_only=True)
            self.assertTrue(any(item["font_id"] == "pretendard" for item in results))

    def test_search_prefers_installed_canonical_over_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            seed = {
                "fonts": [
                    {
                        "font_id": "canonical-best",
                        "family": "Canonical Best",
                        "slug": "canonical-best",
                        "source_site": "noonnu",
                        "source_page_url": "https://example.com/canonical-best",
                        "homepage_url": "https://example.com/canonical-best",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["subtitle"],
                        "recommended_for": ["subtitle"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "zip_file",
                        "download_url": "https://example.com/canonical-best.zip",
                        "download_source": "canonical",
                        "format": "zip",
                        "variable_font": False,
                    },
                    {
                        "font_id": "preview-second",
                        "family": "Preview Second",
                        "slug": "preview-second",
                        "source_site": "noonnu",
                        "source_page_url": "https://example.com/preview-second",
                        "homepage_url": "https://example.com/preview-second",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["subtitle"],
                        "recommended_for": ["subtitle"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "direct_file",
                        "download_url": "https://cdn.jsdelivr.net/gh/projectnoonnu/demo@1.0/preview-second.woff2",
                        "download_source": "preview_webfont",
                        "format": "woff2",
                        "variable_font": False,
                    },
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()
            service.repository.update_verification_fields(
                "canonical-best", "installed", "2026-04-03T00:00:00Z", 4, ""
            )
            service.repository.update_verification_fields(
                "preview-second", "installed", "2026-04-03T00:00:00Z", 1, ""
            )

            results = service.search(query="subtitle", language="ko")

            self.assertEqual(results[0]["font_id"], "canonical-best")
            self.assertEqual(results[1]["font_id"], "preview-second")

    def test_recommend_and_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()

            recommended = service.recommend(task="history documentary title", language="ko")
            self.assertTrue(recommended)
            self.assertIn("why", recommended[0])
            self.assertTrue(recommended[0]["why"])
            preview = service.preview(recommended[0]["font_id"])
            custom_preview = service.preview(
                recommended[0]["font_id"],
                preset="title-ko",
                sample_text="Custom Comparison Text",
            )
            self.assertTrue(Path(preview["preview_path"]).exists())
            self.assertTrue(Path(custom_preview["preview_path"]).exists())
            self.assertIn(".svg", preview["preview_path"])
            self.assertIn("Custom Comparison Text", Path(custom_preview["preview_path"]).read_text(encoding="utf-8"))

    def test_recommend_use_case_applies_constraints_and_preview_preset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            seed = {
                "fonts": [
                    {
                        "font_id": "web-allowed",
                        "family": "Web Allowed",
                        "slug": "web-allowed",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["display", "title", "poster", "thumbnail"],
                        "recommended_for": ["title"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "direct_file",
                        "download_url": "file://fixture/web-allowed.ttf",
                        "download_source": "canonical",
                        "format": "ttf",
                        "variable_font": False,
                    },
                    {
                        "font_id": "web-blocked",
                        "family": "Web Blocked",
                        "slug": "web-blocked",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": False,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["display", "title", "poster", "thumbnail"],
                        "recommended_for": ["title"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "direct_file",
                        "download_url": "file://fixture/web-blocked.ttf",
                        "download_source": "canonical",
                        "format": "ttf",
                        "variable_font": False,
                    },
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()
            service.repository.update_verification_fields(
                "web-allowed", "installed", "2026-04-03T00:00:00Z", 1, ""
            )
            service.repository.update_verification_fields(
                "web-blocked", "installed", "2026-04-03T00:00:00Z", 1, ""
            )

            result = service.recommend_use_case(
                medium="web",
                surface="landing_hero",
                role="title",
                tones=["editorial"],
                languages=["ko"],
                constraints={"commercial_use": True, "web_embedding": True},
                count=3,
            )

            self.assertEqual(result["preview_preset"], "title-ko")
            self.assertEqual(len(result["results"]), 1)
            self.assertEqual(result["results"][0]["font_id"], "web-allowed")
            self.assertIn("매체/표면/역할 기준", " ".join(result["results"][0]["why"]))

    def test_recommend_use_case_uses_reference_signal_to_boost_matching_font(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            seed = {
                "fonts": [
                    {
                        "font_id": "reference-target",
                        "family": "Reference Target",
                        "slug": "reference-target",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["display", "thumbnail", "title"],
                        "recommended_for": ["title"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "direct_file",
                        "download_url": "file://fixture/target.ttf",
                        "download_source": "canonical",
                        "format": "ttf",
                        "variable_font": False,
                    },
                    {
                        "font_id": "reference-other",
                        "family": "Reference Other",
                        "slug": "reference-other",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["display", "thumbnail", "title"],
                        "recommended_for": ["title"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "direct_file",
                        "download_url": "file://fixture/other.ttf",
                        "download_source": "canonical",
                        "format": "ttf",
                        "variable_font": False,
                    },
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()
            service.add_reference(
                title="Thumbnail Reference",
                medium="video",
                surface="thumbnail",
                role="title",
                source_kind="image_asset",
                asset_path="",
                tones=["quirky"],
                languages=["ko"],
                candidate_font_ids=["reference-target"],
                extraction_method="manual",
                extraction_confidence=1.0,
                status="curated",
            )

            result = service.recommend_use_case(
                medium="video",
                surface="thumbnail",
                role="title",
                tones=["quirky"],
                languages=["ko"],
                constraints={"commercial_use": True, "video_use": True},
                count=2,
                detail_level="compact",
            )

            self.assertEqual(result["results"][0]["font_id"], "reference-target")
            self.assertGreater(result["results"][0]["reference_signal"]["score"], 0)

    def test_recommend_use_case_market_reference_outweighs_specimen_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            seed = {
                "fonts": [
                    {
                        "font_id": "market-target",
                        "family": "Market Target",
                        "slug": "market-target",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": False,
                        "languages": ["en"],
                        "tags": ["display", "poster", "title"],
                        "recommended_for": ["title"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "direct_file",
                        "download_url": "file://fixture/market.ttf",
                        "download_source": "canonical",
                        "format": "ttf",
                        "variable_font": False,
                    },
                    {
                        "font_id": "specimen-target",
                        "family": "Specimen Target",
                        "slug": "specimen-target",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": False,
                        "languages": ["en"],
                        "tags": ["display", "poster", "title"],
                        "recommended_for": ["title"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "direct_file",
                        "download_url": "file://fixture/specimen.ttf",
                        "download_source": "canonical",
                        "format": "ttf",
                        "variable_font": False,
                    },
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()
            service.add_reference(
                title="Market Poster Reference",
                medium="print",
                surface="poster_hero",
                role="title",
                reference_class="market",
                source_kind="web_page",
                source_url="https://www.behance.net/example",
                tones=["poster", "editorial"],
                languages=["en"],
                candidate_font_ids=["market-target"],
                extraction_method="manual",
                extraction_confidence=1.0,
                status="curated",
            )
            service.add_reference(
                title="Specimen Poster Reference",
                medium="print",
                surface="poster_hero",
                role="title",
                reference_class="specimen",
                source_kind="web_page",
                source_url="https://fonts.example/specimen",
                tones=["poster", "editorial"],
                languages=["en"],
                candidate_font_ids=["specimen-target"],
                extraction_method="manual",
                extraction_confidence=1.0,
                status="curated",
            )

            result = service.recommend_use_case(
                medium="print",
                surface="poster_hero",
                role="title",
                tones=["poster", "editorial"],
                languages=["en"],
                constraints={"commercial_use": True},
                count=2,
                detail_level="compact",
            )

            self.assertEqual(result["results"][0]["font_id"], "market-target")
            self.assertEqual(result["results"][0]["reference_signal"]["top_matches"][0]["reference_class"], "market")

    def test_recommend_use_case_cohort_prevents_neutral_font_from_overriding_playful_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            seed = {
                "fonts": [
                    {
                        "font_id": "neutral-ui",
                        "family": "Neutral UI",
                        "slug": "neutral-ui",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["modern", "clean", "ui", "subtitle", "sans"],
                        "recommended_for": ["subtitle", "body", "ui"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "direct_file",
                        "download_url": "file://fixture/neutral.ttf",
                        "download_source": "canonical",
                        "format": "ttf",
                        "variable_font": False,
                    },
                    {
                        "font_id": "playful-display",
                        "family": "Playful Display",
                        "slug": "playful-display",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["display", "playful", "thumbnail", "title", "poster"],
                        "recommended_for": ["title", "thumbnail"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "direct_file",
                        "download_url": "file://fixture/playful.ttf",
                        "download_source": "canonical",
                        "format": "ttf",
                        "variable_font": False,
                    },
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()
            service.add_reference(
                title="Quirky Thumbnail Ref",
                medium="video",
                surface="thumbnail",
                role="title",
                source_kind="image_asset",
                asset_path="",
                tones=["quirky"],
                languages=["ko"],
                candidate_font_ids=["neutral-ui"],
                extraction_method="manual",
                extraction_confidence=1.0,
                status="curated",
            )

            result = service.recommend_use_case(
                medium="video",
                surface="thumbnail",
                role="title",
                tones=["quirky"],
                languages=["ko"],
                constraints={"commercial_use": True, "video_use": True},
                count=2,
                detail_level="compact",
            )

            self.assertEqual(result["results"][0]["font_id"], "playful-display")
            self.assertEqual(result["results"][0]["cohort_profile"]["fit"], "preferred")
            self.assertIn(result["results"][1]["cohort_profile"]["fit"], {"acceptable", "neutral"})

    def test_recommend_use_case_subtitle_prefers_neutral_over_display(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            seed = {
                "fonts": [
                    {
                        "font_id": "subtitle-neutral",
                        "family": "Subtitle Neutral",
                        "slug": "subtitle-neutral",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["sans", "subtitle", "readable", "고딕", "문서용"],
                        "recommended_for": ["subtitle", "body"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "direct_file",
                        "download_url": "file://fixture/subtitle.ttf",
                        "download_source": "canonical",
                        "format": "ttf",
                        "variable_font": False,
                    },
                    {
                        "font_id": "subtitle-display",
                        "family": "Poster Burst",
                        "slug": "subtitle-display",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["display", "poster", "thumbnail", "playful"],
                        "recommended_for": ["title", "thumbnail"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "direct_file",
                        "download_url": "file://fixture/display.ttf",
                        "download_source": "canonical",
                        "format": "ttf",
                        "variable_font": False,
                    },
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()

            result = service.recommend_use_case(
                medium="video",
                surface="subtitle_track",
                role="subtitle",
                tones=["readable"],
                languages=["ko"],
                constraints={"commercial_use": True, "video_use": True},
                count=2,
                detail_level="compact",
            )

            self.assertEqual(result["results"][0]["font_id"], "subtitle-neutral")
            self.assertEqual(result["results"][0]["cohort_profile"]["fit"], "preferred")
            self.assertEqual(result["results"][1]["cohort_profile"]["fit"], "avoid")

    def test_add_and_list_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()

            created = service.add_reference(
                title="브랜드 랜딩 히어로 레퍼런스",
                medium="web",
                surface="landing_hero",
                role="title",
                source_kind="web_page",
                source_url="https://example.com/landing",
                tones=["editorial", "luxury"],
                languages=["ko", "en"],
                text_blocks=["브랜드의 첫인상은 타이포그래피에서 시작됩니다"],
                candidate_font_ids=["pretendard"],
                observed_font_labels=["high-contrast serif heading"],
                extraction_method="manual",
                extraction_confidence=0.8,
                status="curated",
                notes=["hero title 기준으로 저장"],
            )

            listed = service.list_references(medium="web", surface="landing_hero")

            self.assertEqual(created["medium"], "web")
            self.assertEqual(len(listed["references"]), 1)
            self.assertEqual(listed["references"][0]["title"], "브랜드 랜딩 히어로 레퍼런스")
            self.assertEqual(listed["references"][0]["status"], "curated")

    def test_reference_extraction_strategies_prefers_playwright_for_web(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()

            web_plan = service.reference_extraction_strategies(
                source_kind="web_page",
                source_url="https://example.com/poster",
            )
            image_plan = service.reference_extraction_strategies(
                source_kind="image",
                asset_path="/tmp/reference.png",
            )

            self.assertEqual(web_plan["strategies"][0]["stage"], "playwright_dom")
            self.assertEqual(image_plan["strategies"][0]["stage"], "ocr")

    def test_extract_web_reference_stores_reference_and_exports_obsidian_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            screenshot = root / "fake-shot.png"
            screenshot.write_text("fake", encoding="utf-8")
            extract_json = root / "fake-extract.json"
            extract_json.write_text(json.dumps({"ok": True}, ensure_ascii=False), encoding="utf-8")
            service = FontAgentService(root)
            service.init()

            with mock.patch(
                "fontagent.service.extract_web_reference_payload",
                return_value={
                    "title": "Reference Page",
                    "url": "https://example.com",
                    "textBlocks": [
                        {"text": "Future of Typography", "fontFamily": "Demo Serif"},
                        {"text": "Readable supporting copy", "fontFamily": "Demo Sans"},
                    ],
                    "uniqueFonts": ["Demo Serif", "Demo Sans"],
                    "json_path": str(extract_json),
                    "screenshot_path": str(screenshot),
                },
            ):
                result = service.extract_web_reference(
                    title="Reference Page",
                    url="https://example.com",
                    medium="web",
                    surface="landing_hero",
                    role="title",
                    tones=["editorial"],
                    languages=["en"],
                    vault_root=root / "vault",
                    vault_category="Fonts",
                    status="curated",
                )

            note_path = Path(result["vault_export"]["note_path"])
            self.assertTrue(note_path.exists())
            self.assertIn("Reference Page", note_path.read_text(encoding="utf-8"))
            self.assertEqual(result["vault_export"]["screenshot_path"], "")
            self.assertTrue(result["vault_export"]["private_screenshot_path"])
            listed = service.list_references(medium="web", surface="landing_hero")
            self.assertEqual(len(listed["references"]), 1)
            self.assertEqual(listed["references"][0]["observed_font_labels"], ["Demo Serif", "Demo Sans"])

    def test_extract_image_reference_stores_reference_and_exports_obsidian_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            asset_path = root / "reference.png"
            asset_path.write_bytes(b"fake-image")
            service = FontAgentService(root)
            service.init()

            with mock.patch(
                "fontagent.service.extract_image_reference_payload",
                return_value={
                    "title": "Poster Reference",
                    "width": 1280,
                    "height": 720,
                    "ratio": 1.777,
                    "textBlocks": [
                        {"text": "HELLO POSTER", "confidence": 0.98, "bounds": {"x": 10, "y": 10, "width": 200, "height": 80}}
                    ],
                    "json_path": str(root / "extract.json"),
                    "screenshot_path": str(asset_path),
                },
            ):
                (root / "extract.json").write_text("{}", encoding="utf-8")
                result = service.extract_image_reference(
                    title="Poster Reference",
                    image_path=asset_path,
                    medium="print",
                    surface="poster_hero",
                    role="title",
                    tones=["poster"],
                    languages=["en"],
                    vault_root=root / "vault",
                    vault_category="Fonts",
                    status="curated",
                )

            note_path = Path(result["vault_export"]["note_path"])
            self.assertTrue(note_path.exists())
            listed = service.list_references(medium="print", surface="poster_hero")
            self.assertEqual(len(listed["references"]), 1)
            self.assertEqual(listed["references"][0]["extraction_method"], "apple_vision_ocr")

    def test_extract_image_reference_applies_vision_guess_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            asset_path = root / "reference.png"
            asset_path.write_bytes(b"fake-image")
            service = FontAgentService(root)
            service.init()

            with mock.patch(
                "fontagent.service.extract_image_reference_payload",
                return_value={
                    "title": "Poster Reference",
                    "width": 1280,
                    "height": 720,
                    "ratio": 1.777,
                    "textBlocks": [{"text": "잘난체", "confidence": 0.98, "bounds": {"x": 10, "y": 10}}],
                    "json_path": str(root / "extract.json"),
                    "screenshot_path": str(asset_path),
                },
            ), mock.patch(
                "fontagent.service.guess_reference_fonts_via_vision",
                return_value={
                    "used": True,
                    "available": True,
                    "reason": "ok",
                    "candidate_font_ids": ["goodchoice-yg-jalnan", "cafe24-supermagic-bold"],
                    "observed_font_labels": ["playful rounded display"],
                    "confidence": 0.91,
                    "reasoning": ["headline looks like playful brand display"],
                },
            ):
                (root / "extract.json").write_text("{}", encoding="utf-8")
                result = service.extract_image_reference(
                    title="Poster Reference",
                    image_path=asset_path,
                    medium="print",
                    surface="poster_hero",
                    role="title",
                    tones=["poster"],
                    languages=["ko"],
                    vault_root=root / "vault",
                    vault_category="Fonts",
                    status="curated",
                )

            listed = service.list_references(medium="print", surface="poster_hero")
            self.assertEqual(len(listed["references"]), 1)
            self.assertTrue(result["vision_guess"]["used"])
            self.assertEqual(listed["references"][0]["candidate_font_ids"][0], "goodchoice-yg-jalnan")
            self.assertEqual(listed["references"][0]["observed_font_labels"], ["playful rounded display"])
            self.assertEqual(listed["references"][0]["extraction_method"], "apple_vision_ocr+openai_vision")

    def test_reference_settings_and_index_sync(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()

            saved = service.save_reference_settings(
                vault_root=str(root / "vault"),
                vault_category="Fonts",
                asset_policy="public_metadata_only",
                private_vault_root=str(root / "private-vault"),
            )
            self.assertTrue(Path(saved["settings_path"]).exists())
            self.assertEqual(service.get_reference_settings()["vault_category"], "Fonts")
            self.assertEqual(service.get_reference_settings()["asset_policy"], "public_metadata_only")

            service.add_reference(
                title="Reference Index Test",
                medium="web",
                surface="landing_hero",
                role="title",
                source_kind="web_page",
                source_url="https://example.com",
                status="curated",
            )

            index_payload = service.sync_reference_index()
            index_path = Path(index_payload["index_path"])
            self.assertTrue(index_path.exists())
            self.assertIn("Reference Index Test", index_path.read_text(encoding="utf-8"))

    def test_add_reference_review_updates_reference_and_exports_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            seed = {
                "fonts": [
                    {
                        "font_id": "goodchoice-yg-jalnan",
                        "family": "여기어때 잘난체",
                        "slug": "yg-jalnan",
                        "source_site": "goodchoice_brand",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["display", "title"],
                        "recommended_for": ["title"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "direct_file",
                        "download_url": "file://fixture/yg-jalnan.ttf",
                        "download_source": "canonical",
                        "format": "ttf",
                        "variable_font": False,
                    }
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()
            service.save_reference_settings(vault_root=str(root / "vault"), vault_category="Fonts")

            created = service.add_reference(
                title="Review Target",
                medium="video",
                surface="thumbnail",
                role="title",
                source_kind="image_asset",
                asset_path="",
                tones=["quirky"],
                languages=["ko"],
                status="curated",
            )
            review_result = service.add_reference_review(
                reference_id=created["reference_id"],
                reviewer_kind="agent_vision",
                reviewer_name="claude",
                model_name="vision-demo",
                summary="동글고 장난스러운 display 계열",
                candidate_font_ids=["goodchoice-yg-jalnan", "pretendard"],
                observed_font_labels=["quirky rounded display"],
                cohort_tags=["display_playful"],
                confidence=0.91,
                notes=["썸네일 제목에 적합"],
                apply_to_reference=True,
            )

            listed_reviews = service.list_reference_reviews(reference_id=created["reference_id"])
            self.assertEqual(len(listed_reviews["reviews"]), 1)
            self.assertEqual(listed_reviews["reviews"][0]["reviewer_name"], "claude")
            listed = service.list_references(medium="video", surface="thumbnail")
            self.assertEqual(listed["references"][0]["candidate_font_ids"][0], "goodchoice-yg-jalnan")
            self.assertEqual(listed["references"][0]["candidate_font_ids"][1], "pretendard")
            self.assertEqual(listed["references"][0]["observed_font_labels"], ["quirky rounded display"])
            self.assertTrue(review_result["vault_export"])
            note_path = Path(review_result["vault_export"]["note_path"])
            self.assertTrue(note_path.exists())
            note_text = note_path.read_text(encoding="utf-8")
            self.assertIn("## Agent Reviews", note_text)
            self.assertIn("claude", note_text)
            self.assertTrue(review_result["vault_export"]["private_review_paths"])

    def test_refresh_reference_candidates_backfills_candidate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            seed = {
                "fonts": [
                    {
                        "font_id": "goodchoice-yg-jalnan",
                        "family": "여기어때 잘난체",
                        "slug": "yg-jalnan",
                        "source_site": "goodchoice_brand",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["display", "title"],
                        "recommended_for": ["title"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "direct_file",
                        "download_url": "file://fixture/yg-jalnan.ttf",
                        "download_source": "canonical",
                        "format": "ttf",
                        "variable_font": False,
                    }
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()
            service.add_reference(
                title="Goodchoice Reference",
                medium="web",
                surface="landing_hero",
                role="title",
                source_kind="web_page",
                source_url="https://example.com",
                observed_font_labels=["yg-jalnan"],
                status="curated",
            )

            result = service.refresh_reference_candidates()
            self.assertEqual(result["updated"], 1)
            listed = service.list_references(status="curated")
            self.assertEqual(listed["references"][0]["candidate_font_ids"], ["goodchoice-yg-jalnan"])

    def test_learn_reference_pack_runs_extraction_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()

            fake_extraction = {
                "url": "https://example.com",
                "title": "Demo Extraction",
                "textBlocks": [{"text": "Hello Reference"}],
                "uniqueFonts": ["Demo Serif"],
                "screenshot_path": "",
                "json_path": "",
            }

            with mock.patch(
                "fontagent.service.extract_web_reference_payload",
                return_value=fake_extraction,
            ):
                result = service.learn_reference_pack(
                    pack_name="trend-korean-brand-display",
                    limit=2,
                    continue_on_error=False,
                )

            self.assertEqual(result["succeeded"], 2)
            self.assertEqual(result["failed"], 0)
            listed = service.list_references(status="curated")
            self.assertEqual(len(listed["references"]), 2)

    def test_list_reference_packs_includes_context_expansion_packs(self) -> None:
        service = FontAgentService(Path("/Users/jleavens_macmini/Projects/fontagent"))
        packs = service.list_reference_packs()["packs"]

        self.assertIn("trend-korean-video-thumbnail-display", packs)
        self.assertIn("trend-video-subtitle-readable", packs)
        self.assertIn("trend-web-editorial-heroes", packs)
        self.assertIn("trend-presentation-cover-display", packs)
        self.assertIn("trend-detailpage-brand-heroes", packs)
        self.assertIn("trend-print-poster-display", packs)
        self.assertIn("market-presentation-covers", packs)
        self.assertIn("market-detailpage-heroes", packs)
        self.assertIn("market-print-poster-typography", packs)

    def test_add_reference_infers_market_class_from_behance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps({"fonts": []}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()

            created = service.add_reference(
                title="Behance Detail Reference",
                medium="detailpage",
                surface="hero",
                role="title",
                source_kind="web_page",
                source_url="https://www.behance.net/gallery/237183715/E-commerce-detail-page-design",
                status="curated",
            )

            self.assertEqual(created["reference_class"], "market")

    def test_list_references_and_status_support_private_user_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps({"fonts": []}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()
            service.add_reference(
                title="Shared Reference",
                medium="web",
                surface="landing_hero",
                role="title",
                source_kind="web_page",
                source_url="https://example.com/shared",
                status="curated",
            )
            service.add_reference(
                title="Private Reference",
                medium="video",
                surface="thumbnail",
                role="title",
                source_kind="image_asset",
                asset_path="/tmp/private.png",
                reference_scope="private_user",
                status="curated",
            )

            listed = service.list_references(reference_scope="private_user")
            status = service.reference_catalog_status()

            self.assertEqual(len(listed["references"]), 1)
            self.assertEqual(listed["references"][0]["title"], "Private Reference")
            self.assertEqual(status["reference_scopes"]["shared_public"], 1)
            self.assertEqual(status["reference_scopes"]["private_user"], 1)

    def test_build_interview_plan_returns_request_and_canvas(self) -> None:
        plan = build_interview_plan(
            "web",
            "landing_hero",
            answers={
                "tone": "luxury",
                "density": "editorial",
                "language_mix": "ko-en",
                "license_mode": "campaign",
            },
            language="ko",
        )

        self.assertEqual(plan["request"]["medium"], "web")
        self.assertEqual(plan["request"]["surface"], "landing_hero")
        self.assertIn("luxury", plan["request"]["tones"])
        self.assertEqual(plan["request"]["languages"], ["ko", "en"])
        self.assertTrue(plan["request"]["constraints"]["web_embedding"])
        self.assertEqual(plan["canvas"]["layout_mode"], "split-hero")
        self.assertTrue(plan["recommended_copy"]["title"])

    def test_guided_interview_recommend_returns_canvas_and_font_system_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()

            result = service.guided_interview_recommend(
                category="video",
                subcategory="thumbnail",
                answers={
                    "tone": "retro",
                    "density": "balanced",
                    "language_mix": "ko",
                    "license_mode": "monetized",
                },
                language="ko",
                count=4,
            )

            self.assertEqual(result["category"], "video")
            self.assertEqual(result["subcategory"], "thumbnail")
            self.assertEqual(result["request"]["medium"], "video")
            self.assertEqual(result["canvas"]["layout_mode"], "left-stack")
            self.assertIn("title", result["font_system_preview"]["roles"])
            self.assertIn("subtitle", result["font_system_preview"]["roles"])
            self.assertIn("body", result["font_system_preview"]["roles"])
            self.assertTrue(result["results"])

    def test_guided_interview_recommend_supports_video_subtitle_track(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()

            result = service.guided_interview_recommend(
                category="video",
                subcategory="subtitle_track",
                answers={
                    "tone": "neutral",
                    "density": "balanced",
                    "language_mix": "ko",
                    "license_mode": "monetized",
                },
                language="ko",
                count=4,
            )

            self.assertEqual(result["request"]["surface"], "subtitle_track")
            self.assertEqual(result["request"]["role"], "subtitle")
            self.assertEqual(result["canvas"]["layout_mode"], "subtitle-band")
            self.assertTrue(result["results"])

    def test_guided_interview_recommend_can_omit_canvas_and_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()

            result = service.guided_interview_recommend(
                category="video",
                subcategory="thumbnail",
                answers={
                    "tone": "retro",
                    "density": "balanced",
                    "language_mix": "ko",
                    "license_mode": "monetized",
                },
                language="ko",
                count=3,
                detail_level="compact",
                include_canvas=False,
                include_font_system_preview=False,
            )

            self.assertNotIn("canvas", result)
            self.assertNotIn("font_system_preview", result)
            self.assertTrue(result["results"])
            self.assertNotIn("download_url", result["results"][0])

    def test_search_attaches_license_and_automation_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            seed = {
                "fonts": [
                    {
                        "font_id": "policy-font",
                        "family": "Policy Font",
                        "slug": "policy-font",
                        "source_site": "gmarket_brand",
                        "source_page_url": "file://fixture/policy",
                        "homepage_url": "file://fixture/policy",
                        "license_id": "fixture",
                        "license_summary": "상업적 이용 가능",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["display", "title"],
                        "recommended_for": ["title"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "zip_file",
                        "download_url": "https://example.com/policy.zip",
                        "download_source": "canonical",
                        "format": "zip",
                        "variable_font": False,
                    },
                    {
                        "font_id": "manual-font",
                        "family": "Manual Font",
                        "slug": "manual-font",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture/manual",
                        "homepage_url": "file://fixture/manual",
                        "license_id": "fixture",
                        "license_summary": "상업적 이용 불가",
                        "commercial_use_allowed": False,
                        "video_use_allowed": False,
                        "web_embedding_allowed": False,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["display"],
                        "recommended_for": ["title"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "manual_only",
                        "download_url": "https://example.com/manual",
                        "download_source": "",
                        "format": "manual",
                        "variable_font": False,
                    },
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()
            service.repository.update_verification_fields(
                "policy-font", "installed", "2026-04-04T00:00:00Z", 3, ""
            )

            results = service.search(language="ko", include_failed=True)
            by_id = {item["font_id"]: item for item in results}

            self.assertEqual(by_id["policy-font"]["license_profile"]["status"], "allowed")
            self.assertEqual(by_id["policy-font"]["license_profile"]["confidence"], "high")
            self.assertEqual(by_id["policy-font"]["license_profile"]["recommended_action"], "proceed")
            self.assertIn("trusted_source_registry_high", by_id["policy-font"]["license_profile"]["basis"])
            self.assertEqual(by_id["policy-font"]["license_profile"]["source_policy"]["review_level"], "low")
            self.assertFalse(by_id["policy-font"]["license_profile"]["review_required"])
            self.assertEqual(by_id["policy-font"]["automation_profile"]["status"], "ready")
            self.assertEqual(by_id["manual-font"]["license_profile"]["status"], "blocked")
            self.assertEqual(by_id["manual-font"]["license_profile"]["recommended_action"], "do_not_use")
            self.assertTrue(by_id["manual-font"]["license_profile"]["review_required"])
            self.assertEqual(by_id["manual-font"]["automation_profile"]["status"], "manual")

    def test_license_policy_catalog_returns_known_sources(self) -> None:
        service = FontAgentService(Path("/Users/jleavens_macmini/Projects/fontagent"))
        result = service.license_policy_catalog()

        self.assertIn("google_fonts", result["sources"])
        self.assertEqual(result["sources"]["google_fonts"]["trust_level"], "high")
        self.assertIn("gongu_freefont", result["sources"])

    def test_search_compact_detail_omits_heavy_download_fields(self) -> None:
        service = FontAgentService(Path("/Users/jleavens_macmini/Projects/fontagent"))
        service.repository.init_db()
        if not service.repository.list_fonts():
            service.init()

        result = service.search(language="ko", detail_level="compact")
        self.assertTrue(result)
        first = result[0]
        self.assertIn("font_id", first)
        self.assertIn("license_profile", first)
        self.assertNotIn("download_url", first)
        self.assertNotIn("source_page_url", first)

    def test_recommend_use_case_compact_detail_returns_compact_results(self) -> None:
        service = FontAgentService(Path("/Users/jleavens_macmini/Projects/fontagent"))
        service.repository.init_db()
        if not service.repository.list_fonts():
            service.init()

        result = service.recommend_use_case(
            medium="web",
            surface="landing_hero",
            role="title",
            tones=["editorial"],
            languages=["ko"],
            constraints={"commercial_use": True, "web_embedding": True},
            count=2,
            detail_level="compact",
        )

        self.assertTrue(result["results"])
        first = result["results"][0]
        self.assertIn("why", first)
        self.assertIn("license_profile", first)
        self.assertNotIn("download_url", first)

    def test_get_contract_schema_returns_typography_handoff_schema(self) -> None:
        service = FontAgentService(Path("/Users/jleavens_macmini/Projects/fontagent"))
        schema = service.get_contract_schema()

        self.assertEqual(schema["name"], "typography-handoff.v1")
        self.assertTrue(schema["path"].endswith("typography-handoff.v1.schema.json"))
        self.assertEqual(schema["schema"]["title"], "FontAgent Typography Handoff v1")

    def test_bootstrap_project_integration_writes_project_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path("/Users/jleavens_macmini/Projects/fontagent")
            project = Path(tmp) / "target-project"
            service = FontAgentService(root)

            result = service.bootstrap_project_integration(
                project_path=project,
                use_case="youtube-thumbnail-ko",
                language="ko",
                target="both",
            )

            self.assertTrue(Path(result["config_path"]).exists())
            self.assertTrue(Path(result["prompt_path"]).exists())
            self.assertTrue(Path(result["mcp_configs"]["codex"]).exists())
            self.assertTrue(Path(result["codex_skill"]).exists())

    def test_recommend_prefers_installed_canonical_over_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            seed = {
                "fonts": [
                    {
                        "font_id": "canonical-title",
                        "family": "Canonical Title",
                        "slug": "canonical-title",
                        "source_site": "noonnu",
                        "source_page_url": "https://example.com/canonical-title",
                        "homepage_url": "https://example.com/canonical-title",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["history", "documentary"],
                        "recommended_for": ["title"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "zip_file",
                        "download_url": "https://example.com/canonical-title.zip",
                        "download_source": "canonical",
                        "format": "zip",
                        "variable_font": False,
                    },
                    {
                        "font_id": "preview-title",
                        "family": "Preview Title",
                        "slug": "preview-title",
                        "source_site": "noonnu",
                        "source_page_url": "https://example.com/preview-title",
                        "homepage_url": "https://example.com/preview-title",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["history", "documentary"],
                        "recommended_for": ["title"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "direct_file",
                        "download_url": "https://cdn.jsdelivr.net/gh/projectnoonnu/demo@1.0/preview-title.woff2",
                        "download_source": "preview_webfont",
                        "format": "woff2",
                        "variable_font": False,
                    },
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()
            service.repository.update_verification_fields(
                "canonical-title", "installed", "2026-04-03T00:00:00Z", 5, ""
            )
            service.repository.update_verification_fields(
                "preview-title", "installed", "2026-04-03T00:00:00Z", 1, ""
            )

            results = service.recommend(task="history documentary title", language="ko", count=2)

            self.assertEqual(results[0]["font_id"], "canonical-title")
            self.assertEqual(results[1]["font_id"], "preview-title")

    def test_install_direct_and_zip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            direct_file = root / "demo.ttf"
            direct_file.write_bytes(b"demo-font")
            zip_path = root / "demo.zip"
            with zipfile.ZipFile(zip_path, "w") as zip_file:
                zip_file.writestr("nested/font.otf", b"otf-font")

            seed = {
                "fonts": [
                    {
                        "font_id": "direct-demo",
                        "family": "Direct Demo",
                        "slug": "direct-demo",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["subtitle"],
                        "recommended_for": ["subtitle"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "direct_file",
                        "download_url": direct_file.as_uri(),
                        "format": "ttf",
                        "variable_font": False,
                    },
                    {
                        "font_id": "zip-demo",
                        "family": "Zip Demo",
                        "slug": "zip-demo",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["title"],
                        "recommended_for": ["title"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "zip_file",
                        "download_url": zip_path.as_uri(),
                        "format": "zip",
                        "variable_font": False,
                    }
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            service = FontAgentService(root)
            service.init()
            install_dir = root / "installed"

            direct_result = service.install("direct-demo", install_dir)
            zip_result = service.install("zip-demo", install_dir)

            self.assertEqual(direct_result["status"], "installed")
            self.assertEqual(zip_result["status"], "installed")
            self.assertTrue(any(path.endswith(".ttf") for path in direct_result["installed_files"]))
            self.assertTrue(any(path.endswith(".otf") for path in zip_result["installed_files"]))

    def test_install_zip_without_font_files_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            zip_path = root / "invalid.zip"
            with zipfile.ZipFile(zip_path, "w") as zip_file:
                zip_file.writestr("README.txt", b"no fonts here")

            seed = {
                "fonts": [
                    {
                        "font_id": "bad-zip",
                        "family": "Bad Zip",
                        "slug": "bad-zip",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["subtitle"],
                        "recommended_for": ["subtitle"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "zip_file",
                        "download_url": zip_path.as_uri(),
                        "format": "zip",
                        "variable_font": False,
                    }
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            service = FontAgentService(root)
            service.init()
            install_dir = root / "installed"
            result = service.install("bad-zip", install_dir)
            self.assertEqual(result["status"], "invalid_archive")

    def test_install_gzip_wrapped_zip_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            zip_path = root / "wrapped.zip"
            plain_zip = root / "plain.zip"
            with zipfile.ZipFile(plain_zip, "w") as zip_file:
                zip_file.writestr("nested/font.ttf", b"ttf-font")
            zip_path.write_bytes(gzip.compress(plain_zip.read_bytes()))

            seed = {
                "fonts": [
                    {
                        "font_id": "wrapped-zip",
                        "family": "Wrapped Zip",
                        "slug": "wrapped-zip",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["subtitle"],
                        "recommended_for": ["subtitle"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "zip_file",
                        "download_url": zip_path.as_uri(),
                        "format": "zip",
                        "variable_font": False,
                    }
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            service = FontAgentService(root)
            service.init()
            result = service.install("wrapped-zip", root / "installed")
            self.assertEqual(result["status"], "installed")
            self.assertTrue(any(path.endswith(".ttf") for path in result["installed_files"]))

    def test_install_nested_zip_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)

            inner_zip = io.BytesIO()
            with zipfile.ZipFile(inner_zip, "w") as zip_file:
                zip_file.writestr("fonts/demo.otf", b"otf-font")

            outer_zip = root / "nested.zip"
            with zipfile.ZipFile(outer_zip, "w") as zip_file:
                zip_file.writestr("packages/font-pack.zip", inner_zip.getvalue())

            seed = {
                "fonts": [
                    {
                        "font_id": "nested-zip",
                        "family": "Nested Zip",
                        "slug": "nested-zip",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["subtitle"],
                        "recommended_for": ["subtitle"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "zip_file",
                        "download_url": outer_zip.as_uri(),
                        "format": "zip",
                        "variable_font": False,
                    }
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            service = FontAgentService(root)
            service.init()
            result = service.install("nested-zip", root / "installed")
            self.assertEqual(result["status"], "installed")
            self.assertTrue(any(path.endswith(".otf") for path in result["installed_files"]))

    def test_install_zip_ignores_macos_metadata_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            zip_path = root / "macos-metadata.zip"
            with zipfile.ZipFile(zip_path, "w") as zip_file:
                zip_file.writestr("__MACOSX/fonts/._Demo.ttf", b"metadata")
                zip_file.writestr("fonts/._Demo.ttf", b"metadata")
                zip_file.writestr("fonts/Demo.ttf", b"real-font")

            seed = {
                "fonts": [
                    {
                        "font_id": "macos-metadata",
                        "family": "MacOS Metadata",
                        "slug": "macos-metadata",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["title"],
                        "recommended_for": ["title"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "zip_file",
                        "download_url": zip_path.as_uri(),
                        "format": "zip",
                        "variable_font": False,
                    }
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            service = FontAgentService(root)
            service.init()
            result = service.install("macos-metadata", root / "installed")
            self.assertEqual(result["status"], "installed")
            self.assertEqual(len(result["installed_files"]), 1)
            self.assertTrue(result["installed_files"][0].endswith("Demo.ttf"))

    def test_prepare_font_system_writes_project_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "demo-project"
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)

            title_file = root / "title.ttf"
            subtitle_file = root / "subtitle.ttf"
            body_file = root / "body.ttf"
            title_file.write_bytes(b"title-font")
            subtitle_file.write_bytes(b"subtitle-font")
            body_file.write_bytes(b"body-font")

            seed = {
                "fonts": [
                    {
                        "font_id": "title-demo",
                        "family": "Title Demo",
                        "slug": "title-demo",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["display", "title", "poster"],
                        "recommended_for": ["title", "thumbnail"],
                        "preview_text_ko": "타이틀",
                        "preview_text_en": "Title",
                        "download_type": "direct_file",
                        "download_url": title_file.as_uri(),
                        "format": "ttf",
                        "variable_font": False,
                    },
                    {
                        "font_id": "subtitle-demo",
                        "family": "Subtitle Demo",
                        "slug": "subtitle-demo",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["subtitle", "sans"],
                        "recommended_for": ["subtitle"],
                        "preview_text_ko": "자막",
                        "preview_text_en": "Subtitle",
                        "download_type": "direct_file",
                        "download_url": subtitle_file.as_uri(),
                        "format": "ttf",
                        "variable_font": False,
                    },
                    {
                        "font_id": "body-demo",
                        "family": "Body Demo",
                        "slug": "body-demo",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["body", "editorial"],
                        "recommended_for": ["body"],
                        "preview_text_ko": "본문",
                        "preview_text_en": "Body",
                        "download_type": "direct_file",
                        "download_url": body_file.as_uri(),
                        "format": "ttf",
                        "variable_font": False,
                    },
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            service = FontAgentService(root)
            service.init()
            result = service.prepare_font_system(
                project_path=project,
                task="history documentary",
                language="ko",
                target="both",
                use_case="documentary-landing-ko",
            )

            self.assertTrue((project / "fontagent" / "font-system.json").exists())
            self.assertTrue((project / "fontagent" / "fonts.css").exists())
            self.assertTrue((project / "fontagent" / "remotion-font-system.ts").exists())
            self.assertEqual(result["roles"]["title"]["font_id"], "title-demo")
            self.assertEqual(result["roles"]["subtitle"]["font_id"], "subtitle-demo")
            self.assertEqual(result["roles"]["body"]["font_id"], "body-demo")
            self.assertEqual(result["use_case"], "documentary-landing-ko")
            css = (project / "fontagent" / "fonts.css").read_text(encoding="utf-8")
            manifest = json.loads((project / "fontagent" / "font-system.json").read_text(encoding="utf-8"))
            remotion = (project / "fontagent" / "remotion-font-system.ts").read_text(encoding="utf-8")
            self.assertIn("--font-family-title", css)
            self.assertIn("--font-weight-body: 400;", css)
            self.assertIn("--font-line-height-subtitle: 1.35;", css)
            self.assertEqual(manifest["use_case"], "documentary-landing-ko")
            self.assertIn("genericFamily", remotion)

    def test_prepare_font_system_with_templates_writes_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "demo-project"
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)

            title_file = root / "title.ttf"
            subtitle_file = root / "subtitle.ttf"
            body_file = root / "body.ttf"
            title_file.write_bytes(b"title-font")
            subtitle_file.write_bytes(b"subtitle-font")
            body_file.write_bytes(b"body-font")

            seed = {
                "fonts": [
                    {
                        "font_id": "title-demo",
                        "family": "Title Demo",
                        "slug": "title-demo",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["display", "title", "poster"],
                        "recommended_for": ["title"],
                        "preview_text_ko": "타이틀",
                        "preview_text_en": "Title",
                        "download_type": "direct_file",
                        "download_url": title_file.as_uri(),
                        "format": "ttf",
                        "variable_font": False,
                    },
                    {
                        "font_id": "subtitle-demo",
                        "family": "Subtitle Demo",
                        "slug": "subtitle-demo",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["subtitle", "sans"],
                        "recommended_for": ["subtitle"],
                        "preview_text_ko": "자막",
                        "preview_text_en": "Subtitle",
                        "download_type": "direct_file",
                        "download_url": subtitle_file.as_uri(),
                        "format": "ttf",
                        "variable_font": False,
                    },
                    {
                        "font_id": "body-demo",
                        "family": "Body Demo",
                        "slug": "body-demo",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["body", "editorial"],
                        "recommended_for": ["body"],
                        "preview_text_ko": "본문",
                        "preview_text_en": "Body",
                        "download_type": "direct_file",
                        "download_url": body_file.as_uri(),
                        "format": "ttf",
                        "variable_font": False,
                    },
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            service = FontAgentService(root)
            service.init()
            result = service.generate_template_bundle(
                project_path=project,
                task="history documentary",
                language="ko",
                target="both",
                use_case="documentary-landing-ko",
            )

            bundle = result["template_bundle"]
            self.assertTrue(Path(bundle["landing_path"]).exists())
            self.assertTrue(Path(bundle["thumbnail_path"]).exists())
            self.assertTrue(Path(bundle["poster_path"]).exists())
            self.assertTrue(Path(bundle["css_path"]).exists())
            landing = Path(bundle["landing_path"]).read_text(encoding="utf-8")
            thumbnail = Path(bundle["thumbnail_path"]).read_text(encoding="utf-8")
            self.assertIn("showcase.css", landing)
            self.assertIn("Thumbnail Template", thumbnail)

    def test_generate_typography_handoff_returns_design_agent_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "demo-project"
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)

            title_file = root / "title.ttf"
            subtitle_file = root / "subtitle.ttf"
            body_file = root / "body.ttf"
            title_file.write_bytes(b"title-font")
            subtitle_file.write_bytes(b"subtitle-font")
            body_file.write_bytes(b"body-font")

            seed = {
                "fonts": [
                    {
                        "font_id": "title-demo",
                        "family": "Title Demo",
                        "slug": "title-demo",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["display", "title", "poster"],
                        "recommended_for": ["title"],
                        "preview_text_ko": "타이틀",
                        "preview_text_en": "Title",
                        "download_type": "direct_file",
                        "download_url": title_file.as_uri(),
                        "format": "ttf",
                        "variable_font": False,
                    },
                    {
                        "font_id": "subtitle-demo",
                        "family": "Subtitle Demo",
                        "slug": "subtitle-demo",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["subtitle", "sans"],
                        "recommended_for": ["subtitle"],
                        "preview_text_ko": "자막",
                        "preview_text_en": "Subtitle",
                        "download_type": "direct_file",
                        "download_url": subtitle_file.as_uri(),
                        "format": "ttf",
                        "variable_font": False,
                    },
                    {
                        "font_id": "body-demo",
                        "family": "Body Demo",
                        "slug": "body-demo",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["body", "editorial"],
                        "recommended_for": ["body"],
                        "preview_text_ko": "본문",
                        "preview_text_en": "Body",
                        "download_type": "direct_file",
                        "download_url": body_file.as_uri(),
                        "format": "ttf",
                        "variable_font": False,
                    },
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            service = FontAgentService(root)
            service.init()
            result = service.generate_typography_handoff(
                project_path=project,
                task="history documentary",
                language="ko",
                target="both",
                use_case="documentary-landing-ko",
            )

            self.assertEqual(result["medium"], "web")
            self.assertEqual(result["surface"], "landing_hero")
            self.assertEqual(result["font_system"]["roles"]["title"]["font_id"], "title-demo")
            self.assertTrue(result["license_notes"])
            self.assertIn("FontAgent는 타이포 시스템", " ".join(result["design_agent_handoff"]["notes"]))

    def test_list_use_cases_returns_presets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = FontAgentService(root)

            result = service.list_use_cases()

            self.assertIn("documentary-landing-ko", result["use_cases"])
            self.assertIn("knowledge-video-white-ko", result["use_cases"])
            self.assertIn("youtube-thumbnail-ko", result["use_cases"])

    def test_pick_preferred_file_uses_role_specific_weight_preferences(self) -> None:
        title_choice = pick_preferred_file(
            [
                "/tmp/Demo-Regular.ttf",
                "/tmp/Demo-Bold.ttf",
                "/tmp/Demo-Light.ttf",
            ],
            "title",
        )
        subtitle_choice = pick_preferred_file(
            [
                "/tmp/Demo-Black.ttf",
                "/tmp/Demo-Regular.ttf",
                "/tmp/Demo-Bold.ttf",
            ],
            "subtitle",
        )
        body_choice = pick_preferred_file(
            [
                "/tmp/Demo-SemiBold.ttf",
                "/tmp/Demo-Regular.ttf",
                "/tmp/Demo-Bold.ttf",
            ],
            "body",
        )

        self.assertEqual(Path(title_choice).name, "Demo-Bold.ttf")
        self.assertEqual(Path(subtitle_choice).name, "Demo-Regular.ttf")
        self.assertEqual(Path(body_choice).name, "Demo-Regular.ttf")

    def test_pick_preferred_file_prefers_family_matching_name(self) -> None:
        choice = pick_preferred_file(
            [
                "/tmp/JejuGothic.ttf",
                "/tmp/JejuMyeongjo.ttf",
            ],
            "body",
            family_hint="jeju-myeongjo",
        )

        self.assertEqual(Path(choice).name, "JejuMyeongjo.ttf")

    def test_install_non_zip_payload_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            fake_zip = root / "fake.zip"
            fake_zip.write_text("not a zip", encoding="utf-8")

            seed = {
                "fonts": [
                    {
                        "font_id": "fake-zip",
                        "family": "Fake Zip",
                        "slug": "fake-zip",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["subtitle"],
                        "recommended_for": ["subtitle"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "zip_file",
                        "download_url": fake_zip.as_uri(),
                        "format": "zip",
                        "variable_font": False,
                    }
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            service = FontAgentService(root)
            service.init()
            result = service.install("fake-zip", root / "installed")
            self.assertEqual(result["status"], "invalid_archive")

    def test_install_persists_verification_and_search_excludes_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            direct_file = root / "demo.ttf"
            direct_file.write_bytes(b"demo-font")
            fake_zip = root / "fake.zip"
            fake_zip.write_text("not a zip", encoding="utf-8")

            seed = {
                "fonts": [
                    {
                        "font_id": "good-demo",
                        "family": "Good Demo",
                        "slug": "good-demo",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["subtitle"],
                        "recommended_for": ["subtitle"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "direct_file",
                        "download_url": direct_file.as_uri(),
                        "format": "ttf",
                        "variable_font": False,
                    },
                    {
                        "font_id": "bad-demo",
                        "family": "Bad Demo",
                        "slug": "bad-demo",
                        "source_site": "fixture",
                        "source_page_url": "file://fixture",
                        "homepage_url": "file://fixture",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["subtitle"],
                        "recommended_for": ["subtitle"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "zip_file",
                        "download_url": fake_zip.as_uri(),
                        "format": "zip",
                        "variable_font": False,
                    },
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            service = FontAgentService(root)
            service.init()

            good_result = service.install("good-demo", root / "installed")
            bad_result = service.install("bad-demo", root / "installed")

            self.assertEqual(good_result["status"], "installed")
            self.assertEqual(bad_result["status"], "invalid_archive")

            good_record = service.repository.get_font("good-demo")
            bad_record = service.repository.get_font("bad-demo")
            self.assertEqual(good_record.verification_status, "installed")
            self.assertEqual(good_record.installed_file_count, 1)
            self.assertEqual(bad_record.verification_status, "invalid_archive")
            self.assertIn("ZIP", bad_record.verification_failure_reason)

            visible = {item["font_id"] for item in service.search()}
            hidden = {item["font_id"] for item in service.search(include_failed=True)}
            self.assertIn("good-demo", visible)
            self.assertNotIn("bad-demo", visible)
            self.assertIn("bad-demo", hidden)

    def test_upsert_many_preserves_verification_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()

            service.repository.update_verification_fields(
                font_id="pretendard",
                verification_status="invalid_archive",
                verified_at="2026-04-03T00:00:00Z",
                installed_file_count=0,
                verification_failure_reason="fixture failure",
            )
            service.repository.upsert_many(
                [
                    {
                        "font_id": "pretendard",
                        "family": "Pretendard",
                        "slug": "pretendard",
                        "source_site": "fixture",
                        "source_page_url": "https://example.com/pretendard",
                        "homepage_url": "https://example.com/pretendard",
                        "license_id": "fixture",
                        "license_summary": "updated",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["subtitle"],
                        "recommended_for": ["subtitle"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "zip_file",
                        "download_url": "https://example.com/pretendard.zip",
                        "format": "zip",
                        "variable_font": False,
                    }
                ]
            )

            stored = service.repository.get_font("pretendard")
            self.assertEqual(stored.license_summary, "updated")
            self.assertEqual(stored.verification_status, "invalid_archive")
            self.assertEqual(stored.verification_failure_reason, "fixture failure")

    def test_init_db_migrates_existing_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "fontagent.db"
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE fonts (
                        font_id TEXT PRIMARY KEY,
                        family TEXT NOT NULL,
                        slug TEXT NOT NULL,
                        source_site TEXT NOT NULL,
                        source_page_url TEXT NOT NULL,
                        homepage_url TEXT NOT NULL,
                        license_id TEXT NOT NULL,
                        license_summary TEXT NOT NULL,
                        commercial_use_allowed INTEGER NOT NULL,
                        video_use_allowed INTEGER NOT NULL,
                        web_embedding_allowed INTEGER NOT NULL,
                        redistribution_allowed INTEGER NOT NULL,
                        languages_json TEXT NOT NULL,
                        tags_json TEXT NOT NULL,
                        recommended_for_json TEXT NOT NULL,
                        preview_text_ko TEXT NOT NULL,
                        preview_text_en TEXT NOT NULL,
                        download_type TEXT NOT NULL,
                        download_url TEXT NOT NULL,
                        format TEXT NOT NULL,
                        variable_font INTEGER NOT NULL
                    )
                    """
                )
                conn.commit()

            service = FontAgentService(root)
            service.repository.init_db()

            with sqlite3.connect(db_path) as conn:
                columns = {row[1] for row in conn.execute("PRAGMA table_info(fonts)").fetchall()}

            self.assertIn("verification_status", columns)
            self.assertIn("verified_at", columns)
            self.assertIn("installed_file_count", columns)
            self.assertIn("verification_failure_reason", columns)
            self.assertIn("download_source", columns)

    def test_parse_noonnu_listing_and_detail(self) -> None:
        fixtures = Path("/Users/jleavens_macmini/Projects/fontagent/tests/fixtures/noonnu")
        listing = parse_listing_html((fixtures / "listing.html").read_text(encoding="utf-8"))
        self.assertEqual([item.slug for item in listing], ["maru-buri", "suit"])

        detail = parse_detail_html(
            (fixtures / "maru-buri.html").read_text(encoding="utf-8"),
            slug="maru-buri",
            source_page_url="https://noonnu.cc/font_page/maru-buri",
            family_hint="MaruBuri",
        )
        self.assertEqual(detail.family, "MaruBuri")
        self.assertTrue(detail.download_url.endswith(".zip"))
        self.assertIn("상업적", detail.license_summary)

    def test_parse_noonnu_live_style_detail(self) -> None:
        detail = parse_detail_html(
            Path("/Users/jleavens_macmini/Projects/fontagent/examples/noonnu_snapshot/details/1269.html").read_text(
                encoding="utf-8"
            ),
            slug="1269",
            source_page_url="https://noonnu.cc/font_page/1269",
            family_hint="Wanted Sans",
        )
        self.assertEqual(detail.family, "Wanted Sans")
        self.assertEqual(detail.download_url, "https://github.com/wanteddev/wanted-sans")
        self.assertIn("라이선스", detail.license_summary)
        self.assertIn("문서용".lower(), detail.tags)
        self.assertIn("기본 고딕".lower(), detail.tags)
        self.assertEqual(detail.to_font_record()["download_type"], "html_button")

    @mock.patch("fontagent.resolver._probe_download_candidate")
    @mock.patch("fontagent.resolver.fetch_text")
    def test_resolve_download_uses_source_page_preview_asset(self, fetch_text_mock, probe_mock) -> None:
        fetch_text_mock.side_effect = [
            "<html><body>external landing page</body></html>",
            "<style>@font-face{src:url('https://cdn.example.com/fonts/demo.woff2') format('woff2');}</style>",
        ]
        probe_mock.return_value = ("https://cdn.example.com/fonts/demo.woff2", "direct_file")

        result = resolve_download(
            {
                "font_id": "demo",
                "family": "Demo",
                "download_type": "html_button",
                "download_url": "https://example.com/download",
                "source_page_url": "https://noonnu.cc/font_page/demo",
            }
        )

        self.assertEqual(result.status, "resolved")
        self.assertEqual(result.download_type, "direct_file")
        self.assertEqual(result.resolved_url, "https://cdn.example.com/fonts/demo.woff2")
        self.assertEqual(result.download_source, "preview_webfont")
        self.assertTrue(any("웹폰트 미리보기" in note for note in result.notes))

    @mock.patch("fontagent.resolver._probe_download_candidate")
    @mock.patch("fontagent.resolver.fetch_text")
    def test_resolve_download_uses_imported_css_from_source_page(self, fetch_text_mock, probe_mock) -> None:
        fetch_text_mock.side_effect = [
            "<html><body>external landing page</body></html>",
            "<style>@import url('https://cdn.example.com/fonts/demo.css');</style>",
            "@font-face{src:url('https://cdn.example.com/fonts/demo-bold.woff2') format('woff2');}",
        ]
        probe_mock.return_value = ("https://cdn.example.com/fonts/demo-bold.woff2", "direct_file")

        result = resolve_download(
            {
                "font_id": "demo-css",
                "family": "Demo CSS",
                "download_type": "html_button",
                "download_url": "https://example.com/download",
                "source_page_url": "https://noonnu.cc/font_page/demo-css",
            }
        )

        self.assertEqual(result.status, "resolved")
        self.assertEqual(result.download_type, "direct_file")
        self.assertEqual(result.resolved_url, "https://cdn.example.com/fonts/demo-bold.woff2")
        self.assertEqual(result.download_source, "preview_webfont")
        self.assertTrue(any("웹폰트 CSS" in note for note in result.notes))

    @mock.patch("fontagent.resolver._probe_download_candidate")
    @mock.patch("fontagent.resolver.fetch_text")
    def test_resolve_download_prefers_family_matching_asset(self, fetch_text_mock, probe_mock) -> None:
        fetch_text_mock.return_value = """
        <html>
          <body>
            <a href="https://cdn.example.com/fonts/Mona8x12.woff2">old</a>
            <a href="https://cdn.example.com/fonts/Mona12Emoji.woff2">target</a>
          </body>
        </html>
        """
        probe_mock.side_effect = lambda url: (url, "direct_file")

        result = resolve_download(
            {
                "font_id": "demo-match",
                "family": "Mona12Emoji",
                "download_type": "html_button",
                "download_url": "https://example.com/download",
                "source_page_url": "https://noonnu.cc/font_page/demo-match",
            }
        )

        self.assertEqual(result.status, "resolved")
        self.assertEqual(result.resolved_url, "https://cdn.example.com/fonts/Mona12Emoji.woff2")
        self.assertEqual(result.download_source, "canonical")

    def test_import_noonnu_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()

            fixtures = Path("/Users/jleavens_macmini/Projects/fontagent/tests/fixtures/noonnu")
            result = service.import_noonnu(
                listing_html=fixtures / "listing.html",
                detail_dir=fixtures,
            )
            self.assertEqual(result["imported"], 2)
            imported = service.search(query="documentary")
            self.assertTrue(any(item["font_id"] == "maru-buri" for item in imported))

    def test_fetch_noonnu_snapshot_with_mocked_http(self) -> None:
        fixtures = Path("/Users/jleavens_macmini/Projects/fontagent/tests/fixtures/noonnu")
        listing_html = (fixtures / "listing.html").read_text(encoding="utf-8")
        maru_html = (fixtures / "maru-buri.html").read_text(encoding="utf-8")
        suit_html = (fixtures / "suit.html").read_text(encoding="utf-8")

        class FakeResponse:
            def __init__(self, text: str) -> None:
                self.text = text

            def read(self) -> bytes:
                return self.text.encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return None

        def fake_urlopen(request, timeout=30):
            url = request.full_url
            if url == "https://noonnu.cc/":
                return FakeResponse(listing_html)
            if url.endswith("/font_page/maru-buri"):
                return FakeResponse(maru_html)
            if url.endswith("/font_page/suit"):
                return FakeResponse(suit_html)
            raise AssertionError(url)

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("fontagent.http_utils.urllib.request.urlopen", side_effect=fake_urlopen):
                result = fetch_noonnu_snapshot(
                    listing_url="https://noonnu.cc/",
                    output_dir=Path(tmp),
                    limit=2,
                )
            self.assertEqual(result["fetched_details"], 2)
            self.assertTrue((Path(tmp) / "listing.html").exists())
            self.assertTrue((Path(tmp) / "details" / "maru-buri.html").exists())

    def test_resolve_download_and_prepare_browser_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            seed = {
                "fonts": [
                    {
                        "font_id": "html-demo",
                        "family": "HTML Demo",
                        "slug": "html-demo",
                        "source_site": "noonnu",
                        "source_page_url": "https://noonnu.cc/font_page/html-demo",
                        "homepage_url": "https://noonnu.cc/font_page/html-demo",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["title"],
                        "recommended_for": ["title"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "html_button",
                        "download_url": "https://noonnu.cc/font_page/html-demo",
                        "format": "html",
                        "variable_font": False
                    }
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()
            with mock.patch(
                "fontagent.resolver.fetch_text",
                side_effect=RuntimeError("network disabled for fixture"),
            ):
                resolved = service.resolve_download("html-demo")
                task = service.prepare_browser_download_task("html-demo", root / "tasks")
            self.assertEqual(resolved["status"], "browser_required")
            self.assertTrue(Path(task["task_path"]).exists())
            payload = json.loads(Path(task["task_path"]).read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "browser_required")

    def test_browser_task_uses_known_source_hints(self) -> None:
        font = {
            "font_id": "cafe24-pro-up",
            "family": "카페24 PRO UP",
            "source_site": "cafe24_brand",
            "source_page_url": "https://www.cafe24.com/story/use/cafe24pro_font.html",
            "download_type": "html_button",
            "download_url": "https://www.cafe24.com/story/use/cafe24pro_font.html",
            "download_source": "",
        }
        result = ResolutionResult(
            status="browser_required",
            download_type="html_button",
            resolved_url="https://www.cafe24.com/story/use/cafe24pro_font.html",
            download_source="",
            notes=["외부 다운로드 페이지에서 direct/zip 링크를 찾지 못했습니다."],
        )
        with tempfile.TemporaryDirectory() as tmp, mock.patch("fontagent.resolver.resolve_download", return_value=result):
            path = write_browser_download_task(font, Path(tmp))
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["task_type"], "browser_source_discovery")
            self.assertIn("www.cafe24.com", payload["accept_domains"])
            self.assertTrue(any("카페24 PRO UP" in step for step in payload["instructions"]))

    def test_resolve_download_html_button_via_external_page(self) -> None:
        font = {
            "font_id": "html-direct",
            "family": "HTML Direct",
            "source_site": "noonnu",
            "source_page_url": "https://noonnu.cc/font_page/html-direct",
            "download_type": "html_button",
            "download_url": "https://example.com/download",
        }
        external_html = """
        <html>
          <body>
            <a href="/files/font-pack.zip">Download zip</a>
          </body>
        </html>
        """
        with mock.patch("fontagent.resolver.fetch_text", return_value=external_html), mock.patch(
            "fontagent.resolver._probe_download_candidate",
            return_value=("https://example.com/files/font-pack.zip", "zip_file"),
        ):
            resolved = resolve_download(font)

        self.assertEqual(resolved.status, "resolved")
        self.assertEqual(resolved.download_type, "zip_file")
        self.assertEqual(resolved.resolved_url, "https://example.com/files/font-pack.zip")
        self.assertEqual(resolved.download_source, "canonical")

    def test_refresh_download_resolutions_persists_to_db(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            seed = {
                "fonts": [
                    {
                        "font_id": "html-demo",
                        "family": "HTML Demo",
                        "slug": "html-demo",
                        "source_site": "noonnu",
                        "source_page_url": "https://noonnu.cc/font_page/html-demo",
                        "homepage_url": "https://noonnu.cc/font_page/html-demo",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["title"],
                        "recommended_for": ["title"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "html_button",
                        "download_url": "https://example.com/download",
                        "format": "html",
                        "variable_font": False,
                    }
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()

            with mock.patch(
                "fontagent.service.resolve_download",
                return_value=mock.Mock(
                    status="resolved",
                    download_type="zip_file",
                    resolved_url="https://example.com/files/font-pack.zip",
                    download_source="canonical",
                    notes=["ok"],
                ),
            ):
                result = service.refresh_download_resolutions(source_site="noonnu")

            self.assertEqual(result["resolved"], 1)
            stored = service.repository.get_font("html-demo")
            self.assertIsNotNone(stored)
            self.assertEqual(stored.download_type, "zip_file")
            self.assertEqual(stored.download_url, "https://example.com/files/font-pack.zip")
            self.assertEqual(stored.download_source, "canonical")
            self.assertEqual(stored.format, "zip")

    def test_parse_duckduckgo_results_filters_noonnu_and_normalizes_url(self) -> None:
        html = """
        <div class="result results_links results_links_deep web-result ">
          <div class="links_main links_deep result__body">
            <h2 class="result__title">
              <a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fhangeul.naver.com%2Ffont%3Futm_source%3Dtest">네이버 글꼴 모음 - Naver</a>
            </h2>
            <div class="result__extras">
              <div class="result__extras__url">
                <a class="result__url" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fhangeul.naver.com%2Ffont%3Futm_source%3Dtest">hangeul.naver.com/font</a>
              </div>
            </div>
            <a class="result__snippet">모든 글꼴은 다운로드 혹은 웹폰트 URL을 통해 자유롭게 사용할 수 있습니다.</a>
          </div>
        </div>
        <div class="result results_links results_links_deep web-result ">
          <div class="links_main links_deep result__body">
            <h2 class="result__title">
              <a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fnoonnu.cc%2Ffont_page%2F123">눈누</a>
            </h2>
            <div class="result__extras">
              <div class="result__extras__url">
                <a class="result__url" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fnoonnu.cc%2Ffont_page%2F123">noonnu.cc/font_page/123</a>
              </div>
            </div>
            <a class="result__snippet">무료 폰트 다운로드</a>
          </div>
        </div>
        """
        results = parse_duckduckgo_results(
            html,
            query="무료 한글 폰트 공식 다운로드",
            blocked_domains={"noonnu.cc"},
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["domain"], "hangeul.naver.com")
        self.assertEqual(results[0]["normalized_url"], "https://hangeul.naver.com/font")
        self.assertEqual(results[0]["status"], "official_candidate")

    def test_get_discovery_queries_display_set(self) -> None:
        queries = get_discovery_queries("display-ko")
        self.assertGreaterEqual(len(queries), 5)
        self.assertIn("무료 한글 제목용 폰트 공식 다운로드", queries)

    def test_parse_naver_fonts_html(self) -> None:
        html = """
        <li class="nanum-gothic">
          <strong class="font-name">나눔고딕</strong>
          <a class="detail_btn" data-category="nanum" data-type="고딕(민부리)"></a>
          <button type="button" class="btn-download" data-url="https://hangeul.naver.com/hangeul_static/webfont/zips/nanum-gothic.zip"
                  data-font-id="nanum-gothic"></button>
        </li>
        <li class="NanumGaRamYeonGgoc">
          <strong class="font-name">나눔손글씨 가람연꽃</strong>
          <a class="detail_btn" data-category="clova" data-type="손글씨"></a>
          <button type="button" class="btn-download" data-url="https://hangeul.naver.com/hangeul_static/webfont/clova/NanumGaRamYeonGgoc.ttf"
                  data-font-id="NanumGaRamYeonGgoc"></button>
        </li>
        """
        records = parse_naver_fonts_html(html)

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["font_id"], "naver-nanum-gothic")
        self.assertEqual(records[0]["download_type"], "zip_file")
        self.assertEqual(records[0]["download_source"], "canonical")
        self.assertEqual(records[1]["download_type"], "direct_file")
        self.assertEqual(records[1]["source_site"], "naver_hangeul")

    def test_parse_hancom_fonts_html(self) -> None:
        html = """
        <li>
          <div class="txt1">
            <img src="../img/main_hun.png" alt="">
            <div class="link_url">
              <a href="../fonts/HancomHoonminjeongeumV.zip">서체 다운로드</a>
            </div>
          </div>
        </li>
        <li>
        <div class="box1">한컴 산스체</div>
        <div class="link_url">
          <a href="../fonts/Hancom Sans.zip">서체 다운로드</a>
        </div>
        </li>
        <li>
        <div class="box1">한컴 말랑말랑체</div>
        <div class="link_url">
          <a href="../fonts/Hancom MalangMalang.zip">서체 다운로드</a>
        </div>
        </li>
        """
        records = parse_hancom_fonts_html(html)

        self.assertEqual(len(records), 3)
        self.assertEqual(records[0]["family"], "한컴훈민정음세로쓰기체")
        self.assertEqual(records[0]["source_site"], "hancom")
        self.assertEqual(records[0]["download_type"], "zip_file")
        self.assertTrue(records[0]["download_url"].startswith("https://font.hancom.com/pc/fonts/"))

    def test_parse_fonco_free_font_list_html(self) -> None:
        html = """
        <ul class="result_list_cont">
          <a href="/collection/sub?family_idx=11152">
            <div class="txt_box flex_cont">
              <span class="name">교보 손글씨 2025 이유빈</span>
              <span class="desc kinds">1종 | 교보문고</span>
            </div>
          </a>
          <a href="/collection/sub?family_idx=11152">
            <div class="txt_box flex_cont">
              <span class="name">교보 손글씨 2025 이유빈</span>
              <span class="desc kinds">1종 | 교보문고</span>
            </div>
          </a>
          <a href="/collection/sub?family_idx=11148">
            <div class="txt_box flex_cont">
              <span class="name">A2Z</span>
              <span class="desc kinds">9종 | 오토노머스에이투지</span>
            </div>
          </a>
        </ul>
        """

        records = parse_fonco_free_font_list_html(html)

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["family_idx"], "11152")
        self.assertEqual(records[0]["company"], "교보문고")
        self.assertEqual(records[1]["source_page_url"], "https://font.co.kr/collection/sub?family_idx=11148")

    def test_parse_fonco_detail_html(self) -> None:
        html = """
        <h2 class="sub_com_tit">교보 손글씨 2025 이유빈<a id="share"></a></h2>
        <p class="tit_desc flex_cont"><span>1종 글꼴</span><span>교보문고</span><span>모든 라이선스</span></p>
        <ul class="heshtag flex_cont">
          <li>#손글씨폰트</li>
          <li>#무료폰트</li>
        </ul>
        <p class="desc">테스트 상세 설명입니다.</p>
        <style>
          @font-face{
            font-family:"web111520";
            src: url("https://cdn.font.co.kr/fonco/static/fonts/OTE2_KyoboHandwriting2025lyb.woff") format("woff") ;
          }
        </style>
        <option value="OTE2_KyoboHandwriting2025lyb.woff" selected>Regular</option>
        """

        record = parse_fonco_detail_html(
            html,
            family_idx="11152",
            source_page_url="https://font.co.kr/collection/sub?family_idx=11152",
            family_hint="교보 손글씨 2025 이유빈",
            company_hint="교보문고",
            style_count_hint="1종",
        )

        self.assertEqual(record["font_id"], "fonco-11152")
        self.assertEqual(record["download_type"], "direct_file")
        self.assertEqual(record["download_source"], "preview_webfont")
        self.assertIn("모든 라이선스", record["license_summary"])
        self.assertTrue(record["commercial_use_allowed"])
        self.assertFalse(record["web_embedding_allowed"])

    def test_parse_gongu_list_html(self) -> None:
        html = """
        <li>
          <div class="font_box">
            <div class="font_area1">
              <span class="tit">학교안심 포스터 B</span>
              <p class="font_source">한국교육학술정보원</p>
              <div class="btnArea">
                <a href="https://gongu.copyright.or.kr/gongu/wrt/wrt/view.do?wrtSn=13383120&menuNo=200195" class="fontLink">바로가기</a>
              </div>
            </div>
            <div class="txt_link">
              OFL (Open Font License)<br/>상업적이용 및 변경 가능
            </div>
          </div>
        </li>
        <div class='paginationSet'><a href='/gongu/bbs/B0000018/list.do?menuNo=200195&pageIndex=5'>5</a></div>
        """

        records, max_page = parse_gongu_list_html(html)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["wrt_sn"], "13383120")
        self.assertEqual(records[0]["source"], "한국교육학술정보원")
        self.assertIn("OFL", records[0]["license_text"])
        self.assertEqual(max_page, 5)

    def test_parse_gongu_download_popup_html(self) -> None:
        html = """
        <script>
        //DEXT5UPLOAD.AddUploadedFile("1", "학교안심 포스터 B.png", '/gongu/wrt/cmmn/wrtFileDownload.do?wrtSn=13383120&fileSn=1', '6240', '', G_UploadID) ;
        //DEXT5UPLOAD.AddUploadedFile("2", "학교안심 포스터 B.zip", '/gongu/wrt/cmmn/wrtFileDownload.do?wrtSn=13383120&fileSn=2', '2402186', '', G_UploadID) ;
        </script>
        """

        record = parse_gongu_download_popup_html(
            html,
            wrt_sn="13383120",
            family="학교안심 포스터 B",
            source_page_url="https://gongu.copyright.or.kr/gongu/wrt/wrt/view.do?wrtSn=13383120&menuNo=200195",
            homepage_url="https://gongu.copyright.or.kr/gongu/bbs/B0000018/list.do?menuNo=200195",
            source="한국교육학술정보원",
            license_text="OFL (Open Font License) 상업적이용 및 변경 가능",
        )

        self.assertEqual(record["font_id"], "gongu-13383120")
        self.assertEqual(record["download_type"], "zip_file")
        self.assertEqual(record["download_source"], "canonical")
        self.assertTrue(record["download_url"].endswith("fileSn=2"))
        self.assertEqual(record["license_id"], "ofl")
        self.assertTrue(record["commercial_use_allowed"])

    def test_discover_web_candidates_stores_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()

            discovered = [
                {
                    "query": "무료 한글 폰트 공식 다운로드",
                    "title": "네이버 글꼴 모음 - Naver",
                    "snippet": "다운로드 혹은 웹폰트 URL로 자유롭게 사용할 수 있습니다.",
                    "result_url": "https://hangeul.naver.com/font",
                    "normalized_url": "https://hangeul.naver.com/font",
                    "domain": "hangeul.naver.com",
                    "discovery_source": "duckduckgo",
                    "status": "official_candidate",
                    "discovered_at": "2026-04-03T00:00:00Z",
                    "note": "공식 또는 준공식 배포처로 보이는 도메인입니다.",
                }
            ]

            with mock.patch("fontagent.service.discover_web_candidates", return_value=discovered):
                result = service.discover_web_candidates(
                    queries=["무료 한글 폰트 공식 다운로드"],
                    limit_per_query=5,
                )

            self.assertEqual(result["discovered"], 1)
            listed = service.list_candidates()
            self.assertEqual(listed["count"], 1)
            self.assertEqual(listed["results"][0]["domain"], "hangeul.naver.com")
            self.assertEqual(listed["results"][0]["status"], "official_candidate")

    def test_seed_curated_candidates_stores_design_display_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()

            result = service.seed_curated_candidates("design-display-ko")
            listed = service.list_candidates(discovery_source="manual_curated")

            self.assertEqual(result["stored"], len(CURATED_CANDIDATE_SETS["design-display-ko"]))
            self.assertEqual(listed["count"], len(CURATED_CANDIDATE_SETS["design-display-ko"]))
            self.assertTrue(any(item["domain"] == "www.woowahan.com" for item in listed["results"]))
            self.assertTrue(all(item["status"] == "official_candidate" for item in listed["results"]))

    def test_classify_candidate_status_recognizes_new_brand_domains(self) -> None:
        for domain in [
            "gds.gmarket.co.kr",
            "www.goodchoice.kr",
            "brand.nexon.com",
            "www.jeju.go.kr",
        ]:
            status, _ = classify_candidate_status(domain)
            self.assertEqual(status, "official_candidate")

    def test_parse_goodchoice_jalnan_css(self) -> None:
        css = """
        @font-face {
            font-family: 'yg-jalnan';
            src: url('./yg-jalnan.eot');
            src: url('./yg-jalnan.eot?#iefix') format('embedded-opentype'),
            url('./yg-jalnan.woff') format('woff'),
            url('./yg-jalnan.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }
        """

        records = parse_goodchoice_jalnan_css(
            css,
            css_url="https://static.goodchoice.kr/fonts/jalnan/font.css",
            source_page_url="https://www.goodchoice.kr/font/mobile",
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["font_id"], "goodchoice-yg-jalnan")
        self.assertEqual(records[0]["family"], "여기어때잘난체")
        self.assertEqual(records[0]["download_type"], "direct_file")
        self.assertEqual(
            records[0]["download_url"],
            "https://static.goodchoice.kr/fonts/jalnan/yg-jalnan.ttf",
        )

    def test_parse_gmarket_design_system_html(self) -> None:
        html = """
        <div class="ResourceCardGroup_root__pFHtE">
          <a class="ResourceCardGroup_item__xwyvw ResourceCard_resource__mLS6s" href="./file/GmarketSans.zip">
            <strong class="ResourceCard_title__8esFt">G마켓 산스 폰트</strong>
          </a>
          <a class="ResourceCardGroup_item__xwyvw ResourceCard_resource__mLS6s" href="./file/System_Font.zip">
            <strong class="ResourceCard_title__8esFt">시스템 폰트</strong>
          </a>
        </div>
        """

        records = parse_gmarket_design_system_html(
            html,
            source_page_url="https://gds.gmarket.co.kr/",
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["font_id"], "gmarket-sans")
        self.assertEqual(records[0]["family"], "G마켓 산스")
        self.assertEqual(records[0]["download_type"], "zip_file")
        self.assertEqual(records[0]["download_url"], "https://gds.gmarket.co.kr/file/GmarketSans.zip")

    def test_fetch_google_display_fonts_returns_curated_english_fonts(self) -> None:
        records = fetch_google_display_fonts()

        self.assertGreaterEqual(len(records), 14)
        self.assertTrue(any(item["font_id"] == "google-anton" for item in records))
        self.assertTrue(any(item["font_id"] == "google-fraunces" for item in records))
        self.assertTrue(all(item["source_site"] == "google_display" for item in records))
        self.assertTrue(all(item["languages"] == ["en"] for item in records))
        self.assertTrue(all(item["download_type"] == "direct_file" for item in records))

    def test_parse_cafe24_catalog_selects_design_fonts(self) -> None:
        payload = {
            "fonts": [
                {
                    "id": "cafe24-pro-up",
                    "nameKr": "카페24 PRO UP",
                    "nameEn": "Cafe24 PRO UP",
                    "tags": ["프로", "비즈니스", "모던"],
                    "downloadUrl": "//img.cafe24.com/csdstatic/freefonts/download/kr/Cafe24PROUP_v0.2.zip",
                },
                {
                    "id": "cafe24-unknown",
                    "nameKr": "카페24 기본체",
                    "nameEn": "Cafe24 Basic",
                    "tags": ["기본"],
                    "downloadUrl": "//img.cafe24.com/csdstatic/freefonts/download/kr/Cafe24Basic.zip",
                },
            ]
        }

        records = parse_cafe24_catalog(payload)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["font_id"], "cafe24-pro-up")

    @mock.patch("fontagent.official_sources.fetch_text")
    def test_fetch_fontshare_fonts_uses_api_kit_zip_download(self, fetch_text_mock) -> None:
        fetch_text_mock.return_value = json.dumps(
            {
                "fonts": [
                    {
                        "slug": "satoshi",
                        "category": "Sans",
                        "license_type": "itf_ffl",
                        "font_tags": [{"name": "Branding"}],
                        "styles": [
                            {
                                "file": "//cdn.fontshare.com/demo/regular.woff2",
                                "is_variable": False,
                                "is_italic": False,
                                "weight": {"number": 400, "weight": 400},
                            },
                            {
                                "file": "//cdn.fontshare.com/demo/variable.woff2",
                                "is_variable": True,
                                "is_italic": False,
                                "weight": {"number": 400, "weight": 400},
                            },
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        )

        records = fetch_fontshare_fonts()

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["font_id"], "fontshare-satoshi")
        self.assertEqual(records[0]["download_type"], "zip_file")
        self.assertEqual(records[0]["download_source"], "canonical")
        self.assertEqual(records[0]["format"], "zip")
        self.assertEqual(
            records[0]["download_url"],
            "https://api.fontshare.com/v2/fonts/download/kit?f[]=satoshi@400",
        )

    def test_parse_jeju_font_info_html_extracts_manual_zip_links(self) -> None:
        html = """
        <a class="btn btn-primary" href="/download.htm?act=download&amp;seq=60060&amp;no=10">수동설치버전</a>
        <a class="btn btn-info" href="/download.htm?act=download&amp;seq=60060&amp;no=11">수동설치버전</a>
        """

        records = parse_jeju_font_info_html(html)

        self.assertEqual(len(records), 3)
        self.assertTrue(all(item["source_site"] == "jeju_official" for item in records))
        self.assertTrue(all(item["download_type"] == "zip_file" for item in records))
        self.assertTrue(
            all(
                item["download_url"] == "https://www.jeju.go.kr/download.htm?act=download&seq=60060&no=10"
                for item in records
            )
        )

    def test_parse_league_font_page_extracts_github_zip(self) -> None:
        html = """
        <a href="https://github.com/theleagueof/league-gothic/releases/download/1.601/LeagueGothic-1.601.zip">Download</a>
        """

        record = parse_league_font_page(
            html,
            font_id="league-league-gothic",
            family="League Gothic",
            slug="league-gothic",
            source_page_url="https://www.theleagueofmoveabletype.com/league-gothic",
            tags=["english", "display", "poster"],
            recommended_for=["title", "poster"],
            preview_text_en="LEAGUE GOTHIC FOR TIGHT HEADLINES",
        )

        self.assertEqual(record["download_type"], "zip_file")
        self.assertEqual(
            record["download_url"],
            "https://github.com/theleagueof/league-gothic/releases/download/1.601/LeagueGothic-1.601.zip",
        )
        self.assertEqual(record["source_site"], "league_movable_type")

    def test_preview_preset_for_english_use_case(self) -> None:
        title_request = UseCaseRequest.from_payload(
            medium="web",
            surface="landing_hero",
            role="title",
            languages=["en"],
        )
        subtitle_request = UseCaseRequest.from_payload(
            medium="video",
            surface="subtitle_track",
            role="subtitle",
            languages=["en"],
        )
        body_request = UseCaseRequest.from_payload(
            medium="document",
            surface="body_copy",
            role="body",
            languages=["en"],
        )

        self.assertEqual(preview_preset_for_use_case(title_request), "title-en")
        self.assertEqual(preview_preset_for_use_case(subtitle_request), "subtitle-en")
        self.assertEqual(preview_preset_for_use_case(body_request), "body-en")

    def test_parse_nexon_brand_bundle(self) -> None:
        html = """
        <html>
          <head><script src="/assets/index-demo.js"></script></head>
        </html>
        """
        bundle = """
        "/resources/NEXON_Lv1_Gothic.zip"
        "/resources/NEXON_Maplestory.zip"
        "/resources/NEXON_CI_Vertical_RGB.zip"
        """

        records = parse_nexon_brand_bundle(
            html,
            bundle,
            source_page_url="https://brand.nexon.com/brand/fonts",
        )

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["font_id"], "nexon-nexon-lv1-gothic")
        self.assertEqual(records[1]["font_id"], "nexon-nexon-maplestory")
        self.assertEqual(
            records[0]["download_url"],
            "https://brand.nexon.com/resources/NEXON_Lv1_Gothic.zip",
        )

    def test_parse_woowahan_font_bundle(self) -> None:
        bundle = """
        https://woowahan-cdn.woowahan.com/static/fonts/BMGEULLIM.zip
        https://woowahan-cdn.woowahan.com/static/fonts/BMDOHYEON_ttf.ttf
        https://woowahan-cdn.woowahan.com/static/fonts/BMDOHYEON_otf.otf
        https://woowahan-cdn.woowahan.com/static/fonts/BMYEONSUNG_ttf.ttf
        """

        records = parse_woowahan_font_bundle(
            bundle,
            source_page_url="https://www.woowahan.com/fonts",
        )

        by_id = {item["font_id"]: item for item in records}
        self.assertIn("woowahan-bmdohyeon", by_id)
        self.assertIn("woowahan-bmgeullim", by_id)
        self.assertEqual(by_id["woowahan-bmdohyeon"]["download_url"], "https://woowahan-cdn.woowahan.com/static/fonts/BMDOHYEON_ttf.ttf")
        self.assertEqual(by_id["woowahan-bmgeullim"]["download_type"], "zip_file")

    def test_normalize_candidate_statuses_reclassifies_existing_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()
            service.repository.upsert_candidates(
                [
                    {
                        "query": "무료 한글 폰트 공식 다운로드",
                        "title": "Naver Font",
                        "snippet": "다운로드 가능",
                        "result_url": "https://hangeul.naver.com/font",
                        "normalized_url": "https://hangeul.naver.com/font",
                        "domain": "hangeul.naver.com",
                        "discovery_source": "duckduckgo",
                        "status": "discovered",
                        "discovered_at": "2026-04-03T00:00:00Z",
                        "note": "",
                    },
                    {
                        "query": "무료 한글 폰트 공식 다운로드",
                        "title": "Blog Post",
                        "snippet": "폰트 추천",
                        "result_url": "https://example.com/post",
                        "normalized_url": "https://example.com/post",
                        "domain": "example.com",
                        "discovery_source": "duckduckgo",
                        "status": "discovered",
                        "discovered_at": "2026-04-03T00:00:00Z",
                        "note": "",
                    },
                ]
            )

            result = service.normalize_candidate_statuses()
            listed = {item["domain"]: item for item in service.list_candidates()["results"]}

            self.assertEqual(result["updated"], 2)
            self.assertEqual(listed["hangeul.naver.com"]["status"], "official_candidate")
            self.assertEqual(listed["example.com"]["status"], "needs_review")

    def test_import_official_sources_marks_candidates_imported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()
            service.repository.upsert_candidates(
                [
                    {
                        "query": "무료 한글 폰트 공식 다운로드",
                        "title": "네이버 글꼴 모음 - Naver",
                        "snippet": "공식",
                        "result_url": "https://hangeul.naver.com/font",
                        "normalized_url": "https://hangeul.naver.com/font",
                        "domain": "hangeul.naver.com",
                        "discovery_source": "duckduckgo",
                        "status": "official_candidate",
                        "discovered_at": "2026-04-03T00:00:00Z",
                        "note": "",
                    },
                    {
                        "query": "무료 한글 폰트 공식 다운로드",
                        "title": "한글과컴퓨터 - Hancom",
                        "snippet": "공식",
                        "result_url": "https://font.hancom.com/pc/main/main.php",
                        "normalized_url": "https://font.hancom.com/pc/main/main.php",
                        "domain": "font.hancom.com",
                        "discovery_source": "duckduckgo",
                        "status": "official_candidate",
                        "discovered_at": "2026-04-03T00:00:00Z",
                        "note": "",
                    },
                    {
                        "query": "무료 한글 폰트 공식 다운로드",
                        "title": "무료폰트 | FONCO",
                        "snippet": "공식",
                        "result_url": "https://font.co.kr/collection/freeFont",
                        "normalized_url": "https://font.co.kr/collection/freeFont",
                        "domain": "font.co.kr",
                        "discovery_source": "duckduckgo",
                        "status": "official_candidate",
                        "discovered_at": "2026-04-03T00:00:00Z",
                        "note": "",
                    },
                    {
                        "query": "무료 한글 폰트 공식 다운로드",
                        "title": "공유마당 안심글꼴",
                        "snippet": "공식",
                        "result_url": "https://gongu.copyright.or.kr/gongu/bbs/B0000018/list.do?menuNo=200195",
                        "normalized_url": "https://gongu.copyright.or.kr/gongu/bbs/B0000018/list.do?menuNo=200195",
                        "domain": "gongu.copyright.or.kr",
                        "discovery_source": "duckduckgo",
                        "status": "official_candidate",
                        "discovered_at": "2026-04-03T00:00:00Z",
                        "note": "",
                    },
                ]
            )

            with mock.patch(
                "fontagent.service.fetch_naver_fonts",
                return_value=[
                    {
                        "font_id": "naver-demo",
                        "family": "네이버 데모",
                        "slug": "naver-demo",
                        "source_site": "naver_hangeul",
                        "source_page_url": "https://hangeul.naver.com/font/nanum",
                        "homepage_url": "https://hangeul.naver.com/font",
                        "license_id": "naver-font-commercial",
                        "license_summary": "상업적 사용 허용",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["naver"],
                        "recommended_for": ["body"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "zip_file",
                        "download_url": "https://example.com/naver-demo.zip",
                        "download_source": "canonical",
                        "format": "zip",
                        "variable_font": False,
                    }
                ],
            ), mock.patch(
                "fontagent.service.fetch_hancom_fonts",
                return_value=[
                    {
                        "font_id": "hancom-demo",
                        "family": "한컴 데모",
                        "slug": "hancom-demo",
                        "source_site": "hancom",
                        "source_page_url": "https://font.hancom.com/pc/main/main.php",
                        "homepage_url": "https://font.hancom.com/",
                        "license_id": "hancom-free-font",
                        "license_summary": "무료 폰트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["hancom"],
                        "recommended_for": ["body"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "zip_file",
                        "download_url": "https://example.com/hancom-demo.zip",
                        "download_source": "canonical",
                        "format": "zip",
                        "variable_font": False,
                    }
                ],
            ), mock.patch(
                "fontagent.service.fetch_fonco_free_fonts",
                return_value=[
                    {
                        "font_id": "fonco-demo",
                        "family": "폰코 데모",
                        "slug": "11152",
                        "source_site": "fonco_freefont",
                        "source_page_url": "https://font.co.kr/collection/sub?family_idx=11152",
                        "homepage_url": "https://font.co.kr/collection/freeFont",
                        "license_id": "fonco-all-license",
                        "license_summary": "FONCO 무료폰트 상세 페이지 기준 라이선스: 모든 라이선스",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": False,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["fonco", "freefont"],
                        "recommended_for": ["body"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "direct_file",
                        "download_url": "https://cdn.font.co.kr/fonco/static/fonts/demo.woff",
                        "download_source": "preview_webfont",
                        "format": "woff",
                        "variable_font": False,
                    }
                ],
            ), mock.patch(
                "fontagent.service.fetch_gongu_fonts",
                return_value=[
                    {
                        "font_id": "gongu-demo",
                        "family": "공유마당 데모",
                        "slug": "13383120",
                        "source_site": "gongu_freefont",
                        "source_page_url": "https://gongu.copyright.or.kr/gongu/wrt/wrt/view.do?wrtSn=13383120&menuNo=200195",
                        "homepage_url": "https://gongu.copyright.or.kr/gongu/bbs/B0000018/list.do?menuNo=200195",
                        "license_id": "ofl",
                        "license_summary": "공유마당 목록 기준 라이선스: OFL",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": True,
                        "languages": ["ko"],
                        "tags": ["gongu", "freefont"],
                        "recommended_for": ["body"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "zip_file",
                        "download_url": "https://gongu.copyright.or.kr/gongu/wrt/cmmn/wrtFileDownload.do?wrtSn=13383120&fileSn=2",
                        "download_source": "canonical",
                        "format": "zip",
                        "variable_font": False,
                    }
                ],
            ):
                service.import_naver_fonts()
                service.import_hancom_fonts()
                service.import_fonco_fonts(limit=1)
                service.import_gongu_fonts(max_pages=1)

            candidates = {item["domain"]: item for item in service.list_candidates()["results"]}
            self.assertEqual(candidates["hangeul.naver.com"]["status"], "imported")
            self.assertEqual(candidates["font.hancom.com"]["status"], "imported")
            self.assertEqual(candidates["font.co.kr"]["status"], "imported")
            self.assertEqual(candidates["gongu.copyright.or.kr"]["status"], "imported")

    def test_import_goodchoice_fonts_marks_candidate_imported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()
            service.repository.upsert_candidates(
                [
                    {
                        "query": "manual curated design display sources",
                        "title": "여기어때잘난체",
                        "snippet": "공식",
                        "result_url": "https://www.goodchoice.kr/font/mobile",
                        "normalized_url": "https://www.goodchoice.kr/font/mobile",
                        "domain": "www.goodchoice.kr",
                        "discovery_source": "manual_curated",
                        "status": "official_candidate",
                        "discovered_at": "2026-04-03T00:00:00Z",
                        "note": "",
                    }
                ]
            )

            with mock.patch(
                "fontagent.service.fetch_goodchoice_fonts",
                return_value=[
                    {
                        "font_id": "goodchoice-yg-jalnan",
                        "family": "여기어때잘난체",
                        "slug": "yg-jalnan",
                        "source_site": "goodchoice_brand",
                        "source_page_url": "https://www.goodchoice.kr/font/mobile",
                        "homepage_url": "https://www.goodchoice.kr/font/mobile",
                        "license_id": "goodchoice-brand-font",
                        "license_summary": "여기어때 공식 서체 페이지에서 제공하는 무료 브랜드 폰트입니다.",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["brand", "display", "title"],
                        "recommended_for": ["title", "thumbnail"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "direct_file",
                        "download_url": "https://static.goodchoice.kr/fonts/jalnan/yg-jalnan.ttf",
                        "download_source": "canonical",
                        "format": "ttf",
                        "variable_font": False,
                    }
                ],
            ):
                service.import_goodchoice_fonts()

            candidates = {item["domain"]: item for item in service.list_candidates()["results"]}
            self.assertEqual(candidates["www.goodchoice.kr"]["status"], "imported")

    def test_import_gmarket_fonts_marks_candidate_imported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()
            service.repository.upsert_candidates(
                [
                    {
                        "query": "manual curated design display sources",
                        "title": "Gmarket Design System",
                        "snippet": "공식",
                        "result_url": "https://gds.gmarket.co.kr/",
                        "normalized_url": "https://gds.gmarket.co.kr/",
                        "domain": "gds.gmarket.co.kr",
                        "discovery_source": "manual_curated",
                        "status": "official_candidate",
                        "discovered_at": "2026-04-03T00:00:00Z",
                        "note": "",
                    }
                ]
            )

            with mock.patch(
                "fontagent.service.fetch_gmarket_fonts",
                return_value=[
                    {
                        "font_id": "gmarket-sans",
                        "family": "G마켓 산스",
                        "slug": "gmarket-sans",
                        "source_site": "gmarket_brand",
                        "source_page_url": "https://gds.gmarket.co.kr/",
                        "homepage_url": "https://gds.gmarket.co.kr/",
                        "license_id": "gmarket-brand-font",
                        "license_summary": "Gmarket Design System에서 제공하는 무료 브랜드 폰트입니다.",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": False,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["brand", "display", "title"],
                        "recommended_for": ["title", "thumbnail"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "zip_file",
                        "download_url": "https://gds.gmarket.co.kr/file/GmarketSans.zip",
                        "download_source": "canonical",
                        "format": "zip",
                        "variable_font": False,
                    }
                ],
            ):
                service.import_gmarket_fonts()

            candidates = {item["domain"]: item for item in service.list_candidates()["results"]}
            self.assertEqual(candidates["gds.gmarket.co.kr"]["status"], "imported")

    def test_import_nexon_fonts_marks_candidate_imported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()
            service.repository.upsert_candidates(
                [
                    {
                        "query": "manual curated design display sources",
                        "title": "Nexon Font",
                        "snippet": "공식",
                        "result_url": "https://brand.nexon.com/brand/fonts",
                        "normalized_url": "https://brand.nexon.com/brand/fonts",
                        "domain": "brand.nexon.com",
                        "discovery_source": "manual_curated",
                        "status": "official_candidate",
                        "discovered_at": "2026-04-03T00:00:00Z",
                        "note": "",
                    }
                ]
            )

            with mock.patch(
                "fontagent.service.fetch_nexon_fonts",
                return_value=[
                    {
                        "font_id": "nexon-nexon-maplestory",
                        "family": "메이플스토리",
                        "slug": "nexon-maplestory",
                        "source_site": "nexon_brand",
                        "source_page_url": "https://brand.nexon.com/brand/fonts",
                        "homepage_url": "https://brand.nexon.com/brand/fonts",
                        "license_id": "nexon-brand-font",
                        "license_summary": "Nexon 브랜드 폰트 페이지에서 제공하는 무료 게임/브랜드 서체입니다.",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": False,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["brand", "display", "title", "game"],
                        "recommended_for": ["title", "thumbnail"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "zip_file",
                        "download_url": "https://brand.nexon.com/resources/NEXON_Maplestory.zip",
                        "download_source": "canonical",
                        "format": "zip",
                        "variable_font": False,
                    }
                ],
            ):
                service.import_nexon_fonts()

            candidates = {item["domain"]: item for item in service.list_candidates()["results"]}
            self.assertEqual(candidates["brand.nexon.com"]["status"], "imported")

    def test_import_woowahan_fonts_marks_candidate_imported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()
            service.repository.upsert_candidates(
                [
                    {
                        "query": "manual curated design display sources",
                        "title": "배달의민족 글꼴",
                        "snippet": "공식",
                        "result_url": "https://www.woowahan.com/fonts",
                        "normalized_url": "https://www.woowahan.com/fonts",
                        "domain": "www.woowahan.com",
                        "discovery_source": "manual_curated",
                        "status": "official_candidate",
                        "discovered_at": "2026-04-03T00:00:00Z",
                        "note": "",
                    }
                ]
            )

            with mock.patch(
                "fontagent.service.fetch_woowahan_fonts",
                return_value=[
                    {
                        "font_id": "woowahan-bmdohyeon",
                        "family": "배민 도현체",
                        "slug": "bmdohyeon",
                        "source_site": "woowahan_brand",
                        "source_page_url": "https://www.woowahan.com/fonts",
                        "homepage_url": "https://www.woowahan.com/fonts",
                        "license_id": "woowahan-brand-font",
                        "license_summary": "우아한형제들 공식 폰트 페이지에서 제공하는 무료 브랜드 폰트입니다.",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["brand", "display", "title", "woowahan"],
                        "recommended_for": ["title", "thumbnail"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "direct_file",
                        "download_url": "https://woowahan-cdn.woowahan.com/static/fonts/BMDOHYEON_ttf.ttf",
                        "download_source": "canonical",
                        "format": "ttf",
                        "variable_font": False,
                    }
                ],
            ):
                service.import_woowahan_fonts()

            candidates = {item["domain"]: item for item in service.list_candidates()["results"]}
            self.assertEqual(candidates["www.woowahan.com"]["status"], "imported")

    def test_normalize_download_sources_backfills_existing_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
            seed = {
                "fonts": [
                    {
                        "font_id": "preview-demo",
                        "family": "Preview Demo",
                        "slug": "preview-demo",
                        "source_site": "noonnu",
                        "source_page_url": "https://noonnu.cc/font_page/preview-demo",
                        "homepage_url": "https://noonnu.cc/font_page/preview-demo",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["title"],
                        "recommended_for": ["title"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "direct_file",
                        "download_url": "https://cdn.jsdelivr.net/gh/projectnoonnu/demo@1.0/PreviewDemo.woff2",
                        "format": "woff2",
                        "variable_font": False,
                    },
                    {
                        "font_id": "canonical-demo",
                        "family": "Canonical Demo",
                        "slug": "canonical-demo",
                        "source_site": "noonnu",
                        "source_page_url": "https://noonnu.cc/font_page/canonical-demo",
                        "homepage_url": "https://noonnu.cc/font_page/canonical-demo",
                        "license_id": "fixture",
                        "license_summary": "테스트",
                        "commercial_use_allowed": True,
                        "video_use_allowed": True,
                        "web_embedding_allowed": True,
                        "redistribution_allowed": False,
                        "languages": ["ko"],
                        "tags": ["title"],
                        "recommended_for": ["title"],
                        "preview_text_ko": "테스트",
                        "preview_text_en": "Test",
                        "download_type": "zip_file",
                        "download_url": "https://example.com/files/canonical-demo.zip",
                        "format": "zip",
                        "variable_font": False,
                    },
                ]
            }
            (root / "fontagent" / "seed" / "fonts.json").write_text(
                json.dumps(seed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            service = FontAgentService(root)
            service.init()

            result = service.normalize_download_sources(source_site="noonnu")

            self.assertEqual(result["updated"], 2)
            self.assertEqual(service.repository.get_font("preview-demo").download_source, "preview_webfont")
            self.assertEqual(service.repository.get_font("canonical-demo").download_source, "canonical")

    def test_resolve_download_extracts_json_download_url(self) -> None:
        font = {
            "font_id": "json-direct",
            "family": "JSON Direct",
            "source_site": "noonnu",
            "source_page_url": "https://noonnu.cc/font_page/json-direct",
            "download_type": "html_button",
            "download_url": "https://example.com/download",
        }
        external_html = '{"downloadUrl":"https://cdn.example.com/fonts/demo.ttf"}'
        with mock.patch("fontagent.resolver.fetch_text", return_value=external_html), mock.patch(
            "fontagent.resolver._probe_download_candidate",
            return_value=("https://cdn.example.com/fonts/demo.ttf", "direct_file"),
        ):
            resolved = resolve_download(font)

        self.assertEqual(resolved.status, "resolved")
        self.assertEqual(resolved.download_type, "direct_file")
        self.assertEqual(resolved.resolved_url, "https://cdn.example.com/fonts/demo.ttf")


if __name__ == "__main__":
    unittest.main()
