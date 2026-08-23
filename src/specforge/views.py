from __future__ import annotations

from pathlib import Path

from .semantic import SemanticDataset


VIEW_VERSION = "1.0.0"
VIEW_DIRECTORY = Path(__file__).with_name("sparql_views")


def available_views() -> tuple[str, ...]:
    """Return the names of versioned, standard SPARQL query resources."""
    return tuple(path.stem for path in sorted(VIEW_DIRECTORY.glob("*.rq")))


def load_view(name: str) -> str:
    """Load a stored SPARQL 1.1 query; names cannot escape the resource directory."""
    if name not in available_views():
        raise KeyError(f"unknown SPARQL view {name!r}@{VIEW_VERSION}")
    return (VIEW_DIRECTORY / f"{name}.rq").read_text(encoding="utf-8")


def query_view(dataset: SemanticDataset, name: str):
    return dataset.query(load_view(name))
