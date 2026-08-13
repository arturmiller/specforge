from __future__ import annotations

import fnmatch
import difflib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import Field

from .agents.protocol import AgentAdapter, AgentExecution, AgentRunStatus
from .io import content_hash, file_hash, pretty_json, write_if_changed
from .model import StrictModel
from .v2 import AgentWorkOrder


class WorkOrderStatus(str, Enum):
    PLANNED = "PLANNED"
    READY = "READY"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class FileChange(StrictModel):
    path: str
    kind: str
    before_hash: str | None = None
    after_hash: str | None = None


class GateResult(StrictModel):
    id: str
    result: str
    expected: dict[str, Any]
    observed: dict[str, Any]


class AgentRunResult(StrictModel):
    schema_version: str = "2"
    id: str
    work_order_id: str
    work_order_hash: str
    base_revision: str
    provider: str
    model: str
    agent_version: str
    started_at: str
    ended_at: str
    status: AgentRunStatus
    work_order_status: WorkOrderStatus
    exit_code: int | None
    summary: str
    changes: list[FileChange]
    diff_hash: str
    permission_violations: list[str]
    gates: list[GateResult]
    tool_activity: list[str] = Field(default_factory=list)


def snapshot(workspace: Path) -> dict[str, str]:
    ignored = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules", "dist"}
    return {
        path.relative_to(workspace).as_posix(): file_hash(path)
        for path in sorted(workspace.rglob("*"))
        if path.is_file() and not any(part in ignored for part in path.relative_to(workspace).parts)
    }


def snapshot_bytes(workspace: Path) -> dict[str, bytes]:
    ignored = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules", "dist"}
    return {
        path.relative_to(workspace).as_posix(): path.read_bytes()
        for path in sorted(workspace.rglob("*"))
        if path.is_file() and not any(part in ignored for part in path.relative_to(workspace).parts)
    }


def render_patch(before: dict[str, bytes], after: dict[str, bytes], changes: list[FileChange]) -> str:
    lines: list[str] = []
    for change in changes:
        try:
            old = before.get(change.path, b"").decode("utf-8").splitlines(keepends=True)
            new = after.get(change.path, b"").decode("utf-8").splitlines(keepends=True)
        except UnicodeDecodeError:
            lines.append(f"Binary file changed: {change.path}\n")
            continue
        lines.extend(difflib.unified_diff(old, new, fromfile=f"a/{change.path}", tofile=f"b/{change.path}"))
    return "".join(lines)


def changes_between(before: dict[str, str], after: dict[str, str]) -> list[FileChange]:
    changes: list[FileChange] = []
    for path in sorted(set(before) | set(after)):
        if path not in before:
            changes.append(FileChange(path=path, kind="created", after_hash=after[path]))
        elif path not in after:
            changes.append(FileChange(path=path, kind="removed", before_hash=before[path]))
        elif before[path] != after[path]:
            changes.append(FileChange(path=path, kind="modified", before_hash=before[path], after_hash=after[path]))
    return changes


def _matches(path: str, pattern: str) -> bool:
    normalized = pattern.replace("\\", "/")
    if normalized.endswith("/**") and path.startswith(normalized[:-3].rstrip("/") + "/"):
        return True
    return fnmatch.fnmatchcase(path, normalized)


def permission_violations(changes: list[FileChange], work_order: AgentWorkOrder) -> list[str]:
    permissions = work_order.permissions
    violations = []
    for change in changes:
        allowed = any(_matches(change.path, pattern) for pattern in permissions.may_modify)
        protected = any(_matches(change.path, pattern) for pattern in permissions.read_only + permissions.must_not_modify)
        if not allowed or protected:
            violations.append(change.path)
    return sorted(violations)


class RunManager:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def execute(
        self,
        work_order: AgentWorkOrder,
        adapter: AgentAdapter,
        configuration: dict[str, str] | None = None,
        gate_runner: "DeterministicGates | None" = None,
    ) -> AgentRunResult:
        started = datetime.now(timezone.utc)
        before_content = snapshot_bytes(self.root)
        before = {path: content_hash(data.hex()) for path, data in before_content.items()}
        execution = adapter.execute(work_order, self.root, configuration or {})
        after_content = snapshot_bytes(self.root)
        after = {path: content_hash(data.hex()) for path, data in after_content.items()}
        changes = changes_between(before, after)
        violations = permission_violations(changes, work_order)
        permission_gate = GateResult(
            id="permission",
            result="FAIL" if violations else "PASS",
            expected={"changed_paths": "MAY_MODIFY only"},
            observed={"violations": violations},
        )
        status = AgentRunStatus.PERMISSION_VIOLATION if violations else execution.status
        gates = [permission_gate]
        if status == AgentRunStatus.COMPLETED:
            resolved_path = self.root / "generated" / work_order.product["id"] / "resolved-spec.json"
            if resolved_path.exists():
                from .generation import generate_product
                from .model import ResolvedSpec

                resolved = ResolvedSpec.model_validate_json(resolved_path.read_text(encoding="utf-8"))
                generate_product(self.root, resolved)
            gates.extend((gate_runner or DeterministicGates()).run(self.root, work_order))
        accepted = status == AgentRunStatus.COMPLETED and all(gate.result == "PASS" for gate in gates)
        run_id = f"run-{started.strftime('%Y%m%dT%H%M%S%fZ')}-{work_order.content_hash[-8:]}"
        result = AgentRunResult(
            id=run_id,
            work_order_id=work_order.id,
            work_order_hash=work_order.content_hash,
            base_revision=work_order.product.get("base_revision", ""),
            provider=execution.provider,
            model=execution.model,
            agent_version=execution.version,
            started_at=started.isoformat(),
            ended_at=datetime.now(timezone.utc).isoformat(),
            status=status,
            work_order_status=WorkOrderStatus.ACCEPTED if accepted else WorkOrderStatus.REJECTED,
            exit_code=execution.exit_code,
            summary=execution.summary,
            changes=changes,
            diff_hash=content_hash([change.model_dump(mode="json") for change in changes]),
            permission_violations=violations,
            gates=gates,
            tool_activity=execution.tool_activity,
        )
        directory = self.root / "runs" / work_order.product["id"] / run_id
        write_if_changed(directory / "work-order.json", pretty_json(work_order.model_dump(mode="json")))
        write_if_changed(directory / "agent-result.json", pretty_json(result.model_dump(mode="json")))
        write_if_changed(directory / "changes.patch", render_patch(before_content, after_content, changes))
        write_if_changed(directory / "gate-results.json", pretty_json([gate.model_dump(mode="json") for gate in result.gates]))
        evidence = {
            "schema_version": "2",
            "work_order_id": work_order.id,
            "work_order_hash": work_order.content_hash,
            "agent_run_id": result.id,
            "agent_adapter": result.provider,
            "model": result.model,
            "base_revision": result.base_revision,
            "diff_hash": result.diff_hash,
            "gates": [gate.model_dump(mode="json") for gate in result.gates],
            "result": result.work_order_status.value,
        }
        write_if_changed(directory / "evidence.json", pretty_json(evidence))
        return result


class DeterministicGates:
    """Run the mandatory V2 acceptance gates without agent judgement."""

    def run(self, root: Path, work_order: AgentWorkOrder) -> list[GateResult]:
        product = work_order.product["id"]
        generated = root / "generated" / product
        app = generated / "app"
        results: list[GateResult] = []

        structured = [
            generated / "resolved-spec.json",
            generated / "implementation-manifest.json",
            generated / "implementation-plan.json",
            generated / "impact-scope.json",
        ]
        invalid: list[str] = []
        parsed: dict[Path, Any] = {}
        for path in structured:
            try:
                parsed[path] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                invalid.append(path.relative_to(root).as_posix())
        manifest_path = generated / "implementation-manifest.json"
        if manifest_path in parsed:
            for item in parsed[manifest_path].get("files", []):
                path = app / item.get("path", "")
                if item.get("classification") != "AGENT_MANAGED" or not path.is_file() or file_hash(path) != item.get("hash"):
                    invalid.append(path.relative_to(root).as_posix())
        results.append(GateResult(id="schema", result="PASS" if not invalid else "FAIL", expected={"valid_json": len(structured)}, observed={"invalid": invalid}))

        compile_result = subprocess.run(
            [str(Path(__import__("sys").executable)), "-m", "compileall", "-q", str(app / "backend")],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        build_ok = compile_result.returncode == 0
        build_observed: dict[str, Any] = {"backend_exit_code": compile_result.returncode}
        frontend = app / "frontend"
        if (frontend / "package.json").exists():
            npm_command = shutil.which("npm.cmd") or shutil.which("npm")
            if npm_command:
                npm = subprocess.run([npm_command, "run", "build"], cwd=frontend, capture_output=True, text=True, check=False, shell=False)
                build_ok &= npm.returncode == 0
                build_observed["frontend_exit_code"] = npm.returncode
            else:
                build_ok = False
                build_observed["frontend_error"] = "npm executable not found"
        results.append(GateResult(id="build", result="PASS" if build_ok else "FAIL", expected={"exit_code": 0}, observed=build_observed))

        forbidden_markers = []
        for path in app.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".ts", ".tsx"} and "node_modules" not in path.parts:
                text = path.read_text(encoding="utf-8")
                if "# type: ignore" in text or "@ts-ignore" in text:
                    forbidden_markers.append(path.relative_to(root).as_posix())
        results.append(GateResult(id="static", result="PASS" if not forbidden_markers else "FAIL", expected={"suppression_markers": []}, observed={"suppression_markers": forbidden_markers}))

        try:
            from .verification import validate_product

            validation = validate_product(root, f"products/{product}")
            requirement_ok = validation.passed
            verification_observed = {"summary": validation.summary}
        except Exception as exc:  # a verifier crash is a deterministic gate failure
            requirement_ok = False
            verification_observed = {"error": f"{type(exc).__name__}: {exc}"}
        results.append(GateResult(id="requirement", result="PASS" if requirement_ok else "FAIL", expected={"mandatory": work_order.verification_plan.mandatory}, observed=verification_observed))
        results.append(GateResult(id="regression", result="PASS" if requirement_ok else "FAIL", expected={"previously_relevant": "PASS"}, observed=verification_observed))

        evidence_path = root / "evidence" / product / "latest.json"
        evidence_ok = False
        evidence_observed: dict[str, Any]
        try:
            bundle = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence_ok = bundle.get("resolved_spec_hash") == work_order.product.get("resolved_spec_after")
            evidence_observed = {"resolved_spec_hash": bundle.get("resolved_spec_hash")}
        except (OSError, ValueError) as exc:
            evidence_observed = {"error": str(exc)}
        results.append(GateResult(id="evidence", result="PASS" if evidence_ok else "FAIL", expected={"resolved_spec_hash": work_order.product.get("resolved_spec_after")}, observed=evidence_observed))
        return results


class RepairWorkOrder(StrictModel):
    schema_version: str = "2"
    original_work_order: AgentWorkOrder
    original_run_id: str
    failed_gates: list[GateResult]
    current_diff_hash: str
    remaining_attempts: int


def create_repair_order(original: AgentWorkOrder, run: AgentRunResult, attempt: int) -> RepairWorkOrder:
    remaining = original.limits.max_repair_runs - attempt
    if remaining < 0:
        raise ValueError("repair limit exhausted")
    return RepairWorkOrder(
        original_work_order=original,
        original_run_id=run.id,
        failed_gates=[gate for gate in run.gates if gate.result == "FAIL"],
        current_diff_hash=run.diff_hash,
        remaining_attempts=remaining,
    )
