from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

def read_yaml(path: Path) -> Any:
    # PyYAML belongs only to the explicit legacy migration boundary. Keeping the
    # import local means the standard RDF/RIF compiler path does not load or
    # require the proprietary authoring parser.
    try:
        import yaml
    except ImportError as exc:
        raise ValueError(
            "legacy YAML migration requires the optional 'specforge[legacy]' dependency"
        ) from exc

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def pretty_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def content_hash(data: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def directory_hash(path: Path) -> str:
    digest = hashlib.sha256()
    for child in sorted(item for item in path.rglob("*") if item.is_file()):
        digest.update(child.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(child.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def write_if_changed(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.write_text(content, encoding="utf-8", newline="\n")
