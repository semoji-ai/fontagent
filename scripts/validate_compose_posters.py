"""End-to-end validation harness for compose_text_layers.

Generates a set of synthetic posters that exercise different typography
scenarios (editorial, display, handwriting, mixed KO/EN, etc.), runs the
full compose pipeline against each one, and tabulates:

- per-region winner font
- whether identify and recommend agreed (confidence tier)
- license-filter behavior
- total pipeline time

The script is self-contained — run it from the repo root with
`PYTHONPATH=. python3 scripts/validate_compose_posters.py`.
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from fontagent.font_identify import build_index
from fontagent.font_identify.index import FontSource
from fontagent.service import FontAgentService


KDIR = Path("/tmp/kfonts")
SYSDIR = Path("/usr/share/fonts")

FONT_CATALOG = [
    # font_id, family, path, tags, languages
    ("noto-sans-kr", "Noto Sans KR", KDIR / "NotoSansKR-Regular.otf", ["gothic", "sans"], ["ko", "en"]),
    ("noto-serif-kr", "Noto Serif KR", KDIR / "NotoSerifKR-Regular.otf", ["serif", "myeongjo"], ["ko", "en"]),
    ("nanum-gothic", "Nanum Gothic", KDIR / "NanumGothic-Regular.ttf", ["gothic", "sans", "clean"], ["ko", "en"]),
    ("nanum-myeongjo", "Nanum Myeongjo", KDIR / "NanumMyeongjo-Regular.ttf", ["serif", "myeongjo"], ["ko", "en"]),
    ("black-han-sans", "Black Han Sans", KDIR / "BlackHanSans-Regular.ttf", ["display", "heavy", "bold"], ["ko"]),
    ("dohyeon", "Do Hyeon", KDIR / "DoHyeon-Regular.ttf", ["display", "bold", "title"], ["ko"]),
    ("jua", "Jua", KDIR / "Jua-Regular.ttf", ["display", "round", "friendly"], ["ko"]),
    ("gugi", "Gugi", KDIR / "Gugi-Regular.ttf", ["display", "brush", "calligraphy"], ["ko"]),
    ("hahmlet", "Hahmlet", KDIR / "Hahmlet-Variable.ttf", ["serif", "modern"], ["ko"]),
    ("nanum-pen", "Nanum Pen Script", KDIR / "NanumPenScript-Regular.ttf", ["handwriting", "pen"], ["ko"]),
    ("gaegu", "Gaegu", KDIR / "Gaegu-Regular.ttf", ["handwriting", "soft"], ["ko"]),
    ("single-day", "Single Day", KDIR / "SingleDay-Regular.ttf", ["handwriting", "casual"], ["ko"]),
    ("dejavu-serif", "DejaVu Serif", SYSDIR / "truetype/dejavu/DejaVuSerif.ttf", ["serif", "classic"], ["en"]),
    ("dejavu-sans", "DejaVu Sans", SYSDIR / "truetype/dejavu/DejaVuSans.ttf", ["sans", "gothic"], ["en"]),
    ("dejavu-mono", "DejaVu Sans Mono", SYSDIR / "truetype/dejavu/DejaVuSansMono.ttf", ["mono", "code"], ["en"]),
    ("freesans", "FreeSans", SYSDIR / "truetype/freefont/FreeSans.ttf", ["sans", "clean"], ["en"]),
    ("freeserif", "FreeSerif", SYSDIR / "truetype/freefont/FreeSerif.ttf", ["serif", "classic"], ["en"]),
]


@dataclass
class Region:
    text: str
    font_id: str
    size: int
    position: tuple[int, int]
    role: str
    style_hints: list[str]
    language: str


@dataclass
class PosterCase:
    name: str
    description: str
    canvas: tuple[int, int]
    regions: list[Region]


CASES: list[PosterCase] = [
    PosterCase(
        name="01-editorial-ko",
        description="Korean editorial, consistent Myeongjo family",
        canvas=(1200, 700),
        regions=[
            Region("봄 에디션", "noto-serif-kr", 120, (80, 80), "title",
                   ["serif", "myeongjo", "editorial"], "ko"),
            Region("2024년 3월호", "noto-serif-kr", 54, (80, 240), "subtitle",
                   ["serif", "myeongjo"], "ko"),
            Region("새로운 이야기가 시작됩니다", "nanum-myeongjo", 36, (80, 340), "body",
                   ["serif", "myeongjo", "soft"], "ko"),
        ],
    ),
    PosterCase(
        name="02-sale-display",
        description="Bold display — sale poster",
        canvas=(1000, 600),
        regions=[
            Region("SALE", "black-han-sans", 200, (100, 80), "title",
                   ["display", "heavy", "bold"], "en"),
            Region("최대 50% 할인", "dohyeon", 72, (100, 320), "subtitle",
                   ["display", "bold"], "ko"),
        ],
    ),
    PosterCase(
        name="03-handwriting-invite",
        description="Handwriting wedding invite",
        canvas=(1000, 700),
        regions=[
            Region("Happy Birthday", "nanum-pen", 96, (80, 100), "title",
                   ["handwriting", "pen", "casual"], "en"),
            Region("Dear Friend", "gaegu", 60, (80, 260), "subtitle",
                   ["handwriting", "soft"], "en"),
            Region("봄의 기운이", "single-day", 48, (80, 420), "body",
                   ["handwriting", "casual"], "ko"),
        ],
    ),
    PosterCase(
        name="04-vintage-en",
        description="Vintage serif display",
        canvas=(1200, 700),
        regions=[
            Region("VINTAGE VIBES", "dejavu-serif", 96, (80, 100), "title",
                   ["serif", "display", "vintage"], "en"),
            Region("EST. 1995", "freeserif", 48, (80, 260), "subtitle",
                   ["serif", "classic"], "en"),
        ],
    ),
    PosterCase(
        name="05-tech-launch",
        description="Clean sans tech announcement",
        canvas=(1200, 600),
        regions=[
            Region("PRODUCT LAUNCH", "dejavu-sans", 72, (80, 80), "title",
                   ["sans", "gothic", "clean"], "en"),
            Region("Q1 2024", "dejavu-mono", 48, (80, 220), "subtitle",
                   ["mono", "code", "tech"], "en"),
            Region("새로운 시대", "nanum-gothic", 56, (80, 340), "body",
                   ["sans", "gothic", "clean"], "ko"),
        ],
    ),
    PosterCase(
        name="06-festival-brush",
        description="Korean festival, brush-style",
        canvas=(1000, 600),
        regions=[
            Region("봄 축제", "gugi", 144, (80, 80), "title",
                   ["display", "brush", "festive"], "ko"),
            Region("VERNAL FESTIVAL", "jua", 48, (80, 300), "subtitle",
                   ["display", "round", "friendly"], "en"),
        ],
    ),
    PosterCase(
        name="07-minimalist-ko",
        description="Minimalist Nanum Gothic throughout",
        canvas=(1200, 800),
        regions=[
            Region("미니멀", "nanum-gothic", 144, (80, 100), "title",
                   ["sans", "gothic", "minimalist"], "ko"),
            Region("간결한 디자인", "nanum-gothic", 54, (80, 320), "subtitle",
                   ["sans", "gothic", "clean"], "ko"),
            Region("가나다라마바사", "nanum-gothic", 42, (80, 440), "body",
                   ["sans", "gothic"], "ko"),
        ],
    ),
    PosterCase(
        name="08-modern-serif-mixed",
        description="Hahmlet serif title with gothic body",
        canvas=(1200, 700),
        regions=[
            Region("HAHMLET 2024", "hahmlet", 108, (80, 100), "title",
                   ["serif", "modern", "editorial"], "en"),
            Region("봄의 서막", "hahmlet", 54, (80, 280), "subtitle",
                   ["serif", "modern"], "ko"),
            Region("읽기 좋은 본문", "noto-sans-kr", 36, (80, 400), "body",
                   ["sans", "gothic"], "ko"),
        ],
    ),
    PosterCase(
        name="09-mono-code",
        description="Pure monospace code block",
        canvas=(1200, 500),
        regions=[
            Region("DEBUG LOG 2024", "dejavu-mono", 72, (80, 80), "title",
                   ["mono", "code", "tech"], "en"),
            Region("print('hello')", "dejavu-mono", 48, (80, 260), "body",
                   ["mono", "code"], "en"),
        ],
    ),
    PosterCase(
        name="10-tiny-body",
        description="Very small body text stresses detection",
        canvas=(1000, 400),
        regions=[
            Region("대한민국", "nanum-gothic", 120, (80, 80), "title",
                   ["sans", "gothic"], "ko"),
            Region("작은 글씨도 읽을 수 있어야 합니다", "nanum-myeongjo", 24, (80, 280), "body",
                   ["serif", "myeongjo"], "ko"),
        ],
    ),
    PosterCase(
        name="11-huge-display",
        description="Extreme size — single giant word",
        canvas=(1400, 500),
        regions=[
            Region("COSMOS", "black-han-sans", 260, (80, 80), "title",
                   ["display", "heavy", "bold"], "en"),
        ],
    ),
    PosterCase(
        name="12-script-korean",
        description="Korean brush calligraphy with explicit hint",
        canvas=(1000, 500),
        regions=[
            Region("서예", "gugi", 200, (80, 80), "title",
                   ["brush", "calligraphy", "display"], "ko"),
        ],
    ),
    PosterCase(
        name="13-mixed-languages",
        description="Single region mixing ko + en",
        canvas=(1200, 400),
        regions=[
            Region("Hello 한국", "noto-sans-kr", 96, (80, 100), "title",
                   ["sans", "gothic", "bilingual"], "ko"),
        ],
    ),
    PosterCase(
        name="14-three-role-system",
        description="Full title/subtitle/body system in consistent Myeongjo",
        canvas=(1200, 900),
        regions=[
            Region("AUTUMN", "nanum-myeongjo", 144, (80, 80), "title",
                   ["serif", "myeongjo", "editorial"], "en"),
            Region("가을의 편지", "nanum-myeongjo", 72, (80, 320), "subtitle",
                   ["serif", "myeongjo", "soft"], "ko"),
            Region("조용히 스며드는 계절의 감각", "nanum-myeongjo", 36, (80, 520), "body",
                   ["serif", "myeongjo"], "ko"),
        ],
    ),
    PosterCase(
        name="15-heavy-weight-contrast",
        description="Heavy display title + thin body",
        canvas=(1200, 700),
        regions=[
            Region("THICK", "black-han-sans", 200, (80, 80), "title",
                   ["display", "heavy", "bold"], "en"),
            Region("가벼운 본문", "nanum-pen", 42, (80, 400), "body",
                   ["handwriting", "pen", "casual"], "ko"),
        ],
    ),
    PosterCase(
        name="16-rounded-display",
        description="Round friendly display pair",
        canvas=(1000, 600),
        regions=[
            Region("WELCOME", "jua", 120, (80, 80), "title",
                   ["display", "round", "friendly"], "en"),
            Region("환영합니다", "jua", 72, (80, 300), "subtitle",
                   ["display", "round", "friendly"], "ko"),
        ],
    ),
]


def seed_database(service: FontAgentService) -> None:
    records = []
    for fid, family, path, tags, languages in FONT_CATALOG:
        records.append({
            "font_id": fid,
            "family": family,
            "slug": fid,
            "source_site": "fixture",
            "source_page_url": f"file://{path}",
            "license_id": "OFL",
            "license_summary": "Fixture OFL-equivalent",
            "commercial_use_allowed": True,
            "video_use_allowed": True,
            "web_embedding_allowed": True,
            "redistribution_allowed": True,
            "languages": languages,
            "tags": tags,
            "recommended_for": [tag for tag in tags if tag in ("title", "body", "subtitle")] or ["title"],
            "download_type": "manual_only",
            "download_url": "",
            "download_source": "fixture",
            "format": "ttf",
            "variable_font": False,
        })
    service.repository.upsert_many(records)


def build_index_for_catalog(service: FontAgentService) -> None:
    sources = [
        FontSource(fid, family, path, languages=languages, tags=tags)
        for fid, family, path, tags, languages in FONT_CATALOG
    ]
    build_index(
        sources,
        index_dir=service.font_identify_index_dir,
        language_hint="both",
    )


def render_poster(case: PosterCase, out_path: Path) -> None:
    canvas = Image.new("RGB", case.canvas, color=(250, 248, 240))
    draw = ImageDraw.Draw(canvas)
    for region in case.regions:
        font_record = next(r for r in FONT_CATALOG if r[0] == region.font_id)
        font_path = font_record[2]
        pil_font = ImageFont.truetype(str(font_path), region.size)
        draw.text(region.position, region.text, fill=(10, 10, 10), font=pil_font)
    canvas.save(out_path)


def regions_payload(case: PosterCase, poster_image: Image.Image) -> list[dict]:
    payload = []
    for region in case.regions:
        font_record = next(r for r in FONT_CATALOG if r[0] == region.font_id)
        font_path = font_record[2]
        pil_font = ImageFont.truetype(str(font_path), region.size)
        # Ink bbox of the rendered text
        sample = Image.new("RGB", poster_image.size, color=(255, 255, 255))
        d = ImageDraw.Draw(sample)
        d.text(region.position, region.text, fill=(0, 0, 0), font=pil_font)
        bbox = sample.getbbox()
        if bbox is None:
            bbox = (*region.position, region.position[0] + 1, region.position[1] + 1)
        # Expand bbox slightly for safety
        x0 = max(0, bbox[0] - 6)
        y0 = max(0, bbox[1] - 6)
        x1 = min(poster_image.size[0], bbox[2] + 6)
        y1 = min(poster_image.size[1], bbox[3] + 6)
        payload.append({
            "bbox": [x0, y0, x1, y1],
            "text": region.text,
            "role": region.role,
            "style_hints": region.style_hints,
            "language": region.language,
        })
    return payload


def evaluate_case(
    service: FontAgentService,
    case: PosterCase,
    work_dir: Path,
) -> dict:
    poster_path = work_dir / f"{case.name}.png"
    render_poster(case, poster_path)
    source_image = Image.open(poster_path)
    regions = regions_payload(case, source_image)

    started = time.time()
    result = service.compose_text_layers(
        image_path=poster_path,
        regions=regions,
        similar_alternatives=5,
        license_constraints={"commercial_use": True},
        svg_output_path=work_dir / f"{case.name}-preview.svg",
    )
    elapsed_ms = int((time.time() - started) * 1000)

    truth_tag_map = {fid: set(tags) for fid, _, _, tags, _ in FONT_CATALOG}

    per_region = []
    for layer, truth in zip(result["text_layers"], case.regions):
        font = layer.get("font") or {}
        sources_info = font.get("match_sources") or {}
        winner_id = font.get("font_id")
        is_identify_top1 = sources_info.get("identify_rank") == 1
        is_recommend_top1 = sources_info.get("recommend_rank") == 1

        # Top-k containment: is truth_font_id among winner + alternatives?
        candidate_ids = [winner_id] + [
            alt.get("font_id") for alt in layer.get("similar_alternatives", [])
        ]
        candidate_ids = [cid for cid in candidate_ids if cid]
        truth_in_top3 = truth.font_id in candidate_ids[:3]
        truth_in_top5 = truth.font_id in candidate_ids[:5]

        # Category/tag overlap: do winner and truth share a distinctive tag?
        winner_tags = truth_tag_map.get(winner_id or "", set())
        truth_tags = truth_tag_map.get(truth.font_id, set())
        shared_tags = winner_tags & truth_tags
        category_match = bool(shared_tags & {
            "serif", "myeongjo", "sans", "gothic",
            "display", "heavy", "handwriting", "brush", "mono",
        })

        per_region.append({
            "role": truth.role,
            "text": truth.text,
            "truth_font_id": truth.font_id,
            "winner_font_id": winner_id,
            "winner_family": font.get("family"),
            "confidence": layer.get("confidence"),
            "tier": layer.get("confidence_tier"),
            "correct": winner_id == truth.font_id,
            "truth_in_top3": truth_in_top3,
            "truth_in_top5": truth_in_top5,
            "category_match": category_match,
            "shared_tags": sorted(shared_tags),
            "identify_rank": sources_info.get("identify_rank"),
            "recommend_rank": sources_info.get("recommend_rank"),
            "identify_top1": is_identify_top1,
            "recommend_top1": is_recommend_top1,
        })

    return {
        "name": case.name,
        "description": case.description,
        "elapsed_ms": elapsed_ms,
        "per_region": per_region,
    }


def main() -> None:
    root = Path("/tmp/validate_root")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    (root / "fontagent" / "seed").mkdir(parents=True)
    (root / "fontagent" / "seed" / "fonts.json").write_text('{"fonts": []}', encoding="utf-8")
    service = FontAgentService(root)
    service.ensure_catalog_ready()
    seed_database(service)
    build_index_for_catalog(service)

    work_dir = root / "posters"
    work_dir.mkdir(parents=True)

    results = [evaluate_case(service, case, work_dir) for case in CASES]

    total = 0
    correct = 0
    top3 = 0
    top5 = 0
    category_ok = 0
    tier_counts: dict[str, int] = {}
    identify_top1 = 0
    recommend_top1 = 0
    both_top1 = 0

    print(
        f"{'case':26} {'role':10} {'text':22} "
        f"{'winner':18} {'truth':18} {'cat':4} "
        f"{'t3':3} {'t5':3} {'id':3} {'rc':3} ok"
    )
    print("-" * 132)
    for res in results:
        for r in res["per_region"]:
            total += 1
            if r["correct"]:
                correct += 1
            if r["truth_in_top3"]:
                top3 += 1
            if r["truth_in_top5"]:
                top5 += 1
            if r["category_match"]:
                category_ok += 1
            tier_counts[r.get("tier", "none")] = tier_counts.get(r.get("tier", "none"), 0) + 1
            if r["identify_top1"]:
                identify_top1 += 1
            if r["recommend_top1"]:
                recommend_top1 += 1
            if r["identify_top1"] and r["recommend_top1"]:
                both_top1 += 1
            print(
                f"{res['name']:26} {r['role']:10} {r['text'][:20]:22} "
                f"{str(r['winner_family'] or '?')[:16]:18} {r['truth_font_id'][:16]:18} "
                f"{'✓' if r['category_match'] else '✗':4} "
                f"{'✓' if r['truth_in_top3'] else '✗':3} "
                f"{'✓' if r['truth_in_top5'] else '✗':3} "
                f"{str(r['identify_rank'] or '-'):3} "
                f"{str(r['recommend_rank'] or '-'):3} "
                f"{'✓' if r['correct'] else '✗'}"
            )
    print("-" * 132)
    print()
    print("=== aggregate ===")
    print(f"posters              : {len(results)}")
    print(f"total regions        : {total}")
    print(f"exact winner correct : {correct}/{total} ({100*correct/total:.0f}%)")
    print(f"truth in top-3       : {top3}/{total} ({100*top3/total:.0f}%)")
    print(f"truth in top-5       : {top5}/{total} ({100*top5/total:.0f}%)")
    print(f"category match       : {category_ok}/{total} ({100*category_ok/total:.0f}%)")
    print(f"identify top-1       : {identify_top1}/{total} ({100*identify_top1/total:.0f}%)")
    print(f"recommend top-1      : {recommend_top1}/{total} ({100*recommend_top1/total:.0f}%)")
    print(f"both agreed top-1    : {both_top1}/{total} ({100*both_top1/total:.0f}%)")
    print(f"confidence tiers     : {tier_counts}")
    print(f"avg ms/poster        : {int(sum(r['elapsed_ms'] for r in results)/len(results))}")


if __name__ == "__main__":
    main()
