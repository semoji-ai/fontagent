# Reference Learning Plan

`FontAgent`의 다음 단계는 폰트 메타데이터만 보는 추천기에서, 실제 사용 레퍼런스를 학습하는 타이포 specialist로 확장되는 것이다.

## 목표

- 실제 사용 사례를 `매체 / 표면 / 역할 / 무드 / 텍스트 구조` 기준으로 저장한다.
- 레퍼런스에서 보이는 폰트와 조합을 추론해 후보 폰트와 연결한다.
- 추천 시 단순 태그 매칭이 아니라, 레퍼런스 유사도와 역할 적합도를 같이 본다.

## 레퍼런스 스키마

저장 단위는 `font_references` 테이블이다.

- `title`
- `medium`
- `surface`
- `role`
- `reference_class`
- `reference_scope`
- `source_kind`
- `source_url`
- `asset_path`
- `tones`
- `languages`
- `text_blocks`
- `candidate_font_ids`
- `observed_font_labels`
- `palette`
- `ratio_hint`
- `extraction_method`
- `extraction_confidence`
- `status`
- `notes`

## 추출 전략

### 1. 웹 레퍼런스

우선순위:
- `Playwright DOM`
- `Studio/Browser screenshot`
- `Vision font guess`

이유:
- 실제 CSS `font-family`, weight, size, line-height를 가장 정확히 얻을 수 있다.

### 2. 이미지/포스터/썸네일

우선순위:
- `Apple Vision OCR`
- `Vision-capable agent font guess`

이유:
- 텍스트 블록과 hierarchy는 OCR이 잘 잡고,
- 폰트의 느낌과 계열 후보는 비전 추론이 보완한다.
- 이 비전 추론은 특정 공급자에 묶지 않고, `Codex`, `Claude`, `VSCode + MCP`, 기타 vision-capable 모델로 수행할 수 있게 두는 편이 좋다.

### 3. PDF/PPT/문서

우선순위:
- `Document parse`
- `OCR`
- `Vision font guess`

이유:
- 내장 폰트 메타가 있으면 가장 강한 근거가 된다.

### 4. 영상 프레임

우선순위:
- `Frame sampling`
- `OCR`
- `Vision font guess`

## 추천 반영 방향

현재 추천은 주로 태그/라이선스/설치 검증 기반이다.

다음 단계에서는 아래 점수를 추가한다.

- `reference_similarity_score`
  - medium / surface / role / tone 유사도
- `pairing_prior_score`
  - title/subtitle/body 조합이 레퍼런스에서 반복된 정도
- `layout_fit_score`
  - 텍스트 길이, 비율, hierarchy 적합도
- `confidence_boost`
  - DOM 추출 / 문서 메타처럼 근거 강도가 높은 레퍼런스일수록 가중치 증가

## 권장 파이프라인

1. 레퍼런스 등록
2. 추출 전략 결정
3. 텍스트/레이아웃/폰트 후보 추출
4. 수동 검토로 curated 상태 승격
5. 추천 점수에 반영

## 초기 운영 전략

처음에는 모든 레퍼런스를 무차별적으로 쌓지 않는다.

- `트렌드 카테고리별 starter pack`을 먼저 만든다.
- 카테고리별로 5~20개 수준의 강한 레퍼런스를 curated 상태로 확보한다.
- 이후에는 주기적으로 소량씩 추가한다.

추천 starter pack:

- `trend-korean-brand-display`
- `trend-english-editorial-display`
- `trend-korean-video-thumbnail-display`
- `trend-video-subtitle-readable`
- `trend-web-editorial-heroes`
- `trend-presentation-cover-display`
- `trend-detailpage-brand-heroes`
- `trend-print-poster-display`
- `market-presentation-covers`
- `market-detailpage-heroes`
- `market-print-poster-typography`

레퍼런스는 두 축으로 나눈다.

- `reference_class`
  - `specimen`: 폰트 소개/브랜드 폰트 페이지
  - `market`: 실제 공개 산출물 레퍼런스
  - `campaign`: 캠페인/브랜딩 전개 맥락
  - `channel`: 유튜브/핀터레스트/인스타그램 같은 채널 맥락
- `reference_scope`
  - `shared_public`: 공개 저장소에 남겨도 되는 메타데이터 중심 레퍼런스
  - `private_user`: 사용자가 개인 취향 학습용으로 넣는 비공개 레퍼런스

추천에서는 기본적으로 `market / campaign / channel` 이 `specimen`보다 더 높은 가중치를 가진다.

## 옵시디언 볼트 저장 원칙

레퍼런스는 옵시디언 볼트에 아래 형태로 저장한다.

기본 루트는 repo 내부 `fontagent_vault` 로 둔다.

다만 공개 저장소 기준으로는 `fontagent_vault` 를 메타데이터/노트 중심으로 유지하고, 실제 캡처 원본과 raw 추출물은 `.fontagent/reference_private_vault` 같은 비공개 로컬 캐시에 두는 것이 안전하다.

- `Fonts/<medium>/<surface>/<slug>.md`
- `Fonts/<medium>/<surface>/_assets/<slug>.png`
- `Fonts/<medium>/<surface>/_raw/<slug>.json`
- `Fonts/<medium>/<surface>/_reviews/<slug>-review-*.json`
- `Fonts/_index/font-references.md`

frontmatter에는 최소한 아래를 넣는다.

- `reference_id`
- `medium`
- `surface`
- `role`
- `reference_class`
- `reference_scope`
- `source_url`
- `tones`
- `languages`
- `candidate_font_ids`
- `observed_font_labels`
- `tags`
- `extraction_method`
- `extraction_confidence`

이 구조는 나중에 벡터화/검색 인덱싱하기 쉽게 하기 위한 것이다.

## 지금 가능한 CLI

- `add-reference`
- `list-references`
- `reference-status`
- `reference-strategies`
- `set-reference-vault`
- `reference-vault`
- `list-reference-packs`
- `learn-reference-pack`
- `sync-reference-index`
- `add-reference-review`
- `list-reference-reviews`

이 단계는 아직 자동 식별 완성본이 아니라, `레퍼런스 라이브러리와 추출 전략 엔진`의 시작점이다.

운영 원칙:

- 초기 큐레이션은 사람이 직접 보거나, `비전 가능한 에이전트`와 함께 한다.
- 제품 런타임은 특정 모델/API 하나에 종속되지 않게 유지한다.
- `OpenAI vision` 같은 공급자 경로는 편의용 플러그인으로 두고, 핵심 구조는 provider-agnostic 하게 간다.
- 에이전트가 내린 분석은 `font_reference_reviews`와 볼트 `_reviews`에 별도로 남기고, 필요할 때만 원본 레퍼런스 후보군에 병합한다.
