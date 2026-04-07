from __future__ import annotations

from copy import deepcopy


INTERVIEW_CATALOG = {
    "video": {
        "label": "영상",
        "subcategories": {
            "thumbnail": {
                "label": "썸네일",
                "medium": "video",
                "surface": "thumbnail",
                "role": "title",
                "tones": ["cinematic", "display"],
                "questions": [
                    {
                        "id": "tone",
                        "label": "어떤 분위기가 핵심인가요?",
                        "default": "cinematic",
                        "options": [
                            {"value": "cinematic", "label": "영화적 / 강한 임팩트", "tones": ["cinematic", "display"], "background_mode": "deep-contrast"},
                            {"value": "retro", "label": "레트로 / 간판체 느낌", "tones": ["retro", "poster"], "background_mode": "warm-paper"},
                            {"value": "serious", "label": "다큐 / 진중함", "tones": ["documentary", "editorial"], "background_mode": "neutral-contrast"},
                        ],
                    },
                    {
                        "id": "density",
                        "label": "텍스트 밀도는 어느 쪽인가요?",
                        "default": "compact",
                        "options": [
                            {"value": "compact", "label": "짧고 강하게", "copy_mode": "compact"},
                            {"value": "balanced", "label": "제목 + 보조 설명", "copy_mode": "balanced"},
                        ],
                    },
                    {
                        "id": "language_mix",
                        "label": "언어 구성은 어떤가요?",
                        "default": "ko",
                        "options": [
                            {"value": "ko", "label": "한글 중심", "languages": ["ko"]},
                            {"value": "ko-en", "label": "한글 + 영문 혼합", "languages": ["ko", "en"], "tones": ["bilingual"]},
                        ],
                    },
                    {
                        "id": "license_mode",
                        "label": "사용 조건은 어떤가요?",
                        "default": "monetized",
                        "options": [
                            {"value": "monetized", "label": "상업 영상 / 수익화", "constraints": {"commercial_use": True, "video_use": True}},
                            {"value": "platform", "label": "웹 배포도 함께", "constraints": {"commercial_use": True, "video_use": True, "web_embedding": True}},
                        ],
                    },
                ],
                "copy_variants": {
                    "compact": {
                        "kicker": "FONTAGENT",
                        "title": "지금 판이 바뀌고 있다",
                        "subtitle": "한눈에 읽히는 타이틀이 먼저 보입니다",
                        "body": "짧은 title과 보조 설명을 분리해 위계를 명확히 잡습니다.",
                    },
                    "balanced": {
                        "kicker": "BREAKDOWN",
                        "title": "역사는 왜 반복처럼 보일까",
                        "subtitle": "강한 제목과 보조 설명을 함께 쓰는 썸네일 구조",
                        "body": "title은 크게, subtitle은 2차 정보만 담당하도록 분리하는 것이 핵심입니다.",
                    },
                },
                "canvas": {
                    "layout_mode": "left-stack",
                    "background_mode": "deep-contrast",
                    "ratio_hint": "16:9",
                    "notes": [
                        "title을 4~6단어 안으로 압축하면 가장 안정적입니다.",
                        "subtitle은 title을 보조하는 한 줄 정보만 남기는 편이 좋습니다.",
                    ],
                },
            },
            "subtitle_track": {
                "label": "자막",
                "medium": "video",
                "surface": "subtitle_track",
                "role": "subtitle",
                "tones": ["readable", "sans"],
                "questions": [
                    {
                        "id": "tone",
                        "label": "자막 톤은 어느 쪽인가요?",
                        "default": "neutral",
                        "options": [
                            {"value": "neutral", "label": "가장 무난하고 잘 읽히게", "tones": ["readable", "neutral", "sans"], "background_mode": "subtitle-safe"},
                            {"value": "documentary", "label": "다큐 / 차분한 정보형", "tones": ["readable", "documentary", "sans"], "background_mode": "subtitle-safe"},
                            {"value": "modern", "label": "모던 / 프로덕트 느낌", "tones": ["clean", "system", "sans"], "background_mode": "subtitle-safe"},
                        ],
                    },
                    {
                        "id": "density",
                        "label": "자막 정보량은 어느 쪽인가요?",
                        "default": "balanced",
                        "options": [
                            {"value": "compact", "label": "짧고 빠른 자막", "copy_mode": "compact"},
                            {"value": "balanced", "label": "한 줄 설명형", "copy_mode": "balanced"},
                        ],
                    },
                    {
                        "id": "language_mix",
                        "label": "언어 구성은 어떤가요?",
                        "default": "ko",
                        "options": [
                            {"value": "ko", "label": "한글 중심", "languages": ["ko"]},
                            {"value": "ko-en", "label": "한글 + 영문 혼합", "languages": ["ko", "en"], "tones": ["bilingual"]},
                            {"value": "en", "label": "영문 중심", "languages": ["en"]},
                        ],
                    },
                    {
                        "id": "license_mode",
                        "label": "사용 조건은 어떤가요?",
                        "default": "monetized",
                        "options": [
                            {"value": "monetized", "label": "상업 영상 / 수익화", "constraints": {"commercial_use": True, "video_use": True}},
                            {"value": "platform", "label": "웹 배포도 함께", "constraints": {"commercial_use": True, "video_use": True, "web_embedding": True}},
                        ],
                    },
                ],
                "copy_variants": {
                    "compact": {
                        "kicker": "SUBTITLE SYSTEM",
                        "title": "지금 가장 중요한 건 가독성입니다",
                        "subtitle": "짧고 빠르게 읽히는 자막 구조",
                        "body": "자막은 표현보다 안정적인 리듬이 먼저여야 합니다.",
                    },
                    "balanced": {
                        "kicker": "READABLE TYPE",
                        "title": "설명형 자막은 제목보다 읽힘이 우선입니다",
                        "subtitle": "정보형 자막은 neutral sans가 가장 오래 버팁니다",
                        "body": "line-height와 자간을 과하게 흔들지 않고, 한 줄 폭을 통제하는 것이 핵심입니다.",
                    },
                },
                "canvas": {
                    "layout_mode": "subtitle-band",
                    "background_mode": "subtitle-safe",
                    "ratio_hint": "16:9",
                    "notes": [
                        "자막은 화면 하단 안전 영역을 우선 확보해야 합니다.",
                        "title용 display 폰트보다 neutral sans가 먼저 올라오도록 설계합니다.",
                    ],
                },
            },
            "opener_title": {
                "label": "오프닝 타이틀",
                "medium": "video",
                "surface": "cover",
                "role": "title",
                "tones": ["cinematic", "editorial"],
                "questions": [
                    {
                        "id": "tone",
                        "label": "오프닝의 인상은 어느 쪽인가요?",
                        "default": "editorial",
                        "options": [
                            {"value": "editorial", "label": "에디토리얼 / 진중함", "tones": ["editorial", "documentary"], "background_mode": "paper-editorial"},
                            {"value": "tech", "label": "미래적 / 시스템 느낌", "tones": ["tech", "display"], "background_mode": "tech-grid"},
                            {"value": "luxury", "label": "고급 / 브랜드 필름", "tones": ["luxury", "serif"], "background_mode": "deep-contrast"},
                        ],
                    },
                    {
                        "id": "density",
                        "label": "텍스트 구조는 어느 쪽인가요?",
                        "default": "balanced",
                        "options": [
                            {"value": "compact", "label": "제목 중심", "copy_mode": "compact"},
                            {"value": "balanced", "label": "제목 + 데크", "copy_mode": "balanced"},
                        ],
                    },
                    {
                        "id": "license_mode",
                        "label": "사용 조건은 어떤가요?",
                        "default": "video",
                        "options": [
                            {"value": "video", "label": "영상 중심", "constraints": {"commercial_use": True, "video_use": True}},
                            {"value": "cross", "label": "웹/키비주얼도 함께", "constraints": {"commercial_use": True, "video_use": True, "web_embedding": True}},
                        ],
                    },
                ],
                "copy_variants": {
                    "compact": {
                        "kicker": "OPENING TITLE",
                        "title": "문명의 리듬은 글자에서 드러난다",
                        "subtitle": "첫 장면에서 톤을 규정하는 제목 구조",
                        "body": "오프닝은 짧은 타이틀과 여백의 밀도로 인상을 결정합니다.",
                    },
                    "balanced": {
                        "kicker": "TITLE SEQUENCE",
                        "title": "우리가 보는 역사는 언제나 편집된 결과다",
                        "subtitle": "타이틀과 데크를 함께 써서 다큐의 분위기를 먼저 잡습니다",
                        "body": "장면 전환 전에도 읽히는 구조를 기준으로 type scale을 설계합니다.",
                    },
                },
                "canvas": {
                    "layout_mode": "center-cover",
                    "background_mode": "paper-editorial",
                    "ratio_hint": "16:9",
                    "notes": [
                        "오프닝은 여백이 곧 톤이므로 subtitle을 과하게 늘리지 않습니다.",
                    ],
                },
            },
        },
    },
    "web": {
        "label": "웹페이지",
        "subcategories": {
            "landing_hero": {
                "label": "랜딩 히어로",
                "medium": "web",
                "surface": "landing_hero",
                "role": "title",
                "tones": ["editorial"],
                "questions": [
                    {
                        "id": "tone",
                        "label": "브랜드 톤은 어느 쪽인가요?",
                        "default": "editorial",
                        "options": [
                            {"value": "editorial", "label": "에디토리얼 / 신뢰감", "tones": ["editorial", "serif"], "background_mode": "paper-editorial"},
                            {"value": "modern", "label": "모던 / 프로덕트", "tones": ["clean", "system"], "background_mode": "neutral-system"},
                            {"value": "luxury", "label": "고급 / 하이엔드", "tones": ["luxury", "serif"], "background_mode": "soft-luxury"},
                        ],
                    },
                    {
                        "id": "density",
                        "label": "헤드라인 길이는 어느 쪽인가요?",
                        "default": "balanced",
                        "options": [
                            {"value": "compact", "label": "짧고 강한 헤드라인", "copy_mode": "compact"},
                            {"value": "balanced", "label": "제목 + 설명형 데크", "copy_mode": "balanced"},
                            {"value": "editorial", "label": "긴 문장형 헤드라인", "copy_mode": "editorial"},
                        ],
                    },
                    {
                        "id": "language_mix",
                        "label": "언어 구성은 어떤가요?",
                        "default": "ko",
                        "options": [
                            {"value": "ko", "label": "한글 중심", "languages": ["ko"]},
                            {"value": "ko-en", "label": "한글 + 영문 혼합", "languages": ["ko", "en"], "tones": ["bilingual"]},
                            {"value": "en", "label": "영문 중심", "languages": ["en"]},
                        ],
                    },
                    {
                        "id": "license_mode",
                        "label": "배포 조건은 어떤가요?",
                        "default": "web",
                        "options": [
                            {"value": "web", "label": "웹 임베딩 필요", "constraints": {"commercial_use": True, "web_embedding": True}},
                            {"value": "campaign", "label": "웹 + 캠페인 이미지", "constraints": {"commercial_use": True, "web_embedding": True, "video_use": True}},
                        ],
                    },
                ],
                "copy_variants": {
                    "compact": {
                        "kicker": "FONT SYSTEM",
                        "title": "브랜드의 첫인상은 타이포그래피에서 시작됩니다",
                        "subtitle": "짧은 헤드라인과 한 줄 설명으로 위계를 분명하게 만듭니다",
                        "body": "디자인 에이전트는 이 구조 위에 컬러와 레이아웃만 더하면 됩니다.",
                    },
                    "balanced": {
                        "kicker": "TYPOGRAPHY LAYER",
                        "title": "글자만 정리해도 화면의 위계는 훨씬 명확해집니다",
                        "subtitle": "Title, subtitle, body를 분리해도 디자인의 밀도는 올라갑니다",
                        "body": "FontAgent는 역할별 폰트와 기본 비율을 먼저 고정하고, 디자인 에이전트는 그 위에 레이아웃을 확장합니다.",
                    },
                    "editorial": {
                        "kicker": "EDITORIAL SYSTEM",
                        "title": "긴 문장형 헤드라인도 질서 있게 보이려면, 우선 폰트 시스템부터 정리해야 합니다",
                        "subtitle": "긴 문장에서는 title의 리듬과 body의 폭이 동시에 중요합니다",
                        "body": "Hero에서는 시각 위계가 먼저 보이고, 본문에서는 가독성이 이어져야 합니다.",
                    },
                },
                "canvas": {
                    "layout_mode": "split-hero",
                    "background_mode": "paper-editorial",
                    "ratio_hint": "responsive",
                    "notes": [
                        "hero title과 supporting deck을 6:4 정도로 나누는 편이 안정적입니다.",
                        "body 영역은 지나치게 넓지 않게 유지하는 것이 좋습니다.",
                    ],
                },
            },
            "detail_banner": {
                "label": "상세페이지 배너",
                "medium": "ecommerce",
                "surface": "detailpage_banner",
                "role": "title",
                "tones": ["display", "promotion"],
                "questions": [
                    {
                        "id": "tone",
                        "label": "제품 배너의 인상은 어느 쪽인가요?",
                        "default": "promotion",
                        "options": [
                            {"value": "promotion", "label": "프로모션 / 강한 CTA", "tones": ["promotion", "display"], "background_mode": "bright-promo"},
                            {"value": "clean", "label": "정보형 / 단정함", "tones": ["clean", "system"], "background_mode": "neutral-system"},
                            {"value": "cute", "label": "키치 / 귀여움", "tones": ["playful", "cute"], "background_mode": "bright-promo"},
                        ],
                    },
                    {
                        "id": "density",
                        "label": "정보량은 어느 쪽인가요?",
                        "default": "balanced",
                        "options": [
                            {"value": "compact", "label": "한 줄 가격/혜택 중심", "copy_mode": "compact"},
                            {"value": "balanced", "label": "제목 + 혜택 + CTA", "copy_mode": "balanced"},
                        ],
                    },
                    {
                        "id": "license_mode",
                        "label": "배포 조건은 어떤가요?",
                        "default": "commerce",
                        "options": [
                            {"value": "commerce", "label": "웹 임베딩 필요", "constraints": {"commercial_use": True, "web_embedding": True}},
                            {"value": "commerce-video", "label": "상세페이지 + 숏폼", "constraints": {"commercial_use": True, "web_embedding": True, "video_use": True}},
                        ],
                    },
                ],
                "copy_variants": {
                    "compact": {
                        "kicker": "LIMITED OFFER",
                        "title": "오늘만 20% OFF",
                        "subtitle": "강한 타이틀과 짧은 CTA가 핵심입니다",
                        "body": "상세페이지 배너는 즉시 읽히는 가격/혜택 구조가 우선입니다.",
                    },
                    "balanced": {
                        "kicker": "PROMOTION",
                        "title": "좋아 보이는 할인 배너는 글자 위계부터 다릅니다",
                        "subtitle": "타이틀, 혜택, CTA의 세 줄 구조를 분리해 설계합니다",
                        "body": "과한 장식보다 읽히는 hierarchy가 전환에 더 직접적으로 기여합니다.",
                    },
                },
                "canvas": {
                    "layout_mode": "banner-stack",
                    "background_mode": "bright-promo",
                    "ratio_hint": "wide banner",
                    "notes": [
                        "혜택 숫자와 CTA를 title과 분리해 두면 배너가 더 읽기 쉬워집니다.",
                    ],
                },
            },
        },
    },
    "presentation": {
        "label": "PPT",
        "subcategories": {
            "cover": {
                "label": "표지 슬라이드",
                "medium": "presentation",
                "surface": "cover",
                "role": "title",
                "tones": ["brand"],
                "questions": [
                    {
                        "id": "tone",
                        "label": "발표의 인상은 어느 쪽인가요?",
                        "default": "brand",
                        "options": [
                            {"value": "brand", "label": "브랜드 / 프로페셔널", "tones": ["brand", "clean"], "background_mode": "neutral-system"},
                            {"value": "editorial", "label": "인사이트 / 리서치", "tones": ["editorial"], "background_mode": "paper-editorial"},
                            {"value": "impact", "label": "세일즈 / 강한 인상", "tones": ["display", "impact"], "background_mode": "deep-contrast"},
                        ],
                    },
                    {
                        "id": "density",
                        "label": "표지 구조는 어느 쪽인가요?",
                        "default": "balanced",
                        "options": [
                            {"value": "compact", "label": "제목 + 부제", "copy_mode": "compact"},
                            {"value": "balanced", "label": "제목 + 설명 + 메타", "copy_mode": "balanced"},
                        ],
                    },
                    {
                        "id": "license_mode",
                        "label": "배포 조건은 어떤가요?",
                        "default": "presentation",
                        "options": [
                            {"value": "presentation", "label": "PPT/PDF 납품", "constraints": {"commercial_use": True}},
                            {"value": "presentation-web", "label": "PDF + 웹 공개", "constraints": {"commercial_use": True, "web_embedding": True}},
                        ],
                    },
                ],
                "copy_variants": {
                    "compact": {
                        "kicker": "PRESENTATION",
                        "title": "타이포 시스템이 프레젠테이션의 톤을 만든다",
                        "subtitle": "표지는 발표의 기대치를 미리 결정합니다",
                        "body": "표지에서는 title과 subtitle만으로도 충분한 경우가 많습니다.",
                    },
                    "balanced": {
                        "kicker": "INSIGHT DECK",
                        "title": "좋은 슬라이드는 레이아웃 이전에 글자 위계가 분명합니다",
                        "subtitle": "표지, 섹션 타이틀, 본문이 같은 문법으로 이어져야 합니다",
                        "body": "PPT는 장식보다 안정적인 type scale과 line-height가 먼저입니다.",
                    },
                },
                "canvas": {
                    "layout_mode": "center-cover",
                    "background_mode": "neutral-system",
                    "ratio_hint": "16:9 slide",
                    "notes": [
                        "표지에서는 여백과 헤드라인의 비율이 가장 먼저 보입니다.",
                    ],
                },
            },
        },
    },
    "print": {
        "label": "인쇄물",
        "subcategories": {
            "poster_headline": {
                "label": "포스터 헤드라인",
                "medium": "print",
                "surface": "poster_headline",
                "role": "title",
                "tones": ["poster", "display"],
                "questions": [
                    {
                        "id": "tone",
                        "label": "포스터 무드는 어느 쪽인가요?",
                        "default": "poster",
                        "options": [
                            {"value": "poster", "label": "전시 / 포스터", "tones": ["poster", "display"], "background_mode": "warm-paper"},
                            {"value": "luxury", "label": "하이엔드 / 세리프", "tones": ["luxury", "serif"], "background_mode": "soft-luxury"},
                            {"value": "street", "label": "스트리트 / 거칠고 강함", "tones": ["street", "impact"], "background_mode": "deep-contrast"},
                        ],
                    },
                    {
                        "id": "density",
                        "label": "텍스트 구조는 어느 쪽인가요?",
                        "default": "compact",
                        "options": [
                            {"value": "compact", "label": "헤드라인 중심", "copy_mode": "compact"},
                            {"value": "balanced", "label": "헤드라인 + 설명", "copy_mode": "balanced"},
                        ],
                    },
                    {
                        "id": "license_mode",
                        "label": "사용 조건은 어떤가요?",
                        "default": "print",
                        "options": [
                            {"value": "print", "label": "인쇄 / 오프라인 중심", "constraints": {"commercial_use": True}},
                            {"value": "print-web", "label": "인쇄 + 웹 홍보", "constraints": {"commercial_use": True, "web_embedding": True}},
                        ],
                    },
                ],
                "copy_variants": {
                    "compact": {
                        "kicker": "POSTER SERIES",
                        "title": "TYPE IS THE MESSAGE",
                        "subtitle": "제목 자체가 포스터의 주인공인 경우",
                        "body": "헤드라인이 가장 먼저 보이고, 나머지 정보는 뒤따라야 합니다.",
                    },
                    "balanced": {
                        "kicker": "EXHIBITION",
                        "title": "좋은 포스터는 헤드라인의 비율에서 이미 완성된다",
                        "subtitle": "제목, 데크, 정보 블록의 간격이 포스터의 리듬을 만듭니다",
                        "body": "타이포가 화면을 지배하도록 여백과 title 면적을 크게 가져갑니다.",
                    },
                },
                "canvas": {
                    "layout_mode": "poster-stack",
                    "background_mode": "warm-paper",
                    "ratio_hint": "3:4",
                    "notes": [
                        "포스터는 title 면적과 여백 대비를 더 크게 잡는 편이 좋습니다.",
                    ],
                },
            },
        },
    },
}


def list_interview_catalog() -> dict:
    return deepcopy(INTERVIEW_CATALOG)


def get_interview_flow(category: str, subcategory: str) -> dict:
    try:
        return deepcopy(INTERVIEW_CATALOG[category]["subcategories"][subcategory])
    except KeyError as exc:
        raise KeyError(f"Unknown interview flow: {category}/{subcategory}") from exc


def build_interview_plan(category: str, subcategory: str, answers: dict | None = None, language: str = "ko") -> dict:
    catalog = list_interview_catalog()
    flow = get_interview_flow(category, subcategory)
    category_info = catalog[category]
    answers = answers or {}

    tones = list(flow.get("tones", []))
    languages = [language]
    constraints = {"commercial_use": True}
    summary: list[dict] = []
    copy_mode = next(iter(flow["copy_variants"]))
    layout_mode = flow["canvas"]["layout_mode"]
    background_mode = flow["canvas"]["background_mode"]

    for question in flow.get("questions", []):
        options = {option["value"]: option for option in question.get("options", [])}
        selected_value = answers.get(question["id"], question.get("default"))
        option = options.get(selected_value)
        if not option:
            option = options[question.get("default")]
        summary.append(
            {
                "id": question["id"],
                "label": question["label"],
                "value": option["value"],
                "answer_label": option["label"],
            }
        )
        tones.extend(option.get("tones", []))
        if option.get("languages"):
            languages = option["languages"]
        if option.get("constraints"):
            constraints.update(option["constraints"])
        if option.get("copy_mode"):
            copy_mode = option["copy_mode"]
        if option.get("layout_mode"):
            layout_mode = option["layout_mode"]
        if option.get("background_mode"):
            background_mode = option["background_mode"]

    deduped_tones: list[str] = []
    seen = set()
    for tone in tones:
        normalized = tone.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped_tones.append(normalized)

    recommended_copy = deepcopy(flow["copy_variants"][copy_mode])
    canvas = {
        "layout_mode": layout_mode,
        "background_mode": background_mode,
        "ratio_hint": flow["canvas"]["ratio_hint"],
        "notes": list(flow["canvas"].get("notes", [])),
        "text_blocks": recommended_copy,
    }

    return {
        "category": category,
        "category_label": category_info["label"],
        "subcategory": subcategory,
        "subcategory_label": flow["label"],
        "request": {
            "medium": flow["medium"],
            "surface": flow["surface"],
            "role": flow["role"],
            "tones": deduped_tones,
            "languages": languages,
            "constraints": constraints,
        },
        "interview_summary": summary,
        "recommended_copy": recommended_copy,
        "canvas": canvas,
    }
