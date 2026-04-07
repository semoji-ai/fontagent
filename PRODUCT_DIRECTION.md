# FontAgent Product Direction

## 목표

`FontAgent`는 무료 폰트 검색 도구를 넘어서, 에이전트와 제품이 함께 재사용할 수 있는 `typography service`가 되는 것이 목표입니다.

핵심 질문은 두 가지입니다.

- 사용자는 어떻게 더 쉽게 원하는 폰트를 찾고 설치할 것인가
- 다른 에이전트는 어떻게 `FontAgent`를 typography 전담 레이어로 호출할 것인가

## 1. 대시보드 방향

대시보드는 단순 검색 페이지가 아니라, "추천 -> 비교 -> 설치 -> 프로젝트 연결" 흐름을 빠르게 만드는 쪽으로 발전해야 합니다.

### 1-1. 추천 폰트 카테고리

초기 카테고리:

- 제목용
- 본문용
- 말자막용
- 차트/표용
- 슬라이드용
- 썸네일용
- 브랜드/캠페인용

각 카테고리는 다음 기준으로 필터링 가능해야 합니다.

- 언어
- 톤
- 라이선스
- 사용 매체
- 상업 사용 여부
- 웹 임베딩 가능 여부

### 1-2. 검색/탐색 UX

대시보드에서 바로 가능해야 하는 것:

- 자유 검색
- 카테고리 탭 이동
- 라이선스 필터
- 설치 가능 여부 확인
- 프리뷰 비교
- 추천 이유 보기

검색 결과는 단순 목록이 아니라 아래 정보를 같이 보여줘야 합니다.

- 폰트 이름
- 추천 역할
- 추천 이유
- 라이선스 상태
- 설치 상태
- 출처

### 1-3. 설치 UX

설치는 최대한 클릭 수를 줄여야 합니다.

원하는 상태:

- 추천 목록에서 바로 설치
- 설치 후 프로젝트에 연결
- 설치 경로/상태 명확히 표시
- manual-only 폰트는 이유와 이동 링크 제공

### 1-4. 프로젝트 연결

대시보드에서 아래 액션이 바로 가능해야 합니다.

- `title/body/subtitle` 조합 저장
- 프로젝트용 font system export
- typography handoff export

## 2. 에이전트 협업 방향

`FontAgent`는 다른 에이전트가 typography 결정을 위임하는 구조로 가야 합니다.

### 2-1. 주요 협업 대상

- Auto Kairos
- ChartAgent
- SlideAgent
- ImageSearchAgent
- ImageGenAgent

### 2-2. 협업 단위

역할 기반 협업이 중요합니다.

예:

- `headline`
- `body_copy`
- `spoken_subtitle`
- `chart_title`
- `axis_label`
- `table_cell`
- `source_note`
- `annotation`

즉 다른 에이전트는 `"이 씬의 headline/body/subtitle 폰트를 골라줘"` 또는 `"이 차트의 title/axis/table/source 폰트를 골라줘"` 같은 요청을 보내고, `FontAgent`는 그 역할별 답을 반환해야 합니다.

### 2-3. 반환 형태

기본 반환은 아래 3종으로 통일하는 것이 좋습니다.

- 추천 목록
- 설치 가능한 폰트 정보
- role 기반 `font system`

## 3. 가까운 개발 우선순위

### 3-1. 사용자 surface 단순화

- README는 사용자용 3분 시작 중심
- 운영자 명령은 별도 문서로 분리
- 복잡한 reference learning 명령은 메인 화면에서 내리기

### 3-2. 대시보드 강화

- 카테고리 탭
- 검색/필터
- 설치 상태 표시
- 원클릭 설치
- 추천 결과 비교

### 3-3. 협업 계약 정리

- role 기반 font request 스키마
- role 기반 font system 응답 스키마
- 다른 에이전트가 재사용 가능한 handoff 포맷

## 4. 피해야 할 방향

- README에 운영 명령을 다 노출하는 것
- 추천/설치/프로젝트 연결이 분리된 UX
- 역할 구분 없이 font family만 반환하는 방식
- 특정 한 프로젝트 구조에만 종속되는 설계

## 5. 제품 원칙

- 처음 쓰는 사용자는 `recommend -> install -> export`만 이해하면 된다
- 운영자는 별도 문서에서 학습/수집/검증을 본다
- 다른 에이전트는 role 기반으로만 `FontAgent`를 호출한다
- 설치와 라이선스 상태는 항상 사용자에게 명확히 보여야 한다
