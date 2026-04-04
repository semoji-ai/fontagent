from __future__ import annotations

import re
import urllib.request
from datetime import datetime, timezone
from html import unescape
from urllib.parse import parse_qs, quote_plus, urlparse, urlsplit, urlunsplit


SEARCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

DEFAULT_DISCOVERY_QUERIES = [
    "무료 한글 폰트 공식 다운로드",
    "기업 무료 폰트 공식 다운로드",
    "오픈소스 한글 폰트 다운로드",
    "코딩용 한글 폰트 GitHub",
]

DISCOVERY_QUERY_SETS = {
    "default": DEFAULT_DISCOVERY_QUERIES,
    "display-ko": [
        "무료 한글 제목용 폰트 공식 다운로드",
        "무료 한글 포스터 폰트 공식 다운로드",
        "무료 레트로 한글 폰트 공식 다운로드",
        "무료 손글씨 폰트 상업적 이용 공식 다운로드",
        "브랜드 무료 폰트 배포 공식 다운로드",
    ],
    "editorial-ko": [
        "무료 명조 타이틀 폰트 공식 다운로드",
        "무료 에디토리얼 한글 폰트 공식 다운로드",
        "무료 감성 한글 명조 공식 다운로드",
        "브랜드 serif 무료 폰트 공식 다운로드",
    ],
    "playful-ko": [
        "무료 키치 한글 폰트 공식 다운로드",
        "무료 귀여운 한글 제목 폰트 공식 다운로드",
        "무료 게임풍 한글 폰트 공식 다운로드",
        "무료 픽셀 한글 폰트 공식 다운로드",
    ],
    "display-en": [
        "free display font official download",
        "free editorial font official download",
        "free poster font OFL download",
        "free branding font official foundry download",
        "open source display font official download",
    ],
}

BLOCKED_DOMAINS = {
    "noonnu.cc",
    "fonts.google.com",
    "gorgopage.com",
    "tistory.com",
    "blog.naver.com",
    "m.blog.naver.com",
    "brunch.co.kr",
    "velog.io",
    "ppss.kr",
    "namu.wiki",
    "wikidocs.net",
}

OFFICIAL_DOMAIN_HINTS = {
    "bingfont.co.kr",
    "github.com",
    "gmarket.co.kr",
    "goodchoice.kr",
    "naver.com",
    "nexon.com",
    "hancom.com",
    "font.co.kr",
    "copyright.or.kr",
    "cafe24.com",
    "jeju.go.kr",
    "woowahan.com",
    "fontshare.com",
    "velvetyne.fr",
    "theleagueofmoveabletype.com",
    "collletttivo.it",
    "indestructibletype.com",
    "kbl.or.kr",
    "seoul.go.kr",
    "eulyoo.co.kr",
    "lottemart.com",
    "yes24.com",
    "bookk.co.kr",
}

KEYWORD_RE = re.compile(r"(font|fonts|폰트|글꼴|서체)", re.I)
FREE_RE = re.compile(r"(무료|free|오픈소스|open\s*source|라이선스|license|다운로드|download)", re.I)


def _clean(text: str) -> str:
    text = unescape(re.sub(r"<[^>]+>", " ", text))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _search_url(query: str) -> str:
    return f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"


def _fetch_search_html(query: str, timeout: int = 20) -> str:
    request = urllib.request.Request(_search_url(query), headers=SEARCH_HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _unwrap_duckduckgo_url(url: str) -> str:
    unescaped = unescape(url)
    if unescaped.startswith("//"):
        unescaped = f"https:{unescaped}"
    parsed = urlparse(unescaped)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path == "/l/":
        params = parse_qs(parsed.query)
        target = params.get("uddg", [""])[0]
        if target:
            return target
    return unescaped


def normalize_result_url(url: str) -> str:
    parsed = urlsplit(_unwrap_duckduckgo_url(url))
    query_params = []
    if parsed.query:
        for part in parsed.query.split("&"):
            if not part:
                continue
            key = part.split("=", 1)[0].lower()
            if key.startswith("utm_") or key in {"fbclid", "gclid", "ref"}:
                continue
            query_params.append(part)
    return urlunsplit(
        (
            parsed.scheme or "https",
            parsed.netloc.lower(),
            parsed.path.rstrip("/") or "/",
            "&".join(query_params),
            "",
        )
    )


def _candidate_score(title: str, snippet: str, url: str, domain: str) -> int:
    score = 0
    haystack = " ".join([title, snippet, url, domain])
    if KEYWORD_RE.search(haystack):
        score += 3
    if FREE_RE.search(haystack):
        score += 2
    if any(token in domain for token in ("github.com", "naver.com", "cafe24.com", "woowahan.com", "co.kr", "go.kr")):
        score += 1
    if any(token in url.lower() for token in ("/font", "/fonts", "typeface", "d2coding")):
        score += 1
    return score


def _matches_domain(domain: str, patterns: set[str]) -> bool:
    return any(domain == pattern or domain.endswith(f".{pattern}") for pattern in patterns)


def _looks_official(domain: str) -> bool:
    return _matches_domain(domain, OFFICIAL_DOMAIN_HINTS) or domain.endswith(".go.kr")


def classify_candidate_status(domain: str) -> tuple[str, str]:
    if _looks_official(domain):
        return "official_candidate", "공식 또는 준공식 배포처로 보이는 도메인입니다."
    return "needs_review", "공식 배포처 여부를 추가 확인해야 합니다."


def parse_duckduckgo_results(
    html: str,
    query: str,
    limit: int = 10,
    blocked_domains: set[str] | None = None,
) -> list[dict]:
    blocked_domains = blocked_domains or set()
    results: list[dict] = []
    seen: set[str] = set()

    pattern = re.compile(
        r'<div class="result results_links.*?'
        r'<a rel="nofollow" class="result__a" href="(?P<href>[^"]+)">(?P<title>.*?)</a>.*?'
        r'<a class="result__url"[^>]*>(?P<display_url>.*?)</a>.*?'
        r'<a class="result__snippet"[^>]*>(?P<snippet>.*?)</a>',
        re.S,
    )
    for match in pattern.finditer(html):
        result_url = _unwrap_duckduckgo_url(match.group("href"))
        normalized_url = normalize_result_url(result_url)
        domain = urlparse(normalized_url).netloc.lower()
        if not normalized_url or _matches_domain(domain, blocked_domains):
            continue
        title = _clean(match.group("title"))
        snippet = _clean(match.group("snippet"))
        if any(token in f"{title} {snippet}".lower() for token in ("추천", "총정리", "top ", "사이트")) and not _looks_official(domain):
            continue
        score = _candidate_score(title, snippet, normalized_url, domain)
        if score < 4:
            continue
        if normalized_url in seen:
            continue
        results.append(
            {
                "query": query,
                "title": title,
                "snippet": snippet,
                "result_url": result_url,
                "normalized_url": normalized_url,
                "domain": domain,
                "discovery_source": "duckduckgo",
                "status": classify_candidate_status(domain)[0],
                "discovered_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "note": classify_candidate_status(domain)[1],
            }
        )
        seen.add(normalized_url)
        if len(results) >= limit:
            break
    return results


def discover_web_candidates(
    queries: list[str] | None = None,
    limit_per_query: int = 10,
    blocked_domains: set[str] | None = None,
) -> list[dict]:
    queries = queries or DEFAULT_DISCOVERY_QUERIES
    blocked = set(BLOCKED_DOMAINS)
    if blocked_domains:
        blocked.update(domain.lower() for domain in blocked_domains)

    discovered: list[dict] = []
    seen: set[str] = set()
    for query in queries:
        html = _fetch_search_html(query)
        for item in parse_duckduckgo_results(html, query=query, limit=limit_per_query, blocked_domains=blocked):
            if item["normalized_url"] in seen:
                continue
            discovered.append(item)
            seen.add(item["normalized_url"])
    return discovered


def get_discovery_queries(query_set: str) -> list[str]:
    try:
        return list(DISCOVERY_QUERY_SETS[query_set])
    except KeyError as exc:
        raise KeyError(f"Unknown discovery query set: {query_set}") from exc
