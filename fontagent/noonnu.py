from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html import unescape
from typing import Optional
from pathlib import Path
import time
from urllib.parse import urlsplit, urlunsplit

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


def parse_sitemap_xml(xml: str, base_url: str = "https://noonnu.cc/") -> list[NoonnuSummary]:
    summaries: list[NoonnuSummary] = []
    seen: set[str] = set()

    for match in re.finditer(r"<loc>(?P<loc>.*?)</loc>", xml, re.I | re.S):
        loc = _clean(match.group("loc"))
        if "/font_page/" not in loc:
            continue
        slug = loc.rstrip("/").split("/")[-1]
        if not slug or slug in seen:
            continue
        summaries.append(
            NoonnuSummary(
                slug=slug,
                family=slug.replace("-", " ").title(),
                source_page_url=absolutize(base_url, loc),
            )
        )
        seen.add(slug)

    return summaries


def _merge_summaries(*groups: list[NoonnuSummary]) -> list[NoonnuSummary]:
    merged: list[NoonnuSummary] = []
    seen: set[str] = set()
    for group in groups:
        for summary in group:
            if summary.slug in seen:
                continue
            merged.append(summary)
            seen.add(summary.slug)
    return merged


def _sort_summaries_for_fetch(summaries: list[NoonnuSummary]) -> list[NoonnuSummary]:
    def key(summary: NoonnuSummary) -> tuple[int, int | str]:
        if summary.slug.isdigit():
            return (0, -int(summary.slug))
        return (1, summary.slug)

    return sorted(summaries, key=key)


def _synthetic_listing_html(summaries: list[NoonnuSummary]) -> str:
    anchors = "\n".join(
        f'    <a href="/font_page/{summary.slug}">{summary.family}</a>'
        for summary in summaries
    )
    return "<html><body>\n" + anchors + "\n</body></html>\n"


def _default_sitemap_url(listing_url: str) -> str:
    parts = urlsplit(listing_url)
    path = "/sitemap.xml"
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


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
    sitemap_url: Optional[str] = None,
) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    detail_dir = output_dir / "details"
    detail_dir.mkdir(parents=True, exist_ok=True)

    listing_html = fetch_text(listing_url)
    source_listing_path = output_dir / "listing.source.html"
    source_listing_path.write_text(listing_html, encoding="utf-8")

    listing_summaries = parse_listing_html(listing_html, base_url=listing_url)
    sitemap_path = None
    sitemap_summaries: list[NoonnuSummary] = []
    sitemap_target = sitemap_url or _default_sitemap_url(listing_url)
    try:
        sitemap_xml = fetch_text(sitemap_target)
        sitemap_path = output_dir / "sitemap.xml"
        sitemap_path.write_text(sitemap_xml, encoding="utf-8")
        sitemap_summaries = _sort_summaries_for_fetch(parse_sitemap_xml(sitemap_xml, base_url=listing_url))
    except Exception:
        sitemap_path = None
        sitemap_summaries = []

    summaries = _merge_summaries(listing_summaries, sitemap_summaries)
    listing_path = output_dir / "listing.html"
    listing_path.write_text(_synthetic_listing_html(summaries), encoding="utf-8")
    fetched = 0
    skipped_existing = 0
    failures: list[dict[str, str]] = []
    for summary in summaries[:limit]:
        detail_path = detail_dir / f"{summary.slug}.html"
        if detail_path.exists():
            skipped_existing += 1
            continue
        try:
            detail_html = fetch_text(summary.source_page_url)
            detail_path.write_text(detail_html, encoding="utf-8")
            fetched += 1
        except Exception as exc:
            failures.append(
                {
                    "slug": summary.slug,
                    "source_page_url": summary.source_page_url,
                    "error": str(exc),
                }
            )
        if delay_seconds > 0:
            time.sleep(delay_seconds)

    failures_path = output_dir / "failed_details.json"
    if failures:
        failures_path.write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "listing_path": str(listing_path),
        "source_listing_path": str(source_listing_path),
        "sitemap_path": str(sitemap_path) if sitemap_path else None,
        "summary_count": len(summaries),
        "listing_summary_count": len(listing_summaries),
        "sitemap_summary_count": len(sitemap_summaries),
        "detail_dir": str(detail_dir),
        "fetched_details": fetched,
        "skipped_existing": skipped_existing,
        "failed_count": len(failures),
        "failed_details_path": str(failures_path) if failures else None,
    }
