from __future__ import annotations

import json
import re
import urllib.request
from html import unescape
from pathlib import PurePosixPath
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from .discovery import normalize_result_url
from .http_utils import fetch_text
from .resolver import absolutize, classify_download_type


TAG_RE = re.compile(r"<[^>]+>")
FONT_FACE_RE = re.compile(r"@font-face\s*{(?P<body>.*?)}", re.S | re.I)
FONT_FAMILY_RE = re.compile(r"font-family:\s*['\"]?(?P<family>[^;'\"\n]+)", re.I)
FONT_URL_RE = re.compile(
    r"url\((?P<quote>['\"]?)(?P<url>[^)'\"]+)(?P=quote)\)\s*(?:format\((?P<format_quote>['\"]?)(?P<format>[^)'\"]+)(?P=format_quote)\))?",
    re.I,
)
HANCOM_FAMILY_BY_ARCHIVE = {
    "hancomhoonminjeongeumv.zip": "한컴훈민정음세로쓰기체",
    "hancomhoonminjeongeumh.zip": "한컴훈민정음가로쓰기체",
}
GONGU_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}
GONGU_LIST_URL = "https://gongu.copyright.or.kr/gongu/bbs/B0000018/list.do?menuNo=200195"
GOODCHOICE_SOURCE_URL = "https://www.goodchoice.kr/font/mobile"
GOODCHOICE_CSS_URL = "https://static.goodchoice.kr/fonts/jalnan/font.css"
GMARKET_SOURCE_URL = "https://gds.gmarket.co.kr/"
CAFE24_SOURCE_URL = "https://www.cafe24.com/story/use/cafe24pro_font.html"
CAFE24_CATALOG_JSON_URL = "https://img.cafe24.com/csdstatic/freefonts/data/fonts_ko.json"
CAFE24_DESIGN_FONT_IDS = {
    "cafe24-pro-up",
    "cafe24-ssurround",
    "cafe24-classictype",
    "cafe24-oneprettynight",
    "cafe24-shiningstar",
    "cafe24-supermagic-bold",
}
JEJU_SOURCE_URL = "https://www.jeju.go.kr/jeju/symbol/font/infor.htm"
LEAGUE_SOURCE_URL = "https://www.theleagueofmoveabletype.com/"
LEAGUE_FONT_PAGES = [
    {
        "font_id": "league-league-gothic",
        "family": "League Gothic",
        "slug": "league-gothic",
        "source_page_url": "https://www.theleagueofmoveabletype.com/league-gothic",
        "tags": ["english", "display", "poster", "headline", "condensed", "editorial"],
        "recommended_for": ["title", "poster", "thumbnail"],
        "preview_text_en": "LEAGUE GOTHIC FOR TIGHT HEADLINES",
    },
    {
        "font_id": "league-knewave",
        "family": "Knewave",
        "slug": "knewave",
        "source_page_url": "https://www.theleagueofmoveabletype.com/knewave",
        "tags": ["english", "display", "playful", "brush", "poster", "thumbnail"],
        "recommended_for": ["title", "poster", "thumbnail"],
        "preview_text_en": "Knewave Adds Hand-Painted Energy",
    },
]
VELVETYNE_SOURCE_URL = "https://velvetyne.fr/"
VELVETYNE_FONTS = [
    {
        "font_id": "velvetyne-outward",
        "family": "Outward",
        "slug": "outward",
        "source_page_url": "https://velvetyne.fr/fonts/outward/",
        "download_url": "https://velvetyne.fr/download/?font=outward",
        "tags": ["english", "display", "brutalist", "poster", "signage", "experimental"],
        "recommended_for": ["title", "poster", "thumbnail"],
        "preview_text_en": "OUTWARD MAKES BRUTAL HEADLINES",
    },
    {
        "font_id": "velvetyne-interlope",
        "family": "Interlope",
        "slug": "interlope",
        "source_page_url": "https://velvetyne.fr/fonts/interlope/",
        "download_url": "https://velvetyne.fr/download/?font=interlope",
        "tags": ["english", "display", "experimental", "editorial", "poster", "fashion"],
        "recommended_for": ["title", "poster", "cover"],
        "preview_text_en": "Interlope Pushes Editorial Tension",
    },
    {
        "font_id": "velvetyne-backout",
        "family": "BackOut",
        "slug": "backout",
        "source_page_url": "https://velvetyne.fr/fonts/backout/",
        "download_url": "https://velvetyne.fr/download/?font=backout",
        "tags": ["english", "display", "retro", "poster", "headline", "experimental"],
        "recommended_for": ["title", "poster", "thumbnail"],
        "preview_text_en": "BackOut Feels Loud and Offbeat",
    },
]
FONTSHARE_SOURCE_URL = "https://www.fontshare.com/"
FONTSHARE_CURATED_FAMILIES = {
    "satoshi": {
        "font_id": "fontshare-satoshi",
        "family": "Satoshi",
        "tags": ["english", "sans", "branding", "editorial", "ui", "modern"],
        "recommended_for": ["title", "subtitle", "body"],
        "preview_text_en": "Satoshi Shapes Modern Branding",
    },
    "clash-display": {
        "font_id": "fontshare-clash-display",
        "family": "Clash Display",
        "tags": ["english", "display", "editorial", "magazine", "headline", "branding"],
        "recommended_for": ["title", "cover", "poster"],
        "preview_text_en": "Clash Display Commands Attention",
    },
    "cabinet-grotesk": {
        "font_id": "fontshare-cabinet-grotesk",
        "family": "Cabinet Grotesk",
        "tags": ["english", "sans", "editorial", "poster", "branding", "headline"],
        "recommended_for": ["title", "subtitle", "cover"],
        "preview_text_en": "Cabinet Grotesk Feels Contemporary",
    },
    "general-sans": {
        "font_id": "fontshare-general-sans",
        "family": "General Sans",
        "tags": ["english", "sans", "branding", "web", "poster", "ui"],
        "recommended_for": ["title", "subtitle", "body"],
        "preview_text_en": "General Sans Reads Clean and Strong",
    },
    "supreme": {
        "font_id": "fontshare-supreme",
        "family": "Supreme",
        "tags": ["english", "sans", "editorial", "poster", "logo", "screen"],
        "recommended_for": ["title", "subtitle", "body"],
        "preview_text_en": "Supreme Balances Poster and Interface",
    },
    "array": {
        "font_id": "fontshare-array",
        "family": "Array",
        "tags": ["english", "display", "branding", "signage", "poster", "experimental"],
        "recommended_for": ["title", "poster", "thumbnail"],
        "preview_text_en": "Array Builds Experimental Posters",
    },
    "boska": {
        "font_id": "fontshare-boska",
        "family": "Boska",
        "tags": ["english", "serif", "display", "editorial", "magazine", "luxury"],
        "recommended_for": ["title", "cover", "body"],
        "preview_text_en": "Boska Brings Magazine Drama",
    },
    "sentient": {
        "font_id": "fontshare-sentient",
        "family": "Sentient",
        "tags": ["english", "serif", "editorial", "books", "magazine", "cover"],
        "recommended_for": ["title", "body", "cover"],
        "preview_text_en": "Sentient Works for Elegant Reading",
    },
}
GOOGLE_FONTS_SOURCE_URL = "https://fonts.google.com/"
NEXON_SOURCE_URL = "https://brand.nexon.com/brand/fonts"
NEXON_BUNDLE_RE = re.compile(r'src="(?P<src>/assets/index-[^"]+\.js)"', re.I)
NEXON_RESOURCE_RE = re.compile(r"/resources/(?P<filename>[A-Za-z0-9_. -]+\.zip)")
NEXON_FAMILY_OVERRIDES = {
    "NEXON_Lv1_Gothic": "넥슨 Lv.1 고딕",
    "NEXON_Lv2_Gothic": "넥슨 Lv.2 고딕",
    "NEXON_Bazzi": "넥슨 배찌체",
    "NEXON_Football_Gothic": "넥슨 풋볼 고딕",
    "NEXON_Maplestory": "메이플스토리",
    "DNF_BitBit_v2": "DNF 비트비트 v2",
    "DNF_ForgedBlade": "DNF 연단된칼날",
    "NEXON_Warhaven": "워헤이븐",
    "NEXON_Kart_Gothic": "넥슨 카트 고딕",
    "Mabinogi_Classic": "마비노기 클래식",
}
WOOWAHAN_SOURCE_URL = "https://www.woowahan.com/fonts"
WOOWAHAN_SCRIPT_RE = re.compile(r"https://woowahan-cdn\.woowahan\.com/static/js/[^\"']+\.js")
WOOWAHAN_FONT_FILE_RE = re.compile(r"static/fonts/(?P<file>[^?\"'\s]+\.(?:zip|ttf|otf))", re.I)
WOOWAHAN_FONT_FALLBACK_FILES = [
    "BMDOHYEON_otf.otf",
    "BMDOHYEON_ttf.ttf",
    "BMEULJIRO.otf",
    "BMEULJIROTTF.ttf",
    "BMEuljiro10yearslater.ttf",
    "BMEuljiro10yearslaterOTF.otf",
    "BMEuljirooraeorae.ttf",
    "BMEuljirooraeoraeOTF.otf",
    "BMGEULLIM.zip",
    "BMHANNAAir_otf.otf",
    "BMHANNAAir_ttf.ttf",
    "BMHANNAPro.ttf",
    "BMHANNAProOTF.otf",
    "BMHANNA_11yrs_otf.otf",
    "BMHANNA_11yrs_ttf.ttf",
    "BMJUA_otf.otf",
    "BMJUA_ttf.ttf",
    "BMKIRANGHAERANG-OTF.otf",
    "BMKIRANGHAERANG-TTF.ttf",
    "BMKkubulim.otf",
    "BMKkubulimTTF.ttf",
    "BMYEONSUNG_otf.otf",
    "BMYEONSUNG_ttf.ttf",
]
WOOWAHAN_FAMILY_OVERRIDES = {
    "BMDOHYEON": "배민 도현체",
    "BMEULJIRO": "배민 을지로체",
    "BMEuljiro10yearslater": "배민 을지로10년후",
    "BMEuljirooraeorae": "배민 을지로오래오래",
    "BMGEULLIM": "배민 글림체",
    "BMHANNAAir": "배민 한나체 Air",
    "BMHANNAPro": "배민 한나체 Pro",
    "BMHANNA_11yrs": "배민 한나체 11년",
    "BMJUA": "배민 주아체",
    "BMKIRANGHAERANG": "배민 기랑해랑체",
    "BMKkubulim": "배민 꾸불림체",
    "BMYEONSUNG": "배민 연성체",
}
GOOGLE_DISPLAY_FONTS = [
    {
        "font_id": "google-anton",
        "family": "Anton",
        "slug": "anton",
        "source_page_url": "https://fonts.google.com/specimen/Anton",
        "download_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf",
        "tags": ["english", "display", "headline", "poster", "bold", "condensed"],
        "recommended_for": ["title", "poster", "thumbnail"],
        "preview_text_en": "ANTON MAKES THE HEADLINE LOUD",
    },
    {
        "font_id": "google-bebas-neue",
        "family": "Bebas Neue",
        "slug": "bebas-neue",
        "source_page_url": "https://fonts.google.com/specimen/Bebas+Neue",
        "download_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/bebasneue/BebasNeue-Regular.ttf",
        "tags": ["english", "display", "headline", "poster", "thumbnail", "condensed"],
        "recommended_for": ["title", "thumbnail", "poster"],
        "preview_text_en": "BEBAS NEUE FOR CLEAN HEADLINES",
    },
    {
        "font_id": "google-abril-fatface",
        "family": "Abril Fatface",
        "slug": "abril-fatface",
        "source_page_url": "https://fonts.google.com/specimen/Abril+Fatface",
        "download_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/abrilfatface/AbrilFatface-Regular.ttf",
        "tags": ["english", "display", "editorial", "luxury", "serif", "headline"],
        "recommended_for": ["title", "cover"],
        "preview_text_en": "Abril Fatface Gives Editorial Drama",
    },
    {
        "font_id": "google-dm-serif-display",
        "family": "DM Serif Display",
        "slug": "dm-serif-display",
        "source_page_url": "https://fonts.google.com/specimen/DM+Serif+Display",
        "download_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/dmserifdisplay/DMSerifDisplay-Regular.ttf",
        "tags": ["english", "display", "editorial", "serif", "luxury", "body"],
        "recommended_for": ["title", "body"],
        "preview_text_en": "DM Serif Display for Elegant Covers",
    },
    {
        "font_id": "google-archivo-black",
        "family": "Archivo Black",
        "slug": "archivo-black",
        "source_page_url": "https://fonts.google.com/specimen/Archivo+Black",
        "download_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/archivoblack/ArchivoBlack-Regular.ttf",
        "tags": ["english", "display", "sans", "headline", "tech", "branding"],
        "recommended_for": ["title", "subtitle"],
        "preview_text_en": "Archivo Black Built for Branding",
    },
    {
        "font_id": "google-bungee",
        "family": "Bungee",
        "slug": "bungee",
        "source_page_url": "https://fonts.google.com/specimen/Bungee",
        "download_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/bungee/Bungee-Regular.ttf",
        "tags": ["english", "display", "playful", "retro", "signage", "headline"],
        "recommended_for": ["title", "poster", "thumbnail"],
        "preview_text_en": "Bungee Brings Retro Energy",
    },
    {
        "font_id": "google-fraunces",
        "family": "Fraunces",
        "slug": "fraunces",
        "source_page_url": "https://fonts.google.com/specimen/Fraunces",
        "download_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/fraunces/Fraunces%5BSOFT,WONK,opsz,wght%5D.ttf",
        "tags": ["english", "display", "serif", "editorial", "luxury", "poster"],
        "recommended_for": ["title", "cover", "poster"],
        "preview_text_en": "Fraunces Brings Editorial Contrast",
        "variable_font": True,
    },
    {
        "font_id": "google-space-grotesk",
        "family": "Space Grotesk",
        "slug": "space-grotesk",
        "source_page_url": "https://fonts.google.com/specimen/Space+Grotesk",
        "download_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf",
        "tags": ["english", "sans", "tech", "branding", "ui", "modern"],
        "recommended_for": ["title", "subtitle", "body"],
        "preview_text_en": "Space Grotesk Fits Modern Interfaces",
        "variable_font": True,
    },
    {
        "font_id": "google-orbitron",
        "family": "Orbitron",
        "slug": "orbitron",
        "source_page_url": "https://fonts.google.com/specimen/Orbitron",
        "download_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/orbitron/Orbitron%5Bwght%5D.ttf",
        "tags": ["english", "display", "tech", "sci-fi", "branding", "headline"],
        "recommended_for": ["title", "poster", "thumbnail"],
        "preview_text_en": "Orbitron Signals Future Tech",
        "variable_font": True,
    },
    {
        "font_id": "google-audiowide",
        "family": "Audiowide",
        "slug": "audiowide",
        "source_page_url": "https://fonts.google.com/specimen/Audiowide",
        "download_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/audiowide/Audiowide-Regular.ttf",
        "tags": ["english", "display", "tech", "arcade", "headline", "retro"],
        "recommended_for": ["title", "thumbnail", "poster"],
        "preview_text_en": "Audiowide Channels Arcade Futures",
    },
    {
        "font_id": "google-monoton",
        "family": "Monoton",
        "slug": "monoton",
        "source_page_url": "https://fonts.google.com/specimen/Monoton",
        "download_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/monoton/Monoton-Regular.ttf",
        "tags": ["english", "display", "retro", "signage", "neon", "poster"],
        "recommended_for": ["title", "poster", "thumbnail"],
        "preview_text_en": "Monoton Turns Titles into Neon Signs",
    },
    {
        "font_id": "google-alfa-slab-one",
        "family": "Alfa Slab One",
        "slug": "alfa-slab-one",
        "source_page_url": "https://fonts.google.com/specimen/Alfa+Slab+One",
        "download_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/alfaslabone/AlfaSlabOne-Regular.ttf",
        "tags": ["english", "display", "slab", "poster", "bold", "headline"],
        "recommended_for": ["title", "poster"],
        "preview_text_en": "Alfa Slab One Anchors Bold Posters",
    },
    {
        "font_id": "google-bricolage-grotesque",
        "family": "Bricolage Grotesque",
        "slug": "bricolage-grotesque",
        "source_page_url": "https://fonts.google.com/specimen/Bricolage+Grotesque",
        "download_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/bricolagegrotesque/BricolageGrotesque%5Bopsz,wdth,wght%5D.ttf",
        "tags": ["english", "display", "branding", "editorial", "sans", "fashion"],
        "recommended_for": ["title", "cover", "branding"],
        "preview_text_en": "Bricolage Grotesque Feels Contemporary",
        "variable_font": True,
    },
    {
        "font_id": "google-syne",
        "family": "Syne",
        "slug": "syne",
        "source_page_url": "https://fonts.google.com/specimen/Syne",
        "download_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/syne/Syne%5Bwght%5D.ttf",
        "tags": ["english", "display", "fashion", "experimental", "poster", "branding"],
        "recommended_for": ["title", "poster", "branding"],
        "preview_text_en": "Syne Pushes Fashion-Forward Typography",
        "variable_font": True,
    },
    {
        "font_id": "google-cormorant-garamond",
        "family": "Cormorant Garamond",
        "slug": "cormorant-garamond",
        "source_page_url": "https://fonts.google.com/specimen/Cormorant+Garamond",
        "download_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/cormorantgaramond/CormorantGaramond%5Bwght%5D.ttf",
        "tags": ["english", "serif", "editorial", "luxury", "body", "cover"],
        "recommended_for": ["title", "body", "cover"],
        "preview_text_en": "Cormorant Garamond for Elegant Pages",
        "variable_font": True,
    },
]


def _clean(text: str) -> str:
    text = unescape(TAG_RE.sub(" ", text))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _fetch_browser_text(url: str, timeout: int = 30) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _guess_use_cases(tags: list[str]) -> list[str]:
    joined = " ".join(tags)
    use_cases = []
    if any(token in joined for token in ("title", "제목", "serif", "명조", "손글씨")):
        use_cases.append("title")
    if any(token in joined for token in ("subtitle", "자막", "sans", "고딕", "코딩")):
        use_cases.append("subtitle")
    if not use_cases:
        use_cases.append("body")
    return use_cases


def _guess_format(url: str) -> str:
    lower = url.lower()
    for ext in ("ttf", "otf", "woff2", "woff", "zip"):
        if f".{ext}" in lower:
            return ext
    return "html" if url else ""


def _infer_hancom_family_from_href(href: str) -> str:
    archive_name = PurePosixPath(href).name.lower()
    if archive_name in HANCOM_FAMILY_BY_ARCHIVE:
        return HANCOM_FAMILY_BY_ARCHIVE[archive_name]
    stem = PurePosixPath(href).stem
    stem = re.sub(r"^hancom", "", stem, flags=re.I)
    stem = re.sub(r"(?<!^)([A-Z])", r" \1", stem).strip()
    return stem or archive_name


def _parse_fonco_license_flags(license_label: str) -> tuple[str, bool, bool, bool]:
    if "모든 라이선스" in license_label:
        return "fonco-all-license", True, True, False
    if "스톡 제휴 라이선스" in license_label:
        return "fonco-stock-license", True, True, False
    return "fonco-restricted-license", False, False, False


def _extract_font_face_sources(css_text: str, css_url: str) -> list[dict]:
    records: list[dict] = []
    for match in FONT_FACE_RE.finditer(css_text):
        body = match.group("body")
        family_match = FONT_FAMILY_RE.search(body)
        if not family_match:
            continue
        family = _clean(family_match.group("family"))
        sources = []
        for url_match in FONT_URL_RE.finditer(body):
            font_url = urljoin(css_url, url_match.group("url").strip())
            fmt = (url_match.group("format") or "").strip().lower()
            if fmt == "truetype":
                fmt = "ttf"
            elif fmt == "opentype":
                fmt = "otf"
            elif fmt == "embedded-opentype":
                fmt = "eot"
            sources.append(
                {
                    "url": font_url,
                    "format": fmt or _guess_format(font_url),
                }
            )
        if not sources:
            continue
        records.append({"family": family, "sources": sources})
    return records


def _pick_preferred_font_source(sources: list[dict]) -> dict:
    order = {"ttf": 0, "otf": 1, "woff2": 2, "woff": 3, "embedded-opentype": 4, "eot": 5}
    return min(sources, key=lambda item: order.get(item["format"], 99))


def _choose_fonco_preview_url(html: str) -> str:
    selected_option_match = re.search(
        r'<option value="(?P<file>[^"]+\.(?:woff2?|ttf|otf))"[^>]*selected',
        html,
        re.I,
    )
    preview_urls = re.findall(
        r'src:\s*url\("(?P<url>https://cdn\.font\.co\.kr/[^"]+\.(?:woff2?|ttf|otf)(?:\?[^"]*)?)"\)',
        html,
        re.I,
    )
    if not preview_urls:
        return ""
    if selected_option_match:
        selected_name = selected_option_match.group("file")
        for url in preview_urls:
            if selected_name in url:
                return url
    return preview_urls[0]


def _upsert_query_param(url: str, key: str, value: str | int) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query[key] = str(value)
    return urlunparse(parsed._replace(query=urlencode(query)))


def _parse_gongu_license(license_text: str) -> tuple[str, bool, bool, bool, bool]:
    cleaned = _clean(license_text)
    if "OFL" in cleaned:
        return "ofl", True, True, True, True
    if any(token in cleaned for token in ("제1유형", "1유형", "1 유형")):
        return "kogl-type1", True, True, True, False
    if any(token in cleaned for token in ("제2유형", "2유형", "2 유형")) or "상업적이용금지" in cleaned or "상업적 이용금지" in cleaned:
        return "kogl-type2", False, False, False, False
    if any(token in cleaned for token in ("제3유형", "3유형", "3 유형")) or "변경금지" in cleaned:
        return "kogl-type3", True, True, False, False
    if any(token in cleaned for token in ("제4유형", "4유형", "4 유형")):
        return "kogl-type4", False, False, False, False
    return "gongu-license", False, False, False, False


def _extract_gongu_download_url(download_popup_html: str, wrt_sn: str) -> tuple[str, str]:
    pattern = re.compile(
        r'//DEXT5UPLOAD\.AddUploadedFile\("?(?P<file_sn>\d+)"?,\s*"(?P<filename>[^"]+)",\s*'
        r"'(?P<path>/gongu/wrt/cmmn/wrtFileDownload\.do\?wrtSn=\d+&fileSn=\d+)'",
        re.S,
    )
    candidates: list[tuple[str, str]] = []
    for match in pattern.finditer(download_popup_html):
        filename = _clean(match.group("filename"))
        path = match.group("path").strip()
        if not filename or not path:
            continue
        candidates.append((filename, urljoin("https://gongu.copyright.or.kr", path)))

    priority_exts = (".zip", ".ttf", ".otf", ".woff2", ".woff")
    for ext in priority_exts:
        for filename, url in candidates:
            if filename.lower().endswith(ext):
                return url, filename

    if candidates:
        return candidates[0][1], candidates[0][0]
    return "", f"{wrt_sn}.zip"


def parse_naver_fonts_html(html: str, source_page_url: str = "https://hangeul.naver.com/font") -> list[dict]:
    pattern = re.compile(
        r'<li[^>]+class="(?P<css_class>[^"]+)"[^>]*>.*?'
        r'<strong class="font-name">\s*(?P<family>.*?)\s*</strong>.*?'
        r'data-category="(?P<category>[^"]+)".*?'
        r'data-type="(?P<font_type>[^"]+)".*?'
        r'<button[^>]+class="btn-download"[^>]+data-url="(?P<download_url>[^"]+)"\s+'
        r'data-font-id="(?P<naver_id>[^"]+)"',
        re.S,
    )
    records: list[dict] = []
    seen: set[str] = set()
    for match in pattern.finditer(html):
        family = _clean(match.group("family"))
        naver_id = match.group("naver_id").strip()
        download_url = match.group("download_url").strip()
        category = _clean(match.group("category"))
        font_type = _clean(match.group("font_type"))
        if not family or not naver_id or not download_url:
            continue
        font_id = f"naver-{naver_id.lower()}"
        if font_id in seen:
            continue
        seen.add(font_id)
        tags = [tag for tag in [category, font_type, "naver"] if tag]
        category_path = category if category in {"nanum", "maru", "clova"} else "font"
        records.append(
            {
                "font_id": font_id,
                "family": family,
                "slug": naver_id,
                "source_site": "naver_hangeul",
                "source_page_url": f"https://hangeul.naver.com/font/{category_path}",
                "homepage_url": source_page_url,
                "license_id": "naver-font-commercial",
                "license_summary": "네이버 글꼴 모음 페이지 기준 라이선스: 상업적 사용 허용.",
                "commercial_use_allowed": True,
                "video_use_allowed": True,
                "web_embedding_allowed": True,
                "redistribution_allowed": False,
                "languages": ["ko"],
                "tags": tags,
                "recommended_for": _guess_use_cases(tags),
                "preview_text_ko": f"{family} 폰트. 네이버 글꼴 모음에서 제공하는 무료 한글 폰트입니다.",
                "preview_text_en": family,
                "download_type": classify_download_type(download_url),
                "download_url": download_url,
                "download_source": "canonical",
                "format": _guess_format(download_url),
                "variable_font": False,
            }
        )
    return records


def fetch_naver_fonts(source_page_url: str = "https://hangeul.naver.com/font/nanum") -> list[dict]:
    return parse_naver_fonts_html(fetch_text(source_page_url, timeout=30), source_page_url=source_page_url)


def parse_hancom_fonts_html(
    html: str,
    source_page_url: str = "https://font.hancom.com/pc/main/main.php",
) -> list[dict]:
    pattern = re.compile(r"<li>\s*(?P<content>.*?)</li>", re.S)
    records: list[dict] = []
    seen: set[str] = set()
    for match in pattern.finditer(html):
        content = match.group("content")
        href_match = re.search(r'<a href="(?P<href>[^"]+\.zip)"[^>]*>서체 다운로드</a>', content, re.S)
        if not href_match:
            continue
        href = href_match.group("href").strip()
        family_match = re.search(r'<div class="box1">(?P<family>.*?)</div>', content, re.S)
        family = _clean(family_match.group("family")) if family_match else _infer_hancom_family_from_href(href)
        download_url = urljoin(source_page_url, href)
        slug = re.sub(r"[^a-z0-9]+", "-", family.lower()).strip("-") or re.sub(
            r"[^a-z0-9]+", "-", href.lower()
        ).strip("-")
        font_id = f"hancom-{slug}"
        if font_id in seen:
            continue
        seen.add(font_id)
        tags = ["hancom", "고딕" if "산스" in family else "명조" if "훈민정음" in family else "display"]
        records.append(
            {
                "font_id": font_id,
                "family": family,
                "slug": slug,
                "source_site": "hancom",
                "source_page_url": source_page_url,
                "homepage_url": "https://font.hancom.com/",
                "license_id": "hancom-free-font",
                "license_summary": "한글과컴퓨터 무료 서체 페이지에서 제공하는 무료 폰트입니다.",
                "commercial_use_allowed": True,
                "video_use_allowed": True,
                "web_embedding_allowed": True,
                "redistribution_allowed": False,
                "languages": ["ko"],
                "tags": tags,
                "recommended_for": _guess_use_cases(tags),
                "preview_text_ko": f"{family} 폰트. 한글과컴퓨터에서 제공하는 무료 한글 폰트입니다.",
                "preview_text_en": family,
                "download_type": classify_download_type(download_url),
                "download_url": download_url,
                "download_source": "canonical",
                "format": _guess_format(download_url),
                "variable_font": False,
            }
        )
    return records


def fetch_hancom_fonts(source_page_url: str = "https://font.hancom.com/pc/main/main.php") -> list[dict]:
    return parse_hancom_fonts_html(fetch_text(source_page_url, timeout=30), source_page_url=source_page_url)


def parse_goodchoice_jalnan_css(
    css_text: str,
    css_url: str = GOODCHOICE_CSS_URL,
    source_page_url: str = GOODCHOICE_SOURCE_URL,
) -> list[dict]:
    records = []
    for face in _extract_font_face_sources(css_text, css_url):
        if face["family"] != "yg-jalnan":
            continue
        selected = _pick_preferred_font_source(face["sources"])
        download_url = selected["url"]
        records.append(
            {
                "font_id": "goodchoice-yg-jalnan",
                "family": "여기어때잘난체",
                "slug": "yg-jalnan",
                "source_site": "goodchoice_brand",
                "source_page_url": source_page_url,
                "homepage_url": source_page_url,
                "license_id": "goodchoice-brand-font",
                "license_summary": "여기어때 공식 서체 페이지에서 제공하는 무료 브랜드 폰트입니다.",
                "commercial_use_allowed": True,
                "video_use_allowed": True,
                "web_embedding_allowed": True,
                "redistribution_allowed": False,
                "languages": ["ko"],
                "tags": ["brand", "display", "title", "thumbnail", "playful", "잘난체", "goodchoice"],
                "recommended_for": ["title", "thumbnail"],
                "preview_text_ko": "여기어때잘난체. 썸네일과 제목 카드에 잘 어울리는 브랜드 디스플레이 폰트입니다.",
                "preview_text_en": "Goodchoice Jalnan",
                "download_type": classify_download_type(download_url),
                "download_url": download_url,
                "download_source": "canonical",
                "format": _guess_format(download_url),
                "variable_font": False,
            }
        )
    return records


def fetch_goodchoice_fonts(
    source_page_url: str = GOODCHOICE_SOURCE_URL,
    css_url: str = GOODCHOICE_CSS_URL,
) -> list[dict]:
    return parse_goodchoice_jalnan_css(
        fetch_text(css_url, timeout=30),
        css_url=css_url,
        source_page_url=source_page_url,
    )


def parse_cafe24_catalog(
    payload: dict,
    source_page_url: str = CAFE24_SOURCE_URL,
) -> list[dict]:
    fonts = payload.get("fonts") or []
    records: list[dict] = []
    seen: set[str] = set()
    for item in fonts:
        font_id = (item.get("id") or "").strip().lower()
        if font_id not in CAFE24_DESIGN_FONT_IDS or font_id in seen:
            continue
        seen.add(font_id)
        family = _clean(item.get("nameKr") or item.get("nameEn") or font_id)
        download_url = absolutize(source_page_url, item.get("downloadUrl", ""))
        raw_tags = item.get("tags") or []
        tags = ["brand", "display", "cafe24"]
        tags.extend(_clean(tag).lower() for tag in raw_tags if _clean(tag))
        lowered = " ".join(tags + [family.lower()])
        if any(token in lowered for token in ("우아한", "classic", "클래식")):
            tags.append("editorial")
        if any(token in lowered for token in ("별", "빛", "magic", "마법")):
            tags.append("playful")
        if any(token in lowered for token in ("프로", "모던", "비즈니스")):
            tags.append("branding")
        if any(token in lowered for token in ("굵은", "강조", "bold")):
            tags.append("poster")
        tags = list(dict.fromkeys(tags))
        recommended_for = ["title", "thumbnail"]
        if any(token in lowered for token in ("editorial", "우아한", "클래식")):
            recommended_for.append("cover")
        if any(token in lowered for token in ("poster", "강조")):
            recommended_for.append("poster")
        records.append(
            {
                "font_id": font_id,
                "family": family,
                "slug": font_id,
                "source_site": "cafe24_brand",
                "source_page_url": source_page_url,
                "homepage_url": "https://fonts.cafe24.com/",
                "license_id": "cafe24-brand-font",
                "license_summary": "Cafe24 공식 무료 폰트 카탈로그에서 제공하는 브랜드 폰트입니다.",
                "commercial_use_allowed": True,
                "video_use_allowed": True,
                "web_embedding_allowed": False,
                "redistribution_allowed": False,
                "languages": ["ko"],
                "tags": tags,
                "recommended_for": list(dict.fromkeys(recommended_for)),
                "preview_text_ko": f"{family}. 브랜드 타이틀, 썸네일, 포스터용으로 쓰기 좋은 카페24 디스플레이 폰트입니다.",
                "preview_text_en": item.get("nameEn") or family,
                "download_type": classify_download_type(download_url),
                "download_url": download_url,
                "download_source": "canonical",
                "format": _guess_format(download_url),
                "variable_font": False,
            }
        )
    return records


def fetch_cafe24_fonts(
    source_page_url: str = CAFE24_SOURCE_URL,
    catalog_json_url: str = CAFE24_CATALOG_JSON_URL,
) -> list[dict]:
    payload = json.loads(fetch_text(catalog_json_url, timeout=30))
    return parse_cafe24_catalog(payload, source_page_url=source_page_url)


def parse_jeju_font_info_html(
    html: str,
    source_page_url: str = JEJU_SOURCE_URL,
) -> list[dict]:
    attachments = {
        number: absolutize(source_page_url, unescape(href))
        for href, number in re.findall(r'href="([^"]*download\.htm\?act=download&amp;seq=60060&amp;no=(\d+))"', html, re.I)
    }
    ttf_zip = attachments.get("10", "")
    otf_zip = attachments.get("11", "")
    if not ttf_zip and not otf_zip:
        raise ValueError("Jeju font info page에서 수동 설치용 ZIP 링크를 찾지 못했습니다.")

    families = [
        ("jeju-gothic", "제주고딕"),
        ("jeju-myeongjo", "제주명조"),
        ("jeju-hallasan", "제주한라산"),
    ]
    records: list[dict] = []
    for slug, family in families:
        tags = ["jeju", "display" if family == "제주한라산" else "editorial"]
        if family == "제주고딕":
            tags.extend(["sans", "subtitle"])
        elif family == "제주명조":
            tags.extend(["serif", "body", "editorial"])
        else:
            tags.extend(["handwriting", "title", "poster"])
        records.append(
            {
                "font_id": slug,
                "family": family,
                "slug": slug,
                "source_site": "jeju_official",
                "source_page_url": source_page_url,
                "homepage_url": source_page_url,
                "license_id": "jeju-official-font",
                "license_summary": "제주특별자치도 공식 전용서체 안내 페이지에서 제공하는 무료 폰트입니다.",
                "commercial_use_allowed": True,
                "video_use_allowed": True,
                "web_embedding_allowed": False,
                "redistribution_allowed": False,
                "languages": ["ko"],
                "tags": tags,
                "recommended_for": _guess_use_cases(tags + [family.lower()]),
                "preview_text_ko": f"{family}. 제주 지역 아이덴티티를 담은 공식 무료 서체입니다.",
                "preview_text_en": family,
                "download_type": "zip_file",
                "download_url": ttf_zip or otf_zip,
                "download_source": "canonical",
                "format": "zip",
                "variable_font": False,
            }
        )
    return records


def fetch_jeju_fonts(source_page_url: str = JEJU_SOURCE_URL) -> list[dict]:
    return parse_jeju_font_info_html(
        fetch_text(source_page_url, timeout=30),
        source_page_url=source_page_url,
    )


def fetch_google_display_fonts(source_page_url: str = GOOGLE_FONTS_SOURCE_URL) -> list[dict]:
    records = []
    for item in GOOGLE_DISPLAY_FONTS:
        records.append(
            {
                "font_id": item["font_id"],
                "family": item["family"],
                "slug": item["slug"],
                "source_site": "google_display",
                "source_page_url": item["source_page_url"],
                "homepage_url": source_page_url,
                "license_id": "google-fonts-ofl",
                "license_summary": "Google Fonts에서 제공하는 오픈 라이선스 영문 폰트입니다.",
                "commercial_use_allowed": True,
                "video_use_allowed": True,
                "web_embedding_allowed": True,
                "redistribution_allowed": True,
                "languages": ["en"],
                "tags": item["tags"],
                "recommended_for": item["recommended_for"],
                "preview_text_ko": f"{item['family']} 영문 폰트. 디자인용 타이틀과 브랜딩에 적합한 Google Fonts 서체입니다.",
                "preview_text_en": item["preview_text_en"],
                "download_type": "direct_file",
                "download_url": item["download_url"],
                "download_source": "canonical",
                "format": _guess_format(item["download_url"]),
                "variable_font": bool(item.get("variable_font", False)),
            }
        )
    return records


def parse_league_font_page(
    html: str,
    *,
    font_id: str,
    family: str,
    slug: str,
    source_page_url: str,
    tags: list[str],
    recommended_for: list[str],
    preview_text_en: str,
) -> dict:
    download_match = re.search(r'https://github\.com/[^"]+\.zip', html, re.I)
    if not download_match:
        raise ValueError(f"{family} 페이지에서 다운로드 ZIP 링크를 찾지 못했습니다.")
    download_url = download_match.group(0)
    return {
        "font_id": font_id,
        "family": family,
        "slug": slug,
        "source_site": "league_movable_type",
        "source_page_url": source_page_url,
        "homepage_url": LEAGUE_SOURCE_URL,
        "license_id": "league-ofl",
        "license_summary": "The League of Moveable Type 공식 페이지 기준 Open Font License 무료 영문 폰트입니다.",
        "commercial_use_allowed": True,
        "video_use_allowed": True,
        "web_embedding_allowed": True,
        "redistribution_allowed": True,
        "languages": ["en"],
        "tags": tags,
        "recommended_for": recommended_for,
        "preview_text_ko": f"{family} 영문 폰트. 포스터와 브랜딩용 제목에 강한 무료 서체입니다.",
        "preview_text_en": preview_text_en,
        "download_type": "zip_file",
        "download_url": download_url,
        "download_source": "canonical",
        "format": "zip",
        "variable_font": False,
    }


def fetch_league_fonts() -> list[dict]:
    records: list[dict] = []
    for item in LEAGUE_FONT_PAGES:
        html = fetch_text(item["source_page_url"], timeout=30)
        records.append(
            parse_league_font_page(
                html,
                font_id=item["font_id"],
                family=item["family"],
                slug=item["slug"],
                source_page_url=item["source_page_url"],
                tags=item["tags"],
                recommended_for=item["recommended_for"],
                preview_text_en=item["preview_text_en"],
            )
        )
    return records


def fetch_velvetyne_fonts() -> list[dict]:
    records: list[dict] = []
    for item in VELVETYNE_FONTS:
        records.append(
            {
                "font_id": item["font_id"],
                "family": item["family"],
                "slug": item["slug"],
                "source_site": "velvetyne_display",
                "source_page_url": item["source_page_url"],
                "homepage_url": VELVETYNE_SOURCE_URL,
                "license_id": "velvetyne-ofl",
                "license_summary": "Velvetyne 공식 페이지 기준 OFL 기반 무료 영문 디자인 폰트입니다.",
                "commercial_use_allowed": True,
                "video_use_allowed": True,
                "web_embedding_allowed": True,
                "redistribution_allowed": True,
                "languages": ["en"],
                "tags": item["tags"],
                "recommended_for": item["recommended_for"],
                "preview_text_ko": f"{item['family']} 영문 폰트. 실험적 포스터와 타이틀에 강한 Velvetyne 서체입니다.",
                "preview_text_en": item["preview_text_en"],
                "download_type": "html_button",
                "download_url": item["download_url"],
                "download_source": "",
                "format": "html",
                "variable_font": False,
            }
        )
    return records


def fetch_fontshare_fonts(api_url: str = "https://api.fontshare.com/v2/fonts") -> list[dict]:
    payload = json.loads(fetch_text(api_url, timeout=30))
    fonts = payload.get("fonts") or []
    records: list[dict] = []
    for item in fonts:
        slug = (item.get("slug") or "").strip()
        curated = FONTSHARE_CURATED_FAMILIES.get(slug)
        if not curated:
            continue
        styles = item.get("styles") or []
        weight_numbers = list(
            dict.fromkeys(
                str((style.get("weight") or {}).get("number"))
                for style in styles
                if (style.get("weight") or {}).get("number") is not None
            )
        )
        if not weight_numbers:
            continue
        download_url = "https://api.fontshare.com/v2/fonts/download/kit?f[]={slug}@{weights}".format(
            slug=slug,
            weights=",".join(weight_numbers),
        )
        font_tags = [tag.get("name", "").strip().lower() for tag in (item.get("font_tags") or []) if tag.get("name")]
        category = (item.get("category") or "").strip().lower()
        tags = list(dict.fromkeys(curated["tags"] + font_tags + ([category] if category else [])))
        records.append(
            {
                "font_id": curated["font_id"],
                "family": curated["family"],
                "slug": slug,
                "source_site": "fontshare_display",
                "source_page_url": f"https://www.fontshare.com/fonts/{slug}",
                "homepage_url": FONTSHARE_SOURCE_URL,
                "license_id": item.get("license_type") or "fontshare-free-font-license",
                "license_summary": "Fontshare free font catalog 기준 상업 사용 가능한 영문 디자인 폰트입니다.",
                "commercial_use_allowed": True,
                "video_use_allowed": True,
                "web_embedding_allowed": True,
                "redistribution_allowed": False,
                "languages": ["en"],
                "tags": tags,
                "recommended_for": curated["recommended_for"],
                "preview_text_ko": f"{curated['family']} 영문 폰트. 브랜딩과 에디토리얼 작업에 강한 Fontshare 서체입니다.",
                "preview_text_en": curated["preview_text_en"],
                "download_type": "zip_file",
                "download_url": download_url,
                "download_source": "canonical",
                "format": "zip",
                "variable_font": any(style.get("is_variable") for style in styles),
            }
        )
    return records


def parse_gmarket_design_system_html(
    html: str,
    source_page_url: str = GMARKET_SOURCE_URL,
) -> list[dict]:
    pattern = re.compile(
        r'<a class="ResourceCardGroup_item__.*?href="(?P<href>[^"]+)".*?'
        r'<strong class="ResourceCard_title__[^"]+">(?P<title>.*?)</strong>',
        re.S,
    )
    records: list[dict] = []
    seen: set[str] = set()
    for match in pattern.finditer(html):
        title = _clean(match.group("title"))
        href = match.group("href").strip()
        if "산스" not in title:
            continue
        download_url = urljoin(source_page_url, href)
        font_id = "gmarket-sans"
        if font_id in seen:
            continue
        seen.add(font_id)
        records.append(
            {
                "font_id": font_id,
                "family": "G마켓 산스",
                "slug": "gmarket-sans",
                "source_site": "gmarket_brand",
                "source_page_url": source_page_url,
                "homepage_url": source_page_url,
                "license_id": "gmarket-brand-font",
                "license_summary": "Gmarket Design System에서 제공하는 무료 브랜드 폰트입니다.",
                "commercial_use_allowed": True,
                "video_use_allowed": True,
                "web_embedding_allowed": False,
                "redistribution_allowed": False,
                "languages": ["ko"],
                "tags": ["brand", "display", "title", "poster", "thumbnail", "gmarket", "sans"],
                "recommended_for": ["title", "thumbnail", "subtitle"],
                "preview_text_ko": "G마켓 산스. 포스터와 썸네일, 브랜드 타이틀에 강한 디스플레이 산스입니다.",
                "preview_text_en": "Gmarket Sans",
                "download_type": classify_download_type(download_url),
                "download_url": download_url,
                "download_source": "canonical",
                "format": _guess_format(download_url),
                "variable_font": False,
            }
        )
    return records


def fetch_gmarket_fonts(source_page_url: str = GMARKET_SOURCE_URL) -> list[dict]:
    return parse_gmarket_design_system_html(
        fetch_text(source_page_url, timeout=30),
        source_page_url=source_page_url,
    )


def _looks_like_nexon_font_resource(stem: str) -> bool:
    excluded = ("NEXON_CI", "Presentation_Templates", "Reproduction_Material")
    return not stem.startswith(excluded)


def _nexon_family_name(stem: str) -> str:
    if stem in NEXON_FAMILY_OVERRIDES:
        return NEXON_FAMILY_OVERRIDES[stem]
    name = stem.replace("_", " ")
    name = re.sub(r"\bv(\d+)\b", r"v\1", name, flags=re.I)
    return name.strip()


def _nexon_tags(stem: str) -> list[str]:
    tags = ["brand", "display", "title", "thumbnail", "game", "nexon"]
    lower = stem.lower()
    if "gothic" in lower:
        tags.extend(["sans", "subtitle"])
    if "bitbit" in lower:
        tags.extend(["pixel", "retro"])
    if "bazzi" in lower:
        tags.append("playful")
    if "maplestory" in lower or "mabinogi" in lower or "kart" in lower:
        tags.append("fantasy")
    if "warhaven" in lower or "forgedblade" in lower:
        tags.append("cinematic")
    return tags


def _nexon_recommended_for(stem: str) -> list[str]:
    items = ["title", "thumbnail"]
    if "gothic" in stem.lower():
        items.append("subtitle")
    return items


def _woowahan_group_key(filename: str) -> str:
    stem = PurePosixPath(filename).stem
    stem = re.sub(r"(_ttf|_otf|ttf|otf)$", "", stem, flags=re.I)
    stem = re.sub(r"[-_]+$", "", stem)
    return stem


def _woowahan_family_name(group_key: str) -> str:
    return WOOWAHAN_FAMILY_OVERRIDES.get(group_key, group_key)


def _woowahan_tags(group_key: str) -> list[str]:
    tags = ["brand", "display", "title", "thumbnail", "woowahan"]
    lower = group_key.lower()
    if "euljiro" in lower:
        tags.extend(["retro", "signage", "poster"])
    if any(token in lower for token in ("yeonsung", "jua", "kiranghaerang")):
        tags.extend(["handwriting", "playful"])
    if any(token in lower for token in ("geullim", "kkubulim")):
        tags.extend(["playful", "experimental"])
    if "dohyeon" in lower:
        tags.extend(["bold", "poster"])
    if "hanna" in lower:
        tags.extend(["editorial", "headline"])
    return tags


def _woowahan_recommended_for(group_key: str) -> list[str]:
    items = ["title", "thumbnail"]
    lower = group_key.lower()
    if "hanna" in lower or "dohyeon" in lower:
        items.append("poster")
    return items


def parse_woowahan_font_bundle(
    bundle_text: str,
    source_page_url: str = WOOWAHAN_SOURCE_URL,
) -> list[dict]:
    files = WOOWAHAN_FONT_FILE_RE.findall(bundle_text)
    grouped: dict[str, list[str]] = {}
    for filename in files:
        if filename == "BM-fonts-package.zip":
            continue
        key = _woowahan_group_key(filename)
        grouped.setdefault(key, []).append(filename)

    priority = {"ttf": 0, "otf": 1, "zip": 2}
    records: list[dict] = []
    for key in sorted(grouped):
        selected = min(
            grouped[key],
            key=lambda item: priority.get(PurePosixPath(item).suffix.lower().lstrip("."), 99),
        )
        family = _woowahan_family_name(key)
        download_url = f"https://woowahan-cdn.woowahan.com/static/fonts/{selected}"
        records.append(
            {
                "font_id": f"woowahan-{key.lower().replace('_', '-').replace(' ', '-')}",
                "family": family,
                "slug": key.lower().replace("_", "-"),
                "source_site": "woowahan_brand",
                "source_page_url": source_page_url,
                "homepage_url": source_page_url,
                "license_id": "woowahan-brand-font",
                "license_summary": "우아한형제들 공식 폰트 페이지에서 제공하는 무료 브랜드 폰트입니다.",
                "commercial_use_allowed": True,
                "video_use_allowed": True,
                "web_embedding_allowed": PurePosixPath(selected).suffix.lower() != ".zip",
                "redistribution_allowed": False,
                "languages": ["ko"],
                "tags": _woowahan_tags(key),
                "recommended_for": _woowahan_recommended_for(key),
                "preview_text_ko": f"{family}. 브랜드 무드가 강한 제목용 한글 디스플레이 폰트입니다.",
                "preview_text_en": family,
                "download_type": classify_download_type(download_url),
                "download_url": download_url,
                "download_source": "canonical",
                "format": _guess_format(download_url),
                "variable_font": False,
            }
        )
    return records


def fetch_woowahan_fonts(source_page_url: str = WOOWAHAN_SOURCE_URL) -> list[dict]:
    try:
        html = _fetch_browser_text(source_page_url, timeout=30)
        scripts = WOOWAHAN_SCRIPT_RE.findall(html)
        for script_url in scripts:
            bundle_text = _fetch_browser_text(script_url, timeout=30)
            if WOOWAHAN_FONT_FILE_RE.search(bundle_text):
                return parse_woowahan_font_bundle(bundle_text, source_page_url=source_page_url)
    except Exception:
        pass

    fallback_bundle = "\n".join(
        f"https://woowahan-cdn.woowahan.com/static/fonts/{filename}"
        for filename in WOOWAHAN_FONT_FALLBACK_FILES
    )
    return parse_woowahan_font_bundle(fallback_bundle, source_page_url=source_page_url)


def parse_nexon_brand_bundle(
    html: str,
    bundle_text: str,
    source_page_url: str = NEXON_SOURCE_URL,
) -> list[dict]:
    match = NEXON_BUNDLE_RE.search(html)
    if not match:
        raise ValueError("Nexon brand page에서 index bundle 경로를 찾지 못했습니다.")
    records: list[dict] = []
    seen: set[str] = set()
    for filename in NEXON_RESOURCE_RE.findall(bundle_text):
        stem = PurePosixPath(filename).stem
        if not _looks_like_nexon_font_resource(stem):
            continue
        font_id = f"nexon-{stem.lower().replace('_', '-').replace(' ', '-')}"
        if font_id in seen:
            continue
        seen.add(font_id)
        family = _nexon_family_name(stem)
        download_url = urljoin(source_page_url, f"/resources/{filename}")
        records.append(
            {
                "font_id": font_id,
                "family": family,
                "slug": stem.lower().replace("_", "-"),
                "source_site": "nexon_brand",
                "source_page_url": source_page_url,
                "homepage_url": source_page_url,
                "license_id": "nexon-brand-font",
                "license_summary": "Nexon 브랜드 폰트 페이지에서 제공하는 무료 게임/브랜드 서체입니다.",
                "commercial_use_allowed": True,
                "video_use_allowed": True,
                "web_embedding_allowed": False,
                "redistribution_allowed": False,
                "languages": ["ko"],
                "tags": _nexon_tags(stem),
                "recommended_for": _nexon_recommended_for(stem),
                "preview_text_ko": f"{family}. 게임/브랜드 무드가 강한 제목용 디스플레이 폰트입니다.",
                "preview_text_en": family,
                "download_type": classify_download_type(download_url),
                "download_url": download_url,
                "download_source": "canonical",
                "format": _guess_format(download_url),
                "variable_font": False,
            }
        )
    return records


def fetch_nexon_fonts(source_page_url: str = NEXON_SOURCE_URL) -> list[dict]:
    html = fetch_text(source_page_url, timeout=30)
    match = NEXON_BUNDLE_RE.search(html)
    if not match:
        raise ValueError("Nexon brand page에서 index bundle 경로를 찾지 못했습니다.")
    bundle_url = urljoin(source_page_url, match.group("src"))
    bundle_text = fetch_text(bundle_url, timeout=30)
    return parse_nexon_brand_bundle(html, bundle_text, source_page_url=source_page_url)


def parse_gongu_list_html(
    html: str,
    source_page_url: str = GONGU_LIST_URL,
) -> tuple[list[dict], int]:
    pattern = re.compile(r"<li>\s*(?P<content><div class=\"font_box\">.*?</div>)\s*</li>", re.S)
    records: list[dict] = []
    seen: set[str] = set()
    for match in pattern.finditer(html):
        content = match.group("content")
        detail_match = re.search(
            r'<a href="(?P<detail_url>https://gongu\.copyright\.or\.kr/gongu/wrt/wrt/view\.do\?wrtSn=(?P<wrt_sn>\d+)[^"]*)"'
            r'[^>]*>바로가기</a>',
            content,
            re.S,
        )
        if not detail_match:
            continue
        wrt_sn = detail_match.group("wrt_sn").strip()
        if wrt_sn in seen:
            continue
        seen.add(wrt_sn)
        family_match = re.search(r'<span class="tit">(?P<family>.*?)</span>', content, re.S)
        source_match = re.search(r'<p class="font_source">(?P<source>.*?)</p>', content, re.S)
        license_match = re.search(
            r'<div class="txt_link">\s*.*?</div>\s*(?P<license_html>.*?)</div>\s*<!-- 2019\.11 11 수정 -->',
            content,
            re.S,
        )
        family = _clean(family_match.group("family")) if family_match else ""
        source = _clean(source_match.group("source")) if source_match else ""
        if license_match:
            license_text = _clean(license_match.group("license_html"))
        else:
            fallback_match = re.search(r'<div class="txt_link">(?P<license_html>.*?)</div>', content, re.S)
            fallback_html = fallback_match.group("license_html") if fallback_match else ""
            fallback_html = re.sub(r'<div class="btnClose">.*?</div>', " ", fallback_html, flags=re.S)
            license_text = _clean(fallback_html)
        detail_url = detail_match.group("detail_url").strip()
        if not family or not detail_url:
            continue
        records.append(
            {
                "wrt_sn": wrt_sn,
                "family": family,
                "source": source,
                "license_text": license_text,
                "source_page_url": detail_url,
                "homepage_url": source_page_url,
            }
        )

    page_indexes = [int(value) for value in re.findall(r"pageIndex=(\d+)", html)]
    max_page = max(page_indexes) if page_indexes else 1
    return records, max_page


def parse_gongu_download_popup_html(
    html: str,
    wrt_sn: str,
    family: str,
    source_page_url: str,
    homepage_url: str,
    source: str,
    license_text: str,
) -> dict:
    download_url, filename = _extract_gongu_download_url(html, wrt_sn)
    license_id, commercial_use_allowed, video_use_allowed, web_embedding_allowed, redistribution_allowed = (
        _parse_gongu_license(license_text)
    )
    tags = [tag for tag in [source.lower(), "gongu", "freefont"] if tag]
    if "ofl" in license_text.lower():
        tags.append("ofl")
    if "학교안심" in family:
        tags.extend(["학교안심폰트", "keris"])
    tags = list(dict.fromkeys(tags))
    download_type = classify_download_type(filename) or classify_download_type(download_url)
    return {
        "font_id": f"gongu-{wrt_sn}",
        "family": family,
        "slug": wrt_sn,
        "source_site": "gongu_freefont",
        "source_page_url": source_page_url,
        "homepage_url": homepage_url,
        "license_id": license_id,
        "license_summary": f"공유마당 목록 기준 라이선스: {license_text}",
        "commercial_use_allowed": commercial_use_allowed,
        "video_use_allowed": video_use_allowed,
        "web_embedding_allowed": web_embedding_allowed,
        "redistribution_allowed": redistribution_allowed,
        "languages": ["ko"],
        "tags": tags,
        "recommended_for": _guess_use_cases(tags + [family.lower()]),
        "preview_text_ko": f"{family}. {source} 제공 안심글꼴입니다.",
        "preview_text_en": family,
        "download_type": download_type,
        "download_url": download_url or source_page_url,
        "download_source": "canonical" if download_url else "",
        "format": _guess_format(filename or download_url),
        "variable_font": False,
    }


def parse_fonco_free_font_list_html(
    html: str,
    source_page_url: str = "https://font.co.kr/collection/freeFont",
) -> list[dict]:
    pattern = re.compile(
        r'<a href="(?P<href>/collection/sub\?family_idx=(?P<family_idx>\d+))">\s*'
        r'(?:<li class="item">)?\s*'
        r'<div class="txt_box.*?'
        r'<span class="name"[^>]*>\s*(?P<family>.*?)\s*</span>.*?'
        r'<span class="desc kinds"[^>]*>(?P<meta>.*?)</span>',
        re.S,
    )
    records: list[dict] = []
    seen: set[str] = set()
    for match in pattern.finditer(html):
        family_idx = match.group("family_idx").strip()
        if family_idx in seen:
            continue
        seen.add(family_idx)
        family = _clean(match.group("family"))
        meta = _clean(match.group("meta"))
        company = ""
        style_count = ""
        if "|" in meta:
            style_count, company = [part.strip() for part in meta.split("|", 1)]
        detail_url = urljoin(source_page_url, match.group("href").strip())
        records.append(
            {
                "family_idx": family_idx,
                "family": family,
                "company": company,
                "style_count": style_count,
                "source_page_url": detail_url,
                "homepage_url": source_page_url,
            }
        )
    return records


def parse_fonco_detail_html(
    html: str,
    family_idx: str,
    source_page_url: str,
    homepage_url: str = "https://font.co.kr/collection/freeFont",
    family_hint: str = "",
    company_hint: str = "",
    style_count_hint: str = "",
) -> dict:
    title_match = re.search(r'<h2 class="sub_com_tit">\s*(?P<family>.*?)\s*(?:<a id=|</h2>)', html, re.S)
    family = _clean(title_match.group("family")) if title_match else family_hint

    tit_desc_match = re.search(r'<p class="tit_desc[^"]*">(?P<body>.*?)</p>', html, re.S)
    tit_desc_spans = re.findall(r"<span>(.*?)</span>", tit_desc_match.group("body"), re.S) if tit_desc_match else []
    tit_desc_spans = [_clean(item) for item in tit_desc_spans if _clean(item)]
    style_count = tit_desc_spans[0] if tit_desc_spans else style_count_hint
    company = tit_desc_spans[1] if len(tit_desc_spans) > 1 else company_hint
    license_label = tit_desc_spans[2] if len(tit_desc_spans) > 2 else "범위제한 라이선스"

    tags = [
        _clean(tag).lstrip("#").lower()
        for tag in re.findall(r"<li>(#[^<]+)</li>", html, re.S)
        if _clean(tag)
    ]
    if company:
        tags.append(company.lower())
    tags.extend(["fonco", "freefont"])
    tags = list(dict.fromkeys([tag for tag in tags if tag]))

    desc_match = re.search(r'<p class="desc">\s*(?P<desc>.*?)\s*</p>', html, re.S)
    description = _clean(desc_match.group("desc")) if desc_match else family

    preview_url = _choose_fonco_preview_url(html)
    license_id, commercial_use_allowed, video_use_allowed, web_embedding_allowed = _parse_fonco_license_flags(
        license_label
    )

    return {
        "font_id": f"fonco-{family_idx}",
        "family": family,
        "slug": family_idx,
        "source_site": "fonco_freefont",
        "source_page_url": source_page_url,
        "homepage_url": homepage_url,
        "license_id": license_id,
        "license_summary": f"FONCO 무료폰트 상세 페이지 기준 라이선스: {license_label}",
        "commercial_use_allowed": commercial_use_allowed,
        "video_use_allowed": video_use_allowed,
        "web_embedding_allowed": web_embedding_allowed,
        "redistribution_allowed": False,
        "languages": ["ko"],
        "tags": tags,
        "recommended_for": _guess_use_cases(tags),
        "preview_text_ko": description,
        "preview_text_en": family,
        "download_type": "direct_file" if preview_url else "html_button",
        "download_url": preview_url or source_page_url,
        "download_source": "preview_webfont" if preview_url else "",
        "format": _guess_format(preview_url or source_page_url),
        "variable_font": False,
        "style_count": style_count,
        "company": company,
    }


def fetch_fonco_free_fonts(
    source_page_url: str = "https://font.co.kr/collection/freeFont",
    limit: int | None = None,
) -> list[dict]:
    listing_html = fetch_text(source_page_url, timeout=30)
    items = parse_fonco_free_font_list_html(listing_html, source_page_url=source_page_url)
    if limit is not None:
        items = items[:limit]

    records: list[dict] = []
    for item in items:
        detail_html = fetch_text(item["source_page_url"], timeout=30)
        record = parse_fonco_detail_html(
            detail_html,
            family_idx=item["family_idx"],
            source_page_url=item["source_page_url"],
            homepage_url=source_page_url,
            family_hint=item["family"],
            company_hint=item["company"],
            style_count_hint=item["style_count"],
        )
        records.append(record)
    return records


def fetch_gongu_fonts(
    source_page_url: str = GONGU_LIST_URL,
    max_pages: int | None = None,
) -> list[dict]:
    first_html = fetch_text(source_page_url, timeout=30, headers=GONGU_HEADERS)
    first_items, discovered_max_page = parse_gongu_list_html(first_html, source_page_url=source_page_url)
    total_pages = min(discovered_max_page, max_pages) if max_pages else discovered_max_page

    items = list(first_items)
    for page_index in range(2, total_pages + 1):
        page_url = _upsert_query_param(source_page_url, "pageIndex", page_index)
        page_html = fetch_text(page_url, timeout=30, headers=GONGU_HEADERS)
        page_items, _ = parse_gongu_list_html(page_html, source_page_url=source_page_url)
        items.extend(page_items)

    unique_items: list[dict] = []
    seen: set[str] = set()
    for item in items:
        if item["wrt_sn"] in seen:
            continue
        seen.add(item["wrt_sn"])
        unique_items.append(item)

    records: list[dict] = []
    for item in unique_items:
        popup_url = (
            "https://gongu.copyright.or.kr/gongu/wrt/wrt/wrtDownPopup.do"
            f"?viewType=BODY&wrtSn={item['wrt_sn']}&menuNo=200195"
        )
        popup_html = fetch_text(popup_url, timeout=30, headers=GONGU_HEADERS)
        records.append(
            parse_gongu_download_popup_html(
                popup_html,
                wrt_sn=item["wrt_sn"],
                family=item["family"],
                source_page_url=item["source_page_url"],
                homepage_url=item["homepage_url"],
                source=item["source"],
                license_text=item["license_text"],
            )
        )
    return records


def imported_candidate_urls_for_sources() -> dict[str, tuple[str, str]]:
    return {
        normalize_result_url("https://hangeul.naver.com/font"): ("imported", "네이버 글꼴 모음 importer로 적재했습니다."),
        normalize_result_url("https://font.hancom.com/pc/main/main.php"): ("imported", "한컴 무료 서체 importer로 적재했습니다."),
        normalize_result_url("https://font.co.kr/collection/freeFont"): ("imported", "FONCO 무료폰트 importer로 적재했습니다."),
        normalize_result_url("https://gds.gmarket.co.kr/"): ("imported", "Gmarket 브랜드 폰트 importer로 적재했습니다."),
        normalize_result_url("https://www.goodchoice.kr/font/mobile"): ("imported", "여기어때 브랜드 폰트 importer로 적재했습니다."),
        normalize_result_url("https://www.cafe24.com/story/use/cafe24pro_font.html"): ("imported", "Cafe24 브랜드 폰트 importer로 적재했습니다."),
        normalize_result_url("https://www.jeju.go.kr/jeju/font.htm"): ("imported", "제주 공식 서체 importer로 적재했습니다."),
        normalize_result_url("https://www.jeju.go.kr/jeju/symbol/font/infor.htm"): ("imported", "제주 공식 서체 importer로 적재했습니다."),
        normalize_result_url("https://www.theleagueofmoveabletype.com/"): ("imported", "The League of Moveable Type importer로 적재했습니다."),
        normalize_result_url("https://velvetyne.fr/"): ("imported", "Velvetyne importer로 적재했습니다."),
        normalize_result_url("https://www.fontshare.com/"): ("imported", "Fontshare importer로 적재했습니다."),
        normalize_result_url("https://brand.nexon.com/brand/fonts"): ("imported", "Nexon 브랜드 폰트 importer로 적재했습니다."),
        normalize_result_url("https://www.woowahan.com/fonts"): ("imported", "우아한형제들 브랜드 폰트 importer로 적재했습니다."),
        normalize_result_url("https://gongu.copyright.or.kr/gongu/bbs/B0000018/list.do?menuNo=200195"): (
            "imported",
            "공유마당 무료글꼴 importer로 적재했습니다.",
        ),
    }
