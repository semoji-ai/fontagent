from __future__ import annotations

import hashlib
from html import escape
from pathlib import Path

from .models import FontRecord


PRESET_MAP = {
    "title-ko": {"size": 56, "sample_attr": "preview_text_ko", "label": "Title / Korean"},
    "title-en": {"size": 56, "sample_attr": "preview_text_en", "label": "Title / English"},
    "subtitle-ko": {"size": 38, "sample_attr": "preview_text_ko", "label": "Subtitle / Korean"},
    "subtitle-en": {"size": 38, "sample_attr": "preview_text_en", "label": "Subtitle / English"},
    "body-ko": {"size": 28, "sample_attr": "preview_text_ko", "label": "Body / Korean"},
    "body-en": {"size": 28, "sample_attr": "preview_text_en", "label": "Body / English"},
}


def render_preview_svg(font: FontRecord, preset: str = "title-ko", sample_text: str | None = None) -> str:
    config = PRESET_MAP.get(preset, PRESET_MAP["title-ko"])
    sample_text = sample_text or getattr(font, config["sample_attr"])
    family = escape(font.family)
    sample_text = escape(sample_text)
    label = escape(config["label"])
    tags = ", ".join(font.tags[:5])
    tags = escape(tags)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <rect width="1200" height="630" fill="#f7f3ea"/>
  <rect x="40" y="40" width="1120" height="550" rx="28" fill="#fffdf8" stroke="#d8cfbe" stroke-width="2"/>
  <text x="80" y="110" font-size="28" font-family="Georgia, serif" fill="#7c6d54">{label}</text>
  <text x="80" y="170" font-size="52" font-weight="700" font-family="Georgia, serif" fill="#1f1b16">{family}</text>
  <text x="80" y="285" font-size="{config["size"]}" font-family="{family}, 'Apple SD Gothic Neo', sans-serif" fill="#16120e">{sample_text}</text>
  <text x="80" y="520" font-size="24" font-family="Menlo, monospace" fill="#5d564b">{escape(font.license_summary)}</text>
  <text x="80" y="560" font-size="22" font-family="Menlo, monospace" fill="#8a7f70">{tags}</text>
</svg>"""


def write_preview(
    font: FontRecord,
    output_dir: Path,
    preset: str = "title-ko",
    sample_text: str | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = ""
    if sample_text:
        suffix = f"-{hashlib.sha1(sample_text.encode('utf-8')).hexdigest()[:10]}"
    output_path = output_dir / f"{font.font_id}-{preset}{suffix}.svg"
    output_path.write_text(
        render_preview_svg(font, preset=preset, sample_text=sample_text),
        encoding="utf-8",
    )
    return output_path
