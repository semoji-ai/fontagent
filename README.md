# FontAgent

무료 폰트를 AI agent와 개발자가 검색, 추천, 미리보기, 설치, export까지 한 번에 다루기 위한 MVP입니다.

현재 MVP 범위:

- SQLite 레지스트리
- 시드 데이터 기반 검색/추천
- SVG 미리보기 생성
- direct/zip/manual 다운로드 방식 추상화
- 눈누 HTML fixture 기반 수집기
- CSS export
- Remotion export
- CLI
- MCP stdio server
- 표준 라이브러리 기반 HTTP JSON API
- 간단한 웹 UI (`/`)
- 디자인/제목용 공식 배포처 curated candidate seed

## 빠른 시작

```bash
cd /Users/jleavens_macmini/Projects/fontagent
python3 -m fontagent.cli init
python3 -m fontagent.cli search --query "subtitle korean"
python3 -m fontagent.cli recommend --task "history documentary title" --language ko
python3 -m fontagent.cli preview pretendard --preset title-ko
python3 -m fontagent.cli import-noonnu --listing-html ./tests/fixtures/noonnu/listing.html --detail-dir ./tests/fixtures/noonnu
python3 -m fontagent.cli import-goodchoice-fonts
python3 -m fontagent.cli import-google-display-fonts
python3 -m fontagent.cli import-cafe24-fonts
python3 -m fontagent.cli import-jeju-fonts
python3 -m fontagent.cli import-league-fonts
python3 -m fontagent.cli import-velvetyne-fonts
python3 -m fontagent.cli import-fontshare-fonts
python3 -m fontagent.cli import-gmarket-fonts
python3 -m fontagent.cli import-nexon-fonts
python3 -m fontagent.cli import-woowahan-fonts
python3 -m fontagent.cli list-query-sets
python3 -m fontagent.cli list-curated-profiles
python3 -m fontagent.cli list-use-cases
python3 -m fontagent.cli list-reference-packs
python3 -m fontagent.cli reference-vault
python3 -m fontagent.cli list-reference-reviews
python3 -m fontagent.cli catalog-status
python3 -m fontagent.cli license-policy-catalog
python3 -m fontagent.cli contract-schema --name typography-handoff.v1
python3 -m fontagent.cli seed-curated-candidates --profile design-display-ko
python3 -m fontagent.cli seed-curated-candidates --profile design-display-en
python3 -m fontagent.cli serve --port 8123
python3 -m fontagent.cli mcp
# 브라우저에서 http://127.0.0.1:8123 열기
```

## 주요 명령

```bash
python3 -m fontagent.cli init
python3 -m fontagent.cli search --query "korean subtitle"
python3 -m fontagent.cli search --query "korean subtitle" --detail compact
python3 -m fontagent.cli recommend --task "youtube documentary title" --language ko
python3 -m fontagent.cli recommend --task "youtube documentary title" --language ko --detail compact
python3 -m fontagent.cli recommend-use-case --medium web --surface landing_hero --role title --tone editorial --language ko --commercial-use --web-embedding
python3 -m fontagent.cli recommend-use-case --medium web --surface landing_hero --role title --tone editorial --language ko --commercial-use --web-embedding --detail compact
python3 -m fontagent.cli install font-id --output-dir ./assets/fonts
python3 -m fontagent.cli export-css font-id
python3 -m fontagent.cli export-remotion font-id
python3 -m fontagent.cli prepare-font-system --project-path ./demo --task "history documentary" --target both
python3 -m fontagent.cli generate-template-bundle --project-path ./demo --task "history documentary" --use-case documentary-landing-ko
python3 -m fontagent.cli generate-typography-handoff --project-path ./demo --task "history documentary" --use-case documentary-landing-ko
python3 -m fontagent.cli preview font-id
python3 -m fontagent.cli discover-web --query-set display-ko --query-set editorial-ko
python3 -m fontagent.cli seed-curated-candidates --profile design-display-ko
python3 -m fontagent.cli seed-curated-candidates --profile design-display-en
python3 -m fontagent.cli import-cafe24-fonts
python3 -m fontagent.cli import-jeju-fonts
python3 -m fontagent.cli import-league-fonts
python3 -m fontagent.cli import-velvetyne-fonts
python3 -m fontagent.cli import-fontshare-fonts
python3 -m fontagent.cli import-goodchoice-fonts
python3 -m fontagent.cli import-google-display-fonts
python3 -m fontagent.cli import-gmarket-fonts
python3 -m fontagent.cli import-nexon-fonts
python3 -m fontagent.cli import-woowahan-fonts
python3 -m fontagent.cli list-candidates --discovery-source manual_curated
python3 -m fontagent.cli list-use-cases
python3 -m fontagent.cli list-reference-packs
python3 -m fontagent.cli set-reference-vault --vault-root /path/to/vault --vault-category Fonts
python3 -m fontagent.cli learn-reference-pack --pack trend-korean-brand-display --continue-on-error
python3 -m fontagent.cli add-reference-review --reference-id <id> --reviewer-kind agent_vision --reviewer-name claude --candidate-font-id goodchoice-yg-jalnan --observed-font "playful rounded display" --confidence 0.91 --apply-to-reference
python3 -m fontagent.cli sync-reference-index
python3 -m fontagent.cli catalog-status
python3 -m fontagent.cli contract-schema --name typography-handoff.v1
python3 -m fontagent.cli import-noonnu --listing-html ./tests/fixtures/noonnu/listing.html --detail-dir ./tests/fixtures/noonnu
python3 -m fontagent.cli serve --port 8123
python3 -m fontagent.cli mcp
```

## 데이터 모델

MVP는 다음 핵심 필드를 다룹니다.

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

MVP는 `direct_file`과 `zip_file` 설치를 지원합니다.

## 눈누 수집기

현재는 네트워크 없는 환경에서도 검증할 수 있게 fixture 기반 수집기를 먼저 넣었습니다.

- 목록 HTML -> 상세 HTML -> 정규화 레코드
- 다운로드 링크 분류: `direct_file`, `zip_file`, `html_button`, `manual_only`
- 실제 라이브 크롤링은 다음 단계에서 추가하면 됩니다.

## 디자인 폰트 큐레이션

본문체 수집만 늘리지 않도록, 디자인/제목용 무료 폰트 배포처를 별도 후보군으로 관리합니다.

- discovery query set
  - `display-ko`
  - `editorial-ko`
  - `playful-ko`
  - `display-en`
- curated candidate profile
  - `design-display-ko`
  - `design-display-en`

예:

```bash
python3 -m fontagent.cli discover-web --query-set display-ko --query-set editorial-ko
python3 -m fontagent.cli seed-curated-candidates --profile design-display-ko
python3 -m fontagent.cli seed-curated-candidates --profile design-display-en
python3 -m fontagent.cli list-candidates --discovery-source manual_curated
```

## 레퍼런스 학습과 옵시디언 볼트

`FontAgent`는 폰트 메타데이터만 추천하는 단계에서, 실제 사용 레퍼런스를 축적하는 단계로 확장되고 있습니다. 핵심은 레퍼런스를 옵시디언 볼트 친화 포맷으로 내보내고, 나중에 벡터화/인덱싱하기 쉽게 구조화하는 것입니다.

기본적으로 `FontAgent`는 repo 내부 [`fontagent_vault`](/Users/jleavens_macmini/Projects/fontagent/fontagent_vault) 를 레퍼런스 볼트로 사용합니다.

기본 정책은 `공개 볼트 = 메타데이터 전용`, `비공개 캐시 = 원본 캡처/추출물` 입니다. 즉 공개 저장소에 들어가는 `fontagent_vault` 는 note/index 중심으로 유지하고, 실제 스크린샷/원본 추출물은 기본적으로 `.fontagent/reference_private_vault` 에 저장합니다.

기본 흐름:

```bash
python3 -m fontagent.cli list-reference-packs

python3 -m fontagent.cli learn-reference-pack \
  --pack trend-korean-brand-display \
  --continue-on-error

python3 -m fontagent.cli set-reference-vault \
  --vault-root /Users/jleavens_macmini/Projects/fontagent/fontagent_vault \
  --vault-category Fonts \
  --asset-policy public_metadata_only \
  --private-vault-root /Users/jleavens_macmini/Projects/fontagent/.fontagent/reference_private_vault

python3 -m fontagent.cli refresh-reference-candidates

python3 -m fontagent.cli extract-web-reference \
  --title "Cafe24 Pro Font Landing" \
  --url "https://www.cafe24.com/story/use/cafe24pro_font.html" \
  --medium web \
  --surface landing_hero \
  --role title \
  --tone playful \
  --language ko \
  --status curated

python3 -m fontagent.cli extract-image-reference \
  --title "Thumbnail Reference" \
  --image-path ./some-thumbnail.png \
  --medium video \
  --surface thumbnail \
  --role title \
  --tone quirky \
  --language ko \
  --status curated

python3 -m fontagent.cli extract-image-reference \
  --title "User Taste Reference" \
  --image-path ./my-private-reference.png \
  --medium presentation \
  --surface cover \
  --role title \
  --reference-class market \
  --reference-scope private_user \
  --tone minimal \
  --language en \
  --status curated
```

starter pack:

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

레퍼런스는 두 축으로 관리합니다.

- `reference_class`
  - `specimen`
  - `market`
  - `campaign`
  - `channel`
- `reference_scope`
  - `shared_public`
  - `private_user`

`market / campaign / channel` 은 실제 산출물/채널 맥락에 더 가까운 레퍼런스라서 추천에서 `specimen`보다 더 높은 가중치를 받습니다.

볼트 내보내기 구조:

- `Fonts/<medium>/<surface>/*.md`
- `Fonts/<medium>/<surface>/_assets/*.png`
- `Fonts/<medium>/<surface>/_raw/*.json`
- `Fonts/<medium>/<surface>/_reviews/*.json`
- `Fonts/_index/font-references.md`

노트 frontmatter에는 `medium`, `surface`, `role`, `tones`, `candidate_font_ids`, `observed_font_labels`, `tags`가 들어가므로, 나중에 임베딩/벡터 인덱싱하기 쉬운 형태입니다.

레퍼런스를 추가한 뒤에는 `refresh-reference-candidates`로 기존 레퍼런스에 후보 폰트 연결을 다시 계산할 수 있습니다.

비전 가능한 에이전트가 레퍼런스를 추가로 분석했다면 `add-reference-review`로 별도 review를 저장할 수 있습니다. 이 review는 DB의 `font_reference_reviews`와 볼트의 `_reviews`에 함께 남고, `--apply-to-reference`를 주면 원본 레퍼런스 후보군에도 병합됩니다.

사용자 취향 레퍼런스는 `--reference-scope private_user` 로 저장하면 public vault가 아니라 `.fontagent/reference_private_vault` 쪽에 note와 자산이 함께 쌓입니다. 즉 공개 저장소를 오염시키지 않고 개인 취향 학습만 별도로 계속 확장할 수 있습니다.

이미지 레퍼런스는 기본적으로 `Apple Vision OCR`을 사용합니다. 그 다음 단계의 폰트 추정은 특정 API에 고정하지 않고, `비전 가능한 에이전트`와 협업하는 것을 권장합니다. 즉 `Codex`, `Claude`, `VSCode + MCP`, 기타 vision-capable 모델과 모두 연결할 수 있습니다.

현재 repo에는 편의용으로 `OPENAI_API_KEY` 기반 vision 추정 경로도 들어 있습니다. 하지만 이건 필수가 아니라 **옵션**입니다. 모델은 기본 `gpt-4.1-mini`이며, 필요하면 `FONTAGENT_VISION_MODEL`로 바꿀 수 있습니다.

## 프로젝트 폰트 시스템

특정 프로젝트에 대해 `title / subtitle / body` 역할 폰트를 고르고, 실제 자산 설치와 디자인 토큰 파일 생성을 함께 수행합니다.

`recommend-use-case` 계열 추천은 이제 단순 태그 매칭만이 아니라 `font cohort`를 먼저 고려합니다. 예를 들어:

- `neutral_ui_sans`
- `neutral_content_sans`
- `editorial_serif`
- `display_bold`
- `display_playful`
- `retro_signage`

같은 유형군을 먼저 보고, 그 다음 레퍼런스/라이선스/설치 가능성으로 세부 랭킹을 정합니다. 그래서 `Pretendard` 같은 중립 고딕은 `subtitle/body/ui`에서 강하고, `quirky thumbnail title` 같은 문맥에서는 표현형 display 폰트가 더 우선됩니다.

```bash
python3 -m fontagent.cli prepare-font-system \
  --project-path ./demo-project \
  --task "history documentary" \
  --use-case documentary-landing-ko \
  --language ko \
  --target both
```

생성 파일:

- `fontagent/font-system.json`
- `fontagent/fonts.css`
- `fontagent/remotion-font-system.ts`

템플릿 번들까지 한 번에 만들려면:

```bash
python3 -m fontagent.cli generate-template-bundle \
  --project-path ./demo-project \
  --task "history documentary" \
  --use-case documentary-landing-ko \
  --language ko \
  --target both
```

추가 생성 파일:

- `fontagent/templates/landing.html`
- `fontagent/templates/thumbnail.html`
- `fontagent/templates/poster.html`
- `fontagent/templates/showcase.css`

디자인 에이전트에 넘길 typography contract를 만들려면:

```bash
python3 -m fontagent.cli generate-typography-handoff \
  --project-path ./demo-project \
  --task "history documentary" \
  --use-case documentary-landing-ko \
  --language ko \
  --target both
```

use case preset:

- `documentary-landing-ko`
- `youtube-thumbnail-ko`
- `video-thumbnail`
- `video-subtitle`
- `web-landing`
- `presentation-cover`
- `document-body`
- `poster-headline`

포함 내용:

- 역할별 설치 자산 경로
- `title / subtitle / body` 폰트 패밀리 토큰
- 기본 weight / line-height / tracking 토큰
- Remotion에서 재사용 가능한 role별 메타데이터

## 구조화 추천

매체/표면/역할/톤/라이선스 제약을 기준으로 추천할 수 있습니다.

```bash
python3 -m fontagent.cli recommend-use-case \
  --medium video \
  --surface thumbnail \
  --role title \
  --tone cinematic \
  --tone retro \
  --language ko \
  --commercial-use \
  --video-use
```

## 웹 UI

`serve`를 실행하면 루트 `/` 에서 간단한 UI를 사용할 수 있습니다.

- 검색
- 추천
- 용도 기반 추천
- 비교형 미리보기
- SVG 미리보기
- 설치
- CSS export
- Remotion export
- 프로젝트 폰트 시스템 생성
- 프로젝트 폰트 시스템 + 템플릿 번들 생성
- 디자인 에이전트 handoff contract 생성

## MCP / 에이전트 연동

`FontAgent`는 HTTP UI만이 아니라 stdio MCP 서버로도 실행할 수 있습니다. 이 경로가 Codex, Claude Desktop, VSCode 같은 에이전트/에디터와 협업할 때 가장 활용도가 높습니다.

실행:

```bash
python3 -m fontagent.cli --root /Users/jleavens_macmini/Projects/fontagent mcp
# 또는 설치 후
fontagent-mcp --root /Users/jleavens_macmini/Projects/fontagent
```

현재 MCP 도구:

- `get_catalog_status`
- `get_license_policy_catalog`
- `get_contract_schema`
- `search_fonts`
- `recommend_fonts`
- `recommend_use_case`
- `guided_interview_recommend`
- `list_use_cases`
- `list_interview_catalog`
- `install_font`
- `prepare_font_system`
- `generate_typography_handoff`

권장 문서:

- [`MCP_INTEGRATIONS.md`](/Users/jleavens_macmini/Projects/fontagent/MCP_INTEGRATIONS.md)
- 예시 설정 파일: [`examples/mcp_configs`](/Users/jleavens_macmini/Projects/fontagent/examples/mcp_configs)
- 계약 스키마: [`fontagent/schemas/typography-handoff.v1.schema.json`](/Users/jleavens_macmini/Projects/fontagent/fontagent/schemas/typography-handoff.v1.schema.json)

추천 이유, 라이선스 프로필, 자동화 준비도까지 같이 반환하므로 바이브 코딩 에이전트가 직접 폰트를 찾고, 걸러내고, 프로젝트에 적용하는 흐름을 만들 수 있습니다.

토큰 최적화:

- CLI는 기본 `full` 응답을 유지합니다.
- 에이전트 경로(MCP)는 검색/추천 계열 도구가 기본적으로 `detail_level=compact`를 사용합니다.
- 사람 디버깅이나 상세 분석이 필요하면 `detail_level=full`로 확장하면 됩니다.
- 소스별 라이선스 신뢰도/검토 강도는 `license-policy-catalog` 또는 MCP `get_license_policy_catalog`로 먼저 확인할 수 있습니다.

## 프로젝트별 사용

`FontAgent`는 특정 프로젝트에 붙여서 쓰는 방식이 가장 강합니다.

- Codex: repo-local skill + MCP/CLI
- Claude Desktop: MCP + workflow prompt
- VSCode/기타 에이전트: MCP + handoff schema

추가 파일:

- Codex skill: [`fontagent-specialist`](/Users/jleavens_macmini/Projects/fontagent/.codex/skills/fontagent-specialist/SKILL.md)
- Workflow prompt: [`fontagent-specialist-prompt.md`](/Users/jleavens_macmini/Projects/fontagent/examples/agent_workflows/fontagent-specialist-prompt.md)

프로젝트에 바로 심으려면:

```bash
python3 -m fontagent.cli --root /Users/jleavens_macmini/Projects/fontagent bootstrap-project \
  --project-path /absolute/path/to/project \
  --use-case documentary-landing-ko \
  --language ko \
  --target both
```

생성되는 것:

- `.fontagent/fontagent.project.json`
- `.fontagent/mcp/codex.fontagent.json`
- `.fontagent/mcp/claude_desktop.fontagent.json`
- `.fontagent/mcp/vscode.fontagent.json`
- `.fontagent/prompts/fontagent-specialist.md`
- `.codex/skills/fontagent-project/SKILL.md`
