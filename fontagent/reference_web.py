from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _tool_dir(root: Path) -> Path:
    return Path(root) / ".tools" / "reference_web"


def ensure_reference_web_tool(root: Path) -> Path:
    tool_dir = _tool_dir(root)
    node_modules = tool_dir / "node_modules"
    if not node_modules.exists():
        subprocess.run(
            ["npm", "install"],
            cwd=str(tool_dir),
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    return tool_dir


def extract_web_reference_payload(
    *,
    root: Path,
    url: str,
    output_dir: Path,
) -> dict:
    tool_dir = ensure_reference_web_tool(root)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "extract.json"
    screenshot_path = output_dir / "reference.png"
    subprocess.run(
        [
            "node",
            str((tool_dir / "extract.js").resolve()),
            "--url",
            url,
            "--out",
            str(json_path.resolve()),
            "--screenshot",
            str(screenshot_path.resolve()),
        ],
        cwd=str(tool_dir),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload["json_path"] = str(json_path)
    payload["screenshot_path"] = str(screenshot_path)
    return payload
