from __future__ import annotations

import json
import platform
import re
import subprocess
from pathlib import Path


SYSTEM_PROFILER_TIMEOUT_SECONDS = 20
FONT_FILE_SUFFIXES = {".ttf", ".otf", ".ttc", ".otc", ".woff", ".woff2"}
SYSTEM_FONT_DIRECTORIES = (
    Path("/System/Library/Fonts"),
    Path("/Library/Fonts"),
    Path.home() / "Library" / "Fonts",
)
WINDOWS_FONT_DIRECTORIES = (
    Path.home() / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts",
    Path("C:/Windows/Fonts"),
)
LINUX_FONT_DIRECTORIES = (
    Path.home() / ".local" / "share" / "fonts",
    Path("/usr/local/share/fonts"),
    Path("/usr/share/fonts"),
)


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^0-9a-z가-힣]+", "-", (value or "").strip().lower())
    return cleaned.strip("-") or "system-font"


def _normalize_format(raw_value: str) -> str:
    lowered = (raw_value or "").strip().lower()
    if lowered in {"truetype", "ttf"}:
        return "ttf"
    if lowered in {"opentype", "otf"}:
        return "otf"
    if lowered in {"truetype collection", "ttc"}:
        return "ttc"
    if lowered in {"opentype collection", "otc"}:
        return "otc"
    return lowered or "unknown"


def _detect_languages(text: str) -> list[str]:
    if re.search(r"[가-힣]", text or ""):
        return ["ko", "en"]
    return ["en"]


def _default_font_record(*, font_id: str, family: str, path: str, format_name: str, languages: list[str]) -> dict:
    return {
        "font_id": font_id,
        "family": family,
        "slug": _slug(family),
        "source_site": "system_local",
        "source_page_url": f"file://{path}",
        "homepage_url": "",
        "license_id": "system_local",
        "license_summary": "로컬 macOS에 설치된 시스템 폰트입니다. 재배포 전 라이선스를 별도로 확인해야 합니다.",
        "commercial_use_allowed": False,
        "video_use_allowed": False,
        "web_embedding_allowed": False,
        "redistribution_allowed": False,
        "languages": languages,
        "tags": ["system", "installed", "local"],
        "recommended_for": ["local_preview"],
        "preview_text_ko": "시스템 폰트 미리보기",
        "preview_text_en": "System font preview",
        "download_type": "manual_only",
        "download_url": "",
        "download_source": "installed_system",
        "format": format_name,
        "variable_font": False,
        "system_paths": [path],
        "installed_file_count": 1,
    }


def scan_system_font_records(timeout: int = SYSTEM_PROFILER_TIMEOUT_SECONDS) -> list[dict]:
    system_name = platform.system().lower()
    if system_name == "darwin":
        try:
            return _scan_macos_with_system_profiler(timeout=timeout)
        except Exception:
            return _scan_font_directories(SYSTEM_FONT_DIRECTORIES)
    if system_name == "windows":
        return _scan_font_directories(WINDOWS_FONT_DIRECTORIES)
    return _scan_font_directories(LINUX_FONT_DIRECTORIES)


def _scan_macos_with_system_profiler(timeout: int) -> list[dict]:
    process = subprocess.run(
        ["system_profiler", "SPFontsDataType", "-json"],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if process.returncode != 0:
        stderr = (process.stderr or "").strip()
        raise RuntimeError(stderr or "system_profiler SPFontsDataType failed")

    payload = json.loads(process.stdout or "{}")
    entries = payload.get("SPFontsDataType") or []
    by_font_id: dict[str, dict] = {}

    for entry in entries:
        path = str(entry.get("path") or "").strip()
        if not path:
            continue
        typefaces = entry.get("typefaces") or []
        primary = typefaces[0] if typefaces else {}
        family = (
            str(primary.get("family") or "").strip()
            or str(entry.get("_name") or "").strip()
            or Path(path).stem
        )
        font_id = f"system-{_slug(family)}"
        format_name = _normalize_format(str(entry.get("type") or Path(path).suffix.lstrip(".")))
        languages = _detect_languages(" ".join([family, str(primary.get("fullname") or ""), str(primary.get("style") or "")]))
        record = by_font_id.get(font_id)
        if record is None:
            record = _default_font_record(
                font_id=font_id,
                family=family,
                path=path,
                format_name=format_name,
                languages=languages,
            )
            by_font_id[font_id] = record
        else:
            record["installed_file_count"] += 1
            if path not in record["system_paths"]:
                record["system_paths"].append(path)
            merged_languages = set(record["languages"])
            merged_languages.update(languages)
            record["languages"] = sorted(merged_languages)

    return sorted(by_font_id.values(), key=lambda item: item["family"].lower())


def _scan_font_directories(directories: tuple[Path, ...]) -> list[dict]:
    by_font_id: dict[str, dict] = {}
    for base in directories:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.suffix.lower() not in FONT_FILE_SUFFIXES:
                continue
            family = path.stem.replace("-", " ").replace("_", " ").strip()
            if not family:
                continue
            font_id = f"system-{_slug(family)}"
            record = by_font_id.get(font_id)
            languages = _detect_languages(family)
            if record is None:
                record = _default_font_record(
                    font_id=font_id,
                    family=family,
                    path=str(path),
                    format_name=path.suffix.lower().lstrip("."),
                    languages=languages,
                )
                by_font_id[font_id] = record
            else:
                record["installed_file_count"] += 1
                string_path = str(path)
                if string_path not in record["system_paths"]:
                    record["system_paths"].append(string_path)
                merged_languages = set(record["languages"])
                merged_languages.update(languages)
                record["languages"] = sorted(merged_languages)
    return sorted(by_font_id.values(), key=lambda item: item["family"].lower())
