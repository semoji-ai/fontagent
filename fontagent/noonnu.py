from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from typing import Optional
from pathlib import Path
import time

from .http_utils import fetch_text
from .resolver import absolutize, classify_download_type


_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    text = unescape(_TAG_RE.sub(" ", text))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


@dataclass
class NoonnuSummary:
    slug: str
    family: str
    source_page_url: str


@dataclass
class NoonnuDetail:
    slug: str
    family: str
    source_page_url: str
    download_url: str
    license_summary: str
    tags: list[str]
    preview_text_ko: str

    def to_font_record(self) -> dict:
        return {
            "font_id": self.slug,
            "family": self.family,
            "slug": self.slug,
            "source_site": "noonnu",
            "source_page_url": self.source_page_url,
            "homepage_url": self.source_page_url,
            "license_id": "noonnu-import",
            "license_summary": self.license_summary or "상세 페이지 라이선스 확인 필요",
            "commercial_use_allowed": True,
            "video_use_allowed": True,
            "web_embedding_allowed": True,
            "redistribution_allowed": False,
            "languages": ["ko"],
            "tags": self.tags,
            "recommended_for": _guess_use_cases(self.tags),
            "preview_text_ko": self.preview_text_ko or "역사는 반복되지 않지만 운율은 닮는다",
            "preview_text_en": self.family,
            "download_type": classify_download_type(self.download_url),
            "download_url": self.download_url,
            "format": _guess_format(self.download_url),
            "variable_font": False,
        }


def _guess_use_cases(tags: list[str]) -> list[str]:
    joined = " ".join(tags)
    use_cases = []
    if any(token in joined for token in ("title", "제목", "serif", "명조")):
        use_cases.append("title")
    if any(token in joined for token in ("subtitle", "자막", "sans", "고딕")):
        use_cases.append("subtitle")
    if not use_cases:
        use_cases.append("body")
    return use_cases


def _guess_format(url: str) -> str:
    lower = url.lower()
    for ext in ("ttf", "otf", "woff2", "woff", "zip"):
        if lower.endswith(f".{ext}"):
            return ext
    return "zip"


def parse_listing_html(html: str, base_url: str = "https://noonnu.cc/") -> list[NoonnuSummary]:
    summaries: list[NoonnuSummary] = []
    seen: set[str] = set()

    for match in re.finditer(r'<a[^>]+href="(?P<href>/font_page/[^"#?]+)"[^>]*>(?P<body>.*?)</a>', html, re.S):
        href = match.group("href")
        slug = href.rstrip("/").split("/")[-1]
        if slug in seen:
            continue
        family = _clean(match.group("body"))
        if not family:
            family = slug.replace("-", " ").title()
        summaries.append(NoonnuSummary(slug=slug, family=family, source_page_url=absolutize(base_url, href)))
        seen.add(slug)

    return summaries


def _extract_download_url(html: str, source_page_url: str) -> str:
    patterns = [
        r'<a[^>]+href="([^"]+)"[^>]*>\s*<span>\s*다운로드 페이지로 이동\s*</span>\s*</a>',
        r'<a[^>]+href="([^"]+\.(?:zip|ttf|otf|woff2?|ZIP|TTF|OTF|WOFF2?))"[^>]*>',
        r'<a[^>]+href="([^"]+)"[^>]*>\s*다운로드\s*</a>',
        r'<button[^>]+onclick="location.href=\'([^\']+)\'"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.I | re.S)
        if match:
            return absolutize(source_page_url, match.group(1))
    return ""


def _extract_license_summary(html: str) -> str:
    section_match = re.search(
        r"라이선스 본문\s*</span>\s*<article[^>]*>(?P<body>.*?)</article>",
        html,
        re.I | re.S,
    )
    if section_match:
        paragraphs = [
            _clean(match)
            for match in re.findall(r"<p[^>]*>(.*?)</p>", section_match.group("body"), re.I | re.S)
        ]
        paragraphs = [paragraph for paragraph in paragraphs if paragraph]
        if paragraphs:
            return " ".join(paragraphs[:2])

    candidates = re.findall(r"(라이선스[^<]{0,200}|상업적 이용[^<]{0,200}|개인 및 상업적 이용[^<]{0,200})", html, re.I)
    for candidate in candidates:
        cleaned = _clean(candidate)
        if cleaned and cleaned != "라이선스 본문":
            return cleaned
    return "상세 페이지 라이선스 확인 필요"


def _extract_preview_text(html: str) -> str:
    match = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', html, re.I)
    if match:
        return _clean(match.group(1))
    return "역사는 반복되지 않지만 운율은 닮는다"


def _extract_tags(html: str) -> list[str]:
    tags = []
    seen = set()

    for match in re.finditer(r'<a[^>]+href="/index\?search=[^"]+"[^>]*>(.*?)</a>', html, re.I | re.S):
        cleaned = _clean(match.group(1)).lower()
        if cleaned and cleaned not in seen:
            tags.append(cleaned)
            seen.add(cleaned)

    for match in re.finditer(r'<a[^>]+class="[^"]*tag[^"]*"[^>]*>(.*?)</a>', html, re.I | re.S):
        cleaned = _clean(match.group(1))
        lowered = cleaned.lower()
        if lowered and lowered not in seen:
            tags.append(lowered)
            seen.add(lowered)
    return tags[:8]


def parse_detail_html(
    html: str,
    slug: str,
    source_page_url: str,
    family_hint: Optional[str] = None,
) -> NoonnuDetail:
    family = family_hint or slug.replace("-", " ").title()
    title_match = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
    if title_match:
        title = _clean(title_match.group(1))
        if title:
            family = title.split("|")[0].strip()
    return NoonnuDetail(
        slug=slug,
        family=family,
        source_page_url=source_page_url,
        download_url=_extract_download_url(html, source_page_url),
        license_summary=_extract_license_summary(html),
        tags=_extract_tags(html),
        preview_text_ko=_extract_preview_text(html),
    )


def fetch_noonnu_snapshot(
    listing_url: str,
    output_dir: Path,
    limit: int = 20,
    delay_seconds: float = 0.0,
) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    detail_dir = output_dir / "details"
    detail_dir.mkdir(parents=True, exist_ok=True)

    listing_html = fetch_text(listing_url)
    listing_path = output_dir / "listing.html"
    listing_path.write_text(listing_html, encoding="utf-8")

    summaries = parse_listing_html(listing_html, base_url=listing_url)
    fetched = 0
    for summary in summaries[:limit]:
        detail_html = fetch_text(summary.source_page_url)
        (detail_dir / f"{summary.slug}.html").write_text(detail_html, encoding="utf-8")
        fetched += 1
        if delay_seconds > 0:
            time.sleep(delay_seconds)

    return {
        "listing_path": str(listing_path),
        "detail_dir": str(detail_dir),
        "fetched_details": fetched,
    }
