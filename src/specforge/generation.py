from __future__ import annotations

from pathlib import Path

from .io import file_hash, pretty_json, write_if_changed
from .model import ResolvedSpec


def generate_product(root: Path, resolved: ResolvedSpec) -> Path:
    """Record an existing agent-managed implementation.

    V2 deliberately has no application templates or rendering path.  The legacy
    function remains as a compatibility boundary for validation/reporting, but
    it never creates or overwrites application code.
    """
    output = root / "generated" / resolved.product.id / "app"
    if not output.is_dir():
        raise OSError(f"missing agent-managed implementation: {output}; use specforge implement")
    files: list[dict[str, str]] = []
    ignored = {"node_modules", "dist", "__pycache__"}
    for path in sorted(path for path in output.rglob("*") if path.is_file() and not any(part in ignored for part in path.relative_to(output).parts)):
        files.append({"path": path.relative_to(output).as_posix(), "hash": file_hash(path), "classification": "AGENT_MANAGED"})
    manifest = {
        "schema_version": "2",
        "product": resolved.product.model_dump(),
        "resolved_spec_hash": resolved.content_hash,
        "patterns": sorted({item.pattern for item in resolved.requirements if item.pattern}),
        "generation_mode": "agent_managed",
        "files": files,
    }
    manifest_path = root / "generated" / resolved.product.id / "implementation-manifest.json"
    write_if_changed(manifest_path, pretty_json(manifest))
    return manifest_path
