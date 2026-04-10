from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .curated_candidates import get_curated_candidates
from .discovery import classify_candidate_status, discover_web_candidates
from .font_system import (
    guess_generic_family,
    pick_preferred_file,
    render_css_token_file,
    render_remotion_token_file,
    role_defaults,
    write_font_system_manifest,
)
from .font_cohorts import cohort_fit_for_request
from .interviews import build_interview_plan, list_interview_catalog
from .license_policy import SOURCE_LICENSE_POLICIES, get_source_license_policy
from .noonnu import fetch_noonnu_snapshot
from .installer import install_font
from .noonnu import parse_detail_html, parse_listing_html
from .official_sources import (
    fetch_cafe24_fonts,
    fetch_goodchoice_fonts,
    fetch_gmarket_fonts,
    fetch_gongu_fonts,
    fetch_google_display_fonts,
    fetch_fonco_free_fonts,
    fetch_hancom_fonts,
    fetch_jeju_fonts,
    fetch_league_fonts,
    fetch_nexon_fonts,
    fetch_naver_fonts,
    fetch_fontshare_fonts,
    fetch_velvetyne_fonts,
    fetch_woowahan_fonts,
    imported_candidate_urls_for_sources,
)
from .obsidian_export import export_reference_note, sync_reference_index
from .preview import write_preview
from .project_bootstrap import bootstrap_project
from .reference_intelligence import build_reference_extraction_plan
from .reference_image import extract_image_reference_payload
from .reference_packs import get_reference_pack, list_reference_packs
from .reference_vision import guess_reference_fonts_via_vision
from .reference_web import extract_web_reference_payload
from .repository import FontRepository
from .resolver import (
    infer_download_source,
    resolve_download,
    write_browser_download_task,
    write_source_browser_task,
)
from .system_scan import scan_system_font_records
from .template_bundle import write_template_bundle
from .use_cases import UseCaseRequest, build_use_case_query, preview_preset_for_use_case
from .use_cases import USE_CASE_PRESETS, get_use_case_preset
from .db import connect


DEFAULT_OFFICIAL_IMPORT_SOURCES = (
    "naver_hangeul",
    "google_display",
    "cafe24_brand",
    "nexon_brand",
    "woowahan_brand",
    "hancom",
    "jeju_official",
    "fontshare_display",
)


def _safe_fs_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value.strip()).strip("-") or "reference"


def _normalize_font_key(value: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", "", (value or "").lower())


def _reference_note_slug(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[-\s]+", "-", value)
    return value or "reference"


REFERENCE_CLASS_WEIGHTS = {
    "specimen": 0.7,
    "market": 1.2,
    "campaign": 1.35,
    "channel": 1.15,
}

SURFACE_REFERENCE_COMPATIBILITY = {
    "scene_overlay": {
        "scene_overlay": 1.0,
        "cover": 0.7,
        "landing_hero": 0.55,
        "poster_headline": 0.45,
        "thumbnail": 0.0,
        "subtitle_track": 0.0,
    },
    "thumbnail": {
        "thumbnail": 1.0,
        "poster_headline": 0.45,
        "cover": 0.3,
        "scene_overlay": 0.0,
    },
    "subtitle_track": {
        "subtitle_track": 1.0,
        "scene_overlay": 0.35,
        "thumbnail": 0.0,
    },
}


def _surface_compatibility(request_surface: str, record_surface: str) -> float:
    requested = str(request_surface or "").strip().lower()
    recorded = str(record_surface or "").strip().lower()
    if not requested or not recorded:
        return 0.35
    if requested == recorded:
        return 1.0
    return SURFACE_REFERENCE_COMPATIBILITY.get(requested, {}).get(recorded, 0.25)


class FontAgentService:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.db_path = self.root / "fontagent.db"
        self.cache_dir = self.root / ".cache" / "downloads"
        self.preview_dir = self.root / ".cache" / "previews"
        self.repository = FontRepository(self.db_path)

    def _reference_settings_path(self) -> Path:
        return self.root / ".fontagent" / "reference-learning.json"

    def get_reference_settings(self) -> dict:
        default_vault_root = str((self.root / "fontagent_vault").resolve())
        default_private_root = str((self.root / ".fontagent" / "reference_private_vault").resolve())
        path = self._reference_settings_path()
        if not path.exists():
            return {
                "vault_root": default_vault_root,
                "vault_category": "Fonts",
                "asset_policy": "public_metadata_only",
                "private_vault_root": default_private_root,
            }
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {
                "vault_root": default_vault_root,
                "vault_category": "Fonts",
                "asset_policy": "public_metadata_only",
                "private_vault_root": default_private_root,
            }
        return {
            "vault_root": str(payload.get("vault_root", default_vault_root) or default_vault_root),
            "vault_category": str(payload.get("vault_category", "Fonts") or "Fonts"),
            "asset_policy": str(payload.get("asset_policy", "public_metadata_only") or "public_metadata_only"),
            "private_vault_root": str(payload.get("private_vault_root", default_private_root) or default_private_root),
        }

    def save_reference_settings(
        self,
        *,
        vault_root: str = "",
        vault_category: str = "Fonts",
        asset_policy: str = "public_metadata_only",
        private_vault_root: str = "",
    ) -> dict:
        path = self._reference_settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "vault_root": str(vault_root or ""),
            "vault_category": str(vault_category or "Fonts"),
            "asset_policy": str(asset_policy or "public_metadata_only"),
            "private_vault_root": str(private_vault_root or ""),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"settings_path": str(path), **payload}

    def _resolve_reference_vault(
        self,
        vault_root: Path | None = None,
        vault_category: str | None = None,
    ) -> tuple[Path | None, str]:
        settings = self.get_reference_settings()
        resolved_root = vault_root
        if resolved_root is None and settings["vault_root"]:
            resolved_root = Path(settings["vault_root"]).expanduser().resolve()
        resolved_category = vault_category or settings["vault_category"] or "Fonts"
        return resolved_root, resolved_category

    def _resolve_reference_export_settings(
        self,
        vault_root: Path | None = None,
        vault_category: str | None = None,
    ) -> tuple[Path | None, str, str, Path | None]:
        settings = self.get_reference_settings()
        resolved_root, resolved_category = self._resolve_reference_vault(vault_root, vault_category)
        asset_policy = settings.get("asset_policy", "public_metadata_only") or "public_metadata_only"
        private_root_value = settings.get("private_vault_root", "") or ""
        private_root = Path(private_root_value).expanduser().resolve() if private_root_value else None
        if resolved_root is not None and private_root == resolved_root:
            private_root = None
        return resolved_root, resolved_category, asset_policy, private_root

    def _font_count(self) -> int:
        with connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM fonts").fetchone()
        return int(row["count"] or 0) if row else 0

    def _font_count_for_source(self, source_site: str) -> int:
        with connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM fonts WHERE source_site = ?",
                (source_site,),
            ).fetchone()
        return int(row["count"] or 0) if row else 0

    def _ensure_reference_vault_paths(self) -> None:
        settings = self.get_reference_settings()
        vault_root = settings.get("vault_root") or ""
        private_root = settings.get("private_vault_root") or ""
        if vault_root:
            Path(vault_root).expanduser().mkdir(parents=True, exist_ok=True)
        if private_root:
            Path(private_root).expanduser().mkdir(parents=True, exist_ok=True)

    def ensure_catalog_ready(self, *, auto_scan_system: bool = False) -> dict:
        self.repository.init_db()
        seeded = 0
        scanned = 0
        seed_path = self.root / "fontagent" / "seed" / "fonts.json"
        if self._font_count() == 0 and seed_path.exists():
            seeded = self.init()
        if auto_scan_system and self._font_count_for_source("system_local") == 0:
            scanned = int(self.scan_system_fonts().get("upserted", 0))
        self._ensure_reference_vault_paths()
        return {
            "db_path": str(self.db_path),
            "seeded": seeded,
            "system_scanned": scanned,
            "total_fonts": self._font_count(),
        }

    def scan_system_fonts(self, *, timeout: int = 20) -> dict:
        records = scan_system_font_records(timeout=timeout)
        imported = self.repository.upsert_many(records)
        verified_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with connect(self.db_path) as conn:
            for item in records:
                conn.execute(
                    """
                    UPDATE fonts
                    SET verification_status = ?,
                        verified_at = ?,
                        installed_file_count = ?,
                        verification_failure_reason = ?
                    WHERE font_id = ?
                    """,
                    (
                        "installed",
                        verified_at,
                        int(item.get("installed_file_count", 1) or 1),
                        "",
                        item["font_id"],
                    ),
                )
            conn.commit()
        return {
            "source": "system_local",
            "scanned_families": len(records),
            "upserted": imported,
            "verified_at": verified_at,
        }

    def import_official_sources(self, *, sources: list[str] | None = None) -> dict:
        requested = list(sources or DEFAULT_OFFICIAL_IMPORT_SOURCES)
        handlers = {
            "naver_hangeul": self.import_naver_fonts,
            "google_display": self.import_google_display_fonts,
            "cafe24_brand": self.import_cafe24_fonts,
            "nexon_brand": self.import_nexon_fonts,
            "woowahan_brand": self.import_woowahan_fonts,
            "hancom": self.import_hancom_fonts,
            "jeju_official": self.import_jeju_fonts,
            "fontshare_display": self.import_fontshare_fonts,
            "gmarket_brand": self.import_gmarket_fonts,
            "goodchoice_brand": self.import_goodchoice_fonts,
            "league_movable_type": self.import_league_fonts,
            "velvetyne_display": self.import_velvetyne_fonts,
            "gongu_freefont": self.import_gongu_fonts,
            "fonco_freefont": self.import_fonco_fonts,
        }
        results: list[dict] = []
        failures: list[dict] = []
        for source in requested:
            handler = handlers.get(source)
            if handler is None:
                failures.append({"source": source, "error": "unknown_source"})
                continue
            try:
                results.append(handler())
            except Exception as exc:  # noqa: BLE001
                failures.append({"source": source, "error": str(exc)})
        return {
            "requested_sources": requested,
            "succeeded": len(results),
            "failed": len(failures),
            "results": results,
            "failures": failures,
        }

    def _infer_reference_class(
        self,
        *,
        source_kind: str,
        source_url: str = "",
        title: str = "",
    ) -> str:
        url = (source_url or "").lower()
        normalized_title = (title or "").lower()
        if any(domain in url for domain in ("youtube.com", "youtu.be", "instagram.com", "pinterest.com", "tiktok.com")):
            return "channel"
        if any(domain in url for domain in ("behance.net", "dribbble.com")):
            return "market"
        if "campaign" in url or "campaign" in normalized_title:
            return "campaign"
        if source_kind in {"image_asset", "video_frame"}:
            return "market"
        return "specimen"

    def init(self) -> int:
        self.repository.init_db()
        return self.repository.seed_from_json(
            self.root / "fontagent" / "seed" / "fonts.json"
        )

    def _get_attr(self, item, name: str):
        if isinstance(item, dict):
            return item.get(name)
        return getattr(item, name)

    def _verification_rank(self, item) -> int:
        status = self._get_attr(item, "verification_status") or ""
        if status == "installed":
            return 3
        if status in {"manual_required", "browser_required", "resolved"}:
            return 2
        if status:
            return 0
        return 1

    def _download_source_rank(self, item) -> int:
        source = self._get_attr(item, "download_source") or ""
        if source == "canonical":
            return 2
        if source == "preview_webfont":
            return 1
        return 0

    def _quality_rank(self, item) -> tuple[int, int, int]:
        return (
            self._verification_rank(item),
            self._download_source_rank(item),
            int(self._get_attr(item, "installed_file_count") or 0),
        )

    def _license_profile(self, item) -> dict:
        license_summary = (self._get_attr(item, "license_summary") or "").strip()
        commercial_allowed = bool(self._get_attr(item, "commercial_use_allowed"))
        video_allowed = bool(self._get_attr(item, "video_use_allowed"))
        web_allowed = bool(self._get_attr(item, "web_embedding_allowed"))
        redistribution_allowed = bool(self._get_attr(item, "redistribution_allowed"))
        source_site = (self._get_attr(item, "source_site") or "").lower()
        download_source_rank = self._download_source_rank(item)
        source_policy = get_source_license_policy(source_site)
        trust_level = source_policy["trust_level"]
        basis: list[str] = []
        gaps: list[str] = []

        if license_summary:
            basis.append("license_summary_present")
        else:
            gaps.append("license_summary_missing")
        if trust_level == "high":
            basis.append("trusted_source_registry_high")
        elif trust_level == "medium":
            basis.append("trusted_source_registry_medium")
        else:
            gaps.append("source_not_in_trusted_registry")
        if download_source_rank >= 2:
            basis.append("canonical_download_source")
        elif download_source_rank == 1:
            basis.append("preview_webfont_source")
        else:
            gaps.append("download_source_not_verified")
        if commercial_allowed:
            basis.append("commercial_use_allowed")
        else:
            gaps.append("commercial_use_not_allowed")
        if video_allowed:
            basis.append("video_use_allowed")
        else:
            gaps.append("video_use_not_confirmed")
        if web_allowed:
            basis.append("web_embedding_allowed")
        else:
            gaps.append("web_embedding_not_confirmed")
        if redistribution_allowed:
            basis.append("redistribution_allowed")

        if not commercial_allowed:
            status = "blocked"
            confidence = "high" if license_summary else "medium"
            score = 20
            summary = "상업 사용 제한"
        else:
            confidence_score = 0
            if license_summary:
                confidence_score += 1
            if download_source_rank >= 2:
                confidence_score += 1
            if trust_level == "high":
                confidence_score += 1
            elif trust_level == "medium":
                confidence_score += 0.5
            if confidence_score >= 3:
                confidence = "high"
                score = 90
            elif confidence_score == 2:
                confidence = "medium"
                score = 74
            else:
                confidence = "low"
                score = 56
            status = "allowed" if video_allowed or web_allowed else "caution"
            summary = "상업 사용 가능"
            if not video_allowed and not web_allowed:
                summary = "상업 사용 가능, 세부 매체 조건 확인 필요"

        if status == "blocked":
            recommended_action = "do_not_use"
        elif status == "allowed" and confidence == "high":
            recommended_action = "proceed" if source_policy["review_level"] == "low" else "proceed_with_license_note"
        elif status == "allowed":
            recommended_action = "proceed_with_license_note"
        elif confidence == "low":
            recommended_action = "manual_review_required"
        else:
            recommended_action = "review_license_page"

        review_required = recommended_action != "proceed"

        notes = [
            f"commercial={'yes' if commercial_allowed else 'no'}",
            f"video={'yes' if video_allowed else 'no'}",
            f"web_embedding={'yes' if web_allowed else 'no'}",
            f"redistribution={'yes' if redistribution_allowed else 'no'}",
        ]
        if license_summary:
            notes.append(f"summary={license_summary}")
        return {
            "status": status,
            "confidence": confidence,
            "score": score,
            "summary": summary,
            "trusted_source": trust_level in {"high", "medium"},
            "source_policy": source_policy,
            "coverage": {
                "commercial_use": commercial_allowed,
                "video_use": video_allowed,
                "web_embedding": web_allowed,
                "redistribution": redistribution_allowed,
            },
            "basis": basis,
            "gaps": gaps,
            "review_required": review_required,
            "recommended_action": recommended_action,
            "notes": notes,
        }

    def _automation_profile(self, item) -> dict:
        verification_status = (self._get_attr(item, "verification_status") or "").strip().lower()
        download_type = (self._get_attr(item, "download_type") or "").strip().lower()
        download_source_rank = self._download_source_rank(item)
        installed_count = int(self._get_attr(item, "installed_file_count") or 0)

        if verification_status == "installed":
            status = "ready"
            score = 95 if installed_count > 1 else 88
            summary = "설치 검증 완료"
        elif download_type in {"direct_file", "zip_file"} and download_source_rank >= 1:
            status = "ready"
            score = 78
            summary = "자동 설치 가능성이 높음"
        elif verification_status in {"browser_required", "resolved"} or download_type == "html_button":
            status = "assisted"
            score = 55
            summary = "브라우저 보조 필요"
        elif download_type == "manual_only":
            status = "manual"
            score = 28
            summary = "수동 설치 필요"
        elif verification_status in {"invalid_archive", "invalid_file", "error"}:
            status = "blocked"
            score = 10
            summary = "자동화 경로 실패"
        else:
            status = "unknown"
            score = 35
            summary = "자동화 가능성 확인 필요"

        return {
            "status": status,
            "score": score,
            "summary": summary,
            "notes": [
                f"verification={verification_status or 'none'}",
                f"download_type={download_type or 'none'}",
                f"installed_files={installed_count}",
            ],
        }

    def _attach_operational_profiles(self, item: dict) -> dict:
        enriched = dict(item)
        enriched["license_profile"] = self._license_profile(enriched)
        enriched["automation_profile"] = self._automation_profile(enriched)
        return enriched

    def _serialize_font_result(self, item: dict, detail_level: str = "full") -> dict:
        if detail_level == "full":
            return dict(item)
        if detail_level != "compact":
            raise ValueError("detail_level must be one of: full, compact")
        compact = {
            "font_id": item.get("font_id", ""),
            "family": item.get("family", ""),
            "source_site": item.get("source_site", ""),
            "languages": item.get("languages", []),
            "tags": item.get("tags", []),
            "recommended_for": item.get("recommended_for", []),
            "license_summary": item.get("license_summary", ""),
            "verification_status": item.get("verification_status", ""),
            "installed_file_count": item.get("installed_file_count", 0),
            "license_profile": item.get("license_profile", {}),
            "automation_profile": item.get("automation_profile", {}),
        }
        if "score" in item:
            compact["score"] = item["score"]
        if "reference_signal" in item:
            compact["reference_signal"] = item["reference_signal"]
        if "why" in item:
            compact["why"] = list(item.get("why", []))[:4]
        if "preview_preset" in item:
            compact["preview_preset"] = item["preview_preset"]
        if "use_case" in item:
            compact["use_case"] = item["use_case"]
        if "cohort_profile" in item:
            compact["cohort_profile"] = {
                "primary": item["cohort_profile"].get("primary", ""),
                "fit": item["cohort_profile"].get("fit", ""),
                "labels": item["cohort_profile"].get("labels", []),
            }
        return compact

    def _role_fit_score(self, item, role: str) -> int:
        tags = [tag.lower() for tag in (self._get_attr(item, "tags") or [])]
        recommended_for = [tag.lower() for tag in (self._get_attr(item, "recommended_for") or [])]
        family = (self._get_attr(item, "family") or "").lower()
        source_site = (self._get_attr(item, "source_site") or "").lower()
        corpus = " ".join(tags + recommended_for + [family, source_site])

        score = 0
        if role == "title":
            for token, points in (
                ("title", 5),
                ("display", 5),
                ("poster", 4),
                ("thumbnail", 4),
                ("brand", 3),
                ("editorial", 2),
                ("retro", 2),
                ("luxury", 2),
                ("playful", 2),
                ("cinematic", 2),
            ):
                if token in corpus:
                    score += points
            if any(token in corpus for token in ("subtitle", "body", "문서용")) and not any(
                token in corpus for token in ("display", "poster", "thumbnail", "title")
            ):
                score -= 2
        elif role == "subtitle":
            for token, points in (
                ("subtitle", 6),
                ("sans", 3),
                ("고딕", 3),
                ("readable", 2),
                ("문서용", 2),
                ("body", 2),
            ):
                if token in corpus:
                    score += points
            for token in ("display", "poster", "thumbnail", "retro", "brush", "손글씨", "pixel", "게임"):
                if token in corpus:
                    score -= 3
        else:
            for token, points in (
                ("body", 6),
                ("editorial", 4),
                ("명조", 4),
                ("바탕", 4),
                ("serif", 4),
                ("문서용", 3),
                ("책 서체", 3),
                ("readable", 2),
                ("subtitle", 1),
            ):
                if token in corpus:
                    score += points
            for token in ("display", "poster", "thumbnail", "pixel", "게임", "brush", "손글씨"):
                if token in corpus:
                    score -= 3
        return score

    def _search_relevance(self, font, query_tokens: list[str]) -> int:
        if not query_tokens:
            return 0
        family = (self._get_attr(font, "family") or "").lower()
        tags = " ".join(self._get_attr(font, "tags") or []).lower()
        recommended_for = " ".join(self._get_attr(font, "recommended_for") or []).lower()
        source_site = (self._get_attr(font, "source_site") or "").lower()

        score = 0
        for token in query_tokens:
            if token in family:
                score += 5
            elif token in tags:
                score += 3
            elif token in recommended_for:
                score += 2
            elif token in source_site:
                score += 1
        return score

    def _match_font_ids_from_labels(
        self,
        *,
        observed_labels: list[str] | None,
        language: str | None = None,
        limit: int = 5,
    ) -> list[str]:
        labels = [_normalize_font_key(label) for label in (observed_labels or []) if label]
        if not labels:
            return []
        matches: list[tuple[int, str]] = []
        for font in self.repository.list_fonts():
            if language and language not in font.languages:
                continue
            keys = {
                _normalize_font_key(font.family),
                _normalize_font_key(getattr(font, "slug", "")),
                _normalize_font_key(font.font_id),
            }
            score = 0
            for label in labels:
                for key in keys:
                    if not key or len(key) < 3:
                        continue
                    if label == key:
                        score = max(score, 12)
                    elif key in label or label in key:
                        score = max(score, 8)
            if score:
                matches.append((score, font.font_id))
        matches.sort(key=lambda item: (-item[0], item[1]))
        seen: set[str] = set()
        ordered: list[str] = []
        for _, font_id in matches:
            if font_id in seen:
                continue
            seen.add(font_id)
            ordered.append(font_id)
            if len(ordered) >= limit:
                break
        return ordered

    def _guess_reference_candidates(
        self,
        *,
        medium: str,
        surface: str,
        role: str,
        tones: list[str] | None,
        languages: list[str] | None,
        observed_labels: list[str] | None = None,
        limit: int = 5,
    ) -> list[str]:
        primary_language = (languages or [None])[0]
        matched = self._match_font_ids_from_labels(
            observed_labels=observed_labels,
            language=primary_language,
            limit=limit,
        )
        if len(matched) >= limit:
            return matched
        query = build_use_case_query(
            UseCaseRequest.from_payload(
                medium=medium,
                surface=surface,
                role=role,
                tones=tones,
                languages=languages,
                constraints={"commercial_use": True},
            )
        )
        suggestions = self.recommend(
            task=query,
            language=primary_language,
            commercial_only=True,
            video_only=(medium == "video"),
            count=limit * 2,
            detail_level="full",
        )
        for item in suggestions:
            font_id = item.get("font_id", "")
            if font_id and font_id not in matched:
                matched.append(font_id)
            if len(matched) >= limit:
                break
        return matched

    def _vision_candidate_pool(
        self,
        *,
        medium: str,
        surface: str,
        role: str,
        tones: list[str] | None,
        languages: list[str] | None,
        limit: int = 12,
    ) -> list[dict]:
        query = build_use_case_query(
            UseCaseRequest.from_payload(
                medium=medium,
                surface=surface,
                role=role,
                tones=tones,
                languages=languages,
                constraints={"commercial_use": True},
            )
        )
        primary_language = (languages or [None])[0]
        return self.recommend(
            task=query,
            language=primary_language,
            commercial_only=True,
            video_only=(medium == "video"),
            count=limit,
            detail_level="full",
        )

    def _reference_signal(
        self,
        *,
        font: dict,
        medium: str,
        surface: str,
        role: str,
        tones: list[str] | None,
        languages: list[str] | None,
    ) -> dict:
        font_id = font.get("font_id", "")
        family_key = _normalize_font_key(font.get("family", ""))
        tone_set = set(tones or [])
        language_set = set(languages or [])
        matches: list[dict] = []
        total_score = 0

        for record in self.repository.list_references(status="curated"):
            surface_multiplier = _surface_compatibility(surface, record.surface)
            if surface_multiplier <= 0:
                continue
            base = 0
            if record.medium == medium:
                base += 4
            if record.surface == surface:
                base += 4
            if record.role == role:
                base += 3
            base += min(len(tone_set.intersection(set(record.tones))) * 2, 4)
            base += min(len(language_set.intersection(set(record.languages))) * 1, 2)
            if base <= 0:
                continue
            class_weight = REFERENCE_CLASS_WEIGHTS.get(record.reference_class or "specimen", 0.7)

            support = 0
            reason = ""
            if font_id and font_id in record.candidate_font_ids:
                support = 8
                reason = "reference_candidate_match"
            else:
                for label in record.observed_font_labels:
                    normalized = _normalize_font_key(label)
                    if family_key and normalized and (family_key in normalized or normalized in family_key):
                        support = 6
                        reason = "reference_observed_label_match"
                        break
            if support <= 0:
                continue
            raw_score = base + support
            score = int(round(raw_score * class_weight * surface_multiplier))
            if score <= 0:
                continue
            total_score += score
            matches.append(
                {
                    "reference_id": record.reference_id,
                    "title": record.title,
                    "score": score,
                    "raw_score": raw_score,
                    "reason": reason,
                    "medium": record.medium,
                    "surface": record.surface,
                    "role": record.role,
                    "reference_class": record.reference_class,
                    "class_weight": class_weight,
                    "surface_multiplier": surface_multiplier,
                }
            )

        matches.sort(key=lambda item: (-item["score"], item["title"]))
        return {
            "score": total_score,
            "match_count": len(matches),
            "top_matches": matches[:3],
        }

    def _reference_candidate_pool(
        self,
        *,
        medium: str,
        surface: str,
        role: str,
        tones: list[str] | None,
        languages: list[str] | None,
        limit: int = 10,
    ) -> list[dict]:
        request = UseCaseRequest.from_payload(
            medium=medium,
            surface=surface,
            role=role,
            tones=tones,
            languages=languages,
            constraints={"commercial_use": True},
        )
        tone_set = set(tones or [])
        language_set = set(languages or [])
        scored_ids: list[tuple[int, str]] = []
        seen: set[str] = set()
        for record in self.repository.list_references(status="curated"):
            surface_multiplier = _surface_compatibility(surface, record.surface)
            if surface_multiplier <= 0:
                continue
            base = 0
            if record.medium == medium:
                base += 4
            if record.surface == surface:
                base += 4
            if record.role == role:
                base += 3
            base += min(len(tone_set.intersection(set(record.tones))) * 2, 4)
            base += min(len(language_set.intersection(set(record.languages))) * 1, 2)
            if base <= 0:
                continue
            for font_id in record.candidate_font_ids:
                if not font_id or font_id in seen:
                    continue
                seen.add(font_id)
                weighted_base = int(
                    round(
                        base
                        * REFERENCE_CLASS_WEIGHTS.get(record.reference_class or "specimen", 0.7)
                        * surface_multiplier
                    )
                )
                scored_ids.append((weighted_base, font_id))
        scored_ids.sort(key=lambda item: (-item[0], item[1]))
        pool: list[dict] = []
        for base_score, font_id in scored_ids[:limit * 2]:
            font = self.repository.get_font(font_id)
            if font:
                enriched = self._attach_operational_profiles(asdict(font))
                cohort_profile = cohort_fit_for_request(enriched, request)
                if cohort_profile["fit"] == "avoid":
                    continue
                enriched["cohort_profile"] = cohort_profile
                enriched["reference_seed_score"] = base_score + cohort_profile["score"]
                pool.append(enriched)
                if len(pool) >= limit:
                    break
        return pool

    def search(
        self,
        query: str = "",
        language: Optional[str] = None,
        commercial_only: bool = False,
        video_only: bool = False,
        include_failed: bool = False,
        detail_level: str = "full",
    ) -> list[dict]:
        fonts = self.repository.list_fonts()
        query_tokens = [token.lower() for token in query.split() if token.strip()]
        results = []
        for font in fonts:
            if not include_failed and font.verification_status in {"invalid_archive", "invalid_file", "error"}:
                continue
            haystack = " ".join(
                [
                    font.family,
                    font.source_site,
                    " ".join(font.tags),
                    " ".join(font.recommended_for),
                    " ".join(font.languages),
                ]
            ).lower()
            if query_tokens and not all(token in haystack for token in query_tokens):
                continue
            if language and language not in font.languages:
                continue
            if commercial_only and not font.commercial_use_allowed:
                continue
            if video_only and not font.video_use_allowed:
                continue
            results.append(asdict(font))
        results.sort(
            key=lambda item: (
                -self._search_relevance(item, query_tokens),
                -self._verification_rank(item),
                -self._download_source_rank(item),
                -(item.get("installed_file_count") or 0),
                item["family"],
            )
        )
        return [
            self._serialize_font_result(self._attach_operational_profiles(item), detail_level=detail_level)
            for item in results
        ]

    def recommend(
        self,
        task: str,
        language: Optional[str] = None,
        commercial_only: bool = True,
        video_only: bool = False,
        count: int = 5,
        include_failed: bool = False,
        detail_level: str = "full",
    ) -> list[dict]:
        fonts = self.search(
            query="",
            language=language,
            commercial_only=commercial_only,
            video_only=video_only,
            include_failed=include_failed,
            detail_level="full",
        )
        task_tokens = [token.lower() for token in task.split() if token.strip()]
        scored: list[tuple[int, dict]] = []
        for font in fonts:
            score = 0
            corpus = " ".join(
                font["tags"] + font["recommended_for"] + [font["family"], font["source_site"]]
            ).lower()
            for token in task_tokens:
                if token in corpus:
                    score += 3
            if "title" in font["recommended_for"]:
                score += 1
            if language and language in font["languages"]:
                score += 2
            verification_rank, download_source_rank, installed_file_count = self._quality_rank(font)
            score += verification_rank * 3
            score += download_source_rank * 2
            if installed_file_count:
                score += 1
            enriched = dict(font)
            enriched["score"] = score
            enriched["why"] = self._recommendation_reasons(
                enriched,
                task_tokens=task_tokens,
                language=language,
            )
            scored.append((score, enriched))
        scored.sort(
            key=lambda item: (
                -item[0],
                -self._verification_rank(item[1]),
                -self._download_source_rank(item[1]),
                -(item[1].get("installed_file_count") or 0),
                item[1]["family"],
            )
        )
        return [self._serialize_font_result(item[1], detail_level=detail_level) for item in scored[:count]]

    def _recommendation_reasons(self, font: dict, *, task_tokens: list[str], language: Optional[str]) -> list[str]:
        reasons: list[str] = []
        matched = []
        corpus_parts = font["tags"] + font["recommended_for"] + [font["family"], font["source_site"]]
        corpus = " ".join(corpus_parts).lower()
        for token in task_tokens:
            if token in corpus:
                matched.append(token)
        if matched:
            reasons.append(f"작업 키워드와 직접 맞는 단서: {', '.join(dict.fromkeys(matched))}")
        if font.get("recommended_for"):
            reasons.append(f"주요 용도 태그: {', '.join(font['recommended_for'][:3])}")
        if language and language in font.get("languages", []):
            reasons.append(f"{language} 언어 지원이 확인됨")
        verification_rank, download_source_rank, installed_file_count = self._quality_rank(font)
        if verification_rank >= 3:
            reasons.append("설치 검증이 끝난 폰트")
        elif verification_rank == 2:
            reasons.append("다운로드 경로가 정리된 폰트")
        if download_source_rank >= 2:
            reasons.append("공식 소스 기반 다운로드 경로")
        elif download_source_rank == 1:
            reasons.append("웹폰트 미리보기 경로로 바로 사용 가능")
        if installed_file_count:
            reasons.append(f"설치 확인 파일 수: {installed_file_count}")
        license_profile = font.get("license_profile") or self._license_profile(font)
        automation_profile = font.get("automation_profile") or self._automation_profile(font)
        reasons.append(
            f"라이선스 상태: {license_profile['status']} / confidence={license_profile['confidence']}"
        )
        reasons.append(
            f"자동화 준비도: {automation_profile['status']} / score={automation_profile['score']}"
        )
        reference_signal = font.get("reference_signal") or {}
        if reference_signal.get("match_count"):
            reasons.append(
                f"유사 레퍼런스 {reference_signal['match_count']}건에서 지지됨"
            )
        return reasons[:5]

    def recommend_use_case(
        self,
        *,
        medium: str,
        surface: str,
        role: str,
        tones: list[str] | None = None,
        languages: list[str] | None = None,
        constraints: dict | None = None,
        count: int = 5,
        include_failed: bool = False,
        detail_level: str = "full",
    ) -> dict:
        request = UseCaseRequest.from_payload(
            medium=medium,
            surface=surface,
            role=role,
            tones=tones,
            languages=languages,
            constraints=constraints,
        )
        query = build_use_case_query(request)
        primary_language = request.languages[0] if request.languages else None
        commercial_only = bool(request.constraints.get("commercial_use", True))
        video_only = bool(request.constraints.get("video_use", request.medium == "video"))
        candidates = self.recommend(
            task=query,
            language=primary_language,
            commercial_only=commercial_only,
            video_only=video_only,
            count=max(count * 3, 12),
            include_failed=include_failed,
            detail_level="full",
        )
        reference_candidates = self._reference_candidate_pool(
            medium=request.medium,
            surface=request.surface,
            role=request.role,
            tones=request.tones,
            languages=request.languages,
            limit=max(count * 2, 8),
        )
        seen_candidate_ids = {item["font_id"] for item in candidates}
        for item in reference_candidates:
            if item["font_id"] not in seen_candidate_ids:
                candidates.append(item)
                seen_candidate_ids.add(item["font_id"])

        filtered = []
        for font in candidates:
            if request.constraints.get("web_embedding") and not font["web_embedding_allowed"]:
                continue
            if request.constraints.get("redistribution") and not font["redistribution_allowed"]:
                continue
            filtered.append(font)

        results = []
        preview_preset = preview_preset_for_use_case(request)
        for font in filtered:
            enriched = dict(font)
            cohort_profile = cohort_fit_for_request(enriched, request)
            enriched["cohort_profile"] = cohort_profile
            enriched["score"] = int(enriched.get("score", 0)) + int(cohort_profile["score"])
            reference_signal = self._reference_signal(
                font=enriched,
                medium=request.medium,
                surface=request.surface,
                role=request.role,
                tones=request.tones,
                languages=request.languages,
            )
            raw_reference_score = int(reference_signal["score"])
            fit = cohort_profile["fit"]
            multiplier = 1.0
            if fit == "preferred":
                multiplier = 1.0
            elif fit == "acceptable":
                multiplier = 0.35
            elif fit == "avoid":
                multiplier = 0.15
            elif fit == "neutral":
                multiplier = 0.2
            applied_reference_score = int(raw_reference_score * multiplier)
            reference_signal["raw_score"] = raw_reference_score
            reference_signal["applied_score"] = applied_reference_score
            reference_signal["cohort_multiplier"] = multiplier
            reference_signal["score"] = applied_reference_score
            enriched["reference_signal"] = reference_signal
            enriched["score"] = int(enriched.get("score", 0)) + applied_reference_score
            enriched["use_case"] = {
                "medium": request.medium,
                "surface": request.surface,
                "role": request.role,
                "tones": request.tones,
                "languages": request.languages,
            }
            enriched["preview_preset"] = preview_preset
            enriched["why"] = list(enriched.get("why", [])) + [
                f"매체/표면/역할 기준: {request.medium} / {request.surface} / {request.role}"
            ]
            enriched["why"].append(
                f"유형군 적합도: {cohort_profile['labels'][0]} / {cohort_profile['fit']}"
            )
            if reference_signal["match_count"]:
                enriched["why"].append(
                    f"레퍼런스 기반 지지: {reference_signal['match_count']}건 / applied={reference_signal['applied_score']}"
                )
            enriched["why"] = enriched["why"][:6]
            results.append(self._serialize_font_result(enriched, detail_level=detail_level))

        results.sort(
            key=lambda item: (
                -int(item.get("score", 0)),
                -int((item.get("reference_signal") or {}).get("score", 0)),
                item.get("family", ""),
            )
        )
        results = results[:count]

        return {
            "request": {
                "medium": request.medium,
                "surface": request.surface,
                "role": request.role,
                "tones": request.tones,
                "languages": request.languages,
                "constraints": request.constraints,
            },
            "query": query,
            "preview_preset": preview_preset,
            "results": results,
        }

    def preview(self, font_id: str, preset: str = "title-ko", sample_text: Optional[str] = None) -> dict:
        font = self.repository.get_font(font_id)
        if not font:
            raise KeyError(f"Unknown font: {font_id}")
        output_path = write_preview(font, self.preview_dir, preset=preset, sample_text=sample_text)
        return {
            "font_id": font_id,
            "preset": preset,
            "sample_text": sample_text or "",
            "preview_path": str(output_path),
        }

    def _record_install_verification(self, font_id: str, result: dict) -> None:
        self.repository.update_verification_fields(
            font_id=font_id,
            verification_status=result.get("status", ""),
            verified_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            installed_file_count=len(result.get("installed_files", [])),
            verification_failure_reason=result.get("message", ""),
        )

    def install(self, font_id: str, output_dir: Path, persist_result: bool = True) -> dict:
        font = self.repository.get_font(font_id)
        if not font:
            raise KeyError(f"Unknown font: {font_id}")
        try:
            result = install_font(font, cache_dir=self.cache_dir, output_dir=Path(output_dir))
        except Exception as exc:
            if persist_result:
                self._record_install_verification(
                    font_id,
                    {
                        "status": "error",
                        "font_id": font_id,
                        "message": str(exc),
                        "installed_files": [],
                    },
                )
            raise
        if persist_result:
            self._record_install_verification(font_id, result)
        return result

    def export_css(self, font_id: str) -> dict:
        font = self.repository.get_font(font_id)
        if not font:
            raise KeyError(f"Unknown font: {font_id}")
        css = (
            f"font-family: '{font.family}', 'Apple SD Gothic Neo', sans-serif;\n"
            f"/* license: {font.license_summary} */"
        )
        return {"font_id": font_id, "css": css}

    def export_remotion(self, font_id: str) -> dict:
        font = self.repository.get_font(font_id)
        if not font:
            raise KeyError(f"Unknown font: {font_id}")
        snippet = (
            f"import {{loadFont}} from '@remotion/google-fonts';\n\n"
            f"// FontAgent generated snippet for {font.family}\n"
            f"const fontFamily = '{font.family}';\n"
            f"// If locally installed, register the font file in your Remotion bootstrap.\n"
        )
        return {"font_id": font_id, "remotion": snippet}

    def add_reference(
        self,
        *,
        title: str,
        medium: str,
        surface: str,
        role: str,
        reference_class: str = "",
        reference_scope: str = "shared_public",
        source_kind: str,
        source_url: str = "",
        asset_path: str = "",
        tones: list[str] | None = None,
        languages: list[str] | None = None,
        text_blocks: list[str] | None = None,
        candidate_font_ids: list[str] | None = None,
        observed_font_labels: list[str] | None = None,
        palette: dict | None = None,
        ratio_hint: dict | None = None,
        extraction_method: str = "manual",
        extraction_confidence: float = 0.0,
        status: str = "draft",
        notes: list[str] | None = None,
    ) -> dict:
        now = datetime.now(timezone.utc)
        created_at = now.isoformat().replace("+00:00", "Z")
        reference_id = f"{medium}-{surface}-{role}-{now.strftime('%Y%m%d%H%M%S%f')}"
        payload = {
            "reference_id": reference_id,
            "title": title,
            "medium": medium,
            "surface": surface,
            "role": role,
            "reference_class": reference_class or self._infer_reference_class(source_kind=source_kind, source_url=source_url, title=title),
            "source_kind": source_kind,
            "source_url": source_url,
            "asset_path": str(Path(asset_path).expanduser().resolve()) if asset_path else "",
            "tones": tones or [],
            "languages": languages or [],
            "text_blocks": text_blocks or [],
            "candidate_font_ids": candidate_font_ids or [],
            "observed_font_labels": observed_font_labels or [],
            "palette": palette or {},
            "ratio_hint": ratio_hint or {},
            "extraction_method": extraction_method,
            "extraction_confidence": extraction_confidence,
            "status": status,
            "notes": notes or [],
            "created_at": created_at,
            "reference_scope": reference_scope or "shared_public",
        }
        self.repository.upsert_reference(payload)
        return payload

    def _refresh_reference_note_export(
        self,
        *,
        reference_id: str,
        vault_root: Path | None = None,
        vault_category: str | None = None,
        extraction: dict | None = None,
    ) -> dict | None:
        resolved_vault_root, resolved_vault_category, asset_policy, private_vault_root = self._resolve_reference_export_settings(
            vault_root,
            vault_category,
        )
        if resolved_vault_root is None:
            return None
        reference = self.repository.get_reference(reference_id)
        if reference is None:
            raise ValueError(f"Unknown reference_id: {reference_id}")
        reviews = [asdict(review) for review in self.repository.list_reference_reviews(reference_id=reference_id)]
        if reference.reference_scope == "private_user":
            if private_vault_root is None:
                raise ValueError("private vault root is not configured for private_user references")
            vault_export = export_reference_note(
                vault_root=private_vault_root,
                category_name=resolved_vault_category,
                reference=asdict(reference),
                extraction=extraction,
                reviews=reviews,
                include_assets=True,
                private_asset_root=None,
            )
            index_export = sync_reference_index(
                vault_root=private_vault_root,
                category_name=resolved_vault_category,
                references=[
                    asdict(record)
                    for record in self.repository.list_references(reference_scope="private_user")
                ],
            )
            vault_root_value = private_vault_root
        else:
            vault_export = export_reference_note(
                vault_root=resolved_vault_root,
                category_name=resolved_vault_category,
                reference=asdict(reference),
                extraction=extraction,
                reviews=reviews,
                include_assets=asset_policy == "public_with_assets",
                private_asset_root=private_vault_root,
            )
            index_export = sync_reference_index(
                vault_root=resolved_vault_root,
                category_name=resolved_vault_category,
                references=[
                    asdict(record)
                    for record in self.repository.list_references(reference_scope="shared_public")
                ],
            )
            vault_root_value = resolved_vault_root
        vault_export.update(index_export)
        vault_export["vault_root"] = str(vault_root_value)
        vault_export["vault_category"] = resolved_vault_category
        vault_export["asset_policy"] = asset_policy
        vault_export["private_vault_root"] = str(private_vault_root) if private_vault_root else ""
        return vault_export

    def list_references(
        self,
        *,
        medium: Optional[str] = None,
        surface: Optional[str] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        reference_scope: Optional[str] = None,
    ) -> dict:
        records = self.repository.list_references(
            medium=medium,
            surface=surface,
            role=role,
            status=status,
            reference_scope=reference_scope,
        )
        return {"references": [asdict(record) for record in records]}

    def add_reference_review(
        self,
        *,
        reference_id: str,
        reviewer_kind: str,
        reviewer_name: str,
        model_name: str = "",
        source: str = "",
        summary: str = "",
        candidate_font_ids: list[str] | None = None,
        observed_font_labels: list[str] | None = None,
        cohort_tags: list[str] | None = None,
        confidence: float = 0.0,
        status: str = "curated",
        notes: list[str] | None = None,
        apply_to_reference: bool = True,
        vault_root: Path | None = None,
        vault_category: str | None = None,
    ) -> dict:
        reference = self.repository.get_reference(reference_id)
        if reference is None:
            raise ValueError(f"Unknown reference_id: {reference_id}")

        now = datetime.now(timezone.utc)
        created_at = now.isoformat().replace("+00:00", "Z")
        review_id = f"{reference_id}-review-{now.strftime('%Y%m%d%H%M%S%f')}"
        payload = {
            "review_id": review_id,
            "reference_id": reference_id,
            "reviewer_kind": reviewer_kind,
            "reviewer_name": reviewer_name,
            "model_name": model_name,
            "source": source,
            "summary": summary,
            "candidate_font_ids": candidate_font_ids or [],
            "observed_font_labels": observed_font_labels or [],
            "cohort_tags": cohort_tags or [],
            "confidence": confidence,
            "status": status,
            "notes": notes or [],
            "created_at": created_at,
        }
        self.repository.upsert_reference_review(payload)

        merged_reference = asdict(reference)
        if apply_to_reference:
            merged_candidate_font_ids: list[str] = []
            for font_id in candidate_font_ids or []:
                if font_id and font_id not in merged_candidate_font_ids:
                    merged_candidate_font_ids.append(font_id)
            for font_id in reference.candidate_font_ids:
                if font_id and font_id not in merged_candidate_font_ids:
                    merged_candidate_font_ids.append(font_id)
            merged_observed_labels = list(reference.observed_font_labels)
            for label in observed_font_labels or []:
                if label and label not in merged_observed_labels:
                    merged_observed_labels.append(label)
            merged_notes = list(reference.notes)
            merged_notes.append(
                f"agent_review:{reviewer_kind}:{reviewer_name}:{confidence:.2f}"
            )
            merged_reference["candidate_font_ids"] = merged_candidate_font_ids[:8]
            merged_reference["observed_font_labels"] = merged_observed_labels[:8]
            merged_reference["notes"] = merged_notes[-16:]
            self.repository.upsert_reference(merged_reference)

        vault_export = self._refresh_reference_note_export(
            reference_id=reference_id,
            vault_root=vault_root,
            vault_category=vault_category,
        )
        return {
            "review": payload,
            "reference": asdict(self.repository.get_reference(reference_id)),
            "vault_export": vault_export,
        }

    def list_reference_reviews(
        self,
        *,
        reference_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> dict:
        reviews = self.repository.list_reference_reviews(reference_id=reference_id, status=status)
        return {"reviews": [asdict(review) for review in reviews]}

    def reference_catalog_status(self) -> dict:
        records = self.repository.list_references()
        medium_counts: dict[str, int] = {}
        reference_class_counts: dict[str, int] = {}
        reference_scope_counts: dict[str, int] = {}
        source_kind_counts: dict[str, int] = {}
        status_counts: dict[str, int] = {}
        method_counts: dict[str, int] = {}
        for record in records:
            medium_counts[record.medium] = medium_counts.get(record.medium, 0) + 1
            reference_class_counts[record.reference_class] = reference_class_counts.get(record.reference_class, 0) + 1
            reference_scope_counts[record.reference_scope] = reference_scope_counts.get(record.reference_scope, 0) + 1
            source_kind_counts[record.source_kind] = source_kind_counts.get(record.source_kind, 0) + 1
            status_counts[record.status] = status_counts.get(record.status, 0) + 1
            method_counts[record.extraction_method] = method_counts.get(record.extraction_method, 0) + 1
        return {
            "total_references": len(records),
            "mediums": dict(sorted(medium_counts.items(), key=lambda item: (-item[1], item[0]))),
            "reference_classes": dict(sorted(reference_class_counts.items(), key=lambda item: (-item[1], item[0]))),
            "reference_scopes": dict(sorted(reference_scope_counts.items(), key=lambda item: (-item[1], item[0]))),
            "source_kinds": dict(sorted(source_kind_counts.items(), key=lambda item: (-item[1], item[0]))),
            "statuses": dict(sorted(status_counts.items(), key=lambda item: (-item[1], item[0]))),
            "extraction_methods": dict(sorted(method_counts.items(), key=lambda item: (-item[1], item[0]))),
        }

    def list_reference_packs(self) -> dict:
        return {"packs": list_reference_packs()}

    def sync_reference_index(
        self,
        *,
        vault_root: Path | None = None,
        vault_category: str | None = None,
    ) -> dict:
        resolved_root, resolved_category = self._resolve_reference_vault(vault_root, vault_category)
        if resolved_root is None:
            raise ValueError("reference vault root is not configured")
        references = [
            asdict(record)
            for record in self.repository.list_references(reference_scope="shared_public")
        ]
        export = sync_reference_index(
            vault_root=resolved_root,
            category_name=resolved_category,
            references=references,
        )
        return {
            "vault_root": str(resolved_root),
            "vault_category": resolved_category,
            **export,
        }

    def sanitize_public_reference_vault(
        self,
        *,
        vault_root: Path | None = None,
        vault_category: str | None = None,
        remove_public_assets: bool = True,
    ) -> dict:
        resolved_vault_root, resolved_vault_category, _, private_vault_root = self._resolve_reference_export_settings(
            vault_root,
            vault_category,
        )
        if resolved_vault_root is None:
            raise ValueError("reference vault root is not configured")
        if private_vault_root is None:
            raise ValueError("private reference vault root is not configured")

        migrated: list[dict] = []
        for record in self.repository.list_references(reference_scope="shared_public"):
            reference = asdict(record)
            slug = _reference_note_slug(reference.get("title", "reference"))
            note_root = resolved_vault_root / resolved_vault_category / reference["medium"] / reference["surface"]
            public_screenshot = note_root / "_assets" / f"{slug}.png"
            public_raw = note_root / "_raw" / f"{slug}.json"
            public_review_dir = note_root / "_reviews"
            extraction = None
            if public_screenshot.exists() or public_raw.exists():
                extraction = {
                    "screenshot_path": str(public_screenshot) if public_screenshot.exists() else "",
                    "json_path": str(public_raw) if public_raw.exists() else "",
                }
            reviews = [asdict(review) for review in self.repository.list_reference_reviews(reference_id=record.reference_id)]
            vault_export = export_reference_note(
                vault_root=resolved_vault_root,
                category_name=resolved_vault_category,
                reference=reference,
                extraction=extraction,
                reviews=reviews,
                include_assets=False,
                private_asset_root=private_vault_root,
            )
            migrated.append(
                {
                    "reference_id": record.reference_id,
                    "title": record.title,
                    "note_path": vault_export["note_path"],
                    "private_screenshot_path": vault_export["private_screenshot_path"],
                    "private_raw_json_path": vault_export["private_raw_json_path"],
                    "private_review_paths": vault_export["private_review_paths"],
                }
            )
            if remove_public_assets:
                if public_screenshot.exists():
                    public_screenshot.unlink()
                if public_raw.exists():
                    public_raw.unlink()
                if public_review_dir.exists():
                    for path in public_review_dir.glob(f"{slug}-review-*.json"):
                        path.unlink()
        index_export = sync_reference_index(
            vault_root=resolved_vault_root,
            category_name=resolved_vault_category,
            references=[
                asdict(record)
                for record in self.repository.list_references(reference_scope="shared_public")
            ],
        )
        if remove_public_assets:
            for root_dir, _, filenames in os.walk(resolved_vault_root / resolved_vault_category):
                current = Path(root_dir)
                if current.name in {"_assets", "_raw", "_reviews"} and not filenames and not any(current.iterdir()):
                    shutil.rmtree(current, ignore_errors=True)
        return {
            "migrated": len(migrated),
            "vault_root": str(resolved_vault_root),
            "vault_category": resolved_vault_category,
            "private_vault_root": str(private_vault_root),
            "remove_public_assets": remove_public_assets,
            "references": migrated,
            "index_path": index_export["index_path"],
        }

    def refresh_reference_candidates(
        self,
        *,
        medium: str | None = None,
        surface: str | None = None,
        role: str | None = None,
        status: str | None = "curated",
    ) -> dict:
        records = self.repository.list_references(
            medium=medium,
            surface=surface,
            role=role,
            status=status,
        )
        updated = 0
        details: list[dict] = []
        for record in records:
            candidate_font_ids = self._guess_reference_candidates(
                medium=record.medium,
                surface=record.surface,
                role=record.role,
                tones=list(record.tones),
                languages=list(record.languages),
                observed_labels=list(record.observed_font_labels),
                limit=5,
            )
            payload = asdict(record)
            payload["candidate_font_ids"] = candidate_font_ids
            self.repository.upsert_reference(payload)
            updated += 1
            details.append(
                {
                    "reference_id": record.reference_id,
                    "title": record.title,
                    "candidate_font_ids": candidate_font_ids,
                }
            )
        return {"updated": updated, "references": details}

    def reference_extraction_strategies(
        self,
        *,
        source_kind: str,
        source_url: str = "",
        asset_path: str = "",
    ) -> dict:
        return build_reference_extraction_plan(
            source_kind=source_kind,
            source_url=source_url,
            asset_path=asset_path,
        )

    def extract_web_reference(
        self,
        *,
        title: str,
        url: str,
        medium: str,
        surface: str,
        role: str,
        reference_class: str = "",
        reference_scope: str = "shared_public",
        tones: list[str] | None = None,
        languages: list[str] | None = None,
        vault_root: Path | None = None,
        vault_category: str = "Fonts",
        status: str = "draft",
    ) -> dict:
        resolved_vault_root, resolved_vault_category = self._resolve_reference_vault(vault_root, vault_category)
        extraction_dir = self.root / ".cache" / "references" / _safe_fs_name(title)
        extraction = extract_web_reference_payload(
            root=self.root,
            url=url,
            output_dir=extraction_dir,
        )
        observed_font_labels = list(extraction.get("uniqueFonts") or [])
        text_blocks = [block.get("text", "") for block in extraction.get("textBlocks", []) if block.get("text")]
        candidate_font_ids = self._guess_reference_candidates(
            medium=medium,
            surface=surface,
            role=role,
            tones=tones,
            languages=languages,
            observed_labels=observed_font_labels,
            limit=5,
        )
        reference = self.add_reference(
            title=title,
            medium=medium,
            surface=surface,
            role=role,
            reference_class=reference_class or self._infer_reference_class(source_kind="web_page", source_url=url, title=title),
            reference_scope=reference_scope,
            source_kind="web_page",
            source_url=url,
            tones=tones,
            languages=languages,
            text_blocks=text_blocks[:12],
            candidate_font_ids=candidate_font_ids,
            observed_font_labels=observed_font_labels,
            extraction_method="playwright_dom",
            extraction_confidence=0.82,
            status=status,
            notes=[
                "웹 레퍼런스에서 DOM/CSS를 직접 추출했습니다.",
                f"후보 폰트 추정 {len(candidate_font_ids)}건을 자동 연결했습니다." if candidate_font_ids else "후보 폰트 자동 연결은 아직 비어 있습니다.",
                "OCR/Vision은 아직 후속 단계로 분리돼 있습니다.",
            ],
        )
        vault_export = self._refresh_reference_note_export(
            reference_id=reference["reference_id"],
            vault_root=resolved_vault_root,
            vault_category=resolved_vault_category,
            extraction=extraction,
        )
        return {
            "reference": reference,
            "extraction": extraction,
            "vault_export": vault_export,
        }

    def extract_image_reference(
        self,
        *,
        title: str,
        image_path: Path,
        medium: str,
        surface: str,
        role: str,
        reference_class: str = "",
        reference_scope: str = "shared_public",
        tones: list[str] | None = None,
        languages: list[str] | None = None,
        vault_root: Path | None = None,
        vault_category: str = "Fonts",
        status: str = "draft",
    ) -> dict:
        resolved_vault_root, resolved_vault_category = self._resolve_reference_vault(vault_root, vault_category)
        extraction_dir = self.root / ".cache" / "references" / _safe_fs_name(title)
        extraction = extract_image_reference_payload(
            root=self.root,
            image_path=Path(image_path),
            output_dir=extraction_dir,
        )
        blocks = extraction.get("textBlocks", [])
        text_blocks = [block.get("text", "") for block in blocks if block.get("text")]
        ratio = extraction.get("ratio", 0.0)
        heuristic_candidate_font_ids = self._guess_reference_candidates(
            medium=medium,
            surface=surface,
            role=role,
            tones=tones,
            languages=languages,
            observed_labels=[],
            limit=5,
        )
        vision_guess = guess_reference_fonts_via_vision(
            image_path=Path(image_path),
            candidate_fonts=self._vision_candidate_pool(
                medium=medium,
                surface=surface,
                role=role,
                tones=tones,
                languages=languages,
                limit=12,
            ),
            medium=medium,
            surface=surface,
            role=role,
            tones=tones,
            languages=languages,
            text_blocks=text_blocks[:8],
        )
        candidate_font_ids: list[str] = []
        for font_id in vision_guess.get("candidate_font_ids", []) + heuristic_candidate_font_ids:
            if font_id and font_id not in candidate_font_ids:
                candidate_font_ids.append(font_id)
            if len(candidate_font_ids) >= 5:
                break
        observed_font_labels = list(vision_guess.get("observed_font_labels", []))
        reference = self.add_reference(
            title=title,
            medium=medium,
            surface=surface,
            role=role,
            reference_class=reference_class or self._infer_reference_class(source_kind="image_asset", title=title),
            reference_scope=reference_scope,
            source_kind="image_asset",
            asset_path=str(Path(image_path).expanduser().resolve()),
            tones=tones,
            languages=languages,
            text_blocks=text_blocks[:12],
            candidate_font_ids=candidate_font_ids,
            observed_font_labels=observed_font_labels,
            ratio_hint={
                "width": extraction.get("width", 0),
                "height": extraction.get("height", 0),
                "aspect_ratio": ratio,
            },
            extraction_method="apple_vision_ocr+openai_vision" if vision_guess.get("used") else "apple_vision_ocr",
            extraction_confidence=max(0.66, float(vision_guess.get("confidence", 0.0) or 0.0)),
            status=status,
            notes=[
                "이미지 레퍼런스에서 Apple Vision OCR로 텍스트 블록을 추출했습니다.",
                (
                    f"Vision 추정 후보 {len(vision_guess.get('candidate_font_ids', []))}건을 반영했습니다."
                    if vision_guess.get("used")
                    else f"Vision 추정은 사용되지 않았습니다: {vision_guess.get('reason', 'unavailable')}"
                ),
                f"통합 후보 폰트 {len(candidate_font_ids)}건을 연결했습니다." if candidate_font_ids else "컨텍스트 기반 후보 폰트 연결은 아직 비어 있습니다.",
            ],
        )
        vault_export = self._refresh_reference_note_export(
            reference_id=reference["reference_id"],
            vault_root=resolved_vault_root,
            vault_category=resolved_vault_category,
            extraction=extraction,
        )
        return {
            "reference": reference,
            "extraction": extraction,
            "vision_guess": vision_guess,
            "vault_export": vault_export,
        }

    def learn_reference_pack(
        self,
        *,
        pack_name: str,
        limit: int | None = None,
        vault_root: Path | None = None,
        vault_category: str | None = None,
        continue_on_error: bool = False,
    ) -> dict:
        pack = get_reference_pack(pack_name)
        resolved_vault_root, resolved_vault_category = self._resolve_reference_vault(vault_root, vault_category)
        items = pack["items"][: limit or len(pack["items"])]
        results: list[dict] = []
        failures: list[dict] = []
        for item in items:
            try:
                if item.source_kind != "web_page":
                    raise ValueError(f"unsupported starter pack source_kind: {item.source_kind}")
                outcome = self.extract_web_reference(
                    title=item.title,
                    url=item.source_url,
                    medium=item.medium,
                    surface=item.surface,
                    role=item.role,
                    reference_class=item.reference_class,
                    tones=list(item.tones),
                    languages=list(item.languages),
                    vault_root=resolved_vault_root,
                    vault_category=resolved_vault_category,
                    status=item.status,
                )
                results.append(
                    {
                        "title": item.title,
                        "source_url": item.source_url,
                        "reference_id": outcome["reference"]["reference_id"],
                        "status": "ok",
                    }
                )
            except Exception as exc:
                failures.append(
                    {
                        "title": item.title,
                        "source_url": item.source_url,
                        "status": "error",
                        "message": str(exc),
                    }
                )
                if not continue_on_error:
                    break
        return {
            "pack_name": pack_name,
            "pack_title": pack["title"],
            "attempted": len(results) + len(failures),
            "succeeded": len(results),
            "failed": len(failures),
            "vault_root": str(resolved_vault_root) if resolved_vault_root else "",
            "vault_category": resolved_vault_category,
            "results": results,
            "failures": failures,
        }

    def catalog_status(self) -> dict:
        fonts = self.repository.list_fonts()
        reference_status = self.reference_catalog_status()
        source_counts: dict[str, int] = {}
        verification_counts: dict[str, int] = {}
        language_counts: dict[str, int] = {}
        for font in fonts:
            source_counts[font.source_site] = source_counts.get(font.source_site, 0) + 1
            status = font.verification_status or "unverified"
            verification_counts[status] = verification_counts.get(status, 0) + 1
            for language in font.languages:
                language_counts[language] = language_counts.get(language, 0) + 1

        installed_total = sum(1 for font in fonts if font.verification_status == "installed")
        commercial_total = sum(1 for font in fonts if font.commercial_use_allowed)
        web_embedding_total = sum(1 for font in fonts if font.web_embedding_allowed)
        video_total = sum(1 for font in fonts if font.video_use_allowed)
        return {
            "db_path": str(self.db_path),
            "total_fonts": len(fonts),
            "installed_fonts": installed_total,
            "commercial_fonts": commercial_total,
            "web_embedding_fonts": web_embedding_total,
            "video_fonts": video_total,
            "sources": dict(sorted(source_counts.items(), key=lambda item: (-item[1], item[0]))),
            "verification": dict(sorted(verification_counts.items(), key=lambda item: (-item[1], item[0]))),
            "languages": dict(sorted(language_counts.items(), key=lambda item: (-item[1], item[0]))),
            "references": reference_status,
        }

    def license_policy_catalog(self) -> dict:
        return {
            "sources": {
                key: get_source_license_policy(key)
                for key in sorted(SOURCE_LICENSE_POLICIES)
            }
        }

    def _contract_schema_path(self, name: str) -> Path:
        root_path = self.root / "fontagent" / "schemas" / f"{name}.schema.json"
        if root_path.exists():
            return root_path
        package_path = Path(__file__).resolve().parent / "schemas" / f"{name}.schema.json"
        if package_path.exists():
            return package_path
        raise KeyError(f"Unknown contract schema: {name}")

    def get_contract_schema(self, name: str = "typography-handoff.v1") -> dict:
        path = self._contract_schema_path(name)
        return {
            "name": name,
            "path": str(path),
            "schema": json.loads(path.read_text(encoding="utf-8")),
        }

    def bootstrap_project_integration(
        self,
        *,
        project_path: Path,
        use_case: str = "documentary-landing-ko",
        language: str = "ko",
        target: str = "both",
        asset_dir: str = "assets/fonts",
        include_codex_skill: bool = True,
    ) -> dict:
        return bootstrap_project(
            fontagent_root=self.root,
            project_path=project_path,
            use_case=use_case,
            language=language,
            target=target,
            asset_dir=asset_dir,
            include_codex_skill=include_codex_skill,
        )

    def list_use_cases(self) -> dict:
        return {"use_cases": USE_CASE_PRESETS}

    def list_interview_catalog(self) -> dict:
        return {"categories": list_interview_catalog()}

    def _effective_task(self, task: str, use_case: Optional[str]) -> str:
        effective_task = task.strip()
        if use_case:
            preset = get_use_case_preset(use_case)
            suffix = preset["task_suffix"]
            effective_task = f"{effective_task} {suffix}".strip()
        if not effective_task:
            raise ValueError("task 또는 use_case 중 하나는 필요합니다.")
        return effective_task

    def _role_query_suffix(self, role: str, use_case: Optional[str]) -> str:
        if use_case:
            preset = get_use_case_preset(use_case)
            role_queries = preset.get("role_queries") or {}
            if role in role_queries:
                return str(role_queries[role]).strip()
        defaults = {
            "title": "korean title display poster thumbnail",
            "subtitle": "korean subtitle readable sans",
            "body": "korean body readable editorial",
        }
        return defaults[role]

    def _role_request_for_use_case(
        self,
        *,
        role: str,
        use_case: Optional[str],
        language: str,
    ) -> UseCaseRequest | None:
        if not use_case:
            return None
        preset = get_use_case_preset(use_case)
        tones = list(preset.get("tones") or [])
        medium = str(preset.get("medium") or "").strip().lower()
        surface = str(preset.get("surface") or "").strip().lower()
        role_name = role
        if role == "subtitle":
            if medium == "video":
                surface = "subtitle_track"
            tones = list(dict.fromkeys(tones + ["readable", "clean"]))
        elif role == "body":
            medium = "document"
            surface = "body_copy"
            tones = list(dict.fromkeys(tones + ["readable", "editorial", "clean"]))
        return UseCaseRequest.from_payload(
            medium=medium,
            surface=surface,
            role=role_name,
            tones=tones,
            languages=[language],
            constraints={"commercial_use": True},
        )

    def _select_role_fonts(self, effective_task: str, language: str, use_case: Optional[str] = None) -> dict[str, dict]:
        title_candidates = self.recommend(
            task=f"{effective_task} {self._role_query_suffix('title', use_case)}".strip(),
            language=language,
            count=20,
        )
        subtitle_candidates = self.recommend(
            task=f"{effective_task} {self._role_query_suffix('subtitle', use_case)}".strip(),
            language=language,
            count=20,
        )
        body_candidates = self.recommend(
            task=f"{effective_task} {self._role_query_suffix('body', use_case)}".strip(),
            language=language,
            count=20,
        )

        used_ids: set[str] = set()

        def pick(role: str, candidates: list[dict], fallback: list[dict]) -> dict:
            merged: dict[str, dict] = {}
            request = self._role_request_for_use_case(role=role, use_case=use_case, language=language)
            for item in candidates + fallback:
                merged.setdefault(item["font_id"], item)
            ranked = sorted(
                merged.values(),
                key=lambda item: (
                    -(cohort_fit_for_request(item, request)["score"] if request else 0),
                    -self._role_fit_score(item, role),
                    -self._verification_rank(item),
                    -self._download_source_rank(item),
                    -(item.get("installed_file_count") or 0),
                    item["family"],
                ),
            )
            for item in ranked:
                if item["font_id"] not in used_ids:
                    used_ids.add(item["font_id"])
                    return item
            raise ValueError("추천 가능한 폰트를 찾지 못했습니다.")

        all_fonts = self.search(language=language, commercial_only=True)
        return {
            "title": pick("title", title_candidates, all_fonts),
            "subtitle": pick("subtitle", subtitle_candidates, all_fonts),
            "body": pick("body", body_candidates, all_fonts),
        }

    def _summarize_role_fonts(self, role_fonts: dict[str, dict]) -> dict[str, dict]:
        summarized: dict[str, dict] = {}
        for role, font in role_fonts.items():
            summarized[role] = {
                "font_id": font["font_id"],
                "family": font["family"],
                "source_site": font["source_site"],
                "license_summary": font["license_summary"],
                "recommended_for": font["recommended_for"],
                "tags": font["tags"],
                "generic_family": guess_generic_family(font["tags"]),
                "defaults": role_defaults(role),
            }
        return summarized

    def guided_interview_recommend(
        self,
        *,
        category: str,
        subcategory: str,
        answers: dict | None = None,
        language: str = "ko",
        count: int = 6,
        include_failed: bool = False,
        detail_level: str = "full",
        include_canvas: bool = True,
        include_font_system_preview: bool = True,
    ) -> dict:
        plan = build_interview_plan(category, subcategory, answers=answers, language=language)
        request = plan["request"]
        recommendation = self.recommend_use_case(
            medium=request["medium"],
            surface=request["surface"],
            role=request["role"],
            tones=request["tones"],
            languages=request["languages"],
            constraints=request["constraints"],
            count=count,
            include_failed=include_failed,
            detail_level=detail_level,
        )
        payload = {
            "category": plan["category"],
            "category_label": plan["category_label"],
            "subcategory": plan["subcategory"],
            "subcategory_label": plan["subcategory_label"],
            "interview_summary": plan["interview_summary"],
            "request": recommendation["request"],
            "query": recommendation["query"],
            "preview_preset": recommendation["preview_preset"],
            "recommended_copy": plan["recommended_copy"],
            "results": recommendation["results"],
        }
        if include_canvas:
            payload["canvas"] = plan["canvas"]
        if include_font_system_preview:
            role_fonts = self._summarize_role_fonts(self._select_role_fonts(recommendation["query"], language))
            payload["font_system_preview"] = {
                "roles": role_fonts,
                "notes": [
                    "이 조합은 실제 프로젝트 파일을 아직 쓰지 않는 draft font system입니다.",
                    "가운데 캔버스는 기본 타이포 레이아웃 구조를 보여주고, 실제 후보 비교는 결과 카드에서 진행합니다.",
                ],
            }
        return payload

    def prepare_font_system(
        self,
        *,
        project_path: Path,
        task: str,
        language: str = "ko",
        target: str = "both",
        asset_dir: str = "assets/fonts",
        use_case: Optional[str] = None,
        with_templates: bool = False,
    ) -> dict:
        if target not in {"web", "remotion", "both"}:
            raise ValueError("target must be one of: web, remotion, both")

        project_path = Path(project_path)
        output_dir = project_path / "fontagent"
        asset_root = project_path / asset_dir
        effective_task = self._effective_task(task, use_case)
        role_fonts = self._select_role_fonts(effective_task, language, use_case=use_case)

        role_assets: dict[str, dict] = {}
        for role, font in role_fonts.items():
            install_result = self.install(font["font_id"], asset_root / font["font_id"])
            match_hint = " ".join(
                value
                for value in (
                    font.get("family", ""),
                    font.get("font_id", ""),
                    font.get("slug", ""),
                )
                if value
            )
            asset_path = pick_preferred_file(install_result["installed_files"], role, family_hint=match_hint)
            role_assets[role] = {
                "font_id": font["font_id"],
                "family": font["family"],
                "asset_path": asset_path,
                "recommended_for": font["recommended_for"],
                "tags": font["tags"],
                "generic_family": guess_generic_family(font["tags"]),
                "defaults": role_defaults(role),
            }

        manifest_path = write_font_system_manifest(
            output_dir / "font-system.json",
            task=effective_task,
            language=language,
            target=target,
            use_case=use_case,
            role_assets=role_assets,
        )

        outputs = {
            "manifest_path": str(manifest_path),
            "project_path": str(project_path),
            "target": target,
            "use_case": use_case or "",
            "task": effective_task,
            "roles": role_assets,
        }

        if target in {"web", "both"}:
            css_path = render_css_token_file(output_dir / "fonts.css", role_assets)
            outputs["css_path"] = str(css_path)
        if target in {"remotion", "both"}:
            remotion_path = render_remotion_token_file(output_dir / "remotion-font-system.ts", role_assets)
            outputs["remotion_path"] = str(remotion_path)
        if with_templates:
            outputs["template_bundle"] = write_template_bundle(output_dir / "templates", manifest_path)
        return outputs

    def generate_template_bundle(
        self,
        *,
        project_path: Path,
        task: str,
        language: str = "ko",
        target: str = "both",
        asset_dir: str = "assets/fonts",
        use_case: Optional[str] = None,
    ) -> dict:
        return self.prepare_font_system(
                project_path=project_path,
                task=task,
                language=language,
                target=target,
                asset_dir=asset_dir,
            use_case=use_case,
            with_templates=True,
        )

    def generate_typography_handoff(
        self,
        *,
        project_path: Path,
        task: str,
        language: str = "ko",
        target: str = "both",
        asset_dir: str = "assets/fonts",
        use_case: Optional[str] = None,
    ) -> dict:
        result = self.prepare_font_system(
            project_path=project_path,
            task=task,
            language=language,
            target=target,
            asset_dir=asset_dir,
            use_case=use_case,
            with_templates=False,
        )
        preset = get_use_case_preset(use_case) if use_case else {}
        roles: dict[str, dict] = {}
        license_notes: list[str] = []
        for role_name, asset in result["roles"].items():
            font = self.repository.get_font(asset["font_id"])
            roles[role_name] = {
                "font_id": asset["font_id"],
                "family": asset["family"],
                "source_site": font.source_site if font else "",
                "license_summary": font.license_summary if font else "",
                "generic_family": asset["generic_family"],
                "defaults": asset["defaults"],
                "tags": asset["tags"],
                "recommended_for": asset["recommended_for"],
                "asset_path": asset["asset_path"],
            }
            if font:
                license_notes.append(
                    f"{role_name}: {font.family} / {font.license_summary} / commercial={font.commercial_use_allowed} / web_embedding={font.web_embedding_allowed} / redistribution={font.redistribution_allowed}"
                )

        medium = preset.get("medium", "")
        surface = preset.get("surface", "")
        tones = preset.get("tones", [])
        primary_role = preset.get("role", "title")
        hints = {
            "type_scale": self._type_scale_hints(medium, surface, primary_role),
            "contrast": self._contrast_hints(medium, surface, tones),
            "ratio": self._ratio_hints(medium, surface),
        }
        guidance = [
            f"Title은 {roles['title']['family']} 중심으로 가장 강한 위계를 가진다.",
            f"Subtitle은 {roles['subtitle']['family']}로 정보 전달과 보조 헤드라인을 담당한다.",
            f"Body는 {roles['body']['family']}로 긴 문단과 설명 블록을 담당한다.",
        ]
        if medium == "video":
            guidance.append("영상 썸네일/타이틀에서는 Title을 짧고 압축적으로 유지하고 Subtitle을 보조 설명에만 사용한다.")
        if medium == "web":
            guidance.append("웹 랜딩에서는 Hero title, section lead, body copy를 명확히 분리하고 line-height를 넉넉히 유지한다.")
        if medium == "print":
            guidance.append("인쇄물과 포스터에서는 Title 크기와 tracking 대비를 크게 두고 Body는 보조 서사에만 사용한다.")

        return {
            "contract_version": "typography-handoff.v1",
            "schema_name": "typography-handoff.v1",
            "schema_path": str(self._contract_schema_path("typography-handoff.v1")),
            "task": result["task"],
            "language": language,
            "use_case": use_case or "",
            "medium": medium,
            "surface": surface,
            "primary_role": primary_role,
            "tones": tones,
            "project_path": result["project_path"],
            "font_system": {
                "manifest_path": result["manifest_path"],
                "css_path": result.get("css_path", ""),
                "remotion_path": result.get("remotion_path", ""),
                "roles": roles,
            },
            "hints": hints,
            "guidance": guidance,
            "license_notes": license_notes,
            "design_agent_handoff": {
                "medium": medium,
                "surface": surface,
                "primary_role": primary_role,
                "tones": tones,
                "recommended_layout_focus": "typography-first",
                "collaboration_boundary": {
                    "font_agent_owns": [
                        "font recommendation",
                        "license review",
                        "font system roles",
                        "type defaults",
                    ],
                    "design_agent_owns": [
                        "layout composition",
                        "color system",
                        "grid and spacing",
                        "final visual hierarchy",
                    ],
                },
                "notes": [
                    "FontAgent는 타이포 시스템과 라이선스 판단까지 담당하고, 최종 레이아웃과 컬러는 디자인 에이전트가 맡는다.",
                    "선택된 폰트 역할과 defaults를 유지한 채 레이아웃/컬러만 확장하는 것이 기본 원칙이다.",
                ],
            },
        }

    def _type_scale_hints(self, medium: str, surface: str, primary_role: str) -> dict:
        if medium == "video" and surface == "thumbnail":
            return {
                "title_to_subtitle_ratio": "3.2:1",
                "subtitle_to_body_ratio": "1.4:1",
                "notes": [
                    "썸네일 title은 4~6단어 이내가 가장 안정적입니다.",
                    "subtitle은 title의 28%~34% 크기 범위를 권장합니다.",
                ],
            }
        if medium == "web" and surface == "landing_hero":
            return {
                "title_to_subtitle_ratio": "2.6:1",
                "subtitle_to_body_ratio": "1.35:1",
                "notes": [
                    "hero title은 subtitle 대비 2.4~2.8배가 안정적입니다.",
                    "body copy는 65~85자 폭과 넉넉한 line-height를 우선합니다.",
                ],
            }
        if medium == "print" and surface == "poster_headline":
            return {
                "title_to_subtitle_ratio": "3.6:1",
                "subtitle_to_body_ratio": "1.5:1",
                "notes": [
                    "포스터는 title 비율을 크게 벌리고 body는 보조 설명으로만 사용합니다.",
                ],
            }
        return {
            "title_to_subtitle_ratio": "2.4:1",
            "subtitle_to_body_ratio": "1.3:1",
            "notes": [
                f"{primary_role} 중심 구조에서는 역할 간 크기 차이를 분명히 유지합니다.",
            ],
        }

    def _contrast_hints(self, medium: str, surface: str, tones: list[str]) -> dict:
        high_impact = medium in {"video", "print"} or surface in {"thumbnail", "poster_headline"}
        editorial = "editorial" in tones
        return {
            "recommended_mode": "high-contrast" if high_impact else "balanced-contrast",
            "background_guidance": (
                "짙은 배경 위 밝은 title 또는 밝은 배경 위 짙은 title처럼 큰 대비를 우선합니다."
                if high_impact
                else "본문 가독성을 해치지 않는 중간 대비를 우선합니다."
            ),
            "notes": [
                "제목은 배경과 즉시 분리될 정도의 명도 대비를 확보합니다.",
                "본문은 과한 채도 대비보다 안정적인 명도 대비를 우선합니다.",
                "에디토리얼 톤에서는 저채도 배경 + 선명한 title 조합이 유리합니다." if editorial else "강한 display 톤에서는 title 면적 대비를 먼저 확인합니다.",
            ],
        }

    def _ratio_hints(self, medium: str, surface: str) -> dict:
        if medium == "video" and surface == "thumbnail":
            return {
                "canvas_ratio": "16:9",
                "title_block_width": "38%~52%",
                "notes": [
                    "썸네일 title 블록은 좌우 중 한쪽에 몰아 배치하는 편이 안정적입니다.",
                ],
            }
        if medium == "web" and surface == "landing_hero":
            return {
                "canvas_ratio": "desktop responsive",
                "title_block_width": "42%~58%",
                "notes": [
                    "hero는 title 블록과 supporting panel을 6:4 안팎으로 나누는 편이 안정적입니다.",
                ],
            }
        if medium == "print" and surface == "poster_headline":
            return {
                "canvas_ratio": "3:4 or A-series",
                "title_block_width": "55%~72%",
                "notes": [
                    "포스터 title은 상단 1/3 지점에 큰 면적으로 두는 편이 강합니다.",
                ],
            }
        return {
            "canvas_ratio": "context dependent",
            "title_block_width": "45%~60%",
            "notes": [
                "레이아웃 비율은 title이 먼저 읽히는 구조를 우선합니다.",
            ],
        }

    def _guess_format_from_url(self, url: str) -> str:
        lower = url.lower()
        for ext in ("ttf", "otf", "woff2", "woff", "zip"):
            if f".{ext}" in lower:
                return ext
        return "html" if url else ""

    def _guess_download_source(self, download_url: str, download_type: str, current_value: str = "") -> str:
        return current_value or infer_download_source(download_url, download_type)

    def resolve_download(self, font_id: str, persist: bool = True) -> dict:
        font = self.repository.get_font(font_id)
        if not font:
            raise KeyError(f"Unknown font: {font_id}")
        result = resolve_download(asdict(font))
        if persist and result.status == "resolved" and result.resolved_url:
            self.repository.update_download_fields(
                font_id=font_id,
                download_type=result.download_type,
                download_url=result.resolved_url,
                download_source=result.download_source,
                format=self._guess_format_from_url(result.resolved_url),
            )
        return {
            "font_id": font_id,
            "status": result.status,
            "download_type": result.download_type,
            "resolved_url": result.resolved_url,
            "download_source": result.download_source,
            "notes": result.notes,
        }

    def refresh_download_resolutions(self, source_site: Optional[str] = None) -> dict:
        fonts = self.repository.list_fonts()
        if source_site:
            fonts = [font for font in fonts if font.source_site == source_site]

        checked = 0
        resolved = 0
        browser_required = 0
        manual_required = 0
        updated: list[dict] = []

        for font in fonts:
            if font.download_type not in {"html_button", "manual_only"}:
                continue
            checked += 1
            result = self.resolve_download(font.font_id, persist=True)
            if result["status"] == "resolved":
                resolved += 1
                updated.append(
                    {
                        "font_id": font.font_id,
                        "download_type": result["download_type"],
                        "resolved_url": result["resolved_url"],
                        "download_source": result["download_source"],
                    }
                )
            elif result["status"] == "browser_required":
                browser_required += 1
            else:
                manual_required += 1

        return {
            "checked": checked,
            "resolved": resolved,
            "browser_required": browser_required,
            "manual_required": manual_required,
            "updated": updated,
        }

    def prepare_browser_download_task(self, font_id: str, output_dir: Path) -> dict:
        font = self.repository.get_font(font_id)
        if not font:
            raise KeyError(f"Unknown font: {font_id}")
        output_path = write_browser_download_task(asdict(font), output_dir=Path(output_dir))
        return {"font_id": font_id, "task_path": str(output_path)}

    def prepare_source_browser_task(self, source_page_url: str, output_dir: Path) -> dict:
        output_path = write_source_browser_task(source_page_url, output_dir=Path(output_dir))
        return {"source_page_url": source_page_url, "task_path": str(output_path)}

    def normalize_download_sources(self, source_site: Optional[str] = None, overwrite: bool = False) -> dict:
        fonts = self.repository.list_fonts()
        if source_site:
            fonts = [font for font in fonts if font.source_site == source_site]

        checked = 0
        updated = 0
        details: list[dict] = []
        for font in fonts:
            checked += 1
            inferred = self._guess_download_source(font.download_url, font.download_type, "" if overwrite else font.download_source)
            if inferred == font.download_source:
                continue
            self.repository.update_download_fields(
                font_id=font.font_id,
                download_type=font.download_type,
                download_url=font.download_url,
                download_source=inferred,
                format=font.format,
            )
            updated += 1
            details.append(
                {
                    "font_id": font.font_id,
                    "family": font.family,
                    "download_type": font.download_type,
                    "download_source": inferred,
                }
            )

        return {
            "checked": checked,
            "updated": updated,
            "items": details,
        }

    def discover_web_candidates(
        self,
        queries: Optional[list[str]] = None,
        limit_per_query: int = 10,
        blocked_domains: Optional[list[str]] = None,
    ) -> dict:
        discovered = discover_web_candidates(
            queries=queries,
            limit_per_query=limit_per_query,
            blocked_domains=set(blocked_domains or []),
        )
        inserted = self.repository.upsert_candidates(discovered)
        return {
            "queries": queries or [],
            "discovered": len(discovered),
            "stored": inserted,
            "results": discovered,
        }

    def seed_curated_candidates(self, profile: str) -> dict:
        candidates = get_curated_candidates(profile)
        inserted = self.repository.upsert_candidates(candidates)
        return {
            "profile": profile,
            "stored": inserted,
            "results": candidates,
        }

    def list_candidates(
        self,
        status: Optional[str] = None,
        discovery_source: Optional[str] = None,
    ) -> dict:
        candidates = self.repository.list_candidates(
            status=status,
            discovery_source=discovery_source,
        )
        return {
            "count": len(candidates),
            "results": [asdict(candidate) for candidate in candidates],
        }

    def _mark_imported_candidates(self, imported_urls: list[str]) -> None:
        candidate_map = imported_candidate_urls_for_sources()
        for url in imported_urls:
            normalized = url
            if normalized not in candidate_map:
                continue
            status, note = candidate_map[normalized]
            self.repository.update_candidate_status(normalized, status=status, note=note)

    def import_naver_fonts(self, source_page_url: str = "https://hangeul.naver.com/font/nanum") -> dict:
        records = fetch_naver_fonts(source_page_url=source_page_url)
        imported = self.repository.upsert_many(records)
        self._mark_imported_candidates(["https://hangeul.naver.com/font"])
        return {
            "source": "naver_hangeul",
            "source_page_url": source_page_url,
            "imported": imported,
        }

    def import_goodchoice_fonts(self, source_page_url: str = "https://www.goodchoice.kr/font/mobile") -> dict:
        records = fetch_goodchoice_fonts(source_page_url=source_page_url)
        imported = self.repository.upsert_many(records)
        self._mark_imported_candidates(["https://www.goodchoice.kr/font/mobile"])
        return {
            "source": "goodchoice_brand",
            "source_page_url": source_page_url,
            "imported": imported,
        }

    def import_google_display_fonts(self, source_page_url: str = "https://fonts.google.com/") -> dict:
        records = fetch_google_display_fonts(source_page_url=source_page_url)
        imported = self.repository.upsert_many(records)
        return {
            "source": "google_display",
            "source_page_url": source_page_url,
            "imported": imported,
        }

    def import_cafe24_fonts(self, source_page_url: str = "https://www.cafe24.com/story/use/cafe24pro_font.html") -> dict:
        records = fetch_cafe24_fonts(source_page_url=source_page_url)
        imported = self.repository.upsert_many(records)
        self._mark_imported_candidates(["https://www.cafe24.com/story/use/cafe24pro_font.html"])
        return {
            "source": "cafe24_brand",
            "source_page_url": source_page_url,
            "imported": imported,
        }

    def import_jeju_fonts(self, source_page_url: str = "https://www.jeju.go.kr/jeju/symbol/font/infor.htm") -> dict:
        records = fetch_jeju_fonts(source_page_url=source_page_url)
        imported = self.repository.upsert_many(records)
        self._mark_imported_candidates(["https://www.jeju.go.kr/jeju/font.htm", "https://www.jeju.go.kr/jeju/symbol/font/infor.htm"])
        return {
            "source": "jeju_official",
            "source_page_url": source_page_url,
            "imported": imported,
        }

    def import_league_fonts(self) -> dict:
        records = fetch_league_fonts()
        imported = self.repository.upsert_many(records)
        self._mark_imported_candidates(["https://www.theleagueofmoveabletype.com/"])
        return {
            "source": "league_movable_type",
            "source_page_url": "https://www.theleagueofmoveabletype.com/",
            "imported": imported,
        }

    def import_velvetyne_fonts(self) -> dict:
        records = fetch_velvetyne_fonts()
        imported = self.repository.upsert_many(records)
        self._mark_imported_candidates(["https://velvetyne.fr/"])
        return {
            "source": "velvetyne_display",
            "source_page_url": "https://velvetyne.fr/",
            "imported": imported,
        }

    def import_fontshare_fonts(self, api_url: str = "https://api.fontshare.com/v2/fonts") -> dict:
        records = fetch_fontshare_fonts(api_url=api_url)
        imported = self.repository.upsert_many(records)
        self._mark_imported_candidates(["https://www.fontshare.com/"])
        return {
            "source": "fontshare_display",
            "source_page_url": "https://www.fontshare.com/",
            "imported": imported,
        }

    def import_gmarket_fonts(self, source_page_url: str = "https://gds.gmarket.co.kr/") -> dict:
        records = fetch_gmarket_fonts(source_page_url=source_page_url)
        imported = self.repository.upsert_many(records)
        self._mark_imported_candidates(["https://gds.gmarket.co.kr/"])
        return {
            "source": "gmarket_brand",
            "source_page_url": source_page_url,
            "imported": imported,
        }

    def import_nexon_fonts(self, source_page_url: str = "https://brand.nexon.com/brand/fonts") -> dict:
        records = fetch_nexon_fonts(source_page_url=source_page_url)
        imported = self.repository.upsert_many(records)
        self._mark_imported_candidates(["https://brand.nexon.com/brand/fonts"])
        return {
            "source": "nexon_brand",
            "source_page_url": source_page_url,
            "imported": imported,
        }

    def import_woowahan_fonts(self, source_page_url: str = "https://www.woowahan.com/fonts") -> dict:
        records = fetch_woowahan_fonts(source_page_url=source_page_url)
        imported = self.repository.upsert_many(records)
        self._mark_imported_candidates(["https://www.woowahan.com/fonts"])
        return {
            "source": "woowahan_brand",
            "source_page_url": source_page_url,
            "imported": imported,
        }

    def import_hancom_fonts(self, source_page_url: str = "https://font.hancom.com/pc/main/main.php") -> dict:
        records = fetch_hancom_fonts(source_page_url=source_page_url)
        imported = self.repository.upsert_many(records)
        self._mark_imported_candidates(["https://font.hancom.com/pc/main/main.php"])
        return {
            "source": "hancom",
            "source_page_url": source_page_url,
            "imported": imported,
        }

    def import_fonco_fonts(
        self,
        source_page_url: str = "https://font.co.kr/collection/freeFont",
        limit: Optional[int] = None,
    ) -> dict:
        records = fetch_fonco_free_fonts(source_page_url=source_page_url, limit=limit)
        imported = self.repository.upsert_many(records)
        self._mark_imported_candidates(["https://font.co.kr/collection/freeFont"])
        return {
            "source": "fonco_freefont",
            "source_page_url": source_page_url,
            "imported": imported,
        }

    def import_gongu_fonts(
        self,
        source_page_url: str = "https://gongu.copyright.or.kr/gongu/bbs/B0000018/list.do?menuNo=200195",
        max_pages: Optional[int] = None,
    ) -> dict:
        records = fetch_gongu_fonts(source_page_url=source_page_url, max_pages=max_pages)
        imported = self.repository.upsert_many(records)
        self._mark_imported_candidates(["https://gongu.copyright.or.kr/gongu/bbs/B0000018/list.do?menuNo=200195"])
        return {
            "source": "gongu_freefont",
            "source_page_url": source_page_url,
            "imported": imported,
        }

    def normalize_candidate_statuses(self) -> dict:
        candidates = self.repository.list_candidates()
        updated = 0
        items: list[dict] = []
        for candidate in candidates:
            status, note = classify_candidate_status(candidate.domain)
            if status == candidate.status and note == candidate.note:
                continue
            self.repository.update_candidate_status(
                normalized_url=candidate.normalized_url,
                status=status,
                note=note,
            )
            updated += 1
            items.append(
                {
                    "candidate_id": candidate.candidate_id,
                    "domain": candidate.domain,
                    "status": status,
                }
            )
        return {
            "checked": len(candidates),
            "updated": updated,
            "items": items,
        }

    def verify_installations(self, output_dir: Path, source_site: Optional[str] = None) -> dict:
        fonts = self.repository.list_fonts()
        if source_site:
            fonts = [font for font in fonts if font.source_site == source_site]
        fonts = [font for font in fonts if font.download_type in {"zip_file", "direct_file"}]

        results = []
        status_counts: dict[str, int] = {}
        for font in fonts:
            target_dir = Path(output_dir) / font.font_id
            try:
                result = self.install(font.font_id, target_dir, persist_result=True)
            except Exception as exc:
                result = {
                    "status": "error",
                    "font_id": font.font_id,
                    "message": str(exc),
                    "installed_files": [],
                }
                self._record_install_verification(font.font_id, result)
            status = result.get("status", "error")
            status_counts[status] = status_counts.get(status, 0) + 1
            results.append(
                {
                    "font_id": font.font_id,
                    "family": font.family,
                    "download_type": font.download_type,
                    "status": status,
                    "installed_file_count": len(result.get("installed_files", [])),
                    "message": result.get("message", ""),
                }
            )

        return {
            "checked": len(fonts),
            "output_dir": str(Path(output_dir)),
            "status_counts": status_counts,
            "results": results,
        }

    def import_noonnu(self, listing_html: Path, detail_dir: Path) -> dict:
        listing = Path(listing_html).read_text(encoding="utf-8")
        summaries = parse_listing_html(listing)
        records = []
        for summary in summaries:
            detail_path = Path(detail_dir) / f"{summary.slug}.html"
            if not detail_path.exists():
                continue
            detail_html = detail_path.read_text(encoding="utf-8")
            detail = parse_detail_html(
                detail_html,
                slug=summary.slug,
                source_page_url=summary.source_page_url,
                family_hint=summary.family,
            )
            records.append(detail.to_font_record())
        inserted = self.repository.upsert_many(records)
        return {"imported": inserted, "source": "noonnu", "detail_dir": str(detail_dir)}

    def fetch_and_import_noonnu(
        self,
        listing_url: str,
        output_dir: Path,
        limit: int = 20,
    ) -> dict:
        snapshot = fetch_noonnu_snapshot(
            listing_url=listing_url,
            output_dir=output_dir,
            limit=limit,
        )
        imported = self.import_noonnu(
            listing_html=Path(snapshot["listing_path"]),
            detail_dir=Path(snapshot["detail_dir"]),
        )
        return {
            "listing_path": snapshot["listing_path"],
            "detail_dir": snapshot["detail_dir"],
            "fetched_details": snapshot["fetched_details"],
            "imported": imported["imported"],
        }
