# FontAgent

`FontAgent`는 에이전트와 개발자가 원하는 톤과 용도에 맞는 무료 폰트를 찾고, 설치하고, 프로젝트용 폰트 시스템으로 넘기기 위한 도구입니다.

핵심은 복잡한 수집 명령이 아니라 아래 4가지입니다.

- 원하는 작업에 맞는 폰트 추천
- 마음에 드는 폰트 설치
- 프로젝트용 폰트 시스템 export
- 이미지에 있는 텍스트에서 폰트 식별

## 권장 사용 방식

가장 단순한 사용 방식은 `FontAgent`를 에이전트에 연결한 뒤 원하는 폰트를 요청하는 것입니다.

예:

- "유튜브 지식채널 제목용 한국어 무료 폰트 추천해줘"
- "화이트 배경 발표자료에 맞는 본문 폰트 조합 찾아줘"
- "이 프로젝트에 맞는 title/body/subtitle 폰트 시스템 만들어줘"

## 빠른 시작

```bash
cd fontagent
python3 -m fontagent.cli init
python3 -m fontagent.cli recommend --task "history documentary title" --language ko
python3 -m fontagent.cli install <font-id> --output-dir ./assets/fonts
python3 -m fontagent.cli prepare-font-system --project-path ./demo --task "history documentary" --target both
python3 -m fontagent.cli mcp
```

설명:

- `init`
  - 로컬 DB 초기화
- `recommend`
  - 작업 설명을 기반으로 추천 폰트 목록 반환
- `install`
  - 원하는 폰트 설치
- `prepare-font-system`
  - 프로젝트용 `title/body/subtitle` 폰트 시스템 생성
- `mcp`
  - 에이전트가 `FontAgent`를 직접 호출할 수 있게 MCP 서버 실행

## 자주 쓰는 명령

```bash
python3 -m fontagent.cli search --query "korean subtitle"
python3 -m fontagent.cli recommend --task "youtube documentary title" --language ko
python3 -m fontagent.cli install <font-id> --output-dir ./assets/fonts
python3 -m fontagent.cli preview <font-id> --preset title-ko
python3 -m fontagent.cli prepare-font-system --project-path ./demo --task "history documentary" --target both
python3 -m fontagent.cli generate-typography-handoff --project-path ./demo --task "history documentary" --use-case documentary-landing-ko
python3 -m fontagent.cli mcp
```

## 에이전트 협업에서의 역할

`FontAgent`는 다른 에이전트가 typography 결정을 외주 줄 수 있는 폰트 전담 레이어를 목표로 합니다.

대표 협업 예:

- 영상 에이전트
  - 제목, 정보 텍스트, 말자막용 폰트 역할 분리
- 차트 에이전트
  - `chart_title`, `axis_label`, `table_cell`, `source_note`용 폰트 제공
- 슬라이드 에이전트
  - cover, section title, body, annotation 체계 제공
- 이미지/썸네일 에이전트
  - 강한 display 폰트 후보와 설치 경로 제공

즉 `FontAgent`는 "폰트 추천기"가 아니라, 다른 에이전트가 재사용 가능한 typography service에 가깝습니다.

## 대시보드 방향

앞으로 대시보드는 아래 방향으로 강화할 예정입니다.

- 카테고리별 추천 폰트 목록
  - 제목
  - 본문
  - 자막
  - 차트/표
  - 슬라이드
- 검색과 필터
  - 언어
  - 톤
  - 라이선스
  - 사용 매체
- 쉬운 설치
  - 추천 목록에서 바로 설치
  - 설치 상태 확인
  - 프로젝트에 바로 연결
- 에이전트 협업
  - 다른 에이전트가 role 기반으로 폰트를 요청하고 결과를 handoff 받을 수 있는 구조

상세 방향은 [PRODUCT_DIRECTION.md](./PRODUCT_DIRECTION.md)에 정리했습니다.

## 운영자 문서

아래 문서는 일반 사용자용이 아니라 운영/학습/통합용입니다.

- 레퍼런스 학습 계획: [REFERENCE_LEARNING_PLAN.md](./REFERENCE_LEARNING_PLAN.md)
- MCP 연동: [MCP_INTEGRATIONS.md](./MCP_INTEGRATIONS.md)
- 네트워크/운영 런북: [NETWORK_RUNBOOK.md](./NETWORK_RUNBOOK.md)

## 현재 범위

현재 MVP 범위:

- SQLite 레지스트리
- 검색/추천
- SVG 미리보기
- direct/zip/manual 다운로드 추상화
- 주요 무료 폰트 소스 importer
- CSS export
- Remotion export
- CLI
- MCP stdio server
- 간단한 웹 UI (`/`)
- 프로젝트용 폰트 시스템/타이포 handoff 생성
- 이미지 → 폰트 식별 (glyph fingerprint 기반)

## 이미지에서 폰트 찾기

설치된 폰트 파일로부터 글자 단위 지문 인덱스를 구축하고, 이미지에 있는
텍스트를 같은 지문 공간에서 비교해 top 1~5 후보 폰트를 각 라이선스
정보와 함께 반환합니다. 의존성이 필요하므로 `identify` extra를 먼저
설치해야 합니다.

```bash
pip install "fontagent[identify]"

python3 -m fontagent.cli build-glyph-index --language both
python3 -m fontagent.cli identify-font \
    --image path/to/slide.png \
    --char-hint H --char-hint E --char-hint L --char-hint L --char-hint O \
    --commercial-use --video-use --similar-count 5
```

- `build-glyph-index`
  - 시스템에 설치된 폰트를 자동 스캔해서 글리프 지문 인덱스를 생성
  - `--font-dir <path>` 를 여러 번 지정해 추가 폰트 파일 디렉터리 포함 가능
  - `--language` 로 ko / en / both 샘플 세트 선택
- `identify-font`
  - 이미지에서 글자를 분리해 인덱스와 비교, top 1~5 후보를 반환
  - 각 후보는 `license` (commercial/video/web/redistribution), `source`,
    `install` 블록을 포함해 다운로드/사용 가능 여부를 바로 판단할 수 있음
  - `--char-hint` 를 감지된 글자 순서대로 전달하면 정확도가 올라감
  - `--similar-count N` 으로 top-1 과 fingerprint 유사도 순으로 N개의
    대체 폰트를 추가 반환 (AI 생성 이미지처럼 정확 매칭이 어렵거나
    라이선스 조건을 만족하는 대안이 필요할 때 유용)
  - `--commercial-use`, `--video-use`, `--web-embedding`,
    `--redistribution` 을 조합해 similar alternatives 의 라이선스 조건
    필터를 지정

MCP에서도 동일하게 `build_glyph_index`, `identify_font_in_image` 도구로 노출됩니다.

## 포스터 → 텍스트 레이어 합성

멀티모달 LLM 에이전트가 OCR·영역 분할을 먼저 해서 `regions` 를 넘겨주면,
FontAgent 가 영역마다 **identify (시각적 매칭) + recommend (역할/스타일/언어
기반 추천)** 을 hybrid(RRF) 로 결합해 가장 맞는 폰트를 배정하고, 각 layer 를
라이선스·설치 정보와 함께 구조화해 돌려줍니다. 옵션으로 디버그 SVG 프리뷰도
작성합니다.

```bash
python3 -m fontagent.cli compose-text-layers \
    --image poster.png \
    --regions regions.json \
    --similar-count 3 \
    --svg-output preview.svg \
    --commercial-use
```

`regions.json` 예:

```json
[
  {
    "bbox": [60, 60, 800, 200],
    "text": "VINTAGE VIBES",
    "role": "title",
    "style_hints": ["serif", "display", "vintage"],
    "language": "en"
  },
  {
    "bbox": [60, 360, 500, 480],
    "text": "봄의 시작",
    "role": "subtitle",
    "style_hints": ["soft", "handwriting"],
    "language": "ko"
  }
]
```

FontAgent 는 OCR 을 직접 수행하지 않으며, `regions` 는 호출하는 에이전트가
채워 넘기는 것을 전제로 합니다. MCP 에서도 `compose_text_layers` 도구로 같은
입력을 받습니다.

### 타이포그래피 프리셋 (폰트 패밀리 조합)

자주 쓰는 title/subtitle/body 조합은 `typography_presets` 카탈로그에
저장해두고 재사용합니다. init 시 5개 시드 (`editorial-serif-ko`,
`modern-ui-ko`, `bilingual-neutral`, `traditional-ko`, `brand-developer-ko`)
가 자동 설치됩니다.

```bash
# 프리셋 목록
python3 -m fontagent.cli list-typography-presets --language ko

# 톤/매체로 프리셋 추천
python3 -m fontagent.cli recommend-typography-preset \
    --tone editorial --tone calm --language ko --medium editorial --count 3

# 프리셋 적용해서 compose
python3 -m fontagent.cli compose-text-layers \
    --image poster.png --regions regions.json \
    --preset editorial-serif-ko

# 새 프리셋 저장 (레퍼런스 이미지나 수동 큐레이션 결과)
python3 -m fontagent.cli save-typography-preset \
    --preset-id my-brand-pack --name "My Brand" \
    --tone brand --tone warm --language ko --medium web --surface landing \
    --role-assignments '{"title":{"font_id":"pretendard","fallback_font_ids":["suit"],"pairing_reason":""},"body":{"font_id":"suit","fallback_font_ids":[],"pairing_reason":""}}'
```

프리셋을 지정하면 각 영역의 `role` 에 해당하는 폰트가 승자로 고정됩니다.
라이선스 제약을 통과하지 못하면 `fallback_font_ids` 를 순서대로 시도하고,
그래도 실패하면 hybrid 매칭 결과로 되돌아갑니다. 프리셋이 골라준 폰트가
특정 영역에 안 어울린다고 판단되면 `similar_alternatives` 에 hybrid 가
추천한 대안이 남아있어 바로 교체 가능. MCP 에서도 `list_typography_presets`
/ `recommend_typography_preset` / `save_typography_preset` /
`delete_typography_preset` / `get_typography_preset` 도구로 노출됩니다.

### 한 번의 호출로 설치 + handoff 까지

`--install-to` / `--handoff-output` / `--css-output` / `--remotion-output`
을 같이 넘기면 한 번의 호출로 다음이 모두 완료됩니다:

1. 영역별 승자 폰트 자동 설치 (각 layer 의 `font.install` 블록에 `installed_files`
   와 `install_status` 부착)
2. 각 layer 에 `confidence ∈ [0,1]` + `confidence_tier ∈ {high,medium,low,none}`
   부착 — identify 와 recommend 둘 다 상위에서 만났는지, 한 쪽에서만 나왔는지에
   따라 계산
3. 설치된 경로를 참조하는 `@font-face` CSS 번들 작성
4. Remotion 에서 로드할 수 있는 `fontAgentTextLayerFonts` 배열 작성
5. `fontagent.text-layer-handoff.v1` 계약을 JSON 으로 영속화 — 다운스트림
   에이전트(예: 별도 PPT 에이전트)가 레이아웃/편집 가능한 텍스트박스를 만들 때
   그대로 소비할 수 있는 region→font 매핑

```bash
python3 -m fontagent.cli compose-text-layers \
    --image poster.png \
    --regions regions.json \
    --install-to ./assets/fonts \
    --handoff-output ./typography-handoff.json \
    --css-output ./fonts.css \
    --remotion-output ./src/remotionFonts.ts \
    --commercial-use
```

## 데이터 모델

핵심 필드:

- `font_id`
- `family`
- `source_site`
- `source_page_url`
- `download_type`
- `download_url`
- `license_summary`
- `commercial_use_allowed`
- `video_use_allowed`
- `web_embedding_allowed`
- `languages`
- `tags`
- `recommended_for`

## 다운로드 타입

- `direct_file`
- `zip_file`
- `html_button`
- `manual_only`

현재 설치 지원:

- `direct_file`
- `zip_file`

## 고급/운영 명령 예시

수집, 레퍼런스 학습, 볼트 동기화 같은 명령은 운영자 영역입니다. 메인 사용 흐름과 분리해서 아래 문서 기준으로 보시면 됩니다.

- [REFERENCE_LEARNING_PLAN.md](./REFERENCE_LEARNING_PLAN.md)
- [MCP_INTEGRATIONS.md](./MCP_INTEGRATIONS.md)
- [NETWORK_RUNBOOK.md](./NETWORK_RUNBOOK.md)
