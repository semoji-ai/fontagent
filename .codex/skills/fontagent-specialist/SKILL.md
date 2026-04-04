---
name: fontagent-specialist
description: Use when a project needs font search, license-aware recommendation, installation, typography system generation, or design-agent handoff via the local FontAgent CLI/MCP. Best for web, video, PPT, document, print, and template work where typography choices must be legally safe and easy to apply.
---

# FontAgent Specialist

Use this skill when the user wants to:
- find fonts for a project
- compare fonts by use case
- check whether a font is safe to use commercially
- install fonts into a project
- generate a `title / subtitle / body` font system
- hand typography decisions off to a design agent

Prefer `FontAgent MCP` if available. Fall back to the local CLI if MCP is not attached.

## Fast workflow

1. Check catalog readiness first.
   - MCP: `get_catalog_status`
   - CLI: `python3 -m fontagent.cli --root /Users/jleavens_macmini/Projects/fontagent catalog-status`

2. Choose the recommendation path.
   - Structured request is known: use `recommend_use_case`
   - User intent is fuzzy: use `guided_interview_recommend`

3. Judge each candidate with operational fields.
   - `license_profile.status`
   - `license_profile.confidence`
   - `license_profile.recommended_action`
   - `automation_profile.status`

4. Apply to the target project.
   - Single font: `install_font`
   - Full system: `prepare_font_system`

5. If another design/development agent must continue, generate a handoff.
   - `generate_typography_handoff`

## CLI examples

```bash
python3 -m fontagent.cli --root /Users/jleavens_macmini/Projects/fontagent recommend-use-case \
  --medium web \
  --surface landing_hero \
  --role title \
  --tone editorial \
  --language ko \
  --commercial-use \
  --web-embedding
```

```bash
python3 -m fontagent.cli --root /Users/jleavens_macmini/Projects/fontagent prepare-font-system \
  --project-path /absolute/path/to/project \
  --task "history documentary" \
  --use-case documentary-landing-ko \
  --language ko \
  --target both
```

## Operating rule

FontAgent is a typography specialist, not a full design tool.

FontAgent should own:
- font discovery
- license review
- typography role selection
- install/export
- typography handoff contract

Another design agent should own:
- page layout
- color system
- spacing/grid
- final visual composition
