from __future__ import annotations

import unittest

from fontagent.http_api import INDEX_HTML, paginate_catalog_results, resolve_recommend_use_case_payload


class FontAgentHttpApiTests(unittest.TestCase):
    def test_index_html_emphasizes_compare_and_export_workflow(self) -> None:
        self.assertIn("Typography Decision Board", INDEX_HTML)
        self.assertIn("Compare Candidates", INDEX_HTML)
        self.assertIn("Applicable Font Catalog", INDEX_HTML)
        self.assertIn("Commit / Export", INDEX_HTML)
        self.assertIn("빠른 시작 프리셋", INDEX_HTML)

    def test_resolve_recommend_use_case_payload_uses_preset_defaults_when_use_case_is_provided(self) -> None:
        payload = resolve_recommend_use_case_payload(
            {
                "use_case": "video-subtitle",
                "languages": ["ko"],
                "constraints": {"commercial_use": True},
                "count": 4,
            }
        )

        self.assertEqual(payload["medium"], "video")
        self.assertEqual(payload["surface"], "subtitle_track")
        self.assertEqual(payload["role"], "subtitle")
        self.assertEqual(payload["tones"], ["readable"])
        self.assertEqual(payload["count"], 4)

    def test_paginate_catalog_results_returns_requested_page(self) -> None:
        payload = paginate_catalog_results(
            [{"font_id": f"font-{index}"} for index in range(45)],
            page=2,
            page_size=20,
        )

        self.assertEqual(payload["count"], 45)
        self.assertEqual(payload["page"], 2)
        self.assertEqual(payload["total_pages"], 3)
        self.assertEqual(len(payload["results"]), 20)
        self.assertEqual(payload["results"][0]["font_id"], "font-20")


if __name__ == "__main__":
    unittest.main()
