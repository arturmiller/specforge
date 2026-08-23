from __future__ import annotations

from pathlib import Path

def load_academy_glossary(root: Path) -> dict[str, str]:
    path = root / "training-prototype" / "glossary.ttl"
    if not path.exists():
        return {}
    from .rdf_authoring import load_skos_glossary

    glossary = load_skos_glossary(path)
    return dict(sorted(glossary.items(), key=lambda item: (-len(item[0]), item[0].casefold())))


def load_product_glossary(product_file: Path) -> dict[str, str]:
    rdf_path = product_file.with_name("glossary.ttl")
    if not rdf_path.exists():
        return {}
    from .rdf_authoring import load_skos_glossary

    return load_skos_glossary(rdf_path)
