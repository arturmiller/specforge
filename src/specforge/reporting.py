from __future__ import annotations

import json
from pathlib import Path

from .compiler import Compiler
from .io import write_if_changed


def create_report(root: Path, product: str) -> Path:
    resolved = Compiler(root).resolve(product)
    evidence_path = root / "evidence" / resolved.product.id / "latest.json"
    if not evidence_path.exists():
        raise RuntimeError("no evidence available; run specforge validate first")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence["resolved_spec_hash"] != resolved.content_hash:
        raise RuntimeError("stale evidence: resolved specification hash differs")
    statuses = evidence["requirement_statuses"]
    by_instance = {entry["requirement_instance"]: entry for entry in evidence["entries"]}
    lines = [
        f"# Requirement Verification Report: {resolved.product.id}@{resolved.product.version}",
        "",
        "## Scope",
        "",
        "This report covers only the formalized, machine-verifiable requirements listed below for the recorded software revision. It makes no general legal or regulatory compliance claim.",
        "",
        f"- Resolved specification: `{resolved.content_hash}`",
        f"- Software revision: `{evidence['software_revision']}`",
        "",
        "## Requirements",
        "",
        "| Requirement instance | Kind | Source | Status | Pattern | Verification | Evidence |",
        "|---|---|---|---|---|---|---|",
    ]
    for instance in resolved.requirements:
        entry = by_instance[instance.id]
        source = f"{instance.source.document}@{instance.source.version}#{instance.source.section}"
        lines.append(f"| `{instance.id}` | {instance.kind} | `{source}` | **{statuses[instance.id]}** | `{instance.pattern or '-'}` | `{entry['verification_id']}` | `{entry['id']}` |")
    lines += ["", "## Knowledge packages", ""]
    for name, package in resolved.knowledge.packages.items():
        lines.append(f"- `{name}@{package['version']}` — `{package['hash']}`")
    run_files = sorted((root / "runs" / resolved.product.id).glob("*/agent-result.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if run_files:
        run = json.loads(run_files[0].read_text(encoding="utf-8"))
        gate_summary = ", ".join(f"{gate['id']}={gate['result']}" for gate in run["gates"])
        lines += [
            "",
            "## Agent run",
            "",
            f"- Adapter: `{run['provider']}`",
            f"- Model: `{run['model']}`",
            f"- Work order: `{run['work_order_id']}` (`{run['work_order_hash']}`)",
            f"- Diff: `{run['diff_hash']}`",
            f"- Result: **{run['work_order_status']}**",
            f"- Gates: {gate_summary}",
        ]
    lines += ["", "## Evidence limitations", "", "A passing integration test proves the recorded observation for the specified input, application revision and execution environment. It is not a mathematical proof of all possible executions.", ""]
    report_path = root / "evidence" / resolved.product.id / "report.md"
    write_if_changed(report_path, "\n".join(lines))
    return report_path
