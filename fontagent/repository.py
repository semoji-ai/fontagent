from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .db import connect, initialize
from .models import FontCandidate, FontRecord, FontReference, FontReferenceReview


class FontRepository:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def init_db(self) -> None:
        initialize(self.db_path)

    def seed_from_json(self, json_path: Path) -> int:
        self.init_db()
        data = json.loads(Path(json_path).read_text(encoding="utf-8"))
        return self.upsert_many(data.get("fonts", []))

    def upsert_many(self, items: list[dict]) -> int:
        rows = 0
        with connect(self.db_path) as conn:
            for item in items:
                conn.execute(
                    """
                    INSERT INTO fonts (
                        font_id, family, slug, source_site, source_page_url, homepage_url,
                        license_id, license_summary, commercial_use_allowed, video_use_allowed,
                        web_embedding_allowed, redistribution_allowed, languages_json, tags_json,
                        recommended_for_json, preview_text_ko, preview_text_en, download_type,
                        download_url, download_source, format, variable_font
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(font_id) DO UPDATE SET
                        family = excluded.family,
                        slug = excluded.slug,
                        source_site = excluded.source_site,
                        source_page_url = excluded.source_page_url,
                        homepage_url = excluded.homepage_url,
                        license_id = excluded.license_id,
                        license_summary = excluded.license_summary,
                        commercial_use_allowed = excluded.commercial_use_allowed,
                        video_use_allowed = excluded.video_use_allowed,
                        web_embedding_allowed = excluded.web_embedding_allowed,
                        redistribution_allowed = excluded.redistribution_allowed,
                        languages_json = excluded.languages_json,
                        tags_json = excluded.tags_json,
                        recommended_for_json = excluded.recommended_for_json,
                        preview_text_ko = excluded.preview_text_ko,
                        preview_text_en = excluded.preview_text_en,
                        download_type = excluded.download_type,
                        download_url = excluded.download_url,
                        download_source = excluded.download_source,
                        format = excluded.format,
                        variable_font = excluded.variable_font
                    """,
                    (
                        item["font_id"],
                        item["family"],
                        item["slug"],
                        item.get("source_site", ""),
                        item.get("source_page_url", ""),
                        item.get("homepage_url", ""),
                        item.get("license_id", ""),
                        item.get("license_summary", ""),
                        int(bool(item.get("commercial_use_allowed", False))),
                        int(bool(item.get("video_use_allowed", False))),
                        int(bool(item.get("web_embedding_allowed", False))),
                        int(bool(item.get("redistribution_allowed", False))),
                        json.dumps(item.get("languages", []), ensure_ascii=False),
                        json.dumps(item.get("tags", []), ensure_ascii=False),
                        json.dumps(item.get("recommended_for", []), ensure_ascii=False),
                        item.get("preview_text_ko", "역사는 반복되지 않지만 운율은 닮는다"),
                        item.get("preview_text_en", "Cinematic Documentary Title"),
                        item.get("download_type", "manual_only"),
                        item.get("download_url", ""),
                        item.get("download_source", ""),
                        item.get("format", ""),
                        int(bool(item.get("variable_font", False))),
                    ),
                )
                rows += 1
            conn.commit()
        return rows

    def list_fonts(self) -> list[FontRecord]:
        with connect(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM fonts ORDER BY family ASC").fetchall()
        return [self._to_record(row) for row in rows]

    def get_font(self, font_id: str) -> Optional[FontRecord]:
        with connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM fonts WHERE font_id = ?", (font_id,)).fetchone()
        return self._to_record(row) if row else None

    def upsert_candidates(self, items: list[dict]) -> int:
        rows = 0
        with connect(self.db_path) as conn:
            for item in items:
                conn.execute(
                    """
                    INSERT INTO font_candidates (
                        query, title, snippet, result_url, normalized_url, domain,
                        discovery_source, status, discovered_at, note
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(normalized_url) DO UPDATE SET
                        query = excluded.query,
                        title = excluded.title,
                        snippet = excluded.snippet,
                        result_url = excluded.result_url,
                        domain = excluded.domain,
                        discovery_source = excluded.discovery_source,
                        status = excluded.status,
                        note = excluded.note
                    """,
                    (
                        item.get("query", ""),
                        item.get("title", ""),
                        item.get("snippet", ""),
                        item.get("result_url", ""),
                        item.get("normalized_url", ""),
                        item.get("domain", ""),
                        item.get("discovery_source", "web_search"),
                        item.get("status", "discovered"),
                        item.get("discovered_at", ""),
                        item.get("note", ""),
                    ),
                )
                rows += 1
            conn.commit()
        return rows

    def list_candidates(
        self,
        status: Optional[str] = None,
        discovery_source: Optional[str] = None,
    ) -> list[FontCandidate]:
        query = "SELECT * FROM font_candidates"
        clauses = []
        params: list[str] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if discovery_source:
            clauses.append("discovery_source = ?")
            params.append(discovery_source)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY discovered_at DESC, candidate_id DESC"
        with connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._to_candidate(row) for row in rows]

    def update_candidate_status(self, normalized_url: str, status: str, note: str = "") -> None:
        with connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE font_candidates
                SET status = ?, note = ?
                WHERE normalized_url = ?
                """,
                (status, note, normalized_url),
            )
            conn.commit()

    def update_download_fields(
        self,
        font_id: str,
        download_type: str,
        download_url: str,
        format: str,
        download_source: str = "",
    ) -> None:
        with connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE fonts
                SET download_type = ?, download_url = ?, download_source = ?, format = ?
                WHERE font_id = ?
                """,
                (download_type, download_url, download_source, format, font_id),
            )
            conn.commit()

    def update_verification_fields(
        self,
        font_id: str,
        verification_status: str,
        verified_at: str,
        installed_file_count: int,
        verification_failure_reason: str,
    ) -> None:
        with connect(self.db_path) as conn:
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
                    verification_status,
                    verified_at,
                    installed_file_count,
                    verification_failure_reason,
                    font_id,
                ),
            )
            conn.commit()

    def upsert_reference(self, item: dict) -> None:
        with connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO font_references (
                    reference_id, title, medium, surface, role, reference_class, source_kind,
                    source_url, asset_path, tones_json, languages_json, text_blocks_json,
                    candidate_font_ids_json, observed_font_labels_json, palette_json,
                    ratio_hint_json, extraction_method, extraction_confidence, status,
                    notes_json, created_at, reference_scope
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(reference_id) DO UPDATE SET
                    title = excluded.title,
                    medium = excluded.medium,
                    surface = excluded.surface,
                    role = excluded.role,
                    reference_class = excluded.reference_class,
                    source_kind = excluded.source_kind,
                    source_url = excluded.source_url,
                    asset_path = excluded.asset_path,
                    tones_json = excluded.tones_json,
                    languages_json = excluded.languages_json,
                    text_blocks_json = excluded.text_blocks_json,
                    candidate_font_ids_json = excluded.candidate_font_ids_json,
                    observed_font_labels_json = excluded.observed_font_labels_json,
                    palette_json = excluded.palette_json,
                    ratio_hint_json = excluded.ratio_hint_json,
                    extraction_method = excluded.extraction_method,
                    extraction_confidence = excluded.extraction_confidence,
                    status = excluded.status,
                    notes_json = excluded.notes_json,
                    reference_scope = excluded.reference_scope
                """,
                (
                    item["reference_id"],
                    item.get("title", ""),
                    item.get("medium", ""),
                    item.get("surface", ""),
                    item.get("role", ""),
                    item.get("reference_class", "specimen"),
                    item.get("source_kind", ""),
                    item.get("source_url", ""),
                    item.get("asset_path", ""),
                    json.dumps(item.get("tones", []), ensure_ascii=False),
                    json.dumps(item.get("languages", []), ensure_ascii=False),
                    json.dumps(item.get("text_blocks", []), ensure_ascii=False),
                    json.dumps(item.get("candidate_font_ids", []), ensure_ascii=False),
                    json.dumps(item.get("observed_font_labels", []), ensure_ascii=False),
                    json.dumps(item.get("palette", {}), ensure_ascii=False),
                    json.dumps(item.get("ratio_hint", {}), ensure_ascii=False),
                    item.get("extraction_method", "manual"),
                    float(item.get("extraction_confidence", 0.0)),
                    item.get("status", "draft"),
                    json.dumps(item.get("notes", []), ensure_ascii=False),
                    item.get("created_at", ""),
                    item.get("reference_scope", "shared_public"),
                ),
            )
            conn.commit()

    def get_reference(self, reference_id: str) -> Optional[FontReference]:
        with connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM font_references WHERE reference_id = ?",
                (reference_id,),
            ).fetchone()
        return self._to_reference(row) if row else None

    def list_references(
        self,
        *,
        medium: Optional[str] = None,
        surface: Optional[str] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        reference_scope: Optional[str] = None,
    ) -> list[FontReference]:
        query = "SELECT * FROM font_references"
        clauses = []
        params: list[str] = []
        if medium:
            clauses.append("medium = ?")
            params.append(medium)
        if surface:
            clauses.append("surface = ?")
            params.append(surface)
        if role:
            clauses.append("role = ?")
            params.append(role)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if reference_scope:
            clauses.append("reference_scope = ?")
            params.append(reference_scope)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC, reference_id DESC"
        with connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._to_reference(row) for row in rows]

    def upsert_reference_review(self, item: dict) -> None:
        with connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO font_reference_reviews (
                    review_id, reference_id, reviewer_kind, reviewer_name, model_name,
                    source, summary, candidate_font_ids_json, observed_font_labels_json,
                    cohort_tags_json, confidence, status, notes_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(review_id) DO UPDATE SET
                    reference_id = excluded.reference_id,
                    reviewer_kind = excluded.reviewer_kind,
                    reviewer_name = excluded.reviewer_name,
                    model_name = excluded.model_name,
                    source = excluded.source,
                    summary = excluded.summary,
                    candidate_font_ids_json = excluded.candidate_font_ids_json,
                    observed_font_labels_json = excluded.observed_font_labels_json,
                    cohort_tags_json = excluded.cohort_tags_json,
                    confidence = excluded.confidence,
                    status = excluded.status,
                    notes_json = excluded.notes_json
                """,
                (
                    item["review_id"],
                    item["reference_id"],
                    item.get("reviewer_kind", ""),
                    item.get("reviewer_name", ""),
                    item.get("model_name", ""),
                    item.get("source", ""),
                    item.get("summary", ""),
                    json.dumps(item.get("candidate_font_ids", []), ensure_ascii=False),
                    json.dumps(item.get("observed_font_labels", []), ensure_ascii=False),
                    json.dumps(item.get("cohort_tags", []), ensure_ascii=False),
                    float(item.get("confidence", 0.0)),
                    item.get("status", "draft"),
                    json.dumps(item.get("notes", []), ensure_ascii=False),
                    item.get("created_at", ""),
                ),
            )
            conn.commit()

    def list_reference_reviews(
        self,
        *,
        reference_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[FontReferenceReview]:
        query = "SELECT * FROM font_reference_reviews"
        clauses = []
        params: list[str] = []
        if reference_id:
            clauses.append("reference_id = ?")
            params.append(reference_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC, review_id DESC"
        with connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._to_reference_review(row) for row in rows]

    def _to_record(self, row) -> FontRecord:
        return FontRecord(
            font_id=row["font_id"],
            family=row["family"],
            slug=row["slug"],
            source_site=row["source_site"],
            source_page_url=row["source_page_url"],
            homepage_url=row["homepage_url"],
            license_id=row["license_id"],
            license_summary=row["license_summary"],
            commercial_use_allowed=bool(row["commercial_use_allowed"]),
            video_use_allowed=bool(row["video_use_allowed"]),
            web_embedding_allowed=bool(row["web_embedding_allowed"]),
            redistribution_allowed=bool(row["redistribution_allowed"]),
            languages=json.loads(row["languages_json"]),
            tags=json.loads(row["tags_json"]),
            recommended_for=json.loads(row["recommended_for_json"]),
            preview_text_ko=row["preview_text_ko"],
            preview_text_en=row["preview_text_en"],
            download_type=row["download_type"],
            download_url=row["download_url"],
            download_source=row["download_source"],
            format=row["format"],
            variable_font=bool(row["variable_font"]),
            verification_status=row["verification_status"],
            verified_at=row["verified_at"],
            installed_file_count=row["installed_file_count"],
            verification_failure_reason=row["verification_failure_reason"],
        )

    def _to_candidate(self, row) -> FontCandidate:
        return FontCandidate(
            candidate_id=row["candidate_id"],
            query=row["query"],
            title=row["title"],
            snippet=row["snippet"],
            result_url=row["result_url"],
            normalized_url=row["normalized_url"],
            domain=row["domain"],
            discovery_source=row["discovery_source"],
            status=row["status"],
            discovered_at=row["discovered_at"],
            note=row["note"],
        )

    def _to_reference(self, row) -> FontReference:
        return FontReference(
            reference_id=row["reference_id"],
            title=row["title"],
            medium=row["medium"],
            surface=row["surface"],
            role=row["role"],
            reference_class=row["reference_class"],
            source_kind=row["source_kind"],
            source_url=row["source_url"],
            asset_path=row["asset_path"],
            tones=json.loads(row["tones_json"]),
            languages=json.loads(row["languages_json"]),
            text_blocks=json.loads(row["text_blocks_json"]),
            candidate_font_ids=json.loads(row["candidate_font_ids_json"]),
            observed_font_labels=json.loads(row["observed_font_labels_json"]),
            palette=json.loads(row["palette_json"]),
            ratio_hint=json.loads(row["ratio_hint_json"]),
            extraction_method=row["extraction_method"],
            extraction_confidence=float(row["extraction_confidence"]),
            status=row["status"],
            notes=json.loads(row["notes_json"]),
            created_at=row["created_at"],
            reference_scope=row["reference_scope"],
        )

    def _to_reference_review(self, row) -> FontReferenceReview:
        return FontReferenceReview(
            review_id=row["review_id"],
            reference_id=row["reference_id"],
            reviewer_kind=row["reviewer_kind"],
            reviewer_name=row["reviewer_name"],
            model_name=row["model_name"],
            source=row["source"],
            summary=row["summary"],
            candidate_font_ids=json.loads(row["candidate_font_ids_json"]),
            observed_font_labels=json.loads(row["observed_font_labels_json"]),
            cohort_tags=json.loads(row["cohort_tags_json"]),
            confidence=float(row["confidence"]),
            status=row["status"],
            notes=json.loads(row["notes_json"]),
            created_at=row["created_at"],
        )
