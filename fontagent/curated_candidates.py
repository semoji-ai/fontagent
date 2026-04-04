from __future__ import annotations

from datetime import datetime, timezone


CURATED_CANDIDATE_SETS = {
    "design-display-ko": [
        {
            "query": "manual curated design display sources",
            "title": "빙그레 서체",
            "snippet": "빙그레가 배포하는 공식 무료 브랜드 서체 페이지입니다.",
            "result_url": "https://www.bingfont.co.kr/",
            "normalized_url": "https://www.bingfont.co.kr/",
            "domain": "www.bingfont.co.kr",
            "discovery_source": "manual_curated",
            "status": "official_candidate",
            "note": "브랜드 공식 무료 서체 배포처입니다.",
        },
        {
            "query": "manual curated design display sources",
            "title": "배달의민족 글꼴",
            "snippet": "우아한형제들이 배포하는 공식 무료 브랜드 서체 페이지입니다.",
            "result_url": "https://www.woowahan.com/fonts",
            "normalized_url": "https://www.woowahan.com/fonts",
            "domain": "www.woowahan.com",
            "discovery_source": "manual_curated",
            "status": "official_candidate",
            "note": "브랜드 공식 무료 서체 배포처입니다.",
        },
        {
            "query": "manual curated design display sources",
            "title": "Gmarket Design System",
            "snippet": "G마켓 산스 폰트 ZIP 다운로드를 제공하는 공식 디자인 시스템입니다.",
            "result_url": "https://gds.gmarket.co.kr/",
            "normalized_url": "https://gds.gmarket.co.kr/",
            "domain": "gds.gmarket.co.kr",
            "discovery_source": "manual_curated",
            "status": "official_candidate",
            "note": "브랜드 공식 디자인 시스템 기반 무료 폰트 배포처입니다.",
        },
        {
            "query": "manual curated design display sources",
            "title": "Nexon Font",
            "snippet": "넥슨이 배포하는 공식 브랜드 폰트 페이지입니다.",
            "result_url": "https://brand.nexon.com/brand/fonts",
            "normalized_url": "https://brand.nexon.com/brand/fonts",
            "domain": "brand.nexon.com",
            "discovery_source": "manual_curated",
            "status": "official_candidate",
            "note": "브랜드 공식 무료 서체 배포처입니다.",
        },
        {
            "query": "manual curated design display sources",
            "title": "여기어때잘난체",
            "snippet": "여기어때가 제공하는 잘난체/잘난체 고딕 공식 배포 페이지입니다.",
            "result_url": "https://www.goodchoice.kr/font/mobile",
            "normalized_url": "https://www.goodchoice.kr/font/mobile",
            "domain": "www.goodchoice.kr",
            "discovery_source": "manual_curated",
            "status": "official_candidate",
            "note": "브랜드 공식 무료 서체 배포처입니다.",
        },
        {
            "query": "manual curated design display sources",
            "title": "카페24 PRO UP 폰트",
            "snippet": "카페24가 제공하는 공식 무료 브랜드 폰트 소개 페이지입니다.",
            "result_url": "https://www.cafe24.com/story/use/cafe24pro_font.html",
            "normalized_url": "https://www.cafe24.com/story/use/cafe24pro_font.html",
            "domain": "www.cafe24.com",
            "discovery_source": "manual_curated",
            "status": "official_candidate",
            "note": "브랜드 공식 무료 폰트 소개 및 배포 맥락 페이지입니다.",
        },
        {
            "query": "manual curated design display sources",
            "title": "제주 전용서체",
            "snippet": "제주특별자치도가 배포하는 공식 무료 서체 페이지입니다.",
            "result_url": "https://www.jeju.go.kr/jeju/font.htm",
            "normalized_url": "https://www.jeju.go.kr/jeju/font.htm",
            "domain": "www.jeju.go.kr",
            "discovery_source": "manual_curated",
            "status": "official_candidate",
            "note": "공공 공식 무료 서체 배포처입니다.",
        },
    ],
    "design-display-en": [
        {
            "query": "manual curated english display sources",
            "title": "The League of Moveable Type",
            "snippet": "공식 오픈소스 영문 폰트 파운드리로 League Gothic, Knewave 같은 디자인용 폰트를 제공합니다.",
            "result_url": "https://www.theleagueofmoveabletype.com/",
            "normalized_url": "https://www.theleagueofmoveabletype.com/",
            "domain": "www.theleagueofmoveabletype.com",
            "discovery_source": "manual_curated",
            "status": "official_candidate",
            "note": "OFL 기반 영문 디자인 폰트 공식 배포처입니다.",
        },
        {
            "query": "manual curated english display sources",
            "title": "Fontshare",
            "snippet": "Clash Display, Cabinet Grotesk, Boska 같은 상업 사용 가능한 free tier 영문 폰트를 제공하는 공식 서비스입니다.",
            "result_url": "https://www.fontshare.com/",
            "normalized_url": "https://www.fontshare.com/",
            "domain": "www.fontshare.com",
            "discovery_source": "manual_curated",
            "status": "official_candidate",
            "note": "브랜딩/에디토리얼용 영문 디자인 폰트 소스입니다.",
        },
        {
            "query": "manual curated english display sources",
            "title": "Velvetyne",
            "snippet": "실험적이고 브루탈리스트 성향의 영문 display 폰트를 제공하는 공식 배포처입니다.",
            "result_url": "https://velvetyne.fr/",
            "normalized_url": "https://velvetyne.fr/",
            "domain": "velvetyne.fr",
            "discovery_source": "manual_curated",
            "status": "official_candidate",
            "note": "실험적 영문 디자인 폰트 공식 배포처입니다.",
        },
        {
            "query": "manual curated english display sources",
            "title": "Collletttivo",
            "snippet": "포스터, 패션, 에디토리얼 무드의 영문 무료 폰트를 제공하는 공식 타입 컬렉티브입니다.",
            "result_url": "https://www.collletttivo.it/licensing",
            "normalized_url": "https://www.collletttivo.it/licensing",
            "domain": "www.collletttivo.it",
            "discovery_source": "manual_curated",
            "status": "official_candidate",
            "note": "실험적 영문 디스플레이 폰트 소스입니다.",
        },
        {
            "query": "manual curated english display sources",
            "title": "indestructible type*",
            "snippet": "Jost, Besley 등 상업 사용 가능한 고품질 영문 세리프/산스를 제공하는 공식 배포처입니다.",
            "result_url": "https://indestructibletype.com/",
            "normalized_url": "https://indestructibletype.com/",
            "domain": "indestructibletype.com",
            "discovery_source": "manual_curated",
            "status": "official_candidate",
            "note": "영문 브랜딩/에디토리얼 폰트 공식 배포처입니다.",
        },
    ],
}


def get_curated_candidates(profile: str) -> list[dict]:
    try:
        items = CURATED_CANDIDATE_SETS[profile]
    except KeyError as exc:
        raise KeyError(f"Unknown curated candidate profile: {profile}") from exc

    discovered_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return [{**item, "discovered_at": discovered_at} for item in items]
