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
텍스트를 같은 지문 공간에서 비교해 후보 폰트를 반환합니다. 의존성이
필요하므로 `identify` extra를 먼저 설치해야 합니다.

```bash
pip install "fontagent[identify]"

python3 -m fontagent.cli build-glyph-index --language both
python3 -m fontagent.cli identify-font \
    --image path/to/slide.png \
    --char-hint H --char-hint E --char-hint L --char-hint L --char-hint O
```

- `build-glyph-index`
  - 시스템에 설치된 폰트를 자동 스캔해서 글리프 지문 인덱스를 생성
  - `--font-dir <path>` 를 여러 번 지정해 추가 폰트 파일 디렉터리 포함 가능
  - `--language` 로 ko / en / both 샘플 세트 선택
- `identify-font`
  - 이미지에서 글자를 분리해 인덱스와 비교, top-k 후보 반환
  - `--char-hint` 를 감지된 글자 순서대로 전달하면 정확도가 올라감
  - 매칭 신뢰도가 임계값보다 낮으면 `recommend` 기반 유사 폰트 fallback을 함께 반환

MCP에서도 동일하게 `build_glyph_index`, `identify_font_in_image` 도구로 노출됩니다.

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
