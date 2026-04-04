# FontAgent MCP Integrations

`FontAgent`는 헤드리스 폰트 엔진으로 동작하고, 가장 권장하는 협업 방식은 `CLI/HTTP`보다 `MCP stdio`입니다.

이 문서는 Codex, Claude Desktop, VSCode 같은 에이전트/에디터가 `FontAgent`를 붙일 때의 예시 설정과 권장 호출 순서를 정리합니다.

주의:
- 아래 JSON은 "예시 스니펫"입니다.
- 실제 설정 파일 위치와 키 이름은 앱 버전에 따라 조금 다를 수 있습니다.
- 핵심은 `fontagent-mcp` 또는 `python3 -m fontagent.cli ... mcp` 를 stdio 서버로 붙이는 것입니다.

## 실행 명령

가장 안정적인 실행 방식:

```bash
python3 -m fontagent.cli --root /Users/jleavens_macmini/Projects/fontagent mcp
```

설치형 스크립트 사용 시:

```bash
fontagent-mcp --root /Users/jleavens_macmini/Projects/fontagent
```

## 권장 에이전트 호출 순서

에이전트가 처음 붙었을 때는 이 순서가 좋습니다.

1. `get_catalog_status`
2. `get_license_policy_catalog`
3. `get_contract_schema`
4. `list_use_cases` 또는 `list_interview_catalog`
5. `recommend_use_case` 또는 `guided_interview_recommend`
6. `install_font`
7. `prepare_font_system`
8. `generate_typography_handoff`

이 흐름을 쓰면 에이전트가 먼저 카탈로그 상태를 파악하고, 그 다음 추천/설치/프로젝트 적용으로 넘어갈 수 있습니다.
특히 `get_contract_schema`를 먼저 보면 handoff JSON을 downstream 에이전트가 안정적으로 읽을 수 있습니다.

## 토큰 최적화 원칙

MCP에서는 검색/추천 계열 도구가 기본적으로 `detail_level=compact`를 쓰는 편이 좋습니다.

- `compact`
  - `font_id`, `family`, `tags`, `recommended_for`
  - `license_profile`
  - `automation_profile`
  - `why`
- `full`
  - source URL, download URL, 원본 메타데이터까지 모두 포함

권장:
- 1차 후보 선정: `compact`
- 설치 직전 검토나 디버깅: `full`

`guided_interview_recommend`는 추가로 다음 토글을 지원합니다.

- `include_canvas`
- `include_font_system_preview`

권장:
- 에이전트 루프: 둘 다 `false`
- UI/사람 검토: 필요할 때만 `true`

## Codex 예시

예시 파일:
- [`examples/mcp_configs/codex.fontagent.json`](/Users/jleavens_macmini/Projects/fontagent/examples/mcp_configs/codex.fontagent.json)

핵심 부분:

```json
{
  "mcpServers": {
    "fontagent": {
      "command": "python3",
      "args": [
        "-m",
        "fontagent.cli",
        "--root",
        "/Users/jleavens_macmini/Projects/fontagent",
        "mcp"
      ]
    }
  }
}
```

## Claude Desktop 예시

예시 파일:
- [`examples/mcp_configs/claude_desktop.fontagent.json`](/Users/jleavens_macmini/Projects/fontagent/examples/mcp_configs/claude_desktop.fontagent.json)

핵심 부분:

```json
{
  "mcpServers": {
    "fontagent": {
      "command": "python3",
      "args": [
        "-m",
        "fontagent.cli",
        "--root",
        "/Users/jleavens_macmini/Projects/fontagent",
        "mcp"
      ]
    }
  }
}
```

## VSCode 예시

예시 파일:
- [`examples/mcp_configs/vscode.fontagent.json`](/Users/jleavens_macmini/Projects/fontagent/examples/mcp_configs/vscode.fontagent.json)

핵심 부분:

```json
{
  "mcpServers": {
    "fontagent": {
      "command": "python3",
      "args": [
        "-m",
        "fontagent.cli",
        "--root",
        "/Users/jleavens_macmini/Projects/fontagent",
        "mcp"
      ]
    }
  }
}
```

## 에이전트 프롬프트 가이드

초기 시스템 프롬프트나 툴 사용 가이드에 이 정도를 넣으면 좋습니다.

```text
FontAgent MCP를 사용할 때는 먼저 get_catalog_status로 카탈로그 상태를 파악하라.
추천이 필요하면 list_use_cases 또는 list_interview_catalog를 본 뒤 recommend_use_case 또는 guided_interview_recommend를 호출하라.
프로젝트 적용이 필요하면 install_font 또는 prepare_font_system을 호출하라.
디자인 에이전트 handoff가 필요하면 generate_typography_handoff를 호출하라.
```

## 중요한 출력 필드

검색/추천 결과에서 에이전트가 특히 봐야 하는 필드:

- `license_profile.status`
- `license_profile.confidence`
- `license_profile.recommended_action`
- `license_profile.review_required`
- `automation_profile.status`
- `automation_profile.summary`

즉 에이전트는 "예쁜 폰트"보다 먼저:
- 써도 되는지
- 자동 설치가 되는지
- 프로젝트에 바로 적용 가능한지
를 같이 판단해야 합니다.

## 카탈로그 상태 예시

`get_catalog_status` 또는 CLI `catalog-status`는 이런 판단의 출발점입니다.

예시 응답:

```json
{
  "total_fonts": 678,
  "installed_fonts": 643,
  "commercial_fonts": 650,
  "web_embedding_fonts": 420,
  "video_fonts": 645,
  "sources": {
    "gongu_freefont": 350,
    "naver_hangeul": 125
  },
  "verification": {
    "installed": 643,
    "invalid_archive": 11
  }
}
```

이 정보를 먼저 보면 에이전트가:
- 어떤 소스가 강한지
- 자동 설치 비율이 어느 정도인지
- 현재 카탈로그가 충분한지
를 빠르게 판단할 수 있습니다.
