from __future__ import annotations

import gzip
import io
import shutil
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

from .http_utils import DEFAULT_HEADERS
from .models import FontRecord

FONT_SUFFIXES = (".ttf", ".otf", ".woff2", ".woff")


class InstallResult(dict):
    pass


def _download_to_path(url: str, destination: Path) -> None:
    parts = urlsplit(url)
    safe_url = urlunsplit(
        (
            parts.scheme,
            parts.netloc.encode("idna").decode("ascii"),
            quote(parts.path, safe="/%@"),
            quote(parts.query, safe="=&%"),
            quote(parts.fragment, safe=""),
        )
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(safe_url, headers=DEFAULT_HEADERS)
    with urllib.request.urlopen(request, timeout=120) as response:
        destination.write_bytes(response.read())


def _normalize_download_payload(path: Path, download_type: str) -> None:
    data = path.read_bytes()
    if not data.startswith(b"\x1f\x8b"):
        return
    try:
        decompressed = gzip.decompress(data)
    except OSError:
        return

    if download_type == "zip_file" and zipfile.is_zipfile(io.BytesIO(decompressed)):
        path.write_bytes(decompressed)
        return
    if download_type == "direct_file" and decompressed[:4] in {b"wOFF", b"wOF2", b"OTTO", b"\x00\x01\x00\x00"}:
        path.write_bytes(decompressed)


def _should_skip_archive_member(member_name: str) -> bool:
    path = Path(member_name)
    if any(part == "__MACOSX" for part in path.parts):
        return True
    return path.name.startswith("._")


def _extract_fonts_from_zip_bytes(data: bytes, output_dir: Path, installed_files: list[str]) -> None:
    with zipfile.ZipFile(io.BytesIO(data)) as zip_file:
        for member in zip_file.infolist():
            if member.is_dir():
                continue
            if _should_skip_archive_member(member.filename):
                continue
            lower = member.filename.lower()
            if lower.endswith(FONT_SUFFIXES):
                target = output_dir / Path(member.filename).name
                with zip_file.open(member) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                installed_files.append(str(target))
                continue
            if lower.endswith(".zip"):
                nested = zip_file.read(member)
                if zipfile.is_zipfile(io.BytesIO(nested)):
                    _extract_fonts_from_zip_bytes(nested, output_dir, installed_files)


def install_font(font: FontRecord, cache_dir: Path, output_dir: Path) -> InstallResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    if font.download_type == "manual_only" or not font.download_url:
        return InstallResult(
            status="manual_required",
            font_id=font.font_id,
            message="이 폰트는 자동 설치를 지원하지 않습니다.",
            source_page_url=font.source_page_url,
        )

    cached = cache_dir / f"{font.font_id}.{font.format or 'bin'}"
    _download_to_path(font.download_url, cached)
    _normalize_download_payload(cached, font.download_type)

    installed_files: list[str] = []
    if font.download_type == "direct_file":
        if not cached.name.lower().endswith(FONT_SUFFIXES):
            return InstallResult(
                status="invalid_file",
                font_id=font.font_id,
                message="다운로드한 direct 파일이 폰트 형식이 아닙니다.",
                source_page_url=font.source_page_url,
                cache_path=str(cached),
            )
        target = output_dir / cached.name
        shutil.copyfile(cached, target)
        installed_files.append(str(target))
    elif font.download_type == "zip_file":
        try:
            _extract_fonts_from_zip_bytes(cached.read_bytes(), output_dir, installed_files)
        except zipfile.BadZipFile:
            return InstallResult(
                status="invalid_archive",
                font_id=font.font_id,
                message="다운로드한 파일이 ZIP 형식이 아닙니다.",
                source_page_url=font.source_page_url,
                cache_path=str(cached),
            )
        if not installed_files:
            return InstallResult(
                status="invalid_archive",
                font_id=font.font_id,
                message="ZIP 안에서 설치 가능한 폰트 파일을 찾지 못했습니다.",
                source_page_url=font.source_page_url,
                cache_path=str(cached),
            )
    else:
        return InstallResult(
            status="manual_required",
            font_id=font.font_id,
            message=f"다운로드 타입 `{font.download_type}` 은 수동 확인이 필요합니다.",
            source_page_url=font.source_page_url,
        )

    return InstallResult(
        status="installed",
        font_id=font.font_id,
        installed_files=installed_files,
        cache_path=str(cached),
    )
