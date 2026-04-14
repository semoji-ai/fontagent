from __future__ import annotations

import base64
import unittest

from fontagent.models import FontRecord
from fontagent.preview import font_data_uri, render_preview_svg


class FontAgentPreviewTests(unittest.TestCase):
    def test_render_preview_svg_uses_font_family_for_header_and_larger_canvas(self) -> None:
        font = FontRecord(
            font_id="fixture-display",
            family="Fixture Display",
            slug="fixture-display",
            source_site="fixture",
            source_page_url="file://fixture",
            homepage_url="file://fixture",
            license_id="fixture",
            license_summary="무료 사용 가능",
            commercial_use_allowed=True,
            video_use_allowed=True,
            web_embedding_allowed=True,
            redistribution_allowed=False,
            languages=["ko"],
            tags=["display", "title"],
            recommended_for=["title"],
            preview_text_ko="시대의 균열은 제목에서 먼저 드러난다",
            preview_text_en="Preview Copy",
            download_type="manual_only",
            download_url="",
            download_source="",
            format="ttf",
            variable_font=False,
            verification_status="unverified",
            verified_at="",
            installed_file_count=0,
            verification_failure_reason="",
        )

        svg = render_preview_svg(font, preset="title-ko")

        self.assertIn('width="1200" height="680"', svg)
        self.assertIn('font-size="96"', svg)
        self.assertIn("font-family=\"Fixture Display, 'Apple SD Gothic Neo', sans-serif\"", svg)
        self.assertIn("무료 사용 가능", svg)

    def test_render_preview_svg_embeds_font_face_when_asset_src_is_provided(self) -> None:
        font = FontRecord(
            font_id="fixture-display",
            family="Fixture Display",
            slug="fixture-display",
            source_site="fixture",
            source_page_url="file://fixture",
            homepage_url="file://fixture",
            license_id="fixture",
            license_summary="무료 사용 가능",
            commercial_use_allowed=True,
            video_use_allowed=True,
            web_embedding_allowed=True,
            redistribution_allowed=False,
            languages=["ko"],
            tags=["display", "title"],
            recommended_for=["title"],
            preview_text_ko="시대의 균열은 제목에서 먼저 드러난다",
            preview_text_en="Preview Copy",
            download_type="manual_only",
            download_url="",
            download_source="",
            format="ttf",
            variable_font=False,
            verification_status="unverified",
            verified_at="",
            installed_file_count=0,
            verification_failure_reason="",
        )

        svg = render_preview_svg(
            font,
            preset="title-ko",
            font_face_src="/fonts/preview-asset?font_id=fixture-display",
            font_face_format="woff2",
        )

        self.assertIn("@font-face", svg)
        self.assertIn("FontAgentPreviewEmbedded", svg)
        self.assertIn("format('woff2')", svg)

    def test_font_data_uri_encodes_font_file(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            font_path = Path(tmp) / "fixture.woff2"
            font_path.write_bytes(b"fixture-font")

            uri = font_data_uri(str(font_path))

            self.assertTrue(uri.startswith("data:font/woff2;base64,"))
            self.assertIn(base64.b64encode(b"fixture-font").decode("ascii"), uri)


if __name__ == "__main__":
    unittest.main()
