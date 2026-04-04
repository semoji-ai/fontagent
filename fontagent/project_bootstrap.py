from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _render_prompt(project_path: Path, use_case: str, language: str, target: str, asset_dir: str) -> str:
    return f"""Use FontAgent as a typography specialist for this project.

Project:
- path: {project_path}
- default_use_case: {use_case}
- language: {language}
- target: {target}
- asset_dir: {asset_dir}

Workflow:
1. Call get_catalog_status first.
2. If the brief is vague, call guided_interview_recommend.
3. If the brief is structured, call recommend_use_case.
4. Prefer candidates with:
   - license_profile.status = allowed
   - license_profile.recommended_action = proceed
   - automation_profile.status = ready
5. If the project needs role-based typography, call prepare_font_system.
6. If another design or coding agent will continue, call generate_typography_handoff.

Boundaries:
- FontAgent owns font choice, license review, typography roles, and install/export.
- The downstream design agent owns layout, color, spacing, and final composition.
"""


def _render_codex_skill(fontagent_root: Path, project_path: Path, use_case: str, language: str, target: str, asset_dir: str) -> str:
    return f"""---
name: fontagent-project
description: Use when this project needs licensed font recommendation, installation, or typography handoff through the central FontAgent workspace at {fontagent_root}. Best for generating or updating project-specific font systems in {project_path}.
---

# FontAgent Project

Use this skill when you need project-specific typography decisions for this repository.

Prefer the central FontAgent CLI/MCP instead of ad-hoc font selection.

## Default project settings

- `project_path`: `{project_path}`
- `use_case`: `{use_case}`
- `language`: `{language}`
- `target`: `{target}`
- `asset_dir`: `{asset_dir}`

## Recommended workflow

1. `python3 -m fontagent.cli --root {fontagent_root} catalog-status`
2. If the brief is vague, use `guided_interview_recommend`
3. Otherwise use `recommend-use-case`
4. Generate or refresh the project font system:

```bash
python3 -m fontagent.cli --root {fontagent_root} prepare-font-system \\
  --project-path {project_path} \\
  --use-case {use_case} \\
  --language {language} \\
  --target {target} \\
  --asset-dir {asset_dir}
```

5. If another agent should continue layout/design work, generate a handoff:

```bash
python3 -m fontagent.cli --root {fontagent_root} generate-typography-handoff \\
  --project-path {project_path} \\
  --use-case {use_case} \\
  --language {language} \\
  --target {target} \\
  --asset-dir {asset_dir}
```
"""


def bootstrap_project(
    *,
    fontagent_root: Path,
    project_path: Path,
    use_case: str = "documentary-landing-ko",
    language: str = "ko",
    target: str = "both",
    asset_dir: str = "assets/fonts",
    include_codex_skill: bool = True,
) -> dict:
    fontagent_root = Path(fontagent_root).resolve()
    project_path = Path(project_path).resolve()
    base_dir = project_path / ".fontagent"
    mcp_dir = base_dir / "mcp"
    prompts_dir = base_dir / "prompts"

    config = {
        "schema_version": "fontagent.project.v1",
        "fontagent_root": str(fontagent_root),
        "project_path": str(project_path),
        "defaults": {
            "use_case": use_case,
            "language": language,
            "target": target,
            "asset_dir": asset_dir,
        },
    }
    config_path = base_dir / "fontagent.project.json"
    _write_json(config_path, config)

    mcp_payload = {
        "mcpServers": {
            "fontagent": {
                "command": "python3",
                "args": [
                    "-m",
                    "fontagent.cli",
                    "--root",
                    str(fontagent_root),
                    "mcp",
                ],
            }
        }
    }
    codex_config_path = mcp_dir / "codex.fontagent.json"
    claude_config_path = mcp_dir / "claude_desktop.fontagent.json"
    vscode_config_path = mcp_dir / "vscode.fontagent.json"
    _write_json(codex_config_path, mcp_payload)
    _write_json(claude_config_path, mcp_payload)
    _write_json(vscode_config_path, mcp_payload)

    prompt_path = prompts_dir / "fontagent-specialist.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(
        _render_prompt(project_path, use_case, language, target, asset_dir),
        encoding="utf-8",
    )

    result = {
        "project_path": str(project_path),
        "config_path": str(config_path),
        "prompt_path": str(prompt_path),
        "mcp_configs": {
            "codex": str(codex_config_path),
            "claude_desktop": str(claude_config_path),
            "vscode": str(vscode_config_path),
        },
    }

    if include_codex_skill:
        skill_dir = project_path / ".codex" / "skills" / "fontagent-project"
        skill_path = skill_dir / "SKILL.md"
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(
            _render_codex_skill(fontagent_root, project_path, use_case, language, target, asset_dir),
            encoding="utf-8",
        )
        openai_yaml_path = skill_dir / "agents" / "openai.yaml"
        openai_yaml_path.parent.mkdir(parents=True, exist_ok=True)
        openai_yaml_path.write_text(
            "\n".join(
                [
                    "display_name: FontAgent Project",
                    "short_description: Use FontAgent defaults for this project.",
                    "default_prompt: Use the project-local FontAgent workflow to choose fonts, install them, and emit a typography handoff when needed.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        result["codex_skill"] = str(skill_path)
        result["codex_openai_yaml"] = str(openai_yaml_path)

    return result
