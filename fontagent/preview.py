from __future__ import annotations

import base64
import hashlib
from html import escape
from pathlib import Path

from .models import FontRecord


PRESET_MAP = {
    "title-ko": {"size": 78, "family_size": 96, "sample_attr": "preview_text_ko", "label": "Title / Korean"},
    "title-en": {"size": 78, "family_size": 96, "sample_attr": "preview_text_en", "label": "Title / English"},
    "subtitle-ko": {"size": 56, "family_size": 88, "sample_attr": "preview_text_ko", "label": "Subtitle / Korean"},
    "subtitle-en": {"size": 56, "family_size": 88, "sample_attr": "preview_text_en", "label": "Subtitle / English"},
    "body-ko": {"size": 42, "family_size": 80, "sample_attr": "preview_text_ko", "label": "Body / Korean"},
    "body-en": {"size": 42, "family_size": 80, "sample_attr": "preview_text_en", "label": "Body / English"},
}

FORMAT_MAP = {
    ".ttf": "truetype",
    ".otf": "opentype",
    ".woff2": "woff2",
    ".woff": "woff",
    ".ttc": "truetype",
    ".otc": "opentype",
}

MIME_MAP = {
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttc": "application/octet-stream",
    ".otc": "application/octet-stream",
}


def css_font_format(path: str) -> str:
    return FORMAT_MAP.get(Path(path).suffix.lower(), "truetype")


def font_data_uri(path: str) -> str:
    file_path = Path(path)
    mime = MIME_MAP.get(file_path.suffix.lower(), "application/octet-stream")
    encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def render_preview_svg(
    font: FontRecord,
    preset: str = "title-ko",
    sample_text: str | None = None,
    font_face_src: str | None = None,
    font_face_format: str | None = None,
) -> str:
    config = PRESET_MAP.get(preset, PRESET_MAP["title-ko"])
    sample_text = sample_text or getattr(font, config["sample_attr"])
    family = escape(font.family)
    sample_text = escape(sample_text)
    label = escape(config["label"])
    license_summary = escape(font.license_summary)
    font_stack = f"{family}, 'Apple SD Gothic Neo', sans-serif"
    font_face_block = ""
    if font_face_src:
        escaped_src = escape(font_face_src, quote=True)
        format_name = escape(font_face_format or "truetype")
        font_stack = "'FontAgentPreviewEmbedded', 'Apple SD Gothic Neo', sans-serif"
        font_face_block = (
            "<defs><style><![CDATA["
            "@font-face {"
            "font-family: 'FontAgentPreviewEmbedded';"
            f"src: url('{escaped_src}') format('{format_name}');"
            "font-display: swap;"
            "}"
            "]]></style></defs>"
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="680" viewBox="0 0 1200 680">
  {font_face_block}
  <rect width="1200" height="680" fill="#f7f3ea"/>
  <rect x="18" y="18" width="1164" height="644" rx="30" fill="#fffdf8" stroke="#d8cfbe" stroke-width="2"/>
  <text x="54" y="74" font-size="22" font-family="Georgia, serif" fill="#7c6d54">{label}</text>
  <text x="54" y="164" font-size="{config["family_size"]}" font-weight="700" font-family="{font_stack}" fill="#17120e">{family}</text>
  <text x="54" y="338" font-size="{config["size"]}" font-family="{font_stack}" fill="#17120e">{sample_text}</text>
  <text x="54" y="618" font-size="21" font-family="Menlo, monospace" fill="#6c6256">{license_summary}</text>
</svg>"""


def write_preview(
    font: FontRecord,
    output_dir: Path,
    preset: str = "title-ko",
    sample_text: str | None = None,
    font_face_src: str | None = None,
    font_face_format: str | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = ""
    if sample_text:
        suffix = f"-{hashlib.sha1(sample_text.encode('utf-8')).hexdigest()[:10]}"
    output_path = output_dir / f"{font.font_id}-{preset}{suffix}.svg"
    output_path.write_text(
        render_preview_svg(
            font,
            preset=preset,
            sample_text=sample_text,
            font_face_src=font_face_src,
            font_face_format=font_face_format,
        ),
        encoding="utf-8",
    )
    return output_path
