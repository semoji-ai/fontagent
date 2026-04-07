from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fontagent.mcp_server import FontAgentMCPApplication


class FontAgentMCPTests(unittest.TestCase):
    def _make_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        (root / "fontagent" / "seed").mkdir(parents=True, exist_ok=True)
        source = Path("/Users/jleavens_macmini/Projects/fontagent/fontagent/seed/fonts.json")
        (root / "fontagent" / "seed" / "fonts.json").write_text(
            source.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        return root

    def test_initialize_returns_tools_capability(self) -> None:
        app = FontAgentMCPApplication(self._make_root())
        response = app.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"},
                },
            }
        )

        self.assertEqual(response["result"]["protocolVersion"], "2025-06-18")
        self.assertIn("tools", response["result"]["capabilities"])
        self.assertEqual(response["result"]["serverInfo"]["name"], "fontagent")

    def test_tools_list_contains_guided_interview_and_handoff(self) -> None:
        app = FontAgentMCPApplication(self._make_root())
        response = app.handle_message(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        )

        tool_names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertIn("get_catalog_status", tool_names)
        self.assertIn("get_license_policy_catalog", tool_names)
        self.assertIn("get_contract_schema", tool_names)
        self.assertIn("bootstrap_project_integration", tool_names)
        self.assertIn("guided_interview_recommend", tool_names)
        self.assertIn("generate_typography_handoff", tool_names)
        self.assertIn("list_reference_packs", tool_names)
        self.assertIn("add_reference_review", tool_names)
        self.assertIn("list_reference_reviews", tool_names)
        self.assertIn("search_fonts", tool_names)

    def test_get_catalog_status_tool_returns_totals(self) -> None:
        app = FontAgentMCPApplication(self._make_root())
        response = app.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "get_catalog_status",
                    "arguments": {},
                },
            }
        )

        result = response["result"]["structuredContent"]
        self.assertIn("total_fonts", result)
        self.assertIn("installed_fonts", result)
        self.assertIn("sources", result)
        self.assertGreater(result["total_fonts"], 0)

    def test_get_contract_schema_tool_returns_schema(self) -> None:
        app = FontAgentMCPApplication(self._make_root())
        response = app.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "get_contract_schema",
                    "arguments": {"name": "typography-handoff.v1"},
                },
            }
        )

        result = response["result"]["structuredContent"]
        self.assertEqual(result["name"], "typography-handoff.v1")
        self.assertEqual(result["schema"]["title"], "FontAgent Typography Handoff v1")

    def test_get_license_policy_catalog_tool_returns_sources(self) -> None:
        app = FontAgentMCPApplication(self._make_root())
        response = app.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/call",
                "params": {
                    "name": "get_license_policy_catalog",
                    "arguments": {},
                },
            }
        )

        result = response["result"]["structuredContent"]
        self.assertIn("sources", result)
        self.assertIn("google_fonts", result["sources"])

    def test_bootstrap_project_integration_tool_writes_files(self) -> None:
        app = FontAgentMCPApplication(self._make_root())
        with tempfile.TemporaryDirectory() as tmp:
            response = app.handle_message(
                {
                    "jsonrpc": "2.0",
                    "id": 6,
                    "method": "tools/call",
                    "params": {
                        "name": "bootstrap_project_integration",
                        "arguments": {
                            "project_path": str(Path(tmp) / "demo-project"),
                            "use_case": "youtube-thumbnail-ko",
                            "language": "ko"
                        },
                    },
                }
            )

            result = response["result"]["structuredContent"]
            self.assertTrue(Path(result["config_path"]).exists())
            self.assertTrue(Path(result["prompt_path"]).exists())

    def test_tools_call_returns_structured_content(self) -> None:
        app = FontAgentMCPApplication(self._make_root())
        response = app.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "guided_interview_recommend",
                    "arguments": {
                        "category": "video",
                        "subcategory": "thumbnail",
                        "answers": {
                            "tone": "retro",
                            "density": "balanced",
                            "language_mix": "ko",
                            "license_mode": "monetized",
                        },
                        "language": "ko",
                        "count": 3,
                        "include_canvas": True,
                        "include_font_system_preview": True,
                    },
                },
            }
        )

        result = response["result"]["structuredContent"]
        self.assertEqual(result["category"], "video")
        self.assertEqual(result["subcategory"], "thumbnail")
        self.assertEqual(result["canvas"]["layout_mode"], "left-stack")
        self.assertIn("title", result["font_system_preview"]["roles"])
        self.assertTrue(result["results"])
        self.assertNotIn("download_url", result["results"][0])
        self.assertIsInstance(json.loads(response["result"]["content"][0]["text"]), dict)

    def test_guided_interview_mcp_defaults_omit_canvas_and_preview(self) -> None:
        app = FontAgentMCPApplication(self._make_root())
        response = app.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {
                    "name": "guided_interview_recommend",
                    "arguments": {
                        "category": "video",
                        "subcategory": "thumbnail",
                        "answers": {
                            "tone": "retro",
                            "density": "balanced",
                            "language_mix": "ko",
                            "license_mode": "monetized"
                        },
                        "language": "ko",
                        "count": 2
                    },
                },
            }
        )

        result = response["result"]["structuredContent"]
        self.assertNotIn("canvas", result)
        self.assertNotIn("font_system_preview", result)
        self.assertTrue(result["results"])

    def test_add_reference_review_tool_stores_review(self) -> None:
        app = FontAgentMCPApplication(self._make_root())
        created = app.service.add_reference(
            title="MCP Review Target",
            medium="video",
            surface="thumbnail",
            role="title",
            source_kind="image_asset",
            status="curated",
        )
        response = app.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 9,
                "method": "tools/call",
                "params": {
                    "name": "add_reference_review",
                    "arguments": {
                        "reference_id": created["reference_id"],
                        "reviewer_kind": "agent_vision",
                        "reviewer_name": "codex",
                        "candidate_font_ids": ["goodchoice-yg-jalnan"],
                        "observed_font_labels": ["playful display"],
                        "confidence": 0.88,
                        "apply_to_reference": True,
                    },
                },
            }
        )

        result = response["result"]["structuredContent"]
        self.assertEqual(result["review"]["reviewer_name"], "codex")
        listed = app.service.list_reference_reviews(reference_id=created["reference_id"])
        self.assertEqual(len(listed["reviews"]), 1)


if __name__ == "__main__":
    unittest.main()
