from __future__ import annotations

import json
from pathlib import Path
import re

from .io import read_yaml


def load_academy_glossary(root: Path) -> dict[str, str]:
    path = root / "training-prototype" / "app.js"
    if not path.exists():
        return {}
    glossary: dict[str, str] = {}
    source = path.read_text(encoding="utf-8")
    for block in re.findall(r"terms:\s*(\[\[.*?\]\])", source):
        try:
            terms = json.loads(block)
        except json.JSONDecodeError:
            continue
        for term, definition in terms:
            glossary.setdefault(term, definition)
    additions = path.with_name("glossary.json")
    if additions.exists():
        for term, definition in json.loads(additions.read_text(encoding="utf-8")).items():
            glossary.setdefault(term, definition)
    return dict(sorted(glossary.items(), key=lambda item: (-len(item[0]), item[0].casefold())))


def load_product_glossary(product_file: Path) -> dict[str, str]:
    path = product_file.with_name("glossary.yaml")
    if not path.exists():
        return {}
    glossary = read_yaml(path)
    return dict(sorted(glossary.items(), key=lambda item: (-len(item[0]), item[0].casefold())))
