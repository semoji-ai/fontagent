from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

from .service import FontAgentService


PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {
    "name": "fontagent",
    "title": "FontAgent MCP",
    "version": "0.1.0",
}


class FontAgentMCPApplication:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.service = FontAgentService(self.root)
        self._ensure_ready()

    def _ensure_ready(self) -> None:
        self.service.ensure_catalog_ready(auto_scan_system=True)

    def tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "get_catalog_status",
                "title": "Get Catalog Status",
                "description": "카탈로그 총량, 설치 검증 수, source/verification/language 분포를 반환합니다.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_license_policy_catalog",
                "title": "Get License Policy Catalog",
                "description": "source_site별 신뢰도와 검토 강도 정책을 반환합니다.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_contract_schema",
                "title": "Get Contract Schema",
                "description": "타이포그래피 handoff 같은 계약의 JSON Schema를 반환합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"}
                    }
                },
            },
            {
                "name": "bootstrap_project_integration",
                "title": "Bootstrap Project Integration",
                "description": "특정 프로젝트에 FontAgent 설정, MCP 예시, prompt, Codex skill을 생성합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string"},
                        "use_case": {"type": "string"},
                        "language": {"type": "string"},
                        "target": {"type": "string"},
                        "asset_dir": {"type": "string"},
                        "include_codex_skill": {"type": "boolean"}
                    },
                    "required": ["project_path"]
                }
            },
            {
                "name": "search_fonts",
                "title": "Search Fonts",
                "description": "검색어, 언어, 라이선스 조건으로 폰트를 검색합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "language": {"type": "string"},
                        "commercial_only": {"type": "boolean"},
                        "video_only": {"type": "boolean"},
                        "include_failed": {"type": "boolean"},
                        "detail_level": {"type": "string"},
                    },
                },
            },
            {
                "name": "recommend_fonts",
                "title": "Recommend Fonts",
                "description": "작업 설명을 기반으로 폰트를 추천합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "language": {"type": "string"},
                        "count": {"type": "integer"},
                        "commercial_only": {"type": "boolean"},
                        "video_only": {"type": "boolean"},
                        "include_failed": {"type": "boolean"},
                        "detail_level": {"type": "string"},
                    },
                    "required": ["task"],
                },
            },
            {
                "name": "recommend_use_case",
                "title": "Recommend Use Case",
                "description": "medium/surface/role/tone/constraints 기반으로 폰트를 추천합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "medium": {"type": "string"},
                        "surface": {"type": "string"},
                        "role": {"type": "string"},
                        "tones": {"type": "array", "items": {"type": "string"}},
                        "languages": {"type": "array", "items": {"type": "string"}},
                        "constraints": {"type": "object"},
                        "count": {"type": "integer"},
                        "include_failed": {"type": "boolean"},
                        "detail_level": {"type": "string"},
                    },
                    "required": ["medium", "surface", "role"],
                },
            },
            {
                "name": "guided_interview_recommend",
                "title": "Guided Interview Recommend",
                "description": "카테고리와 세부 카테고리, 답변을 바탕으로 인터뷰 기반 폰트 추천과 캔버스 프리뷰 데이터를 반환합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "subcategory": {"type": "string"},
                        "answers": {"type": "object"},
                        "language": {"type": "string"},
                        "count": {"type": "integer"},
                        "include_failed": {"type": "boolean"},
                        "detail_level": {"type": "string"},
                        "include_canvas": {"type": "boolean"},
                        "include_font_system_preview": {"type": "boolean"},
                    },
                    "required": ["category", "subcategory"],
                },
            },
            {
                "name": "list_use_cases",
                "title": "List Use Cases",
                "description": "사전 정의된 use-case preset 목록을 반환합니다.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "list_interview_catalog",
                "title": "List Interview Catalog",
                "description": "카테고리/세부 카테고리별 인터뷰 질문 세트를 반환합니다.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "list_reference_packs",
                "title": "List Reference Packs",
                "description": "초기 레퍼런스 학습용 starter pack 목록을 반환합니다.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "add_reference_review",
                "title": "Add Reference Review",
                "description": "에이전트/비전 모델이 분석한 레퍼런스 리뷰를 저장하고, 필요하면 원본 레퍼런스 후보군에도 반영합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "reference_id": {"type": "string"},
                        "reviewer_kind": {"type": "string"},
                        "reviewer_name": {"type": "string"},
                        "model_name": {"type": "string"},
                        "source": {"type": "string"},
                        "summary": {"type": "string"},
                        "candidate_font_ids": {"type": "array", "items": {"type": "string"}},
                        "observed_font_labels": {"type": "array", "items": {"type": "string"}},
                        "cohort_tags": {"type": "array", "items": {"type": "string"}},
                        "confidence": {"type": "number"},
                        "status": {"type": "string"},
                        "notes": {"type": "array", "items": {"type": "string"}},
                        "apply_to_reference": {"type": "boolean"},
                    },
                    "required": ["reference_id", "reviewer_kind", "reviewer_name"],
                },
            },
            {
                "name": "list_reference_reviews",
                "title": "List Reference Reviews",
                "description": "저장된 레퍼런스 리뷰를 reference_id별로 반환합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "reference_id": {"type": "string"},
                        "status": {"type": "string"},
                    },
                },
            },
            {
                "name": "install_font",
                "title": "Install Font",
                "description": "특정 폰트를 지정 경로에 설치합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "font_id": {"type": "string"},
                        "output_dir": {"type": "string"},
                    },
                    "required": ["font_id", "output_dir"],
                },
            },
            {
                "name": "prepare_font_system",
                "title": "Prepare Font System",
                "description": "프로젝트용 title/subtitle/body 폰트 시스템을 생성합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string"},
                        "task": {"type": "string"},
                        "language": {"type": "string"},
                        "target": {"type": "string"},
                        "asset_dir": {"type": "string"},
                        "use_case": {"type": "string"},
                        "with_templates": {"type": "boolean"},
                    },
                    "required": ["project_path"],
                },
            },
            {
                "name": "build_glyph_index",
                "title": "Build Glyph Index",
                "description": "설치된 폰트로부터 이미지-폰트 식별용 글리프 지문 인덱스를 빌드합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "font_dirs": {"type": "array", "items": {"type": "string"}},
                        "language": {"type": "string"},
                        "characters": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            {
                "name": "identify_font_in_image",
                "title": "Identify Font In Image",
                "description": "이미지에서 텍스트 글리프를 추출하고 지문 인덱스와 비교해 top 1~5 후보 폰트를 각 라이선스 정보와 함께 반환합니다. license_constraints로 상업/영상/웹/재배포 조건을 지정하면 조건을 만족하는 유사 대체 폰트를 fingerprint 유사도로 정렬해 함께 돌려줍니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "image_path": {"type": "string"},
                        "top_k": {"type": "integer"},
                        "char_hints": {"type": "array", "items": {"type": "string"}},
                        "max_glyphs": {"type": "integer"},
                        "similar_alternatives": {"type": "integer"},
                        "license_constraints": {
                            "type": "object",
                            "properties": {
                                "commercial_use": {"type": "boolean"},
                                "video_use": {"type": "boolean"},
                                "web_embedding": {"type": "boolean"},
                                "redistribution": {"type": "boolean"},
                            },
                        },
                    },
                    "required": ["image_path"],
                },
            },
            {
                "name": "list_typography_presets",
                "title": "List Typography Presets",
                "description": "저장된 모든 typography preset (title/subtitle/body 폰트 패밀리 조합)을 반환합니다. 언어/매체/서페이스/출처로 필터링 가능.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "language": {"type": "string"},
                        "medium": {"type": "string"},
                        "surface": {"type": "string"},
                        "source": {"type": "string"},
                    },
                },
            },
            {
                "name": "get_typography_preset",
                "title": "Get Typography Preset",
                "description": "preset_id 로 단일 preset 을 조회합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"preset_id": {"type": "string"}},
                    "required": ["preset_id"],
                },
            },
            {
                "name": "recommend_typography_preset",
                "title": "Recommend Typography Preset",
                "description": "tones/languages/medium/surface 조건으로 가장 잘 맞는 preset 을 랭킹해서 반환합니다. compose_text_layers 에 바로 먹일 수 있는 preset_id 를 제안.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tones": {"type": "array", "items": {"type": "string"}},
                        "languages": {"type": "array", "items": {"type": "string"}},
                        "medium": {"type": "string"},
                        "surface": {"type": "string"},
                        "count": {"type": "integer"},
                    },
                },
            },
            {
                "name": "save_typography_preset",
                "title": "Save Typography Preset",
                "description": "새 preset 을 저장하거나 기존 preset 을 업데이트합니다. 수동 큐레이션 또는 레퍼런스 이미지에서 학습된 결과를 카탈로그에 영속화할 때 사용.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "preset_id": {"type": "string"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "tones": {"type": "array", "items": {"type": "string"}},
                        "languages": {"type": "array", "items": {"type": "string"}},
                        "mediums": {"type": "array", "items": {"type": "string"}},
                        "surfaces": {"type": "array", "items": {"type": "string"}},
                        "role_assignments": {"type": "object"},
                        "source": {"type": "string"},
                        "source_url": {"type": "string"},
                        "reference_image_path": {"type": "string"},
                        "confidence": {"type": "number"},
                        "verified": {"type": "boolean"},
                    },
                    "required": ["preset_id", "name", "role_assignments"],
                },
            },
            {
                "name": "delete_typography_preset",
                "title": "Delete Typography Preset",
                "description": "preset_id 로 preset 을 삭제합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"preset_id": {"type": "string"}},
                    "required": ["preset_id"],
                },
            },
            {
                "name": "compose_text_layers",
                "title": "Compose Text Layers",
                "description": "포스터/장면 이미지에 대해 호출자가 미리 OCR·영역 분할해둔 regions 배열을 입력으로 받아, 각 영역에 시각적 identify + 역할/스타일 기반 recommend 를 hybrid(RRF)로 결합해 최적 폰트를 배정합니다. 각 text layer 는 font 상세(라이선스/source/install/confidence) 와 유사 대안을 포함합니다. install_to 가 지정되면 승자 폰트를 해당 디렉터리에 자동 설치하고, css/remotion/handoff output 경로를 넘기면 @font-face, Remotion 폰트 맵, text-layer-handoff.v1 계약을 함께 출력합니다. OCR 은 FontAgent 에서 수행하지 않습니다 — 멀티모달 LLM 이 regions 를 생성해 넘겨주는 것이 전제.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "image_path": {"type": "string"},
                        "regions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "bbox": {
                                        "type": "array",
                                        "items": {"type": "number"},
                                        "minItems": 4,
                                        "maxItems": 4,
                                    },
                                    "text": {"type": "string"},
                                    "role": {"type": "string"},
                                    "style_hints": {"type": "array", "items": {"type": "string"}},
                                    "tones": {"type": "array", "items": {"type": "string"}},
                                    "language": {"type": "string"},
                                },
                                "required": ["bbox"],
                            },
                        },
                        "similar_alternatives": {"type": "integer"},
                        "svg_output_path": {"type": "string"},
                        "install_to": {"type": "string"},
                        "handoff_output_path": {"type": "string"},
                        "css_output_path": {"type": "string"},
                        "remotion_output_path": {"type": "string"},
                        "preset_id": {"type": "string"},
                        "license_constraints": {
                            "type": "object",
                            "properties": {
                                "commercial_use": {"type": "boolean"},
                                "video_use": {"type": "boolean"},
                                "web_embedding": {"type": "boolean"},
                                "redistribution": {"type": "boolean"},
                            },
                        },
                    },
                    "required": ["image_path", "regions"],
                },
            },
            {
                "name": "generate_typography_handoff",
                "title": "Generate Typography Handoff",
                "description": "디자인 에이전트로 넘길 typography handoff contract를 생성합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string"},
                        "task": {"type": "string"},
                        "language": {"type": "string"},
                        "target": {"type": "string"},
                        "asset_dir": {"type": "string"},
                        "use_case": {"type": "string"},
                    },
                    "required": ["project_path"],
                },
            },
        ]

    def handle_message(self, message: dict[str, Any]) -> Optional[dict[str, Any]]:
        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params") or {}

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": SERVER_INFO,
                    "instructions": "FontAgent MCP는 무료 폰트 검색, 추천, 라이선스/자동화 판단, 설치, font system, typography handoff를 제공합니다.",
                },
            }
        if method == "notifications/initialized":
            return None
        if method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": self.tool_definitions()},
            }
        if method == "tools/call":
            name = params.get("name", "")
            arguments = params.get("arguments") or {}
            try:
                payload = self.call_tool(name, arguments)
            except KeyError:
                return self._error_response(request_id, -32601, f"Unknown tool: {name}")
            except Exception as exc:  # noqa: BLE001
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Tool error: {exc}"}],
                        "structuredContent": {"error": str(exc)},
                        "isError": True,
                    },
                }
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}],
                    "structuredContent": payload,
                },
            }
        if request_id is None:
            return None
        return self._error_response(request_id, -32601, f"Unknown method: {method}")

    def _error_response(self, request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "search_fonts":
            return {
                "results": self.service.search(
                    query=arguments.get("query", ""),
                    language=arguments.get("language"),
                    commercial_only=bool(arguments.get("commercial_only", False)),
                    video_only=bool(arguments.get("video_only", False)),
                    include_failed=bool(arguments.get("include_failed", False)),
                    detail_level=arguments.get("detail_level", "compact"),
                )
            }
        if name == "get_catalog_status":
            return self.service.catalog_status()
        if name == "get_license_policy_catalog":
            return self.service.license_policy_catalog()
        if name == "get_contract_schema":
            return self.service.get_contract_schema(arguments.get("name", "typography-handoff.v1"))
        if name == "bootstrap_project_integration":
            return self.service.bootstrap_project_integration(
                project_path=Path(arguments.get("project_path", "")),
                use_case=arguments.get("use_case", "documentary-landing-ko"),
                language=arguments.get("language", "ko"),
                target=arguments.get("target", "both"),
                asset_dir=arguments.get("asset_dir", "assets/fonts"),
                include_codex_skill=bool(arguments.get("include_codex_skill", True)),
            )
        if name == "recommend_fonts":
            return {
                "results": self.service.recommend(
                    task=arguments.get("task", ""),
                    language=arguments.get("language"),
                    commercial_only=bool(arguments.get("commercial_only", True)),
                    video_only=bool(arguments.get("video_only", False)),
                    count=int(arguments.get("count", 5)),
                    include_failed=bool(arguments.get("include_failed", False)),
                    detail_level=arguments.get("detail_level", "compact"),
                )
            }
        if name == "recommend_use_case":
            return self.service.recommend_use_case(
                medium=arguments.get("medium", ""),
                surface=arguments.get("surface", ""),
                role=arguments.get("role", ""),
                tones=arguments.get("tones"),
                languages=arguments.get("languages"),
                constraints=arguments.get("constraints"),
                count=int(arguments.get("count", 5)),
                include_failed=bool(arguments.get("include_failed", False)),
                detail_level=arguments.get("detail_level", "compact"),
            )
        if name == "guided_interview_recommend":
            return self.service.guided_interview_recommend(
                category=arguments.get("category", ""),
                subcategory=arguments.get("subcategory", ""),
                answers=arguments.get("answers"),
                language=arguments.get("language", "ko"),
                count=int(arguments.get("count", 6)),
                include_failed=bool(arguments.get("include_failed", False)),
                detail_level=arguments.get("detail_level", "compact"),
                include_canvas=bool(arguments.get("include_canvas", False)),
                include_font_system_preview=bool(arguments.get("include_font_system_preview", False)),
            )
        if name == "list_use_cases":
            return self.service.list_use_cases()
        if name == "list_interview_catalog":
            return self.service.list_interview_catalog()
        if name == "list_reference_packs":
            return self.service.list_reference_packs()
        if name == "add_reference_review":
            return self.service.add_reference_review(
                reference_id=arguments.get("reference_id", ""),
                reviewer_kind=arguments.get("reviewer_kind", ""),
                reviewer_name=arguments.get("reviewer_name", ""),
                model_name=arguments.get("model_name", ""),
                source=arguments.get("source", ""),
                summary=arguments.get("summary", ""),
                candidate_font_ids=arguments.get("candidate_font_ids"),
                observed_font_labels=arguments.get("observed_font_labels"),
                cohort_tags=arguments.get("cohort_tags"),
                confidence=float(arguments.get("confidence", 0.0)),
                status=arguments.get("status", "curated"),
                notes=arguments.get("notes"),
                apply_to_reference=bool(arguments.get("apply_to_reference", True)),
            )
        if name == "list_reference_reviews":
            return self.service.list_reference_reviews(
                reference_id=arguments.get("reference_id"),
                status=arguments.get("status"),
            )
        if name == "install_font":
            return self.service.install(
                arguments["font_id"],
                Path(arguments["output_dir"]).expanduser(),
            )
        if name == "prepare_font_system":
            return self.service.prepare_font_system(
                project_path=Path(arguments["project_path"]).expanduser(),
                task=arguments.get("task", ""),
                language=arguments.get("language", "ko"),
                target=arguments.get("target", "both"),
                asset_dir=arguments.get("asset_dir", "assets/fonts"),
                use_case=arguments.get("use_case"),
                with_templates=bool(arguments.get("with_templates", False)),
            )
        if name == "build_glyph_index":
            font_dirs = arguments.get("font_dirs") or []
            language = arguments.get("language") or "both"
            language_hint = None if language == "both" else language
            return self.service.build_font_identify_index(
                extra_font_dirs=[Path(item) for item in font_dirs],
                language_hint=language_hint,
                characters=arguments.get("characters"),
            )
        if name == "identify_font_in_image":
            image_path = arguments.get("image_path") or ""
            if not image_path:
                raise ValueError("image_path is required")
            return self.service.identify_font_in_image(
                image_path=Path(image_path).expanduser(),
                top_k=int(arguments.get("top_k", 5)),
                char_hints=arguments.get("char_hints"),
                max_glyphs=int(arguments.get("max_glyphs", 32)),
                similar_alternatives=int(arguments.get("similar_alternatives", 5)),
                license_constraints=arguments.get("license_constraints"),
            )
        if name == "compose_text_layers":
            image_path = arguments.get("image_path") or ""
            if not image_path:
                raise ValueError("image_path is required")
            regions = arguments.get("regions")
            if not isinstance(regions, list):
                raise ValueError("regions must be a list")
            svg_output = arguments.get("svg_output_path")
            install_to = arguments.get("install_to")
            handoff_output = arguments.get("handoff_output_path")
            css_output = arguments.get("css_output_path")
            remotion_output = arguments.get("remotion_output_path")
            return self.service.compose_text_layers(
                image_path=Path(image_path).expanduser(),
                regions=regions,
                similar_alternatives=int(arguments.get("similar_alternatives", 3)),
                license_constraints=arguments.get("license_constraints"),
                svg_output_path=Path(svg_output).expanduser() if svg_output else None,
                install_to=Path(install_to).expanduser() if install_to else None,
                handoff_output_path=Path(handoff_output).expanduser() if handoff_output else None,
                css_output_path=Path(css_output).expanduser() if css_output else None,
                remotion_output_path=Path(remotion_output).expanduser() if remotion_output else None,
                preset_id=arguments.get("preset_id"),
            )
        if name == "list_typography_presets":
            return {"presets": self.service.list_typography_presets(
                language=arguments.get("language"),
                medium=arguments.get("medium"),
                surface=arguments.get("surface"),
                source=arguments.get("source"),
            )}
        if name == "get_typography_preset":
            preset_id = arguments.get("preset_id") or ""
            if not preset_id:
                raise ValueError("preset_id is required")
            preset = self.service.get_typography_preset(preset_id)
            if preset is None:
                raise KeyError(f"preset not found: {preset_id}")
            return preset
        if name == "recommend_typography_preset":
            return {"results": self.service.recommend_typography_preset(
                tones=arguments.get("tones"),
                languages=arguments.get("languages"),
                medium=arguments.get("medium"),
                surface=arguments.get("surface"),
                count=int(arguments.get("count", 3)),
            )}
        if name == "save_typography_preset":
            return self.service.save_typography_preset(
                preset_id=arguments.get("preset_id") or "",
                name=arguments.get("name") or "",
                description=arguments.get("description", ""),
                tones=arguments.get("tones"),
                languages=arguments.get("languages"),
                mediums=arguments.get("mediums"),
                surfaces=arguments.get("surfaces"),
                role_assignments=arguments.get("role_assignments") or {},
                source=arguments.get("source", "manual"),
                source_url=arguments.get("source_url", ""),
                reference_image_path=arguments.get("reference_image_path", ""),
                confidence=float(arguments.get("confidence", 0.7)),
                verified=bool(arguments.get("verified", False)),
            )
        if name == "delete_typography_preset":
            preset_id = arguments.get("preset_id") or ""
            if not preset_id:
                raise ValueError("preset_id is required")
            return self.service.delete_typography_preset(preset_id)
        if name == "generate_typography_handoff":
            return self.service.generate_typography_handoff(
                project_path=Path(arguments["project_path"]).expanduser(),
                task=arguments.get("task", ""),
                language=arguments.get("language", "ko"),
                target=arguments.get("target", "both"),
                asset_dir=arguments.get("asset_dir", "assets/fonts"),
                use_case=arguments.get("use_case"),
            )
        raise KeyError(name)


def _read_message(stream) -> Optional[dict[str, Any]]:
    headers: dict[str, str] = {}
    while True:
        line = stream.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        decoded = line.decode("utf-8").strip()
        if not decoded:
            break
        name, _, value = decoded.partition(":")
        headers[name.lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    body = stream.read(length)
    if not body:
        return None
    return json.loads(body.decode("utf-8"))


def _write_message(stream, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
    stream.write(header)
    stream.write(body)
    stream.flush()


def serve_stdio(root: Path) -> None:
    app = FontAgentMCPApplication(root)
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    while True:
        message = _read_message(stdin)
        if message is None:
            break
        response = app.handle_message(message)
        if response is not None:
            _write_message(stdout, response)


def main() -> None:
    parser = argparse.ArgumentParser(description="FontAgent MCP stdio server")
    parser.add_argument("--root", default=str(Path.cwd()), help="FontAgent project root")
    args = parser.parse_args()
    serve_stdio(Path(args.root).expanduser().resolve())


if __name__ == "__main__":
    main()
