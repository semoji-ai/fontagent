from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FontRecord:
    font_id: str
    family: str
    slug: str
    source_site: str
    source_page_url: str
    homepage_url: str
    license_id: str
    license_summary: str
    commercial_use_allowed: bool
    video_use_allowed: bool
    web_embedding_allowed: bool
    redistribution_allowed: bool
    languages: list[str]
    tags: list[str]
    recommended_for: list[str]
    preview_text_ko: str
    preview_text_en: str
    download_type: str
    download_url: str
    download_source: str
    format: str
    variable_font: bool
    verification_status: str
    verified_at: str
    installed_file_count: int
    verification_failure_reason: str


@dataclass
class FontCandidate:
    candidate_id: int
    query: str
    title: str
    snippet: str
    result_url: str
    normalized_url: str
    domain: str
    discovery_source: str
    status: str
    discovered_at: str
    note: str


@dataclass
class FontReference:
    reference_id: str
    title: str
    medium: str
    surface: str
    role: str
    source_kind: str
    source_url: str
    asset_path: str
    tones: list[str]
    languages: list[str]
    text_blocks: list[str]
    candidate_font_ids: list[str]
    observed_font_labels: list[str]
    palette: dict
    ratio_hint: dict
    extraction_method: str
    extraction_confidence: float
    status: str
    notes: list[str]
    created_at: str
    reference_class: str = "specimen"
    reference_scope: str = "shared_public"


@dataclass
class FontReferenceReview:
    review_id: str
    reference_id: str
    reviewer_kind: str
    reviewer_name: str
    model_name: str
    source: str
    summary: str
    candidate_font_ids: list[str]
    observed_font_labels: list[str]
    cohort_tags: list[str]
    confidence: float
    status: str
    notes: list[str]
    created_at: str
