from __future__ import annotations

import json
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
from .preview import write_preview
from .project_bootstrap import bootstrap_project
from .repository import FontRepository
from .resolver import (
    infer_download_source,
    resolve_download,
    write_browser_download_task,
    write_source_browser_task,
)
from .template_bundle import write_template_bundle
from .use_cases import UseCaseRequest, build_use_case_query, preview_preset_for_use_case
from .use_cases import USE_CASE_PRESETS, get_use_case_preset


class FontAgentService:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.db_path = self.root / "fontagent.db"
        self.cache_dir = self.root / ".cache" / "downloads"
        self.preview_dir = self.root / ".cache" / "previews"
        self.repository = FontRepository(self.db_path)

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
        if "why" in item:
            compact["why"] = list(item.get("why", []))[:4]
        if "preview_preset" in item:
            compact["preview_preset"] = item["preview_preset"]
        if "use_case" in item:
            compact["use_case"] = item["use_case"]
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

        filtered = []
        for font in candidates:
            if request.constraints.get("web_embedding") and not font["web_embedding_allowed"]:
                continue
            if request.constraints.get("redistribution") and not font["redistribution_allowed"]:
                continue
            filtered.append(font)

        results = []
        preview_preset = preview_preset_for_use_case(request)
        for font in filtered[:count]:
            enriched = dict(font)
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
            enriched["why"] = enriched["why"][:6]
            results.append(self._serialize_font_result(enriched, detail_level=detail_level))

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

    def catalog_status(self) -> dict:
        fonts = self.repository.list_fonts()
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

    def _select_role_fonts(self, effective_task: str, language: str) -> dict[str, dict]:
        title_candidates = self.recommend(
            task=f"{effective_task} korean title display poster thumbnail",
            language=language,
            count=20,
        )
        subtitle_candidates = self.recommend(
            task=f"{effective_task} korean subtitle readable sans",
            language=language,
            count=20,
        )
        body_candidates = self.recommend(
            task=f"{effective_task} korean body readable editorial",
            language=language,
            count=20,
        )

        used_ids: set[str] = set()

        def pick(role: str, candidates: list[dict], fallback: list[dict]) -> dict:
            merged: dict[str, dict] = {}
            for item in candidates + fallback:
                merged.setdefault(item["font_id"], item)
            ranked = sorted(
                merged.values(),
                key=lambda item: (
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
        role_fonts = self._select_role_fonts(effective_task, language)

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
