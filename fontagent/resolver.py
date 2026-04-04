from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse, urlsplit, urlunsplit

from .http_utils import DEFAULT_HEADERS, fetch_text


def classify_download_type(url: str) -> str:
    lower = url.lower()
    if lower.endswith((".ttf", ".otf", ".woff", ".woff2")):
        return "direct_file"
    if lower.endswith(".zip"):
        return "zip_file"
    if url:
        return "html_button"
    return "manual_only"


def absolutize(base_url: str, maybe_relative: str) -> str:
    if not maybe_relative:
        return ""
    return urljoin(base_url, maybe_relative)


KNOWN_BROWSER_PAGE_TASKS = {
    "https://www.cafe24.com/story/use/cafe24pro_font.html": {
        "task_id": "cafe24-pro-up",
        "title": "Cafe24 PRO UP download discovery",
        "task_type": "browser_source_discovery",
        "download_type": "browser_required",
        "accept_domains": [
            "www.cafe24.com",
            "img.echosting.cafe24.com",
            "m-img.cafe24.com",
        ],
        "notes": [
            "정적 HTML에서 direct/zip 링크가 바로 보이지 않습니다.",
            "다운로드 버튼 클릭 후 발생하는 최종 파일 URL 또는 네트워크 요청을 기록해야 합니다.",
        ],
        "page_hints": [
            "실제 다운로드 허브는 fonts.cafe24.com 또는 img.cafe24.com JSON 카탈로그일 수 있습니다.",
            "최종 zip 링크가 protocol-relative URL(//img.cafe24.com/...)로 내려올 수 있습니다.",
        ],
        "instructions": [
            "Open the source page in a browser-enabled worker.",
            "Find UI text related to 무료 다운로드 or 폰트 다운로드.",
            "Click the download action and capture the final file response URL if one appears.",
            "If a direct file URL is not exposed, record the exact click selector and resulting request URL or redirect chain.",
        ],
        "success_criteria": [
            "A final direct_file or zip_file URL is captured.",
            "If not possible, the blocking browser step is documented precisely for later automation.",
        ],
    },
    "https://www.jeju.go.kr/jeju/font.htm": {
        "task_id": "jeju-official-fonts",
        "title": "Jeju official font download discovery",
        "task_type": "browser_source_discovery",
        "download_type": "browser_required",
        "accept_domains": [
            "www.jeju.go.kr",
        ],
        "notes": [
            "정적 HTML에서 제주고딕/제주명조/제주한라산 다운로드 파일이 바로 노출되지 않습니다.",
            "페이지 상호작용이나 추가 경로 탐색이 필요합니다.",
        ],
        "page_hints": [
            "실제 안내 페이지는 jeju/symbol/font/infor.htm 형태일 수 있습니다.",
            "수동설치용 TTF/OTF ZIP과 자동설치 파일이 분리돼 있을 수 있습니다.",
        ],
        "instructions": [
            "Open the source page in a browser-enabled worker.",
            "Locate download controls or sections mentioning 제주고딕, 제주명조, 제주한라산.",
            "Capture the final file URL, attachment endpoint, or popup target for each family if available.",
            "If the page only provides manual download steps, record the exact path and required interaction sequence.",
        ],
        "success_criteria": [
            "At least one downloadable asset URL or attachment endpoint is identified.",
            "Otherwise, a precise manual/browser flow is documented for later importer work.",
        ],
    },
    "https://www.jeju.go.kr/jeju/symbol/font/infor.htm": {
        "task_id": "jeju-official-fonts",
        "title": "Jeju official font download discovery",
        "task_type": "browser_source_discovery",
        "download_type": "browser_required",
        "accept_domains": [
            "www.jeju.go.kr",
        ],
        "notes": [
            "정적 HTML에서 제주고딕/제주명조/제주한라산 다운로드 파일이 바로 노출되지 않을 수 있습니다.",
            "수동설치용 ZIP과 자동설치용 파일을 구분해야 합니다.",
        ],
        "page_hints": [
            "안내 페이지는 infor.htm 경로에 있습니다.",
            "수동설치용 TTF/OTF ZIP과 자동설치 파일이 분리돼 있을 수 있습니다.",
        ],
        "instructions": [
            "Open the source page in a browser-enabled worker.",
            "Locate download controls or sections mentioning 제주고딕, 제주명조, 제주한라산.",
            "Capture the final file URL, attachment endpoint, or popup target for each family if available.",
            "If the page only provides manual download steps, record the exact path and required interaction sequence.",
        ],
        "success_criteria": [
            "At least one downloadable asset URL or attachment endpoint is identified.",
            "Otherwise, a precise manual/browser flow is documented for later importer work.",
        ],
    },
}


@dataclass
class ResolutionResult:
    status: str
    download_type: str
    resolved_url: str
    download_source: str
    notes: list[str]


def _build_browser_task_payload(font: dict, result: ResolutionResult) -> dict:
    source_page_url = font.get("source_page_url", "")
    family = font.get("family", "")
    payload = {
        "font_id": font["font_id"],
        "family": family,
        "family_hints": [family] if family else [],
        "source_site": font["source_site"],
        "source_page_url": source_page_url,
        "start_url": result.resolved_url or source_page_url,
        "download_url": result.resolved_url,
        "download_type": result.download_type,
        "download_source": result.download_source,
        "status": result.status,
        "notes": list(result.notes),
        "instructions": [
            "Open the source page in a browser-enabled worker.",
            "Locate the final download button or redirect target.",
            "Record the final direct file URL if possible.",
            "Download the asset or return the extracted final link.",
        ],
    }
    known_task = KNOWN_BROWSER_PAGE_TASKS.get(source_page_url)
    if not known_task:
        return payload

    payload.update(
        {
            "task_id": known_task["task_id"],
            "title": known_task["title"],
            "task_type": known_task["task_type"],
            "accept_domains": list(known_task.get("accept_domains", [])),
            "page_hints": list(known_task.get("page_hints", [])),
            "success_criteria": list(known_task.get("success_criteria", [])),
            "instructions": list(known_task.get("instructions", [])),
            "notes": list(dict.fromkeys(list(result.notes) + list(known_task.get("notes", [])))),
        }
    )
    if family:
        payload["instructions"].append(f"Prioritize UI elements or downloads that correspond to the `{family}` family.")
    return payload


def _normalize_html(html: str) -> str:
    return (
        html.replace("\\u002F", "/")
        .replace("\\/", "/")
        .replace('\\"', '"')
        .replace("&amp;", "&")
    )


def _extract_css_urls(text: str, base_url: str) -> list[str]:
    normalized = _normalize_html(text)
    urls: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"@import\s+url\((['\"]?)([^)'\"]+)\1\)", normalized, re.I):
        candidate = absolutize(base_url, unescape(match.group(2).strip()))
        if candidate not in seen:
            urls.append(candidate)
            seen.add(candidate)
    for match in re.finditer(r'<link[^>]+href="([^"]+\.css(?:\?[^"]*)?)"', normalized, re.I):
        candidate = absolutize(base_url, unescape(match.group(1).strip()))
        if candidate not in seen:
            urls.append(candidate)
            seen.add(candidate)
    return urls


def _extract_asset_urls_from_css(text: str, base_url: str) -> list[str]:
    normalized = _normalize_html(text)
    urls: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"url\((['\"]?)([^)'\"]+)\1\)", normalized, re.I):
        raw = unescape(match.group(2).strip())
        if raw.startswith("data:"):
            continue
        candidate = absolutize(base_url, raw)
        if classify_download_type(candidate) not in {"direct_file", "zip_file"}:
            continue
        if candidate not in seen:
            urls.append(candidate)
            seen.add(candidate)
    return urls


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _pick_best_asset_url(candidates: list[str], family_hint: str = "") -> str:
    if not candidates:
        return ""
    if not family_hint:
        return candidates[0]

    family_token = _normalize_token(family_hint)
    ranked: list[tuple[int, str]] = []
    for candidate in candidates:
        candidate_token = _normalize_token(candidate)
        score = 0
        if family_token and family_token in candidate_token:
            score += 20
        family_parts = [part for part in re.split(r"[^a-z0-9]+", family_hint.lower()) if part]
        score += sum(3 for part in family_parts if len(part) >= 3 and part in candidate.lower())
        ranked.append((score, candidate))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    best_score, best_candidate = ranked[0]
    if len(candidates) > 1 and best_score == 0:
        basenames = [
            _normalize_token(Path(urlparse(candidate).path).stem)
            for candidate in candidates
            if Path(urlparse(candidate).path).stem
        ]
        if basenames:
            common_prefix = basenames[0]
            for basename in basenames[1:]:
                limit = min(len(common_prefix), len(basename))
                idx = 0
                while idx < limit and common_prefix[idx] == basename[idx]:
                    idx += 1
                common_prefix = common_prefix[:idx]
                if not common_prefix:
                    break
            if len(common_prefix) >= 6:
                return candidates[0]
        return ""
    return best_candidate


def _extract_direct_asset_url(html: str, base_url: str, family_hint: str = "") -> str:
    normalized = _normalize_html(html)
    candidates: list[str] = []

    bookk_match = re.search(
        r'"fontFile":\{.*?"primaryFile":\{.*?"path":"([^"]+\.zip)"',
        normalized,
        re.I | re.S,
    )
    if bookk_match:
        candidates.append(absolutize(base_url, unescape(bookk_match.group(1))))

    for pattern in (
        r'window\.open\("([^"]+\.(?:zip|ttf|otf|woff2?|dmg(?:\.zip)?))"',
        r'<option[^>]+value="([^"]+\.(?:zip|ttf|otf|woff2?|dmg(?:\.zip)?)(?:\?[^"]*)?)"',
        r"<a[^>]+href=['\"]([^'\"]+\.(?:zip|ttf|otf|woff2?|dmg(?:\.zip)?)(?:\?[^'\"]*)?)['\"]",
    ):
        for match in re.finditer(pattern, normalized, re.I | re.S):
            candidates.append(absolutize(base_url, unescape(match.group(1))))

    for match in re.finditer(r'"?(?:href|src|downloadUrl|path|url|download_url)"?\s*[:=]\s*"([^"]+)"', normalized, re.I):
        candidate = unescape(match.group(1))
        absolute = absolutize(base_url, candidate)
        if classify_download_type(absolute) in {"direct_file", "zip_file"}:
            candidates.append(absolute)
    for match in re.finditer(r"'?(?:href|src|downloadUrl|path|url|download_url)'?\s*[:=]\s*'([^']+)'", normalized, re.I):
        candidate = unescape(match.group(1))
        absolute = absolutize(base_url, candidate)
        if classify_download_type(absolute) in {"direct_file", "zip_file"}:
            candidates.append(absolute)
    candidates.extend(_extract_asset_urls_from_css(normalized, base_url))

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate not in seen:
            deduped.append(candidate)
            seen.add(candidate)
    return _pick_best_asset_url(deduped, family_hint=family_hint)


def _candidate_follow_links(html: str, base_url: str) -> list[str]:
    normalized = _normalize_html(html)
    candidates: list[str] = []
    seen: set[str] = set()
    parsed = urlparse(base_url)

    for match in re.finditer(r'"?(?:href|src|downloadUrl|path|url|download_url)"?\s*[:=]\s*"([^"]+)"', normalized, re.I):
        candidate = absolutize(base_url, unescape(match.group(1)))
        if candidate in seen:
            continue
        lower = candidate.lower()
        if any(token in lower for token in ("/releases", "/download", "/expanded_assets/", "raw.githubusercontent.com", "/raw/", "fontdwon", "/resources/primaryfiles/", "post_file_download.cm")):
            candidates.append(candidate)
            seen.add(candidate)

    for match in re.finditer(r"'?(?:href|src|downloadUrl|path|url|download_url)'?\s*[:=]\s*'([^']+)'", normalized, re.I):
        candidate = absolutize(base_url, unescape(match.group(1)))
        if candidate in seen:
            continue
        lower = candidate.lower()
        if any(token in lower for token in ("/releases", "/download", "/expanded_assets/", "raw.githubusercontent.com", "/raw/", "fontdwon", "/resources/primaryfiles/", "post_file_download.cm")):
            candidates.append(candidate)
            seen.add(candidate)

    for match in re.finditer(r"location\.href='([^']+)'", normalized, re.I):
        candidate = absolutize(base_url, unescape(match.group(1)))
        if candidate not in seen:
            candidates.append(candidate)
            seen.add(candidate)

    if parsed.netloc == "github.com":
        path = parsed.path.rstrip("/")
        parts = [part for part in path.split("/") if part]
        if len(parts) == 2:
            for suffix in ("/releases/latest", "/releases", "/archive/refs/heads/main.zip", "/archive/refs/heads/master.zip"):
                candidate = f"{parsed.scheme}://{parsed.netloc}{path}{suffix}"
                if candidate not in seen:
                    candidates.append(candidate)
                    seen.add(candidate)

    return candidates[:12]


def _probe_download_candidate(url: str) -> tuple[str, str] | None:
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
    request = urllib.request.Request(safe_url, headers=DEFAULT_HEADERS, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            final_url = response.geturl()
            content_type = (response.headers.get("Content-Type") or "").lower()
            disposition = response.headers.get("Content-Disposition") or ""
    except Exception:
        return None

    canonical_url = url
    parsed_original = urlparse(url)
    if parsed_original.netloc in {"github.com", "raw.githubusercontent.com"}:
        canonical_url = url
    elif "codeload.github.com" in final_url and "github.com" in url:
        canonical_url = url

    for value in (disposition, final_url, canonical_url):
        lowered = value.lower()
        if ".zip" in lowered:
            return canonical_url, "zip_file"
        if ".ttf" in lowered:
            return canonical_url, "direct_file"
        if ".otf" in lowered:
            return canonical_url, "direct_file"
        if ".woff2" in lowered:
            return canonical_url, "direct_file"
        if ".woff" in lowered:
            return canonical_url, "direct_file"

    if "zip" in content_type:
        return canonical_url, "zip_file"
    if any(token in content_type for token in ("font/", "application/font", "application/x-font")):
        return canonical_url, "direct_file"
    return None


def infer_download_source(download_url: str, download_type: str) -> str:
    if not download_url or download_type not in {"direct_file", "zip_file"}:
        return ""
    lower = download_url.lower()
    if "projectnoonnu" in lower:
        return "preview_webfont"
    if download_type == "direct_file" and "/web/" in lower:
        return "preview_webfont"
    return "canonical"


def _resolve_webfont_preview(font: dict) -> ResolutionResult | None:
    source_page_url = font.get("source_page_url", "")
    if not source_page_url:
        return None
    try:
        source_html = fetch_text(source_page_url, timeout=20)
    except RuntimeError:
        return None

    preview_assets = _extract_asset_urls_from_css(source_html, source_page_url)
    best_preview_asset = _pick_best_asset_url(preview_assets, family_hint=font.get("family", ""))
    for asset_url in ([best_preview_asset] if best_preview_asset else []):
        probed = _probe_download_candidate(asset_url)
        if probed:
            resolved_url, resolved_type = probed
            return ResolutionResult(
                status="resolved",
                download_type=resolved_type,
                resolved_url=resolved_url,
                download_source="preview_webfont",
                notes=["소스 상세 페이지의 웹폰트 미리보기 자산을 자동 해석했습니다."],
            )

    for css_url in _extract_css_urls(source_html, source_page_url):
        try:
            css_text = fetch_text(css_url, timeout=20)
        except RuntimeError:
            continue
        css_assets = _extract_asset_urls_from_css(css_text, css_url)
        best_css_asset = _pick_best_asset_url(css_assets, family_hint=font.get("family", ""))
        for asset_url in ([best_css_asset] if best_css_asset else []):
            probed = _probe_download_candidate(asset_url)
            if probed:
                resolved_url, resolved_type = probed
                return ResolutionResult(
                    status="resolved",
                    download_type=resolved_type,
                    resolved_url=resolved_url,
                    download_source="preview_webfont",
                    notes=["소스 상세 페이지가 불러오는 웹폰트 CSS에서 자동 설치 가능한 링크를 찾았습니다."],
                )
    return None


def resolve_download(font: dict) -> ResolutionResult:
    download_type = font.get("download_type", "manual_only")
    download_url = unescape(font.get("download_url", ""))
    if download_type in {"direct_file", "zip_file"} and download_url:
        return ResolutionResult(
            status="resolved",
            download_type=download_type,
            resolved_url=download_url,
            download_source=font.get("download_source") or infer_download_source(download_url, download_type),
            notes=["자동 설치 가능한 다운로드 링크가 있습니다."],
        )
    if download_type == "html_button" and download_url:
        notes = ["상세 페이지 또는 버튼 클릭 흐름이 필요합니다."]
        try:
            external_html = fetch_text(download_url, timeout=20)
            asset_url = _extract_direct_asset_url(external_html, download_url, family_hint=font.get("family", ""))
            if asset_url:
                probed = _probe_download_candidate(asset_url)
                if probed:
                    resolved_url, resolved_type = probed
                    return ResolutionResult(
                        status="resolved",
                        download_type=resolved_type,
                        resolved_url=resolved_url,
                        download_source=infer_download_source(resolved_url, resolved_type),
                        notes=["외부 다운로드 페이지에서 자동 설치 가능한 링크를 찾았습니다."],
                    )
                asset_type = classify_download_type(asset_url)
                if asset_type in {"direct_file", "zip_file"} and urlparse(asset_url).netloc in {
                    "github.com",
                    "raw.githubusercontent.com",
                }:
                    return ResolutionResult(
                        status="resolved",
                        download_type=asset_type,
                        resolved_url=asset_url,
                        download_source=infer_download_source(asset_url, asset_type),
                        notes=["외부 다운로드 페이지에서 GitHub canonical 다운로드 링크를 찾았습니다."],
                    )
            for candidate in _candidate_follow_links(external_html, download_url):
                candidate_type = classify_download_type(candidate)
                if candidate_type in {"direct_file", "zip_file"}:
                    probed = _probe_download_candidate(candidate)
                    if probed:
                        resolved_url, resolved_type = probed
                        return ResolutionResult(
                            status="resolved",
                            download_type=resolved_type,
                            resolved_url=resolved_url,
                            download_source=infer_download_source(resolved_url, resolved_type),
                            notes=["외부 다운로드 페이지 링크를 따라가 자동 설치 가능한 URL을 추론했습니다."],
                        )
                probed = _probe_download_candidate(candidate)
                if probed:
                    resolved_url, resolved_type = probed
                    return ResolutionResult(
                        status="resolved",
                        download_type=resolved_type,
                        resolved_url=resolved_url,
                        download_source=infer_download_source(resolved_url, resolved_type),
                        notes=["확장자 없는 다운로드 엔드포인트를 probe하여 설치 가능한 링크를 찾았습니다."],
                    )
                try:
                    candidate_html = fetch_text(candidate, timeout=20)
                except RuntimeError:
                    continue
                asset_url = _extract_direct_asset_url(candidate_html, candidate, family_hint=font.get("family", ""))
                if asset_url:
                    asset_type = classify_download_type(asset_url)
                    probed = _probe_download_candidate(asset_url)
                    if probed:
                        resolved_url, resolved_type = probed
                        return ResolutionResult(
                            status="resolved",
                            download_type=resolved_type,
                            resolved_url=resolved_url,
                            download_source=infer_download_source(resolved_url, resolved_type),
                            notes=["외부 다운로드 페이지를 한 단계 더 추적해 자동 설치 가능한 링크를 찾았습니다."],
                        )
                    if asset_type in {"direct_file", "zip_file"} and urlparse(asset_url).netloc in {
                        "github.com",
                        "raw.githubusercontent.com",
                    }:
                        return ResolutionResult(
                            status="resolved",
                            download_type=asset_type,
                            resolved_url=asset_url,
                            download_source=infer_download_source(asset_url, asset_type),
                            notes=["외부 다운로드 페이지를 한 단계 더 추적해 GitHub canonical 다운로드 링크를 찾았습니다."],
                        )
                for nested_candidate in _candidate_follow_links(candidate_html, candidate):
                    nested_type = classify_download_type(nested_candidate)
                    if nested_type in {"direct_file", "zip_file"}:
                        probed = _probe_download_candidate(nested_candidate)
                        if probed:
                            resolved_url, resolved_type = probed
                            return ResolutionResult(
                                status="resolved",
                                download_type=resolved_type,
                                resolved_url=resolved_url,
                                download_source=infer_download_source(resolved_url, resolved_type),
                                notes=["외부 다운로드 페이지를 두 단계 추적해 자동 설치 가능한 링크를 찾았습니다."],
                            )
                        if urlparse(nested_candidate).netloc in {"github.com", "raw.githubusercontent.com"}:
                            return ResolutionResult(
                                status="resolved",
                                download_type=nested_type,
                                resolved_url=nested_candidate,
                                download_source=infer_download_source(nested_candidate, nested_type),
                                notes=["외부 다운로드 페이지를 두 단계 추적해 GitHub canonical 다운로드 링크를 찾았습니다."],
                            )
                    probed = _probe_download_candidate(nested_candidate)
                    if probed:
                        resolved_url, resolved_type = probed
                        return ResolutionResult(
                            status="resolved",
                            download_type=resolved_type,
                            resolved_url=resolved_url,
                            download_source=infer_download_source(resolved_url, resolved_type),
                            notes=["외부 다운로드 페이지를 두 단계 추적해 자동 설치 가능한 링크를 찾았습니다."],
                        )
            notes.append("외부 다운로드 페이지에서 direct/zip 링크를 찾지 못했습니다.")
        except RuntimeError as exc:
            notes.append(str(exc))
        preview_result = _resolve_webfont_preview(font)
        if preview_result is not None:
            return preview_result
        return ResolutionResult(
            status="browser_required",
            download_type=download_type,
            resolved_url=download_url,
            download_source=font.get("download_source", ""),
            notes=notes,
        )
    return ResolutionResult(
        status="manual_required",
        download_type=download_type,
        resolved_url=download_url,
        download_source=font.get("download_source", ""),
        notes=["자동 해석이 어려워 수동 확인이 필요합니다."],
    )


def write_browser_download_task(font: dict, output_dir: Path) -> Path:
    result = resolve_download(font)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{font['font_id']}.browser-download-task.json"
    payload = _build_browser_task_payload(font, result)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def write_source_browser_task(source_page_url: str, output_dir: Path) -> Path:
    try:
        task = KNOWN_BROWSER_PAGE_TASKS[source_page_url]
    except KeyError as exc:
        raise KeyError(f"Unsupported browser-required source page: {source_page_url}") from exc
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{task['task_id']}.source-browser-task.json"
    payload = dict(task)
    payload["source_page_url"] = source_page_url
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path
