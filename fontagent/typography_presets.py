"""Curated typography presets — named title/subtitle/body font combinations.

A preset is a reusable "font family recipe": for a given tone, language,
and medium, here are the fonts to use for title, subtitle, and body.
These are persisted in the SQLite catalog via
`service.ensure_typography_presets_seeded()` and are the primary data
source for `recommend_typography_preset()` and preset-driven
`compose_text_layers()` calls.

Seed presets here reference font_ids that live in the default seed
(`fontagent/seed/fonts.json`) so they are usable out of the box. A
future learning pass (from reference images / Pinterest boards) will
extend this list with user-curated entries via the repository.

Design choices:

- `fallback_font_ids` is ordered: the first entry that passes license
  constraints and exists in the catalog wins. This makes presets
  portable across catalogs that differ in which fonts are installed.
- Every role entry includes a `pairing_reason` — a short string that
  explains why this pairing works. Surfaces nicely in match_reasoning
  when a downstream agent wants to show "why these fonts".
- `tones` / `mediums` / `surfaces` are all free-form lists; the
  matcher treats them as tag bags.
"""

from __future__ import annotations

from typing import Any


def _role(font_id: str, *, fallbacks: list[str] | None = None, reason: str = "") -> dict[str, Any]:
    return {
        "font_id": font_id,
        "fallback_font_ids": list(fallbacks or []),
        "pairing_reason": reason,
    }


SEED_PRESETS: list[dict[str, Any]] = [
    {
        "preset_id": "editorial-serif-ko",
        "name": "에디토리얼 명조",
        "description": "차분한 한국어 에디토리얼 지면. 본고딕 계열 제목에 명조 본문을 짝지어 고전 인쇄 감각을 재현.",
        "tones": ["editorial", "calm", "minimal", "soft"],
        "languages": ["ko"],
        "mediums": ["editorial", "poster", "web"],
        "surfaces": ["article", "cover", "landing"],
        "role_assignments": {
            "title": _role("gowun-batang",
                           fallbacks=["noto-sans-kr", "pretendard"],
                           reason="bowl-heavy batang title sits well above a myeongjo body"),
            "subtitle": _role("gowun-batang",
                              fallbacks=["pretendard"],
                              reason="same family keeps subtitle tonally linked to title"),
            "body": _role("gowun-batang",
                          fallbacks=["noto-sans-kr"],
                          reason="sustained reading in a single serif family"),
        },
        "source": "curated",
        "confidence": 0.85,
    },
    {
        "preset_id": "modern-ui-ko",
        "name": "모던 UI 스택",
        "description": "서비스/대시보드에 바로 쓰는 한국어 산세리프 쌍. Pretendard 가 헤드라인, SUIT 가 본문/캡션을 담당.",
        "tones": ["modern", "clean", "ui", "minimal", "neutral"],
        "languages": ["ko", "en"],
        "mediums": ["web", "app", "dashboard"],
        "surfaces": ["landing", "dashboard", "article"],
        "role_assignments": {
            "title": _role("pretendard",
                           fallbacks=["suit", "noto-sans-kr"],
                           reason="variable weight title with a neutral UI voice"),
            "subtitle": _role("suit",
                              fallbacks=["pretendard", "noto-sans-kr"],
                              reason="slight tonal shift, still sans"),
            "body": _role("suit",
                          fallbacks=["pretendard", "noto-sans-kr"],
                          reason="comfortable body reading at 14–16px"),
        },
        "source": "curated",
        "confidence": 0.9,
    },
    {
        "preset_id": "bilingual-neutral",
        "name": "한영 중립 본고딕",
        "description": "한국어와 영어가 섞이는 슬라이드/웹 문서용. Noto Sans KR 하나로 모든 역할을 통일해 시각적 흔들림 없음.",
        "tones": ["bilingual", "neutral", "clean", "presentation"],
        "languages": ["ko", "en"],
        "mediums": ["slide", "web", "video"],
        "surfaces": ["slide", "landing", "report"],
        "role_assignments": {
            "title": _role("noto-sans-kr",
                           fallbacks=["pretendard", "suit"],
                           reason="wide weight range supports display at title size"),
            "subtitle": _role("noto-sans-kr",
                              fallbacks=["suit"],
                              reason="mid-weight keeps hierarchy visible"),
            "body": _role("noto-sans-kr",
                          fallbacks=["suit", "pretendard"],
                          reason="regular weight for body copy"),
        },
        "source": "curated",
        "confidence": 0.85,
    },
    {
        "preset_id": "traditional-ko",
        "name": "전통 한국 인쇄",
        "description": "붓글씨 느낌이 섞인 전통 한글 제목에 안정적인 명조 본문. 박물관·문화 관련 레이아웃에 잘 맞음.",
        "tones": ["traditional", "warm", "cultural", "literary"],
        "languages": ["ko"],
        "mediums": ["poster", "editorial", "exhibition"],
        "surfaces": ["cover", "article", "signage"],
        "role_assignments": {
            "title": _role("maruburi",
                           fallbacks=["gowun-batang", "noto-sans-kr"],
                           reason="soft brushed title sets a cultural tone"),
            "subtitle": _role("gowun-batang",
                              fallbacks=["maruburi"],
                              reason="serif subtitle anchors the calligraphic title"),
            "body": _role("gowun-batang",
                          fallbacks=["noto-sans-kr"],
                          reason="readable serif body"),
        },
        "source": "curated",
        "confidence": 0.8,
    },
    {
        "preset_id": "brand-developer-ko",
        "name": "브랜드 개발자",
        "description": "개발자 도구, 테크 블로그, 스타트업 랜딩 — 중립 산세리프 강조 + SUIT 본문.",
        "tones": ["brand", "developer", "tech", "clean", "modern"],
        "languages": ["ko", "en"],
        "mediums": ["web", "app", "documentation"],
        "surfaces": ["landing", "article", "dashboard"],
        "role_assignments": {
            "title": _role("suit",
                           fallbacks=["pretendard"],
                           reason="neutral tech voice, strong character shapes"),
            "subtitle": _role("pretendard",
                              fallbacks=["suit", "noto-sans-kr"],
                              reason="contrast between developer-neutral title and modern subtitle"),
            "body": _role("suit",
                          fallbacks=["pretendard"],
                          reason="developer-friendly body with wide character variety"),
        },
        "source": "curated",
        "confidence": 0.8,
    },
]


def get_seed_presets() -> list[dict[str, Any]]:
    """Return a deep-copied list of curated preset definitions."""
    import copy

    return copy.deepcopy(SEED_PRESETS)
