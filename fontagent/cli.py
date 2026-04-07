from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Union

from .curated_candidates import CURATED_CANDIDATE_SETS
from .discovery import DISCOVERY_QUERY_SETS, get_discovery_queries
from .http_api import serve
from .mcp_server import serve_stdio
from .service import FontAgentService
from .use_cases import USE_CASE_PRESETS


def _print(payload: Union[Dict, List[Dict]]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="FontAgent MVP CLI")
    parser.add_argument("--root", default=str(Path.cwd()), help="FontAgent project root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init")
    subparsers.add_parser("catalog-status")
    subparsers.add_parser("reference-status")
    subparsers.add_parser("reference-vault")
    subparsers.add_parser("license-policy-catalog")
    set_reference_vault = subparsers.add_parser("set-reference-vault")
    set_reference_vault.add_argument("--vault-root", required=True)
    set_reference_vault.add_argument("--vault-category", default="Fonts")
    set_reference_vault.add_argument(
        "--asset-policy",
        choices=["public_metadata_only", "public_with_assets"],
        default="public_metadata_only",
    )
    set_reference_vault.add_argument("--private-vault-root")
    contract_schema = subparsers.add_parser("contract-schema")
    contract_schema.add_argument("--name", default="typography-handoff.v1")
    bootstrap_project = subparsers.add_parser("bootstrap-project")
    bootstrap_project.add_argument("--project-path", required=True)
    bootstrap_project.add_argument("--use-case", default="documentary-landing-ko")
    bootstrap_project.add_argument("--language", default="ko")
    bootstrap_project.add_argument("--target", choices=["web", "remotion", "both"], default="both")
    bootstrap_project.add_argument("--asset-dir", default="assets/fonts")
    bootstrap_project.add_argument("--without-codex-skill", action="store_true")

    search = subparsers.add_parser("search")
    search.add_argument("--query", default="")
    search.add_argument("--language")
    search.add_argument("--commercial-only", action="store_true")
    search.add_argument("--video-only", action="store_true")
    search.add_argument("--include-failed", action="store_true")
    search.add_argument("--detail", choices=["full", "compact"], default="full")

    recommend = subparsers.add_parser("recommend")
    recommend.add_argument("--task", required=True)
    recommend.add_argument("--language")
    recommend.add_argument("--count", type=int, default=5)
    recommend.add_argument("--video-only", action="store_true")
    recommend.add_argument("--include-failed", action="store_true")
    recommend.add_argument("--detail", choices=["full", "compact"], default="full")

    recommend_use_case = subparsers.add_parser("recommend-use-case")
    recommend_use_case.add_argument("--medium", required=True)
    recommend_use_case.add_argument("--surface", required=True)
    recommend_use_case.add_argument("--role", required=True)
    recommend_use_case.add_argument("--tone", action="append")
    recommend_use_case.add_argument("--language", action="append")
    recommend_use_case.add_argument("--count", type=int, default=5)
    recommend_use_case.add_argument("--commercial-use", action="store_true")
    recommend_use_case.add_argument("--video-use", action="store_true")
    recommend_use_case.add_argument("--web-embedding", action="store_true")
    recommend_use_case.add_argument("--redistribution", action="store_true")
    recommend_use_case.add_argument("--include-failed", action="store_true")
    recommend_use_case.add_argument("--detail", choices=["full", "compact"], default="full")

    preview = subparsers.add_parser("preview")
    preview.add_argument("font_id")
    preview.add_argument("--preset", default="title-ko")
    preview.add_argument("--sample-text")

    install = subparsers.add_parser("install")
    install.add_argument("font_id")
    install.add_argument("--output-dir", required=True)

    verify_installs = subparsers.add_parser("verify-installations")
    verify_installs.add_argument("--output-dir", required=True)
    verify_installs.add_argument("--source-site")

    resolve_download = subparsers.add_parser("resolve-download")
    resolve_download.add_argument("font_id")

    prepare_browser = subparsers.add_parser("prepare-browser-task")
    prepare_browser.add_argument("font_id")
    prepare_browser.add_argument("--output-dir", required=True)

    prepare_source_browser = subparsers.add_parser("prepare-source-browser-task")
    prepare_source_browser.add_argument("--source-page-url", required=True)
    prepare_source_browser.add_argument("--output-dir", required=True)

    refresh_resolutions = subparsers.add_parser("refresh-downloads")
    refresh_resolutions.add_argument("--source-site")

    discover_web = subparsers.add_parser("discover-web")
    discover_web.add_argument("--query", action="append")
    discover_web.add_argument("--query-set", action="append", choices=sorted(DISCOVERY_QUERY_SETS))
    discover_web.add_argument("--limit-per-query", type=int, default=10)
    discover_web.add_argument("--blocked-domain", action="append")

    subparsers.add_parser("list-query-sets")

    seed_curated = subparsers.add_parser("seed-curated-candidates")
    seed_curated.add_argument("--profile", required=True, choices=sorted(CURATED_CANDIDATE_SETS))

    subparsers.add_parser("list-curated-profiles")
    subparsers.add_parser("list-use-cases")

    add_reference = subparsers.add_parser("add-reference")
    add_reference.add_argument("--title", required=True)
    add_reference.add_argument("--medium", required=True)
    add_reference.add_argument("--surface", required=True)
    add_reference.add_argument("--role", required=True)
    add_reference.add_argument("--reference-class", choices=["specimen", "market", "campaign", "channel"])
    add_reference.add_argument("--reference-scope", choices=["shared_public", "private_user"], default="shared_public")
    add_reference.add_argument("--source-kind", required=True)
    add_reference.add_argument("--source-url", default="")
    add_reference.add_argument("--asset-path", default="")
    add_reference.add_argument("--tone", action="append")
    add_reference.add_argument("--language", action="append")
    add_reference.add_argument("--text", action="append")
    add_reference.add_argument("--candidate-font-id", action="append")
    add_reference.add_argument("--observed-font", action="append")
    add_reference.add_argument("--palette-json", default="{}")
    add_reference.add_argument("--ratio-json", default="{}")
    add_reference.add_argument("--extraction-method", default="manual")
    add_reference.add_argument("--extraction-confidence", type=float, default=0.0)
    add_reference.add_argument("--status", default="draft")
    add_reference.add_argument("--note", action="append")

    list_references = subparsers.add_parser("list-references")
    list_references.add_argument("--medium")
    list_references.add_argument("--surface")
    list_references.add_argument("--role")
    list_references.add_argument("--status")
    list_references.add_argument("--reference-scope", choices=["shared_public", "private_user"])

    add_reference_review = subparsers.add_parser("add-reference-review")
    add_reference_review.add_argument("--reference-id", required=True)
    add_reference_review.add_argument("--reviewer-kind", required=True)
    add_reference_review.add_argument("--reviewer-name", required=True)
    add_reference_review.add_argument("--model-name", default="")
    add_reference_review.add_argument("--source", default="")
    add_reference_review.add_argument("--summary", default="")
    add_reference_review.add_argument("--candidate-font-id", action="append")
    add_reference_review.add_argument("--observed-font", action="append")
    add_reference_review.add_argument("--cohort-tag", action="append")
    add_reference_review.add_argument("--confidence", type=float, default=0.0)
    add_reference_review.add_argument("--status", default="curated")
    add_reference_review.add_argument("--note", action="append")
    add_reference_review.add_argument("--apply-to-reference", action="store_true")
    add_reference_review.add_argument("--vault-root")
    add_reference_review.add_argument("--vault-category", default="Fonts")

    list_reference_reviews = subparsers.add_parser("list-reference-reviews")
    list_reference_reviews.add_argument("--reference-id")
    list_reference_reviews.add_argument("--status")

    refresh_reference_candidates = subparsers.add_parser("refresh-reference-candidates")
    refresh_reference_candidates.add_argument("--medium")
    refresh_reference_candidates.add_argument("--surface")
    refresh_reference_candidates.add_argument("--role")
    refresh_reference_candidates.add_argument("--status", default="curated")

    reference_strategies = subparsers.add_parser("reference-strategies")
    reference_strategies.add_argument("--source-kind", required=True)
    reference_strategies.add_argument("--source-url", default="")
    reference_strategies.add_argument("--asset-path", default="")

    extract_web_reference = subparsers.add_parser("extract-web-reference")
    extract_web_reference.add_argument("--title", required=True)
    extract_web_reference.add_argument("--url", required=True)
    extract_web_reference.add_argument("--medium", required=True)
    extract_web_reference.add_argument("--surface", required=True)
    extract_web_reference.add_argument("--role", required=True)
    extract_web_reference.add_argument("--reference-class", choices=["specimen", "market", "campaign", "channel"])
    extract_web_reference.add_argument("--reference-scope", choices=["shared_public", "private_user"], default="shared_public")
    extract_web_reference.add_argument("--tone", action="append")
    extract_web_reference.add_argument("--language", action="append")
    extract_web_reference.add_argument("--vault-root")
    extract_web_reference.add_argument("--vault-category", default="Fonts")
    extract_web_reference.add_argument("--status", default="draft")

    extract_image_reference = subparsers.add_parser("extract-image-reference")
    extract_image_reference.add_argument("--title", required=True)
    extract_image_reference.add_argument("--image-path", required=True)
    extract_image_reference.add_argument("--medium", required=True)
    extract_image_reference.add_argument("--surface", required=True)
    extract_image_reference.add_argument("--role", required=True)
    extract_image_reference.add_argument("--reference-class", choices=["specimen", "market", "campaign", "channel"])
    extract_image_reference.add_argument("--reference-scope", choices=["shared_public", "private_user"], default="shared_public")
    extract_image_reference.add_argument("--tone", action="append")
    extract_image_reference.add_argument("--language", action="append")
    extract_image_reference.add_argument("--vault-root")
    extract_image_reference.add_argument("--vault-category", default="Fonts")
    extract_image_reference.add_argument("--status", default="draft")

    subparsers.add_parser("list-reference-packs")
    learn_reference_pack = subparsers.add_parser("learn-reference-pack")
    learn_reference_pack.add_argument("--pack", required=True)
    learn_reference_pack.add_argument("--limit", type=int)
    learn_reference_pack.add_argument("--vault-root")
    learn_reference_pack.add_argument("--vault-category")
    learn_reference_pack.add_argument("--continue-on-error", action="store_true")

    sync_reference_index = subparsers.add_parser("sync-reference-index")
    sync_reference_index.add_argument("--vault-root")
    sync_reference_index.add_argument("--vault-category")

    sanitize_reference_vault = subparsers.add_parser("sanitize-reference-vault")
    sanitize_reference_vault.add_argument("--vault-root")
    sanitize_reference_vault.add_argument("--vault-category")
    sanitize_reference_vault.add_argument("--keep-public-assets", action="store_true")

    list_candidates = subparsers.add_parser("list-candidates")
    list_candidates.add_argument("--status")
    list_candidates.add_argument("--discovery-source")

    subparsers.add_parser("normalize-candidate-statuses")

    normalize_sources = subparsers.add_parser("normalize-download-sources")
    normalize_sources.add_argument("--source-site")
    normalize_sources.add_argument("--overwrite", action="store_true")

    export_css = subparsers.add_parser("export-css")
    export_css.add_argument("font_id")

    export_remotion = subparsers.add_parser("export-remotion")
    export_remotion.add_argument("font_id")

    prepare_font_system = subparsers.add_parser("prepare-font-system")
    prepare_font_system.add_argument("--project-path", required=True)
    prepare_font_system.add_argument("--task", default="")
    prepare_font_system.add_argument("--language", default="ko")
    prepare_font_system.add_argument("--target", choices=["web", "remotion", "both"], default="both")
    prepare_font_system.add_argument("--asset-dir", default="assets/fonts")
    prepare_font_system.add_argument("--use-case", choices=sorted(USE_CASE_PRESETS))
    prepare_font_system.add_argument("--with-templates", action="store_true")

    generate_template_bundle = subparsers.add_parser("generate-template-bundle")
    generate_template_bundle.add_argument("--project-path", required=True)
    generate_template_bundle.add_argument("--task", default="")
    generate_template_bundle.add_argument("--language", default="ko")
    generate_template_bundle.add_argument("--target", choices=["web", "remotion", "both"], default="both")
    generate_template_bundle.add_argument("--asset-dir", default="assets/fonts")
    generate_template_bundle.add_argument("--use-case", choices=sorted(USE_CASE_PRESETS))

    generate_typography_handoff = subparsers.add_parser("generate-typography-handoff")
    generate_typography_handoff.add_argument("--project-path", required=True)
    generate_typography_handoff.add_argument("--task", default="")
    generate_typography_handoff.add_argument("--language", default="ko")
    generate_typography_handoff.add_argument("--target", choices=["web", "remotion", "both"], default="both")
    generate_typography_handoff.add_argument("--asset-dir", default="assets/fonts")
    generate_typography_handoff.add_argument("--use-case", choices=sorted(USE_CASE_PRESETS))

    import_noonnu = subparsers.add_parser("import-noonnu")
    import_noonnu.add_argument("--listing-html", required=True)
    import_noonnu.add_argument("--detail-dir", required=True)

    import_naver = subparsers.add_parser("import-naver-fonts")
    import_naver.add_argument("--source-page-url", default="https://hangeul.naver.com/font/nanum")

    import_hancom = subparsers.add_parser("import-hancom-fonts")
    import_hancom.add_argument("--source-page-url", default="https://font.hancom.com/pc/main/main.php")

    import_goodchoice = subparsers.add_parser("import-goodchoice-fonts")
    import_goodchoice.add_argument("--source-page-url", default="https://www.goodchoice.kr/font/mobile")

    import_google_display = subparsers.add_parser("import-google-display-fonts")
    import_google_display.add_argument("--source-page-url", default="https://fonts.google.com/")

    import_cafe24 = subparsers.add_parser("import-cafe24-fonts")
    import_cafe24.add_argument("--source-page-url", default="https://www.cafe24.com/story/use/cafe24pro_font.html")

    import_jeju = subparsers.add_parser("import-jeju-fonts")
    import_jeju.add_argument("--source-page-url", default="https://www.jeju.go.kr/jeju/symbol/font/infor.htm")

    subparsers.add_parser("import-league-fonts")

    subparsers.add_parser("import-velvetyne-fonts")

    import_fontshare = subparsers.add_parser("import-fontshare-fonts")
    import_fontshare.add_argument("--api-url", default="https://api.fontshare.com/v2/fonts")

    import_gmarket = subparsers.add_parser("import-gmarket-fonts")
    import_gmarket.add_argument("--source-page-url", default="https://gds.gmarket.co.kr/")

    import_nexon = subparsers.add_parser("import-nexon-fonts")
    import_nexon.add_argument("--source-page-url", default="https://brand.nexon.com/brand/fonts")

    import_woowahan = subparsers.add_parser("import-woowahan-fonts")
    import_woowahan.add_argument("--source-page-url", default="https://www.woowahan.com/fonts")

    import_fonco = subparsers.add_parser("import-fonco-fonts")
    import_fonco.add_argument("--source-page-url", default="https://font.co.kr/collection/freeFont")
    import_fonco.add_argument("--limit", type=int)

    import_gongu = subparsers.add_parser("import-gongu-fonts")
    import_gongu.add_argument(
        "--source-page-url",
        default="https://gongu.copyright.or.kr/gongu/bbs/B0000018/list.do?menuNo=200195",
    )
    import_gongu.add_argument("--max-pages", type=int)

    fetch_noonnu = subparsers.add_parser("fetch-noonnu")
    fetch_noonnu.add_argument("--listing-url", default="https://noonnu.cc/")
    fetch_noonnu.add_argument("--output-dir", required=True)
    fetch_noonnu.add_argument("--limit", type=int, default=20)

    serve_cmd = subparsers.add_parser("serve")
    serve_cmd.add_argument("--host", default="127.0.0.1")
    serve_cmd.add_argument("--port", type=int, default=8123)

    subparsers.add_parser("mcp")

    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    service = FontAgentService(root)

    try:
        if args.command == "init":
            _print({"seeded": service.init(), "db_path": str(service.db_path)})
        elif args.command == "catalog-status":
            _print(service.catalog_status())
        elif args.command == "reference-status":
            _print(service.reference_catalog_status())
        elif args.command == "reference-vault":
            _print(service.get_reference_settings())
        elif args.command == "license-policy-catalog":
            _print(service.license_policy_catalog())
        elif args.command == "set-reference-vault":
            _print(
                service.save_reference_settings(
                    vault_root=args.vault_root,
                    vault_category=args.vault_category,
                    asset_policy=args.asset_policy,
                    private_vault_root=args.private_vault_root or "",
                )
            )
        elif args.command == "contract-schema":
            _print(service.get_contract_schema(args.name))
        elif args.command == "bootstrap-project":
            _print(
                service.bootstrap_project_integration(
                    project_path=Path(args.project_path),
                    use_case=args.use_case,
                    language=args.language,
                    target=args.target,
                    asset_dir=args.asset_dir,
                    include_codex_skill=not args.without_codex_skill,
                )
            )
        elif args.command == "search":
            _print(
                {
                    "results": service.search(
                        query=args.query,
                        language=args.language,
                        commercial_only=args.commercial_only,
                        video_only=args.video_only,
                        include_failed=args.include_failed,
                        detail_level=args.detail,
                    )
                }
            )
        elif args.command == "recommend":
            _print(
                {
                    "results": service.recommend(
                        task=args.task,
                        language=args.language,
                        count=args.count,
                        video_only=args.video_only,
                        include_failed=args.include_failed,
                        detail_level=args.detail,
                    )
                }
            )
        elif args.command == "recommend-use-case":
            _print(
                service.recommend_use_case(
                    medium=args.medium,
                    surface=args.surface,
                    role=args.role,
                    tones=args.tone,
                    languages=args.language,
                    constraints={
                        "commercial_use": args.commercial_use,
                        "video_use": args.video_use,
                        "web_embedding": args.web_embedding,
                        "redistribution": args.redistribution,
                    },
                    count=args.count,
                    include_failed=args.include_failed,
                    detail_level=args.detail,
                )
            )
        elif args.command == "preview":
            _print(service.preview(args.font_id, preset=args.preset, sample_text=args.sample_text))
        elif args.command == "install":
            _print(service.install(args.font_id, Path(args.output_dir)))
        elif args.command == "verify-installations":
            _print(
                service.verify_installations(
                    output_dir=Path(args.output_dir),
                    source_site=args.source_site,
                )
            )
        elif args.command == "resolve-download":
            _print(service.resolve_download(args.font_id))
        elif args.command == "prepare-browser-task":
            _print(service.prepare_browser_download_task(args.font_id, Path(args.output_dir)))
        elif args.command == "prepare-source-browser-task":
            _print(service.prepare_source_browser_task(args.source_page_url, Path(args.output_dir)))
        elif args.command == "refresh-downloads":
            _print(service.refresh_download_resolutions(source_site=args.source_site))
        elif args.command == "discover-web":
            queries = list(args.query or [])
            for query_set in args.query_set or []:
                queries.extend(get_discovery_queries(query_set))
            _print(
                service.discover_web_candidates(
                    queries=queries or None,
                    limit_per_query=args.limit_per_query,
                    blocked_domains=args.blocked_domain,
                )
            )
        elif args.command == "list-query-sets":
            _print({"query_sets": DISCOVERY_QUERY_SETS})
        elif args.command == "seed-curated-candidates":
            _print(service.seed_curated_candidates(profile=args.profile))
        elif args.command == "list-curated-profiles":
            _print({"profiles": CURATED_CANDIDATE_SETS})
        elif args.command == "list-use-cases":
            _print(service.list_use_cases())
        elif args.command == "add-reference":
            _print(
                service.add_reference(
                    title=args.title,
                    medium=args.medium,
                    surface=args.surface,
                    role=args.role,
                    reference_class=args.reference_class or "",
                    reference_scope=args.reference_scope,
                    source_kind=args.source_kind,
                    source_url=args.source_url,
                    asset_path=args.asset_path,
                    tones=args.tone,
                    languages=args.language,
                    text_blocks=args.text,
                    candidate_font_ids=args.candidate_font_id,
                    observed_font_labels=args.observed_font,
                    palette=json.loads(args.palette_json),
                    ratio_hint=json.loads(args.ratio_json),
                    extraction_method=args.extraction_method,
                    extraction_confidence=args.extraction_confidence,
                    status=args.status,
                    notes=args.note,
                )
            )
        elif args.command == "list-references":
            _print(
                service.list_references(
                    medium=args.medium,
                    surface=args.surface,
                    role=args.role,
                    status=args.status,
                    reference_scope=args.reference_scope,
                )
            )
        elif args.command == "add-reference-review":
            _print(
                service.add_reference_review(
                    reference_id=args.reference_id,
                    reviewer_kind=args.reviewer_kind,
                    reviewer_name=args.reviewer_name,
                    model_name=args.model_name,
                    source=args.source,
                    summary=args.summary,
                    candidate_font_ids=args.candidate_font_id,
                    observed_font_labels=args.observed_font,
                    cohort_tags=args.cohort_tag,
                    confidence=args.confidence,
                    status=args.status,
                    notes=args.note,
                    apply_to_reference=args.apply_to_reference,
                    vault_root=Path(args.vault_root).expanduser().resolve() if args.vault_root else None,
                    vault_category=args.vault_category,
                )
            )
        elif args.command == "list-reference-reviews":
            _print(
                service.list_reference_reviews(
                    reference_id=args.reference_id,
                    status=args.status,
                )
            )
        elif args.command == "refresh-reference-candidates":
            _print(
                service.refresh_reference_candidates(
                    medium=args.medium,
                    surface=args.surface,
                    role=args.role,
                    status=args.status,
                )
            )
        elif args.command == "reference-strategies":
            _print(
                service.reference_extraction_strategies(
                    source_kind=args.source_kind,
                    source_url=args.source_url,
                    asset_path=args.asset_path,
                )
            )
        elif args.command == "extract-web-reference":
            _print(
                service.extract_web_reference(
                    title=args.title,
                    url=args.url,
                    medium=args.medium,
                    surface=args.surface,
                    role=args.role,
                    reference_class=args.reference_class or "",
                    reference_scope=args.reference_scope,
                    tones=args.tone,
                    languages=args.language,
                    vault_root=Path(args.vault_root).expanduser().resolve() if args.vault_root else None,
                    vault_category=args.vault_category,
                    status=args.status,
                )
            )
        elif args.command == "extract-image-reference":
            _print(
                service.extract_image_reference(
                    title=args.title,
                    image_path=Path(args.image_path),
                    medium=args.medium,
                    surface=args.surface,
                    role=args.role,
                    reference_class=args.reference_class or "",
                    reference_scope=args.reference_scope,
                    tones=args.tone,
                    languages=args.language,
                    vault_root=Path(args.vault_root).expanduser().resolve() if args.vault_root else None,
                    vault_category=args.vault_category,
                    status=args.status,
                )
            )
        elif args.command == "list-reference-packs":
            _print(service.list_reference_packs())
        elif args.command == "learn-reference-pack":
            _print(
                service.learn_reference_pack(
                    pack_name=args.pack,
                    limit=args.limit,
                    vault_root=Path(args.vault_root).expanduser().resolve() if args.vault_root else None,
                    vault_category=args.vault_category,
                    continue_on_error=args.continue_on_error,
                )
            )
        elif args.command == "sync-reference-index":
            _print(
                service.sync_reference_index(
                    vault_root=Path(args.vault_root).expanduser().resolve() if args.vault_root else None,
                    vault_category=args.vault_category,
                )
            )
        elif args.command == "sanitize-reference-vault":
            _print(
                service.sanitize_public_reference_vault(
                    vault_root=Path(args.vault_root).expanduser().resolve() if args.vault_root else None,
                    vault_category=args.vault_category,
                    remove_public_assets=not args.keep_public_assets,
                )
            )
        elif args.command == "list-candidates":
            _print(
                service.list_candidates(
                    status=args.status,
                    discovery_source=args.discovery_source,
                )
            )
        elif args.command == "normalize-candidate-statuses":
            _print(service.normalize_candidate_statuses())
        elif args.command == "normalize-download-sources":
            _print(
                service.normalize_download_sources(
                    source_site=args.source_site,
                    overwrite=args.overwrite,
                )
            )
        elif args.command == "export-css":
            _print(service.export_css(args.font_id))
        elif args.command == "export-remotion":
            _print(service.export_remotion(args.font_id))
        elif args.command == "prepare-font-system":
            _print(
                service.prepare_font_system(
                    project_path=Path(args.project_path),
                    task=args.task,
                    language=args.language,
                    target=args.target,
                    asset_dir=args.asset_dir,
                    use_case=args.use_case,
                    with_templates=args.with_templates,
                )
            )
        elif args.command == "generate-template-bundle":
            _print(
                service.generate_template_bundle(
                    project_path=Path(args.project_path),
                    task=args.task,
                    language=args.language,
                    target=args.target,
                    asset_dir=args.asset_dir,
                    use_case=args.use_case,
                )
            )
        elif args.command == "generate-typography-handoff":
            _print(
                service.generate_typography_handoff(
                    project_path=Path(args.project_path),
                    task=args.task,
                    language=args.language,
                    target=args.target,
                    asset_dir=args.asset_dir,
                    use_case=args.use_case,
                )
            )
        elif args.command == "import-noonnu":
            _print(
                service.import_noonnu(
                    listing_html=Path(args.listing_html),
                    detail_dir=Path(args.detail_dir),
                )
            )
        elif args.command == "import-naver-fonts":
            _print(service.import_naver_fonts(source_page_url=args.source_page_url))
        elif args.command == "import-hancom-fonts":
            _print(service.import_hancom_fonts(source_page_url=args.source_page_url))
        elif args.command == "import-goodchoice-fonts":
            _print(service.import_goodchoice_fonts(source_page_url=args.source_page_url))
        elif args.command == "import-google-display-fonts":
            _print(service.import_google_display_fonts(source_page_url=args.source_page_url))
        elif args.command == "import-cafe24-fonts":
            _print(service.import_cafe24_fonts(source_page_url=args.source_page_url))
        elif args.command == "import-jeju-fonts":
            _print(service.import_jeju_fonts(source_page_url=args.source_page_url))
        elif args.command == "import-league-fonts":
            _print(service.import_league_fonts())
        elif args.command == "import-velvetyne-fonts":
            _print(service.import_velvetyne_fonts())
        elif args.command == "import-fontshare-fonts":
            _print(service.import_fontshare_fonts(api_url=args.api_url))
        elif args.command == "import-gmarket-fonts":
            _print(service.import_gmarket_fonts(source_page_url=args.source_page_url))
        elif args.command == "import-nexon-fonts":
            _print(service.import_nexon_fonts(source_page_url=args.source_page_url))
        elif args.command == "import-woowahan-fonts":
            _print(service.import_woowahan_fonts(source_page_url=args.source_page_url))
        elif args.command == "import-fonco-fonts":
            _print(
                service.import_fonco_fonts(
                    source_page_url=args.source_page_url,
                    limit=args.limit,
                )
            )
        elif args.command == "import-gongu-fonts":
            _print(
                service.import_gongu_fonts(
                    source_page_url=args.source_page_url,
                    max_pages=args.max_pages,
                )
            )
        elif args.command == "fetch-noonnu":
            _print(
                service.fetch_and_import_noonnu(
                    listing_url=args.listing_url,
                    output_dir=Path(args.output_dir),
                    limit=args.limit,
                )
            )
        elif args.command == "serve":
            serve(root, host=args.host, port=args.port)
        elif args.command == "mcp":
            serve_stdio(root)
    except Exception as exc:
        _print({"error": str(exc)})
        raise SystemExit(1)


if __name__ == "__main__":
    main()
