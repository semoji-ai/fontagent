from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .db import connect, initialize
from .models import FontCandidate, FontRecord


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
