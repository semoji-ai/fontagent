from __future__ import annotations

import json
import shutil
from pathlib import Path


def render_template_css(manifest: dict, bundle_assets: dict[str, dict]) -> str:
    lines: list[str] = []
    format_map = {
        ".ttf": "truetype",
        ".otf": "opentype",
        ".woff2": "woff2",
        ".woff": "woff",
    }

    for role in ("title", "subtitle", "body"):
        asset = bundle_assets[role]
        alias = f"FontAgentTemplate{role.capitalize()}"
        suffix = Path(asset["asset_path"]).suffix.lower()
        lines.extend(
            [
                "@font-face {",
                f"  font-family: '{alias}';",
                f"  src: url('./{asset['bundle_relative_path']}') format('{format_map.get(suffix, 'truetype')}');",
                "  font-display: swap;",
                "}",
                "",
            ]
        )

    lines.extend(
        [
            ":root {",
            f"  --font-title: 'FontAgentTemplateTitle', '{manifest['roles']['title']['family']}', {manifest['roles']['title']['generic_family']};",
            "  --font-family-title: var(--font-title);",
            f"  --font-weight-title: {manifest['roles']['title']['defaults']['weight']};",
            f"  --font-line-height-title: {manifest['roles']['title']['defaults']['line_height']};",
            f"  --font-tracking-title: {manifest['roles']['title']['defaults']['tracking_em']}em;",
            f"  --font-subtitle: 'FontAgentTemplateSubtitle', '{manifest['roles']['subtitle']['family']}', {manifest['roles']['subtitle']['generic_family']};",
            "  --font-family-subtitle: var(--font-subtitle);",
            f"  --font-weight-subtitle: {manifest['roles']['subtitle']['defaults']['weight']};",
            f"  --font-line-height-subtitle: {manifest['roles']['subtitle']['defaults']['line_height']};",
            f"  --font-tracking-subtitle: {manifest['roles']['subtitle']['defaults']['tracking_em']}em;",
            f"  --font-body: 'FontAgentTemplateBody', '{manifest['roles']['body']['family']}', {manifest['roles']['body']['generic_family']};",
            "  --font-family-body: var(--font-body);",
            f"  --font-weight-body: {manifest['roles']['body']['defaults']['weight']};",
            f"  --font-line-height-body: {manifest['roles']['body']['defaults']['line_height']};",
            f"  --font-tracking-body: {manifest['roles']['body']['defaults']['tracking_em']}em;",
            "  --bg-cream: #f3eee3;",
            "  --bg-ink: #151515;",
            "  --surface: rgba(255, 252, 247, 0.9);",
            "  --surface-strong: rgba(255, 250, 242, 0.96);",
            "  --line: rgba(39, 29, 16, 0.14);",
            "  --ink: #18130d;",
            "  --muted: #675c51;",
            "  --accent: #c95d2f;",
            "  --accent-deep: #873a1e;",
            "  --shadow: 0 24px 80px rgba(44, 29, 13, 0.16);",
            "}",
            "",
            "* { box-sizing: border-box; }",
            "",
            "body {",
            "  margin: 0;",
            "  color: var(--ink);",
            "  background:",
            "    radial-gradient(circle at 12% 18%, rgba(255, 139, 61, 0.24), transparent 28%),",
            "    radial-gradient(circle at 88% 22%, rgba(90, 66, 203, 0.14), transparent 26%),",
            "    linear-gradient(180deg, #fbf6ed 0%, var(--bg-cream) 48%, #efe2ce 100%);",
            "}",
            "",
            ".shell {",
            "  max-width: 1440px;",
            "  margin: 0 auto;",
            "  padding: 28px;",
            "}",
            "",
            ".pill {",
            "  display: inline-flex;",
            "  align-items: center;",
            "  gap: 10px;",
            "  padding: 10px 14px;",
            "  border-radius: 999px;",
            "  background: rgba(255,255,255,0.75);",
            "  border: 1px solid rgba(31,22,15,0.12);",
            "  font-family: var(--font-family-subtitle);",
            "  font-weight: var(--font-weight-subtitle);",
            "  line-height: var(--font-line-height-subtitle);",
            "  letter-spacing: .03em;",
            "}",
            "",
            ".landing-grid {",
            "  display: grid;",
            "  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);",
            "  gap: 18px;",
            "}",
            "",
            ".panel {",
            "  background: var(--surface);",
            "  border: 1px solid var(--line);",
            "  border-radius: 28px;",
            "  box-shadow: var(--shadow);",
            "}",
            "",
            ".hero-panel {",
            "  min-height: 720px;",
            "  padding: 34px;",
            "}",
            "",
            ".hero-top {",
            "  display: flex;",
            "  justify-content: space-between;",
            "  gap: 16px;",
            "  margin-bottom: 72px;",
            "}",
            "",
            ".kicker {",
            "  display: inline-block;",
            "  margin-bottom: 14px;",
            "  padding: 10px 14px;",
            "  border-radius: 999px;",
            "  background: rgba(24, 19, 13, 0.08);",
            "  color: var(--accent-deep);",
            "  font-family: var(--font-family-subtitle);",
            "  font-weight: var(--font-weight-subtitle);",
            "}",
            "",
            ".hero-title {",
            "  max-width: 11ch;",
            "  margin: 0;",
            "  font-family: var(--font-family-title);",
            "  font-weight: var(--font-weight-title);",
            "  font-size: clamp(72px, 10vw, 142px);",
            "  line-height: var(--font-line-height-title);",
            "  letter-spacing: var(--font-tracking-title);",
            "}",
            "",
            ".hero-title em,",
            ".thumbnail-title em,",
            ".poster-title em {",
            "  color: var(--accent-deep);",
            "  font-style: normal;",
            "}",
            "",
            ".hero-copy,",
            ".panel p,",
            ".poster-copy {",
            "  font-family: var(--font-family-body);",
            "  font-weight: var(--font-weight-body);",
            "  line-height: 1.72;",
            "}",
            "",
            ".aside-stack {",
            "  display: grid;",
            "  gap: 18px;",
            "}",
            "",
            ".aside-panel {",
            "  padding: 24px;",
            "}",
            "",
            ".aside-panel h2 {",
            "  margin: 0 0 10px;",
            "  font-family: var(--font-family-title);",
            "  font-weight: var(--font-weight-title);",
            "  font-size: clamp(30px, 4vw, 46px);",
            "  line-height: 1.05;",
            "}",
            "",
            ".stat-grid {",
            "  display: grid;",
            "  grid-template-columns: repeat(2, minmax(0, 1fr));",
            "  gap: 12px;",
            "  margin-top: 18px;",
            "}",
            "",
            ".stat-box {",
            "  padding: 16px;",
            "  border-radius: 18px;",
            "  background: rgba(24, 19, 13, 0.92);",
            "  color: white;",
            "}",
            "",
            ".stat-box strong {",
            "  display: block;",
            "  font-family: var(--font-family-title);",
            "  font-weight: var(--font-weight-title);",
            "  font-size: 40px;",
            "  line-height: 1;",
            "}",
            "",
            ".thumbnail-stage {",
            "  width: min(1280px, 100%);",
            "  aspect-ratio: 16 / 9;",
            "  border-radius: 34px;",
            "  overflow: hidden;",
            "  background:",
            "    linear-gradient(0deg, rgba(17, 12, 8, 0.4), rgba(17, 12, 8, 0.4)),",
            "    radial-gradient(circle at 80% 22%, rgba(255, 130, 59, 0.48), transparent 20%),",
            "    linear-gradient(125deg, #231711 0%, #5d3120 44%, #190f0b 100%);",
            "  box-shadow: 0 34px 120px rgba(10, 5, 3, 0.46);",
            "}",
            "",
            ".thumbnail-grid {",
            "  display: grid;",
            "  grid-template-columns: 1.15fr 0.85fr;",
            "  height: 100%;",
            "}",
            "",
            ".thumbnail-copy {",
            "  padding: 58px 52px;",
            "  display: flex;",
            "  flex-direction: column;",
            "  justify-content: flex-end;",
            "}",
            "",
            ".thumbnail-kicker,",
            ".poster-kicker {",
            "  display: inline-flex;",
            "  width: fit-content;",
            "  margin-bottom: 18px;",
            "  padding: 10px 14px;",
            "  border-radius: 999px;",
            "  background: rgba(255,255,255,.08);",
            "  color: rgba(255,245,231,.92);",
            "  font-family: var(--font-family-subtitle);",
            "  font-weight: var(--font-weight-subtitle);",
            "  letter-spacing: .08em;",
            "  text-transform: uppercase;",
            "}",
            "",
            ".thumbnail-title {",
            "  max-width: 6ch;",
            "  margin: 0;",
            "  color: #fff5e8;",
            "  font-family: var(--font-family-title);",
            "  font-weight: var(--font-weight-title);",
            "  font-size: clamp(70px, 8vw, 132px);",
            "  line-height: .94;",
            "  letter-spacing: var(--font-tracking-title);",
            "}",
            "",
            ".thumbnail-subtitle {",
            "  max-width: 28ch;",
            "  margin-top: 18px;",
            "  color: rgba(255, 248, 239, 0.88);",
            "  font-family: var(--font-family-subtitle);",
            "  font-weight: var(--font-weight-subtitle);",
            "  font-size: 24px;",
            "  line-height: 1.4;",
            "}",
            "",
            ".thumbnail-aside {",
            "  display: grid;",
            "  padding: 32px 32px 32px 0;",
            "}",
            "",
            ".thumbnail-card {",
            "  align-self: end;",
            "  padding: 22px;",
            "  border-radius: 26px;",
            "  background: rgba(255, 251, 245, 0.12);",
            "  border: 1px solid rgba(255, 255, 255, 0.12);",
            "  color: white;",
            "}",
            "",
            ".thumbnail-card h2,",
            ".poster-title {",
            "  margin: 0 0 10px;",
            "  font-family: var(--font-family-title);",
            "  font-weight: var(--font-weight-title);",
            "}",
            "",
            ".thumbnail-card ul {",
            "  padding-left: 20px;",
            "  font-family: var(--font-family-subtitle);",
            "  font-weight: var(--font-weight-subtitle);",
            "}",
            "",
            ".poster-stage {",
            "  min-height: 1600px;",
            "  padding: 56px;",
            "  border-radius: 40px;",
            "  background:",
            "    radial-gradient(circle at 18% 22%, rgba(255, 142, 60, 0.25), transparent 22%),",
            "    linear-gradient(180deg, #151210 0%, #241711 54%, #120d0b 100%);",
            "  color: #fff8ef;",
            "  box-shadow: 0 34px 120px rgba(10, 5, 3, 0.46);",
            "}",
            "",
            ".poster-header {",
            "  display: flex;",
            "  justify-content: space-between;",
            "  align-items: flex-start;",
            "  gap: 18px;",
            "}",
            "",
            ".poster-title {",
            "  max-width: 8ch;",
            "  font-size: clamp(88px, 10vw, 180px);",
            "  line-height: .9;",
            "  letter-spacing: var(--font-tracking-title);",
            "}",
            "",
            ".poster-meta,",
            ".poster-copy {",
            "  font-family: var(--font-family-subtitle);",
            "  font-weight: var(--font-weight-subtitle);",
            "  color: rgba(255,248,239,.82);",
            "}",
            "",
            ".poster-copy {",
            "  max-width: 28ch;",
            "  margin-top: 24px;",
            "  font-family: var(--font-family-body);",
            "  font-weight: var(--font-weight-body);",
            "  font-size: 28px;",
            "  line-height: 1.55;",
            "}",
            "",
            ".poster-grid {",
            "  display: grid;",
            "  grid-template-columns: repeat(3, minmax(0, 1fr));",
            "  gap: 16px;",
            "  margin-top: 34px;",
            "}",
            "",
            ".poster-chip {",
            "  padding: 14px 16px;",
            "  border-radius: 20px;",
            "  background: rgba(255,255,255,.08);",
            "  border: 1px solid rgba(255,255,255,.12);",
            "  font-family: var(--font-family-subtitle);",
            "}",
            "",
            "@media (max-width: 1100px) {",
            "  .landing-grid,",
            "  .thumbnail-grid,",
            "  .poster-grid {",
            "    grid-template-columns: 1fr;",
            "  }",
            "}",
        ]
    )
    return "\n".join(lines)


def _role_family(manifest: dict, role: str) -> str:
    return manifest["roles"][role]["family"]


def render_landing_html(manifest: dict) -> str:
    task = manifest.get("task", "FontAgent Project")
    use_case = manifest.get("use_case") or "custom"
    title_font = _role_family(manifest, "title")
    subtitle_font = _role_family(manifest, "subtitle")
    body_font = _role_family(manifest, "body")
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>FontAgent Landing Template</title>
  <link rel="stylesheet" href="./showcase.css" />
</head>
<body>
  <main class="shell">
    <section class="landing-grid">
      <article class="panel hero-panel">
        <header class="hero-top">
          <div class="pill">FontAgent Template System</div>
          <div class="pill">{use_case}</div>
        </header>
        <span class="kicker">{title_font} + {subtitle_font} + {body_font}</span>
        <h1 class="hero-title">{task}<br /><em>타이포 시스템으로 정리하다</em></h1>
        <p class="hero-copy">
          이 페이지는 프로젝트별 폰트 시스템에서 바로 생성된 템플릿입니다.
          제목, 부제, 본문 역할을 분리해 웹 랜딩과 영상 브랜딩이 같은 시각 언어를 공유하도록 설계했습니다.
        </p>
      </article>
      <aside class="aside-stack">
        <section class="panel aside-panel">
          <h2>선택된 역할</h2>
          <p>Title은 강한 존재감, Subtitle은 빠른 정보 전달, Body는 긴 호흡의 서사를 맡습니다.</p>
        </section>
        <section class="panel aside-panel">
          <h2>폰트 시스템 파일</h2>
          <div class="stat-grid">
            <div class="stat-box"><strong>3</strong><span>role fonts</span></div>
            <div class="stat-box"><strong>CSS</strong><span>design tokens</span></div>
            <div class="stat-box"><strong>TS</strong><span>remotion bridge</span></div>
            <div class="stat-box"><strong>HTML</strong><span>template bundle</span></div>
          </div>
        </section>
      </aside>
    </section>
  </main>
</body>
</html>
"""


def render_thumbnail_html(manifest: dict) -> str:
    task = manifest.get("task", "FontAgent Project")
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>FontAgent Thumbnail Template</title>
  <link rel="stylesheet" href="./showcase.css" />
</head>
<body>
  <main class="shell">
    <section class="thumbnail-stage">
      <div class="thumbnail-grid">
        <div class="thumbnail-copy">
          <div class="thumbnail-kicker">FontAgent / Thumbnail Template</div>
          <h1 class="thumbnail-title">{task}<em>한 줄로 압축</em></h1>
          <p class="thumbnail-subtitle">
            프로젝트 폰트 시스템에서 바로 생성된 썸네일 템플릿입니다.
          </p>
        </div>
        <aside class="thumbnail-aside">
          <div class="thumbnail-card">
            <h2>역할 분리</h2>
            <p>Title은 시선 확보, Subtitle은 설명, Body는 카드 요약에 맞게 분리합니다.</p>
            <ul>
              <li>Title: {_role_family(manifest, "title")}</li>
              <li>Subtitle: {_role_family(manifest, "subtitle")}</li>
              <li>Body: {_role_family(manifest, "body")}</li>
            </ul>
          </div>
        </aside>
      </div>
    </section>
  </main>
</body>
</html>
"""


def render_poster_html(manifest: dict) -> str:
    task = manifest.get("task", "FontAgent Project")
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>FontAgent Poster Template</title>
  <link rel="stylesheet" href="./showcase.css" />
</head>
<body>
  <main class="shell">
    <section class="poster-stage">
      <div class="poster-header">
        <div>
          <div class="poster-kicker">FontAgent / Poster Template</div>
          <h1 class="poster-title">{task}<br /><em>Poster Edition</em></h1>
        </div>
        <div class="poster-meta">
          {_role_family(manifest, "title")} / {_role_family(manifest, "subtitle")} / {_role_family(manifest, "body")}
        </div>
      </div>
      <p class="poster-copy">
        인쇄물과 포스터용 템플릿에서는 제목의 밀도와 본문의 톤 차이를 크게 가져가야 합니다.
        이 번들은 프로젝트 폰트 시스템을 기반으로 한 장짜리 프로모션 출력물을 바로 시작할 수 있게 합니다.
      </p>
      <div class="poster-grid">
        <div class="poster-chip">Editorial hierarchy</div>
        <div class="poster-chip">Brand-consistent typography</div>
        <div class="poster-chip">Ready for print mockups</div>
      </div>
    </section>
  </main>
</body>
</html>
"""


def write_template_bundle(output_dir: Path, manifest_path: Path) -> dict:
    output_dir = Path(output_dir)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)

    bundle_assets_dir = output_dir / "assets"
    bundle_assets: dict[str, dict] = {}
    for role in ("title", "subtitle", "body"):
        source_path = Path(manifest["roles"][role]["asset_path"])
        target_dir = bundle_assets_dir / role
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / source_path.name
        shutil.copyfile(source_path, target_path)
        bundle_assets[role] = {
            "asset_path": str(target_path),
            "bundle_relative_path": target_path.relative_to(output_dir).as_posix(),
        }

    css_path = output_dir / "showcase.css"
    landing_path = output_dir / "landing.html"
    thumbnail_path = output_dir / "thumbnail.html"
    poster_path = output_dir / "poster.html"

    css_path.write_text(render_template_css(manifest, bundle_assets), encoding="utf-8")
    landing_path.write_text(render_landing_html(manifest), encoding="utf-8")
    thumbnail_path.write_text(render_thumbnail_html(manifest), encoding="utf-8")
    poster_path.write_text(render_poster_html(manifest), encoding="utf-8")

    return {
        "template_dir": str(output_dir),
        "css_path": str(css_path),
        "landing_path": str(landing_path),
        "thumbnail_path": str(thumbnail_path),
        "poster_path": str(poster_path),
        "manifest_path": str(manifest_path),
        "asset_paths": {role: asset["asset_path"] for role, asset in bundle_assets.items()},
    }
