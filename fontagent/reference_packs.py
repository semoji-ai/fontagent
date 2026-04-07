from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReferencePackItem:
    title: str
    medium: str
    surface: str
    role: str
    source_kind: str
    source_url: str
    tones: tuple[str, ...]
    languages: tuple[str, ...]
    status: str = "curated"
    reference_class: str = "specimen"


REFERENCE_PACKS: dict[str, dict] = {
    "trend-korean-brand-display": {
        "title": "트렌드 한글 브랜드 디스플레이",
        "description": "국내 브랜드 무료 폰트 페이지를 기반으로 title/display 감각을 학습하는 starter pack",
        "items": [
            ReferencePackItem(
                title="Cafe24 Pro Font Landing",
                medium="web",
                surface="landing_hero",
                role="title",
                source_kind="web_page",
                source_url="https://www.cafe24.com/story/use/cafe24pro_font.html",
                tones=("playful", "display", "brand"),
                languages=("ko",),
            ),
            ReferencePackItem(
                title="Goodchoice Jalnan Mobile Font",
                medium="web",
                surface="landing_hero",
                role="title",
                source_kind="web_page",
                source_url="https://www.goodchoice.kr/font/mobile",
                tones=("quirky", "playful", "brand"),
                languages=("ko",),
            ),
            ReferencePackItem(
                title="Gmarket Design System",
                medium="web",
                surface="landing_hero",
                role="title",
                source_kind="web_page",
                source_url="https://gds.gmarket.co.kr/",
                tones=("bold", "retail", "display"),
                languages=("ko",),
            ),
            ReferencePackItem(
                title="Nexon Brand Fonts",
                medium="web",
                surface="landing_hero",
                role="title",
                source_kind="web_page",
                source_url="https://brand.nexon.com/brand/fonts",
                tones=("game", "playful", "display"),
                languages=("ko",),
            ),
            ReferencePackItem(
                title="Jeju Font Info",
                medium="web",
                surface="landing_hero",
                role="title",
                source_kind="web_page",
                source_url="https://www.jeju.go.kr/jeju/symbol/font/infor.htm",
                tones=("editorial", "regional", "display"),
                languages=("ko",),
            ),
        ],
    },
    "trend-english-editorial-display": {
        "title": "트렌드 영문 에디토리얼/디스플레이",
        "description": "영문 editorial/display 계열을 빠르게 학습하는 starter pack",
        "items": [
            ReferencePackItem(
                title="Fontshare General Sans",
                medium="web",
                surface="landing_hero",
                role="title",
                source_kind="web_page",
                source_url="https://www.fontshare.com/fonts/general-sans",
                tones=("editorial", "clean", "brand"),
                languages=("en",),
            ),
            ReferencePackItem(
                title="Fontshare Clash Display",
                medium="web",
                surface="landing_hero",
                role="title",
                source_kind="web_page",
                source_url="https://www.fontshare.com/fonts/clash-display",
                tones=("display", "luxury", "editorial"),
                languages=("en",),
            ),
            ReferencePackItem(
                title="League Gothic Specimen",
                medium="web",
                surface="poster_hero",
                role="title",
                source_kind="web_page",
                source_url="https://www.theleagueofmoveabletype.com/league-gothic",
                tones=("poster", "condensed", "bold"),
                languages=("en",),
            ),
            ReferencePackItem(
                title="Google Fonts Fraunces",
                medium="web",
                surface="landing_hero",
                role="title",
                source_kind="web_page",
                source_url="https://fonts.google.com/specimen/Fraunces",
                tones=("serif", "editorial", "luxury"),
                languages=("en",),
            ),
            ReferencePackItem(
                title="Velvetyne Avara",
                medium="web",
                surface="poster_hero",
                role="title",
                source_kind="web_page",
                source_url="https://velvetyne.fr/fonts/avara/",
                tones=("experimental", "poster", "artsy"),
                languages=("en",),
            ),
        ],
    },
    "trend-korean-video-thumbnail-display": {
        "title": "트렌드 한글 영상 썸네일 디스플레이",
        "description": "유튜브 썸네일/오프닝 타이틀에 가까운 표현형 제목체 레퍼런스를 빠르게 쌓는 팩",
        "items": [
            ReferencePackItem(
                title="Goodchoice Jalnan Mobile Font Thumbnail",
                medium="video",
                surface="thumbnail",
                role="title",
                source_kind="web_page",
                source_url="https://www.goodchoice.kr/font/mobile",
                tones=("quirky", "playful", "brand"),
                languages=("ko",),
            ),
            ReferencePackItem(
                title="Cafe24 Supermagic Poster Style",
                medium="video",
                surface="thumbnail",
                role="title",
                source_kind="web_page",
                source_url="https://www.cafe24.com/story/use/cafe24pro_font.html",
                tones=("playful", "display", "poster"),
                languages=("ko",),
            ),
            ReferencePackItem(
                title="Nexon Brand Fonts Thumbnail Style",
                medium="video",
                surface="thumbnail",
                role="title",
                source_kind="web_page",
                source_url="https://brand.nexon.com/brand/fonts",
                tones=("game", "playful", "display"),
                languages=("ko",),
            ),
        ],
    },
    "trend-video-subtitle-readable": {
        "title": "트렌드 영상 자막 리더블 산세리프",
        "description": "실제 영상 자막에 가까운 읽기 좋은 sans/subtitle 계열 레퍼런스를 쌓는 팩",
        "items": [
            ReferencePackItem(
                title="Naver Nanum Subtitle Reference",
                medium="video",
                surface="subtitle_track",
                role="subtitle",
                source_kind="web_page",
                source_url="https://hangeul.naver.com/font",
                tones=("readable", "neutral", "sans"),
                languages=("ko",),
            ),
            ReferencePackItem(
                title="Gmarket Sans Subtitle Reference",
                medium="video",
                surface="subtitle_track",
                role="subtitle",
                source_kind="web_page",
                source_url="https://gds.gmarket.co.kr/",
                tones=("readable", "sans", "clean"),
                languages=("ko",),
            ),
            ReferencePackItem(
                title="Fontshare General Sans Subtitle Reference",
                medium="video",
                surface="subtitle_track",
                role="subtitle",
                source_kind="web_page",
                source_url="https://www.fontshare.com/fonts/general-sans",
                tones=("readable", "sans", "neutral"),
                languages=("en",),
            ),
        ],
    },
    "trend-web-editorial-heroes": {
        "title": "트렌드 웹 에디토리얼 히어로",
        "description": "브랜드 사이트와 에디토리얼 랜딩 히어로를 위한 레퍼런스 팩",
        "items": [
            ReferencePackItem(
                title="Cafe24 Editorial Hero",
                medium="web",
                surface="landing_hero",
                role="title",
                source_kind="web_page",
                source_url="https://www.cafe24.com/story/use/cafe24pro_font.html",
                tones=("editorial", "brand", "playful"),
                languages=("ko",),
            ),
            ReferencePackItem(
                title="Fontshare Clash Display Hero",
                medium="web",
                surface="landing_hero",
                role="title",
                source_kind="web_page",
                source_url="https://www.fontshare.com/fonts/clash-display",
                tones=("editorial", "luxury", "display"),
                languages=("en",),
            ),
            ReferencePackItem(
                title="Google Fonts Fraunces Editorial Hero",
                medium="web",
                surface="landing_hero",
                role="title",
                source_kind="web_page",
                source_url="https://fonts.google.com/specimen/Fraunces",
                tones=("editorial", "luxury", "serif"),
                languages=("en",),
            ),
        ],
    },
    "trend-presentation-cover-display": {
        "title": "트렌드 프레젠테이션 표지 디스플레이",
        "description": "피치덱/PPT 표지에 가까운 타이포그래피 감각을 학습하는 팩",
        "items": [
            ReferencePackItem(
                title="Fontshare Clash Display Presentation Cover",
                medium="presentation",
                surface="cover",
                role="title",
                source_kind="web_page",
                source_url="https://www.fontshare.com/fonts/clash-display",
                tones=("deck", "display", "luxury"),
                languages=("en",),
            ),
            ReferencePackItem(
                title="Google Fonts Fraunces Presentation Cover",
                medium="presentation",
                surface="cover",
                role="title",
                source_kind="web_page",
                source_url="https://fonts.google.com/specimen/Fraunces",
                tones=("editorial", "serif", "luxury"),
                languages=("en",),
            ),
            ReferencePackItem(
                title="Cafe24 Presentation Cover",
                medium="presentation",
                surface="cover",
                role="title",
                source_kind="web_page",
                source_url="https://www.cafe24.com/story/use/cafe24pro_font.html",
                tones=("brand", "playful", "display"),
                languages=("ko",),
            ),
        ],
    },
    "trend-detailpage-brand-heroes": {
        "title": "트렌드 상세페이지 브랜드 히어로",
        "description": "상세페이지 첫 화면과 세일즈 헤드라인에 가까운 레퍼런스를 쌓는 팩",
        "items": [
            ReferencePackItem(
                title="Gmarket Detail Page Hero",
                medium="detailpage",
                surface="hero",
                role="title",
                source_kind="web_page",
                source_url="https://gds.gmarket.co.kr/",
                tones=("retail", "bold", "display"),
                languages=("ko",),
            ),
            ReferencePackItem(
                title="Goodchoice Detail Headline",
                medium="detailpage",
                surface="hero",
                role="title",
                source_kind="web_page",
                source_url="https://www.goodchoice.kr/font/mobile",
                tones=("quirky", "brand", "cta"),
                languages=("ko",),
            ),
            ReferencePackItem(
                title="Fontshare General Sans Detail Hero",
                medium="detailpage",
                surface="hero",
                role="title",
                source_kind="web_page",
                source_url="https://www.fontshare.com/fonts/general-sans",
                tones=("clean", "commerce", "brand"),
                languages=("en",),
            ),
        ],
    },
    "trend-print-poster-display": {
        "title": "트렌드 인쇄 포스터 디스플레이",
        "description": "포스터 헤드라인과 인쇄물 제목체 감각을 빠르게 쌓는 팩",
        "items": [
            ReferencePackItem(
                title="Velvetyne Avara Poster",
                medium="print",
                surface="poster_hero",
                role="title",
                source_kind="web_page",
                source_url="https://velvetyne.fr/fonts/avara/",
                tones=("poster", "experimental", "artsy"),
                languages=("en",),
            ),
            ReferencePackItem(
                title="League Gothic Poster",
                medium="print",
                surface="poster_hero",
                role="title",
                source_kind="web_page",
                source_url="https://www.theleagueofmoveabletype.com/league-gothic",
                tones=("poster", "condensed", "bold"),
                languages=("en",),
            ),
            ReferencePackItem(
                title="Cafe24 Poster Display",
                medium="print",
                surface="poster_hero",
                role="title",
                source_kind="web_page",
                source_url="https://www.cafe24.com/story/use/cafe24pro_font.html",
                tones=("poster", "playful", "display"),
                languages=("ko",),
            ),
        ],
    },
    "market-presentation-covers": {
        "title": "실전 프레젠테이션 표지 레퍼런스",
        "description": "실제 공개 프레젠테이션/덱 산출물에서 표지 타이포 감각을 관찰하는 market pack",
        "items": [
            ReferencePackItem(
                title="Behance Minimal Presentation Template",
                medium="presentation",
                surface="cover",
                role="title",
                source_kind="web_page",
                source_url="https://www.behance.net/gallery/223968913/Minimal-Presentation-Template",
                tones=("deck", "minimal", "editorial"),
                languages=("en",),
                reference_class="market",
            ),
        ],
    },
    "market-detailpage-heroes": {
        "title": "실전 상세페이지 히어로 레퍼런스",
        "description": "실제 공개 상세페이지 산출물에서 상단 타이포 감각을 관찰하는 market pack",
        "items": [
            ReferencePackItem(
                title="Behance E-commerce Detail Page Design",
                medium="detailpage",
                surface="hero",
                role="title",
                source_kind="web_page",
                source_url="https://www.behance.net/gallery/237183715/E-commerce-detail-page-design",
                tones=("retail", "clean", "brand"),
                languages=("en",),
                reference_class="market",
            ),
        ],
    },
    "market-print-poster-typography": {
        "title": "실전 타이포 포스터 레퍼런스",
        "description": "실제 공개 포스터/브로슈어 산출물에서 타이포 감각을 관찰하는 market pack",
        "items": [
            ReferencePackItem(
                title="Behance Brocure Trends in Typography 2025",
                medium="print",
                surface="poster_hero",
                role="title",
                source_kind="web_page",
                source_url="https://www.behance.net/gallery/240772865/Brocure-Trends-in-Typography-2025",
                tones=("poster", "editorial", "trend"),
                languages=("en",),
                reference_class="market",
            ),
        ],
    },
}


def list_reference_packs() -> dict[str, dict]:
    payload: dict[str, dict] = {}
    for key, value in REFERENCE_PACKS.items():
        payload[key] = {
            "title": value["title"],
            "description": value["description"],
            "count": len(value["items"]),
            "mediums": sorted({item.medium for item in value["items"]}),
            "surfaces": sorted({item.surface for item in value["items"]}),
            "languages": sorted({lang for item in value["items"] for lang in item.languages}),
            "reference_classes": sorted({item.reference_class for item in value["items"]}),
        }
    return payload


def get_reference_pack(name: str) -> dict:
    if name not in REFERENCE_PACKS:
        raise KeyError(f"Unknown reference pack: {name}")
    return REFERENCE_PACKS[name]
