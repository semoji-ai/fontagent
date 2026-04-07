from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any
from urllib import error, request


def _strip_json_block(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
    return cleaned.strip()


def guess_reference_fonts_via_vision(
    *,
    image_path: Path,
    candidate_fonts: list[dict[str, Any]],
    medium: str,
    surface: str,
    role: str,
    tones: list[str] | None = None,
    languages: list[str] | None = None,
    text_blocks: list[str] | None = None,
) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return {
            "used": False,
            "available": False,
            "reason": "missing_api_key",
            "candidate_font_ids": [],
            "observed_font_labels": [],
            "confidence": 0.0,
        }

    model = os.getenv("FONTAGENT_VISION_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
    image_bytes = Path(image_path).read_bytes()
    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    candidate_lines = []
    for item in candidate_fonts[:12]:
        candidate_lines.append(
            f"- {item['font_id']} | {item['family']} | tags={','.join(item.get('tags', [])[:6])} | roles={','.join(item.get('recommended_for', [])[:4])}"
        )
    prompt = "\n".join(
        [
            "You are helping FontAgent identify the most likely font candidates for a reference image.",
            "Pick only from the provided candidate font IDs.",
            f"Context: medium={medium}, surface={surface}, role={role}, tones={','.join(tones or [])}, languages={','.join(languages or [])}",
            f"OCR text: {' | '.join(text_blocks or [])}",
            "Return JSON only with this schema:",
            '{"candidate_font_ids":["font-id"],"observed_font_labels":["descriptor"],"confidence":0.0,"reasoning":["short reason"]}',
            "Candidate fonts:",
            *candidate_lines,
        ]
    )
    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{image_b64}",
                        "detail": "high",
                    },
                ],
            }
        ],
    }
    req = request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=90) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except error.URLError as exc:
        return {
            "used": False,
            "available": True,
            "reason": f"request_failed:{exc}",
            "candidate_font_ids": [],
            "observed_font_labels": [],
            "confidence": 0.0,
        }

    output_text = str(raw.get("output_text", "") or "")
    if not output_text and raw.get("output"):
        parts: list[str] = []
        for item in raw["output"]:
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    parts.append(content.get("text", ""))
        output_text = "\n".join(part for part in parts if part)
    try:
        parsed = json.loads(_strip_json_block(output_text))
    except json.JSONDecodeError:
        return {
            "used": False,
            "available": True,
            "reason": "invalid_json_output",
            "candidate_font_ids": [],
            "observed_font_labels": [],
            "confidence": 0.0,
            "raw_text": output_text,
        }

    valid_ids = {item["font_id"] for item in candidate_fonts}
    candidate_font_ids = [font_id for font_id in parsed.get("candidate_font_ids", []) if font_id in valid_ids][:5]
    observed_font_labels = [str(label) for label in parsed.get("observed_font_labels", []) if str(label).strip()][:5]
    confidence = float(parsed.get("confidence", 0.0) or 0.0)
    reasoning = [str(line) for line in parsed.get("reasoning", []) if str(line).strip()][:5]
    return {
        "used": True,
        "available": True,
        "reason": "ok",
        "model": model,
        "candidate_font_ids": candidate_font_ids,
        "observed_font_labels": observed_font_labels,
        "confidence": max(0.0, min(confidence, 1.0)),
        "reasoning": reasoning,
        "raw_text": output_text,
    }
