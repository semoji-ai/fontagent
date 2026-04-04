from __future__ import annotations


SOURCE_LICENSE_POLICIES: dict[str, dict] = {
    "google_fonts": {
        "trust_level": "high",
        "review_level": "low",
        "notes": ["공식 오픈 폰트 배포처", "웹/앱/영상 워크플로에 자주 사용되는 안정적 소스"],
    },
    "google_display": {
        "trust_level": "high",
        "review_level": "low",
        "notes": ["Google Fonts curated display 세트", "소스 신뢰도는 높지만 개별 패밀리 조건은 여전히 확인 필요"],
    },
    "fontshare_display": {
        "trust_level": "high",
        "review_level": "low",
        "notes": ["공식 배포 API 기반", "상업 사용과 웹 임베딩 판단에 유리한 소스"],
    },
    "league_movable_type": {
        "trust_level": "high",
        "review_level": "medium",
        "notes": ["공식 오픈 배포 소스", "개별 패밀리 라이선스 페이지를 함께 확인하면 더 안전함"],
    },
    "velvetyne_display": {
        "trust_level": "medium",
        "review_level": "medium",
        "notes": ["실험적/독립 배포 성격이 강함", "프로젝트 납품 전 개별 라이선스 페이지 확인 권장"],
    },
    "naver_hangeul": {
        "trust_level": "high",
        "review_level": "low",
        "notes": ["공식 브랜드/플랫폼 배포 소스", "한국어 프로젝트에서 신뢰도가 높음"],
    },
    "hancom": {
        "trust_level": "high",
        "review_level": "medium",
        "notes": ["공식 배포처", "매체별 사용 범위는 요약문과 원문을 함께 보는 편이 안전함"],
    },
    "gongu_freefont": {
        "trust_level": "medium",
        "review_level": "high",
        "notes": ["공공 포털이지만 개별 항목별 조건 차이가 있을 수 있음", "클라이언트 납품/웹 임베딩 전 개별 페이지 검토 권장"],
    },
    "noonnu": {
        "trust_level": "medium",
        "review_level": "medium",
        "notes": ["허브/인덱스 성격", "최종 판단은 원 출처 또는 라이선스 요약과 함께 보는 편이 안전함"],
    },
    "fonco_freefont": {
        "trust_level": "medium",
        "review_level": "medium",
        "notes": ["디자인 큐레이션 소스", "자동 설치는 편하지만 납품 전 라이선스 문구 재확인 권장"],
    },
    "gmarket_brand": {
        "trust_level": "high",
        "review_level": "low",
        "notes": ["공식 브랜드 배포 소스"],
    },
    "goodchoice_brand": {
        "trust_level": "high",
        "review_level": "low",
        "notes": ["공식 브랜드 배포 소스"],
    },
    "woowahan_brand": {
        "trust_level": "high",
        "review_level": "low",
        "notes": ["공식 브랜드 배포 소스"],
    },
    "nexon_brand": {
        "trust_level": "high",
        "review_level": "low",
        "notes": ["공식 브랜드 배포 소스"],
    },
    "cafe24_brand": {
        "trust_level": "high",
        "review_level": "low",
        "notes": ["공식 브랜드 배포 소스"],
    },
    "jeju_official": {
        "trust_level": "high",
        "review_level": "medium",
        "notes": ["공식 지자체 배포 소스", "웹 임베딩/재배포 등 세부 매체 조건은 재확인 권장"],
    },
}


DEFAULT_SOURCE_LICENSE_POLICY = {
    "trust_level": "low",
    "review_level": "high",
    "notes": ["정책 카탈로그에 없는 소스", "사용 전 원문 라이선스 확인 권장"],
}


def get_source_license_policy(source_site: str) -> dict:
    key = (source_site or "").strip().lower()
    policy = SOURCE_LICENSE_POLICIES.get(key, DEFAULT_SOURCE_LICENSE_POLICY)
    return {
        "source_site": key,
        "trust_level": policy["trust_level"],
        "review_level": policy["review_level"],
        "notes": list(policy["notes"]),
    }
