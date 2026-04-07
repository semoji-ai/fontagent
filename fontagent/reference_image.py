from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _tool_dir(root: Path) -> Path:
    return Path(root) / ".tools" / "reference_image"


def extract_image_reference_payload(
    *,
    root: Path,
    image_path: Path,
    output_dir: Path,
) -> dict:
    tool_dir = _tool_dir(root)
    script_path = tool_dir / "extract.swift"
    if not script_path.exists():
        raise FileNotFoundError(f"reference image extractor not found: {script_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "extract.json"
    subprocess.run(
        [
            "swift",
            str(script_path.resolve()),
            "--image",
            str(Path(image_path).expanduser().resolve()),
            "--out",
            str(json_path.resolve()),
        ],
        cwd=str(tool_dir),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload["json_path"] = str(json_path)
    payload["screenshot_path"] = str(Path(image_path).expanduser().resolve())
    return payload
