from __future__ import annotations

import json
import re
from pathlib import Path


ROLE_PREFERENCE = {
    "title": [".ttf", ".otf", ".woff2", ".woff"],
    "subtitle": [".ttf", ".otf", ".woff2", ".woff"],
    "body": [".ttf", ".otf", ".woff2", ".woff"],
}

ROLE_WEIGHT_PREFERENCE = {
    "title": [
        ("black", "heavy"),
        ("extrabold", "ultrabold", "xbold"),
        ("bold", "semibold", "demibold"),
        ("medium",),
        ("regular", "book", "normal"),
        ("light",),
    ],
    "subtitle": [
        ("regular", "book", "normal"),
        ("medium",),
        ("semibold", "demibold"),
        ("bold",),
        ("light",),
        ("black", "heavy", "extrabold", "ultrabold", "xbold"),
    ],
    "body": [
        ("regular", "book", "normal"),
        ("medium",),
        ("light",),
        ("semibold", "demibold"),
        ("bold",),
        ("black", "heavy", "extrabold", "ultrabold", "xbold"),
    ],
}

ROLE_DEFAULTS = {
    "title": {"weight": 700, "line_height": 1.1, "tracking_em": -0.02},
    "subtitle": {"weight": 600, "line_height": 1.35, "tracking_em": -0.01},
    "body": {"weight": 400, "line_height": 1.6, "tracking_em": 0.0},
}


def role_defaults(role: str) -> dict:
    return dict(ROLE_DEFAULTS.get(role, ROLE_DEFAULTS["body"]))


def guess_generic_family(tags: list[str]) -> str:
    corpus = " ".join(tags).lower()
    if any(token in corpus for token in ("mono", "monospace", "code", "코드", "픽셀", "pixel", "게임", "game")):
        return "monospace"
    if any(token in corpus for token in ("sans", "고딕", "grotesk", "neo-grotesk", "ui")):
        return "sans-serif"
    if any(token in corpus for token in ("serif", "editorial", "명조", "바탕", "책 서체")):
        return "serif"
    return "sans-serif"


def _weight_rank(path: Path, role: str) -> int:
    stem = path.stem.lower()
    for index, keyword_group in enumerate(ROLE_WEIGHT_PREFERENCE.get(role, ())):
        if any(keyword in stem for keyword in keyword_group):
            return index
    return 99


def _normalize_match_text(value: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", "", value.lower())


def _family_match_rank(path: Path, family_hint: str | None) -> int:
    if not family_hint:
        return 0
    stem = _normalize_match_text(path.stem)
    if not stem:
        return 0
    hint = _normalize_match_text(family_hint)
    if hint and hint in stem:
        return -100
    parts = [_normalize_match_text(part) for part in re.split(r"[^0-9a-z가-힣]+", family_hint.lower()) if len(part) >= 3]
    match_score = sum(len(part) for part in parts if part and part in stem)
    return -match_score


def pick_preferred_file(paths: list[str], role: str, family_hint: str | None = None) -> str:
    candidates = [Path(path) for path in paths]
    order = {suffix: index for index, suffix in enumerate(ROLE_PREFERENCE.get(role, []))}
    selected = min(
        candidates,
        key=lambda path: (
            _family_match_rank(path, family_hint),
            order.get(path.suffix.lower(), 99),
            _weight_rank(path, role),
            len(path.name),
            path.name.lower(),
        ),
    )
    return str(selected)


def _css_format(path: str) -> str:
    suffix = Path(path).suffix.lower()
    mapping = {
        ".ttf": "truetype",
        ".otf": "opentype",
        ".woff2": "woff2",
        ".woff": "woff",
    }
    return mapping.get(suffix, "truetype")


def render_css_token_file(
    output_path: Path,
    role_assets: dict[str, dict],
) -> Path:
    lines = []
    for role in ("title", "subtitle", "body"):
        asset = role_assets[role]
        relative = Path(asset["asset_path"]).relative_to(output_path.parent.parent)
        alias = f"FontAgent{role.capitalize()}"
        lines.append("@font-face {")
        lines.append(f"  font-family: '{alias}';")
        lines.append(f"  src: url('../{relative.as_posix()}') format('{_css_format(asset['asset_path'])}');")
        lines.append("  font-display: swap;")
        lines.append("}")
        lines.append("")
    lines.append(":root {")
    for role in ("title", "subtitle", "body"):
        asset = role_assets[role]
        alias = f"FontAgent{role.capitalize()}"
        lines.append(f"  --font-{role}: '{alias}', '{asset['family']}', {asset['generic_family']};")
        lines.append(f"  --font-family-{role}: var(--font-{role});")
        lines.append(f"  --font-weight-{role}: {asset['defaults']['weight']};")
        lines.append(f"  --font-line-height-{role}: {asset['defaults']['line_height']};")
        lines.append(f"  --font-tracking-{role}: {asset['defaults']['tracking_em']}em;")
    lines.append("}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def render_remotion_token_file(output_path: Path, role_assets: dict[str, dict]) -> Path:
    payload = {
        role: {
            "fontId": asset["font_id"],
            "family": asset["family"],
            "assetPath": asset["asset_path"],
            "genericFamily": asset["generic_family"],
            "defaults": asset["defaults"],
        }
        for role, asset in role_assets.items()
    }
    content = (
        "// FontAgent generated file\n"
        f"export const fontSystem = {json.dumps(payload, ensure_ascii=False, indent=2)} as const;\n"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def write_font_system_manifest(
    output_path: Path,
    *,
    task: str,
    language: str,
    target: str,
    use_case: str | None,
    role_assets: dict[str, dict],
) -> Path:
    payload = {
        "task": task,
        "language": language,
        "target": target,
        "use_case": use_case or "",
        "roles": role_assets,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path
