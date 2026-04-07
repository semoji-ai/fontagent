from __future__ import annotations

import json
import re
import shutil
from pathlib import Path


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[-\s]+", "-", value)
    return value or "reference"


def export_reference_note(
    *,
    vault_root: Path,
    category_name: str,
    reference: dict,
    extraction: dict | None = None,
    reviews: list[dict] | None = None,
    include_assets: bool = True,
    private_asset_root: Path | None = None,
) -> dict:
    medium = reference.get("medium", "unknown")
    surface = reference.get("surface", "unknown")
    note_root = Path(vault_root) / category_name / medium / surface
    assets_dir = note_root / "_assets"
    raw_dir = note_root / "_raw"
    review_dir = note_root / "_reviews"
    note_root.mkdir(parents=True, exist_ok=True)
    if include_assets:
        assets_dir.mkdir(parents=True, exist_ok=True)
        raw_dir.mkdir(parents=True, exist_ok=True)
        review_dir.mkdir(parents=True, exist_ok=True)

    private_assets_dir = None
    private_raw_dir = None
    private_review_dir = None
    if private_asset_root:
        private_note_root = Path(private_asset_root) / category_name / medium / surface
        private_assets_dir = private_note_root / "_assets"
        private_raw_dir = private_note_root / "_raw"
        private_review_dir = private_note_root / "_reviews"
        private_assets_dir.mkdir(parents=True, exist_ok=True)
        private_raw_dir.mkdir(parents=True, exist_ok=True)
        private_review_dir.mkdir(parents=True, exist_ok=True)

    note_name = _slugify(reference.get("title", "")) + ".md"
    note_path = note_root / note_name
    screenshot_target = None
    json_target = None
    review_targets: list[str] = []
    private_screenshot_target = None
    private_json_target = None
    private_review_targets: list[str] = []

    if extraction and extraction.get("screenshot_path") and include_assets:
        screenshot_target = assets_dir / f"{_slugify(reference.get('title', 'reference'))}.png"
        shutil.copy2(extraction["screenshot_path"], screenshot_target)
    if extraction and extraction.get("json_path") and include_assets:
        json_target = raw_dir / f"{_slugify(reference.get('title', 'reference'))}.json"
        shutil.copy2(extraction["json_path"], json_target)
    if extraction and extraction.get("screenshot_path") and private_assets_dir is not None:
        private_screenshot_target = private_assets_dir / f"{_slugify(reference.get('title', 'reference'))}.png"
        shutil.copy2(extraction["screenshot_path"], private_screenshot_target)
    if extraction and extraction.get("json_path") and private_raw_dir is not None:
        private_json_target = private_raw_dir / f"{_slugify(reference.get('title', 'reference'))}.json"
        shutil.copy2(extraction["json_path"], private_json_target)
    if reviews and include_assets:
        prefix = _slugify(reference.get("title", "reference"))
        for index, review in enumerate(reviews, start=1):
            review_target = review_dir / f"{prefix}-review-{index:02d}.json"
            review_target.write_text(
                json.dumps(review, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            review_targets.append(review_target.name)
    if reviews and private_review_dir is not None:
        prefix = _slugify(reference.get("title", "reference"))
        for index, review in enumerate(reviews, start=1):
            review_target = private_review_dir / f"{prefix}-review-{index:02d}.json"
            review_target.write_text(
                json.dumps(review, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            private_review_targets.append(str(review_target))

    tags = ["font-reference", medium, surface, reference.get("role", "")]
    tones = reference.get("tones", [])
    tags.extend([f"tone/{tone}" for tone in tones])

    frontmatter = {
        "reference_id": reference.get("reference_id", ""),
        "medium": medium,
        "surface": surface,
        "role": reference.get("role", ""),
        "reference_class": reference.get("reference_class", "specimen"),
        "reference_scope": reference.get("reference_scope", "shared_public"),
        "source_kind": reference.get("source_kind", ""),
        "source_url": reference.get("source_url", ""),
        "tones": reference.get("tones", []),
        "languages": reference.get("languages", []),
        "candidate_font_ids": reference.get("candidate_font_ids", []),
        "observed_font_labels": reference.get("observed_font_labels", []),
        "status": reference.get("status", ""),
        "extraction_method": reference.get("extraction_method", ""),
        "extraction_confidence": reference.get("extraction_confidence", 0.0),
        "tags": [tag for tag in tags if tag],
        "aliases": [reference.get("title", "")],
    }
    frontmatter_text = "---\n" + "\n".join(
        f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in frontmatter.items()
    ) + "\n---\n"

    body_lines = [
        f"# {reference.get('title', 'Untitled Reference')}",
        "",
        "## Summary",
        "",
        f"- Medium: `{medium}`",
        f"- Surface: `{surface}`",
        f"- Role: `{reference.get('role', '')}`",
        f"- Reference class: `{reference.get('reference_class', 'specimen')}`",
        f"- Reference scope: `{reference.get('reference_scope', 'shared_public')}`",
        f"- Source: `{reference.get('source_url', '') or reference.get('asset_path', '')}`",
    ]
    if reference.get("text_blocks"):
        body_lines.extend(
            [
                "",
                "## Text Blocks",
                "",
                *[f"- {text}" for text in reference["text_blocks"]],
            ]
        )
    if extraction and extraction.get("uniqueFonts"):
        body_lines.extend(
            [
                "",
                "## Extracted Font Families",
                "",
                *[f"- `{family}`" for family in extraction["uniqueFonts"]],
            ]
        )
    if screenshot_target:
        body_lines.extend(["", "## Screenshot", "", f"![[{screenshot_target.name}]]"])
    if json_target:
        body_lines.extend(["", "## Raw Extraction", "", f"- `{json_target.name}`"])
    if private_screenshot_target or private_json_target or private_review_targets:
        body_lines.extend(["", "## Private Cache", ""])
        if private_screenshot_target:
            body_lines.append(f"- screenshot: `{private_screenshot_target}`")
        if private_json_target:
            body_lines.append(f"- raw: `{private_json_target}`")
        if private_review_targets:
            body_lines.extend([f"- review: `{path}`" for path in private_review_targets])
    if reviews:
        body_lines.extend(["", "## Agent Reviews", ""])
        for review in reviews:
            title = review.get("reviewer_name") or review.get("reviewer_kind") or "review"
            summary = review.get("summary", "")
            confidence = review.get("confidence", 0.0)
            candidate_font_ids = review.get("candidate_font_ids", [])
            review_line = (
                f"- `{title}` · confidence `{confidence}` · candidates `{', '.join(candidate_font_ids[:4]) or '-'}`"
            )
            if summary:
                review_line += f" · {summary}"
            body_lines.append(review_line)
        if review_targets:
            body_lines.extend(["", "### Review Files", ""])
            body_lines.extend([f"- `{name}`" for name in review_targets])
    if reference.get("notes"):
        body_lines.extend(["", "## Notes", "", *[f"- {note}" for note in reference["notes"]]])

    note_path.write_text(frontmatter_text + "\n".join(body_lines) + "\n", encoding="utf-8")
    return {
        "note_path": str(note_path),
        "screenshot_path": str(screenshot_target) if screenshot_target else "",
        "raw_json_path": str(json_target) if json_target else "",
        "review_paths": [str(review_dir / name) for name in review_targets],
        "private_screenshot_path": str(private_screenshot_target) if private_screenshot_target else "",
        "private_raw_json_path": str(private_json_target) if private_json_target else "",
        "private_review_paths": private_review_targets,
    }


def sync_reference_index(
    *,
    vault_root: Path,
    category_name: str,
    references: list[dict],
) -> dict:
    note_root = Path(vault_root) / category_name
    index_dir = note_root / "_index"
    index_dir.mkdir(parents=True, exist_ok=True)
    index_path = index_dir / "font-references.md"

    grouped: dict[tuple[str, str], list[dict]] = {}
    for reference in references:
        key = (reference.get("medium", "unknown"), reference.get("surface", "unknown"))
        grouped.setdefault(key, []).append(reference)

    lines = [
        "# Font References",
        "",
        f"- Total references: `{len(references)}`",
        "",
    ]
    for (medium, surface) in sorted(grouped):
        lines.extend([f"## {medium} / {surface}", ""])
        for reference in sorted(grouped[(medium, surface)], key=lambda item: item.get("title", "")):
            slug = _slugify(reference.get("title", "")) + ".md"
            lines.append(
                f"- [[{medium}/{surface}/{slug[:-3]}|{reference.get('title', 'Untitled')}]]"
                f" · `{reference.get('role', '')}` · `{reference.get('status', '')}`"
            )
        lines.append("")

    index_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"index_path": str(index_path)}
