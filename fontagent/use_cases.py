from __future__ import annotations

from dataclasses import dataclass, field


MEDIUM_KEYWORDS = {
    "web": ["web", "landing", "ui"],
    "video": ["video", "thumbnail", "subtitle"],
    "presentation": ["presentation", "slide", "cover"],
    "document": ["document", "editorial", "body"],
    "print": ["print", "poster", "headline"],
    "mockup": ["mockup", "branding", "packaging"],
    "ecommerce": ["detailpage", "banner", "promotion"],
}

SURFACE_KEYWORDS = {
    "landing_hero": ["landing", "hero", "headline"],
    "thumbnail": ["thumbnail", "poster", "display"],
    "subtitle_track": ["subtitle", "readable", "sans"],
    "cover": ["cover", "title", "display"],
    "body_copy": ["body", "editorial", "readable"],
    "poster_headline": ["poster", "headline", "display"],
    "detailpage_banner": ["banner", "promotion", "headline"],
}

ROLE_KEYWORDS = {
    "title": ["title", "display"],
    "subtitle": ["subtitle", "sans", "readable"],
    "body": ["body", "editorial", "readable"],
    "caption": ["caption", "small", "readable"],
    "cta": ["cta", "headline", "display"],
}

PREVIEW_PRESET_BY_ROLE = {
    "title": "title-ko",
    "subtitle": "subtitle-ko",
    "body": "body-ko",
    "caption": "subtitle-ko",
    "cta": "title-ko",
}

USE_CASE_PRESETS = {
    "documentary-landing-ko": {
        "medium": "web",
        "surface": "landing_hero",
        "role": "title",
        "tones": ["editorial", "documentary"],
        "task_suffix": "documentary landing hero editorial title korean",
        "target": "web",
    },
    "youtube-thumbnail-ko": {
        "medium": "video",
        "surface": "thumbnail",
        "role": "title",
        "tones": ["cinematic", "display"],
        "task_suffix": "youtube video thumbnail title cinematic display korean",
        "target": "both",
    },
    "video-thumbnail": {
        "medium": "video",
        "surface": "thumbnail",
        "role": "title",
        "tones": ["cinematic", "display"],
        "task_suffix": "video thumbnail title cinematic display",
        "target": "both",
    },
    "video-subtitle": {
        "medium": "video",
        "surface": "subtitle_track",
        "role": "subtitle",
        "tones": ["readable"],
        "task_suffix": "video subtitle readable sans",
        "target": "both",
    },
    "web-landing": {
        "medium": "web",
        "surface": "landing_hero",
        "role": "title",
        "tones": ["editorial"],
        "task_suffix": "web landing hero editorial title",
        "target": "web",
    },
    "presentation-cover": {
        "medium": "presentation",
        "surface": "cover",
        "role": "title",
        "tones": ["brand"],
        "task_suffix": "presentation cover title display",
        "target": "both",
    },
    "document-body": {
        "medium": "document",
        "surface": "body_copy",
        "role": "body",
        "tones": ["editorial"],
        "task_suffix": "document body editorial readable",
        "target": "web",
    },
    "poster-headline": {
        "medium": "print",
        "surface": "poster_headline",
        "role": "title",
        "tones": ["poster", "display"],
        "task_suffix": "print poster headline display",
        "target": "both",
    },
}


@dataclass
class UseCaseRequest:
    medium: str
    surface: str
    role: str
    tones: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=lambda: ["ko"])
    constraints: dict = field(default_factory=dict)

    @classmethod
    def from_payload(
        cls,
        *,
        medium: str,
        surface: str,
        role: str,
        tones: list[str] | None = None,
        languages: list[str] | None = None,
        constraints: dict | None = None,
    ) -> "UseCaseRequest":
        return cls(
            medium=(medium or "").strip().lower(),
            surface=(surface or "").strip().lower(),
            role=(role or "").strip().lower(),
            tones=[tone.strip().lower() for tone in (tones or []) if tone.strip()],
            languages=[language.strip().lower() for language in (languages or ["ko"]) if language.strip()],
            constraints=constraints or {},
        )


def build_use_case_query(request: UseCaseRequest) -> str:
    tokens: list[str] = []
    tokens.extend(MEDIUM_KEYWORDS.get(request.medium, [request.medium]))
    tokens.extend(SURFACE_KEYWORDS.get(request.surface, [request.surface]))
    tokens.extend(ROLE_KEYWORDS.get(request.role, [request.role]))
    tokens.extend(request.tones)
    tokens.extend(request.languages)
    deduped = []
    seen = set()
    for token in tokens:
        normalized = token.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return " ".join(deduped)


def preview_preset_for_use_case(request: UseCaseRequest) -> str:
    primary_language = (request.languages or ["ko"])[0]
    if request.medium == "video" and request.role == "subtitle":
        return "subtitle-en" if primary_language == "en" else "subtitle-ko"
    if request.medium in {"document", "presentation"} and request.role == "body":
        return "body-en" if primary_language == "en" else "body-ko"
    default_preset = PREVIEW_PRESET_BY_ROLE.get(request.role, "title-ko")
    if primary_language == "en":
        return default_preset.replace("-ko", "-en")
    return default_preset


def get_use_case_preset(name: str) -> dict:
    try:
        return dict(USE_CASE_PRESETS[name])
    except KeyError as exc:
        raise KeyError(f"Unknown use case preset: {name}") from exc
