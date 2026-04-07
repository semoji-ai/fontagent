from __future__ import annotations

from collections import defaultdict
import re
from typing import Any

from .use_cases import UseCaseRequest


COHORT_LABELS = {
    "neutral_ui_sans": "중립 UI 산세리프",
    "neutral_content_sans": "중립 본문 산세리프",
    "editorial_serif": "에디토리얼 세리프",
    "luxury_serif": "럭셔리 세리프",
    "display_bold": "굵은 디스플레이",
    "display_playful": "유쾌한 디스플레이",
    "retro_signage": "레트로 간판체",
    "handwritten": "손글씨",
    "tech_display": "테크 디스플레이",
    "pixel_game": "픽셀/게임체",
    "general_purpose": "범용",
}


COHORT_KEYWORDS = {
    "neutral_ui_sans": {
        "ui": 4,
        "interface": 4,
        "modern": 2,
        "clean": 2,
        "sans": 2,
        "grotesk": 2,
        "subtitle": 3,
        "caption": 2,
        "고딕": 2,
        "기본 고딕": 4,
        "ui용": 4,
    },
    "neutral_content_sans": {
        "body": 4,
        "document": 3,
        "content": 3,
        "readable": 3,
        "문서용": 4,
        "본문": 4,
        "sans": 2,
        "고딕": 2,
        "text": 2,
        "subtitle": 1,
    },
    "editorial_serif": {
        "editorial": 4,
        "serif": 4,
        "명조": 5,
        "바탕": 5,
        "magazine": 3,
        "books": 3,
        "book": 3,
        "documentary": 1,
    },
    "luxury_serif": {
        "luxury": 5,
        "fashion": 4,
        "high-contrast": 4,
        "elegant": 3,
        "serif": 2,
        "editorial": 1,
    },
    "display_bold": {
        "display": 5,
        "title": 4,
        "headline": 4,
        "poster": 4,
        "thumbnail": 4,
        "cover": 3,
        "branding": 2,
        "bold": 3,
        "condensed": 2,
        "slab": 2,
    },
    "display_playful": {
        "playful": 5,
        "quirky": 5,
        "cute": 4,
        "kids": 4,
        "magic": 3,
        "cartoon": 4,
        "bubble": 3,
        "round": 2,
        "마법": 3,
        "귀여움": 4,
    },
    "retro_signage": {
        "retro": 5,
        "signage": 4,
        "sign": 3,
        "vintage": 3,
        "간판": 5,
        "간판글씨": 5,
        "레트로": 5,
        "을지로": 4,
    },
    "handwritten": {
        "handwritten": 5,
        "brush": 4,
        "script": 4,
        "pen": 3,
        "손글씨": 5,
        "캘리": 4,
        "필기": 4,
    },
    "tech_display": {
        "tech": 5,
        "digital": 4,
        "futuristic": 4,
        "sf": 4,
        "sci-fi": 4,
        "arcade": 2,
        "cyber": 4,
    },
    "pixel_game": {
        "pixel": 5,
        "game": 4,
        "gaming": 4,
        "arcade": 4,
        "8bit": 4,
        "bitmap": 4,
    },
}


def _values(font: dict[str, Any] | Any, key: str) -> list[str]:
    if isinstance(font, dict):
        value = font.get(key, [])
    else:
        value = getattr(font, key, [])
    if isinstance(value, list):
        return [str(item) for item in value]
    if value:
        return [str(value)]
    return []


def _text(font: dict[str, Any] | Any, key: str) -> str:
    if isinstance(font, dict):
        return str(font.get(key, "") or "")
    return str(getattr(font, key, "") or "")


def _has_token(corpus: str, token: str, normalized_corpus: str) -> bool:
    normalized_token = token.strip().lower()
    if not normalized_token:
        return False
    if re.fullmatch(r"[0-9a-z\- ]+", normalized_token):
        compact = re.sub(r"[^0-9a-z]+", " ", normalized_token).strip()
        if not compact:
            return False
        return f" {compact} " in normalized_corpus
    return normalized_token in corpus


def classify_font_cohorts(font: dict[str, Any] | Any) -> dict[str, Any]:
    corpus_parts = _values(font, "tags") + _values(font, "recommended_for")
    corpus_parts.extend(
        [
            _text(font, "family"),
            _text(font, "source_site"),
        ]
    )
    corpus = " ".join(corpus_parts).lower()
    normalized_corpus = f" {re.sub(r'[^0-9a-z가-힣]+', ' ', corpus).strip()} "
    score_map: dict[str, int] = defaultdict(int)

    for cohort, keywords in COHORT_KEYWORDS.items():
        for token, points in keywords.items():
            if _has_token(corpus, token, normalized_corpus):
                score_map[cohort] += points

    if not score_map:
        score_map["general_purpose"] = 1
    elif "display_bold" in score_map and "display_playful" in score_map:
        score_map["display_bold"] += 1
    elif "editorial_serif" in score_map and "luxury_serif" in score_map:
        score_map["editorial_serif"] += 1

    ordered = sorted(score_map.items(), key=lambda item: (-item[1], item[0]))
    cohorts = [name for name, score in ordered if score > 0]
    if not cohorts:
        cohorts = ["general_purpose"]
        ordered = [("general_purpose", 1)]
    primary = cohorts[0]
    return {
        "primary": primary,
        "cohorts": cohorts,
        "scores": {name: score for name, score in ordered if score > 0},
        "labels": [COHORT_LABELS.get(name, name) for name in cohorts],
    }


def cohort_policy_for_request(request: UseCaseRequest) -> dict[str, Any]:
    preferred: set[str] = set()
    acceptable: set[str] = set()
    avoid: set[str] = set()

    if request.role == "title":
        preferred.update({"display_bold"})
        acceptable.update({"neutral_ui_sans", "editorial_serif"})
        avoid.update({"neutral_content_sans"})
    elif request.role == "subtitle":
        preferred.update({"neutral_ui_sans", "neutral_content_sans"})
        acceptable.update({"editorial_serif"})
        avoid.update(
            {"display_playful", "retro_signage", "tech_display", "pixel_game", "handwritten"}
        )
    else:
        preferred.update({"neutral_content_sans", "editorial_serif"})
        acceptable.update({"neutral_ui_sans"})
        avoid.update(
            {"display_bold", "display_playful", "retro_signage", "tech_display", "pixel_game", "handwritten"}
        )

    if request.medium == "video" and request.surface == "thumbnail" and request.role == "title":
        preferred.update({"display_bold", "display_playful"})
        acceptable.update({"retro_signage", "tech_display", "neutral_ui_sans"})
        avoid.update({"neutral_content_sans", "editorial_serif"})
    if request.medium == "video" and request.surface == "subtitle_track":
        preferred.update({"neutral_ui_sans", "neutral_content_sans"})
        avoid.update({"display_bold", "display_playful", "retro_signage", "pixel_game", "handwritten"})
    if request.medium == "video" and request.surface == "scene_overlay" and request.role == "title":
        preferred.discard("display_bold")
        preferred.discard("display_playful")
        preferred.update({"neutral_ui_sans", "editorial_serif"})
        acceptable.update({"neutral_content_sans", "display_bold"})
        avoid.update({"display_playful", "retro_signage", "tech_display", "pixel_game", "handwritten"})
    if request.medium == "web" and request.surface == "landing_hero" and request.role == "title":
        preferred.update({"display_bold"})
        acceptable.update({"neutral_ui_sans", "editorial_serif"})
    if request.medium == "document" and request.surface == "body_copy":
        preferred.update({"neutral_content_sans", "editorial_serif"})
        acceptable.update({"neutral_ui_sans"})
    if request.medium == "print" and request.surface == "poster_headline":
        preferred.update({"display_bold", "retro_signage"})
        acceptable.update({"display_playful", "tech_display"})

    tone_set = set(request.tones)
    if {"quirky", "playful", "kids", "fun"} & tone_set:
        preferred.update({"display_playful"})
        acceptable.update({"retro_signage"})
        avoid.update({"luxury_serif"})
    if {"retro", "vintage"} & tone_set:
        preferred.update({"retro_signage"})
        acceptable.update({"display_bold"})
    if {"editorial", "documentary"} & tone_set:
        preferred.update({"editorial_serif"})
        acceptable.update({"neutral_ui_sans", "display_bold"})
    if {"clean", "knowledge", "news"} & tone_set:
        preferred.update({"neutral_ui_sans"})
        acceptable.update({"neutral_content_sans", "editorial_serif"})
        avoid.update({"display_playful", "retro_signage"})
    if {"luxury", "fashion", "elegant"} & tone_set:
        preferred.update({"luxury_serif", "editorial_serif"})
        avoid.update({"display_playful", "pixel_game"})
    if {"tech", "digital", "futuristic", "cyber"} & tone_set:
        preferred.update({"tech_display"})
        acceptable.update({"display_bold"})
    if {"pixel", "game", "gaming", "arcade"} & tone_set:
        preferred.update({"pixel_game"})
        avoid.update({"luxury_serif", "editorial_serif"})

    preferred -= avoid
    acceptable -= avoid
    acceptable -= preferred
    return {
        "preferred": sorted(preferred),
        "acceptable": sorted(acceptable),
        "avoid": sorted(avoid),
    }


def cohort_fit_for_request(font: dict[str, Any] | Any, request: UseCaseRequest) -> dict[str, Any]:
    profile = classify_font_cohorts(font)
    policy = cohort_policy_for_request(request)
    cohorts = set(profile["cohorts"])
    preferred = [name for name in policy["preferred"] if name in cohorts]
    acceptable = [name for name in policy["acceptable"] if name in cohorts]
    avoid = [name for name in policy["avoid"] if name in cohorts]

    if preferred:
        fit = "preferred"
        score = 14 if profile["primary"] in preferred else 10
    elif acceptable:
        fit = "acceptable"
        score = 5 if profile["primary"] in acceptable else 3
    elif avoid:
        fit = "avoid"
        score = -10 if profile["primary"] in avoid else -6
    else:
        fit = "neutral"
        score = 0

    return {
        "primary": profile["primary"],
        "cohorts": profile["cohorts"],
        "labels": profile["labels"],
        "fit": fit,
        "score": score,
        "matched_preferred": preferred,
        "matched_acceptable": acceptable,
        "matched_avoid": avoid,
        "policy": policy,
    }
