from __future__ import annotations

from pathlib import Path


def build_reference_extraction_plan(
    *,
    source_kind: str,
    source_url: str = "",
    asset_path: str = "",
) -> dict:
    kind = (source_kind or "").strip().lower()
    asset_suffix = Path(asset_path).suffix.lower()

    strategies: list[dict] = []
    notes: list[str] = []

    if kind in {"web", "web_page", "landing_page", "site"}:
        strategies.append(
            {
                "stage": "playwright_dom",
                "goal": "DOM, CSS font-family, computed styles, visible text blocks 추출",
                "confidence": "high",
            }
        )
        strategies.append(
            {
                "stage": "studio_screenshot",
                "goal": "실제 렌더된 타이포 캡처와 레이아웃 비율 확인",
                "confidence": "medium",
            }
        )
        strategies.append(
            {
                "stage": "vision_font_guess",
                "goal": "DOM으로 식별되지 않는 폰트나 이미지화된 제목 폰트 후보 추론",
                "confidence": "medium",
            }
        )
        notes.append("웹 레퍼런스는 DOM/CSS가 가장 신뢰도 높은 1차 근거입니다.")
    elif kind in {"image", "poster", "thumbnail", "mockup", "screenshot"} or asset_suffix in {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
    }:
        strategies.append(
            {
                "stage": "ocr",
                "goal": "텍스트 블록 위치와 실제 카피를 추출",
                "confidence": "medium",
            }
        )
        strategies.append(
            {
                "stage": "vision_font_guess",
                "goal": "display/body 폰트 성격, 조합, 무드, 계열 후보 추론",
                "confidence": "medium",
            }
        )
        notes.append("이미지 레퍼런스는 OCR만으로는 폰트 식별이 어렵고, 비전 추론이 보조로 필요합니다.")
    elif kind in {"pdf", "document", "ppt"} or asset_suffix in {".pdf", ".ppt", ".pptx"}:
        strategies.append(
            {
                "stage": "document_parse",
                "goal": "문서 메타/내장 폰트와 텍스트 구조 추출",
                "confidence": "high",
            }
        )
        strategies.append(
            {
                "stage": "ocr",
                "goal": "페이지 이미지 기준 제목/본문 hierarchy 보조 추출",
                "confidence": "medium",
            }
        )
        strategies.append(
            {
                "stage": "vision_font_guess",
                "goal": "내장 폰트가 없거나 outline 처리된 경우 폰트 후보 추론",
                "confidence": "low",
            }
        )
        notes.append("문서/PPT는 내장 폰트 정보가 있으면 그것이 가장 우선입니다.")
    elif kind in {"video_frame", "video"} or asset_suffix in {".mp4", ".mov"}:
        strategies.append(
            {
                "stage": "frame_sampling",
                "goal": "대표 프레임 추출",
                "confidence": "high",
            }
        )
        strategies.append(
            {
                "stage": "ocr",
                "goal": "프레임별 텍스트와 자막 위치 추출",
                "confidence": "medium",
            }
        )
        strategies.append(
            {
                "stage": "vision_font_guess",
                "goal": "타이틀/자막/수치 폰트 성격과 조합 추론",
                "confidence": "medium",
            }
        )
        notes.append("영상은 프레임 샘플링 후 OCR/비전 조합이 필요합니다.")
    else:
        strategies.append(
            {
                "stage": "manual_annotation",
                "goal": "매체/역할/무드/폰트 후보를 사람이 먼저 남김",
                "confidence": "high",
            }
        )
        strategies.append(
            {
                "stage": "vision_font_guess",
                "goal": "후속 자동 식별 후보 보강",
                "confidence": "low",
            }
        )
        notes.append("소스 형식이 불명확하면 수동 주석이 우선입니다.")

    return {
        "source_kind": kind or "unknown",
        "source_url": source_url,
        "asset_path": asset_path,
        "strategies": strategies,
        "notes": notes,
    }
