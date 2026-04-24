from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS fonts (
    font_id TEXT PRIMARY KEY,
    family TEXT NOT NULL,
    slug TEXT NOT NULL,
    source_site TEXT NOT NULL,
    source_page_url TEXT NOT NULL,
    homepage_url TEXT NOT NULL,
    license_id TEXT NOT NULL,
    license_summary TEXT NOT NULL,
    commercial_use_allowed INTEGER NOT NULL,
    video_use_allowed INTEGER NOT NULL,
    web_embedding_allowed INTEGER NOT NULL,
    redistribution_allowed INTEGER NOT NULL,
    languages_json TEXT NOT NULL,
    tags_json TEXT NOT NULL,
    recommended_for_json TEXT NOT NULL,
    preview_text_ko TEXT NOT NULL,
    preview_text_en TEXT NOT NULL,
    download_type TEXT NOT NULL,
    download_url TEXT NOT NULL,
    download_source TEXT NOT NULL DEFAULT '',
    format TEXT NOT NULL,
    variable_font INTEGER NOT NULL,
    verification_status TEXT NOT NULL DEFAULT '',
    verified_at TEXT NOT NULL DEFAULT '',
    installed_file_count INTEGER NOT NULL DEFAULT 0,
    verification_failure_reason TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS font_candidates (
    candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    title TEXT NOT NULL,
    snippet TEXT NOT NULL,
    result_url TEXT NOT NULL,
    normalized_url TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL,
    discovery_source TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'discovered',
    discovered_at TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS font_references (
    reference_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    medium TEXT NOT NULL,
    surface TEXT NOT NULL,
    role TEXT NOT NULL,
    reference_class TEXT NOT NULL DEFAULT 'specimen',
    source_kind TEXT NOT NULL,
    source_url TEXT NOT NULL DEFAULT '',
    asset_path TEXT NOT NULL DEFAULT '',
    tones_json TEXT NOT NULL,
    languages_json TEXT NOT NULL,
    text_blocks_json TEXT NOT NULL,
    candidate_font_ids_json TEXT NOT NULL,
    observed_font_labels_json TEXT NOT NULL,
    palette_json TEXT NOT NULL,
    ratio_hint_json TEXT NOT NULL,
    extraction_method TEXT NOT NULL DEFAULT 'manual',
    extraction_confidence REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'draft',
    notes_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    reference_scope TEXT NOT NULL DEFAULT 'shared_public'
);

CREATE TABLE IF NOT EXISTS font_reference_reviews (
    review_id TEXT PRIMARY KEY,
    reference_id TEXT NOT NULL,
    reviewer_kind TEXT NOT NULL,
    reviewer_name TEXT NOT NULL,
    model_name TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    candidate_font_ids_json TEXT NOT NULL,
    observed_font_labels_json TEXT NOT NULL,
    cohort_tags_json TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'draft',
    notes_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(reference_id) REFERENCES font_references(reference_id)
);

CREATE TABLE IF NOT EXISTS typography_presets (
    preset_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    tones_json TEXT NOT NULL DEFAULT '[]',
    languages_json TEXT NOT NULL DEFAULT '[]',
    mediums_json TEXT NOT NULL DEFAULT '[]',
    surfaces_json TEXT NOT NULL DEFAULT '[]',
    role_assignments_json TEXT NOT NULL DEFAULT '{}',
    source TEXT NOT NULL DEFAULT 'manual',
    source_url TEXT NOT NULL DEFAULT '',
    reference_image_path TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 0.7,
    verified INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

MIGRATIONS = {
    "download_source": "ALTER TABLE fonts ADD COLUMN download_source TEXT NOT NULL DEFAULT ''",
    "verification_status": "ALTER TABLE fonts ADD COLUMN verification_status TEXT NOT NULL DEFAULT ''",
    "verified_at": "ALTER TABLE fonts ADD COLUMN verified_at TEXT NOT NULL DEFAULT ''",
    "installed_file_count": "ALTER TABLE fonts ADD COLUMN installed_file_count INTEGER NOT NULL DEFAULT 0",
    "verification_failure_reason": "ALTER TABLE fonts ADD COLUMN verification_failure_reason TEXT NOT NULL DEFAULT ''",
}

REFERENCE_MIGRATIONS = {
    "reference_class": "ALTER TABLE font_references ADD COLUMN reference_class TEXT NOT NULL DEFAULT 'specimen'",
    "reference_scope": "ALTER TABLE font_references ADD COLUMN reference_scope TEXT NOT NULL DEFAULT 'shared_public'",
}


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def initialize(db_path: Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        existing_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(fonts)").fetchall()
        }
        for column, statement in MIGRATIONS.items():
            if column not in existing_columns:
                conn.execute(statement)
        existing_reference_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(font_references)").fetchall()
        }
        for column, statement in REFERENCE_MIGRATIONS.items():
            if column not in existing_reference_columns:
                conn.execute(statement)
        conn.commit()
