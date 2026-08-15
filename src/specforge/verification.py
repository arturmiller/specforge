from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from .compiler import Compiler
from .generation import generate_product
from .io import content_hash, pretty_json, write_if_changed
from .model import EvidenceEntry, RequirementStatus, ResolvedSpec, VerificationSpec


ALICE = {"Authorization": "Bearer demo-token-alice"}
BOB = {"Authorization": "Bearer demo-token-bob"}
VALID_EVENT = {
    "title": "Architecture review",
    "description": "Review SpecForge V2",
    "location": "Berlin",
    "start": "2026-08-10T09:00:00Z",
    "end": "2026-08-10T10:00:00Z",
}
@dataclass
class ValidationResult:
    passed: bool
    summary: str
    evidence_path: Path


def _revision(root: Path, app_dir: Path) -> str:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        commit = "unversioned"
    digest = hashlib.sha256()
    for path in sorted(p for p in app_dir.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        digest.update(path.relative_to(app_dir).as_posix().encode())
        digest.update(path.read_bytes())
    return f"{commit}+app.sha256.{digest.hexdigest()[:16]}"


def _load_app(root: Path):
    module_path = root / "generated/calendar/app/backend/calendar_app/app.py"
    if not module_path.exists():
        raise RuntimeError("generated calendar backend missing; run specforge generate products/calendar")
    name = "specforge_generated_calendar_app"
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module.create_app


def _client(create_app):
    return TestClient(create_app("sqlite://"))


def _create(client: TestClient, headers: dict[str, str] = ALICE) -> dict[str, Any]:
    response = client.post("/events", headers=headers, json=VALID_EVENT)
    if response.status_code != 201:
        raise RuntimeError(f"verification setup failed: create returned {response.status_code}: {response.text}")
    return response.json()


def expected_assertion(resolved: ResolvedSpec, target: str, verification: VerificationSpec) -> dict[str, Any]:
    assertion = verification.assertion.model_dump(mode="json", exclude_none=True)
    source = assertion.pop("response_fields_from", None)
    if source is None:
        return assertion
    operation_id = target.removeprefix("operation.")
    operation = next((item for item in resolved.operations if item.id == operation_id), None)
    if operation is None or operation.returns is None:
        raise RuntimeError(f"cannot derive response schema for {target}: operation has no response resource")
    entity = next((item for item in resolved.entities if item.id == operation.returns), None)
    if entity is None:
        raise RuntimeError(f"cannot derive response schema for {target}: unknown entity {operation.returns}")
    assertion["response_fields"] = sorted(field.response_name or field.name for field in entity.fields)
    assertion["required_response_fields"] = sorted(
        field.response_name or field.name for field in entity.fields if not field.optional
    )
    return assertion


def response_schema_matches(expected: dict[str, Any], observed: dict[str, Any]) -> bool:
    fields = set(observed.get("response_fields", []))
    return set(expected.get("required_response_fields", [])) <= fields <= set(expected["response_fields"])


def _observe(create_app, resolved: ResolvedSpec, requirement: str, target: str, verification: VerificationSpec) -> tuple[dict[str, Any], dict[str, Any], bool]:
    action = target.removeprefix("operation.").removesuffix("_event")
    expected = expected_assertion(resolved, target, verification)
    with _client(create_app) as client:
        if requirement.startswith("PRODUCT-"):
            if action == "create":
                response = client.post("/events", headers=ALICE, json=VALID_EVENT)
                observed = {"response_status": response.status_code, "stored_matches": response.status_code == 201 and response.json()["title"] == VALID_EVENT["title"]}
            else:
                event = _create(client)
                url = f"/events/{event['id']}"
                if action == "read":
                    response = client.get(url, headers=ALICE)
                    observed = {"response_status": response.status_code, "resource_matches": response.status_code == 200 and response.json()["id"] == event["id"]}
                elif action == "update":
                    changed = {**VALID_EVENT, "title": "Updated review"}
                    response = client.put(url, headers=ALICE, json=changed)
                    observed = {"response_status": response.status_code, "stored_matches": response.status_code == 200 and client.get(url, headers=ALICE).json()["title"] == "Updated review"}
                else:
                    response = client.delete(url, headers=ALICE)
                    after = client.get(url, headers=ALICE)
                    observed = {"response_status": response.status_code, "after_status": after.status_code}
        elif requirement == "SEC-001":
            url = "/events/00000000-0000-0000-0000-000000000000"
            if action == "create":
                response = client.post("/events", json=VALID_EVENT)
            elif action == "read":
                response = client.get(url)
            elif action == "update":
                response = client.put(url, json=VALID_EVENT)
            else:
                response = client.delete(url)
            observed = {"response_status": response.status_code}
        elif requirement == "SEC-002":
            event = _create(client)
            url = f"/events/{event['id']}"
            if action == "read":
                response = client.get(url, headers=BOB)
            elif action == "update":
                response = client.put(url, headers=BOB, json=VALID_EVENT)
            else:
                response = client.delete(url, headers=BOB)
            observed = {"response_status": response.status_code}
        elif requirement == "PRIVACY-001":
            if action == "create":
                response = client.post("/events", headers=ALICE, json=VALID_EVENT)
            else:
                event = _create(client)
                url = f"/events/{event['id']}"
                response = client.get(url, headers=ALICE) if action == "read" else client.put(url, headers=ALICE, json=VALID_EVENT)
            fields = sorted(response.json()) if response.status_code in {200, 201} else []
            observed = {"response_fields": fields}
        elif requirement == "DATA-001":
            invalid = {**VALID_EVENT, "end": VALID_EVENT["start"]}
            if action == "create":
                response = client.post("/events", headers=ALICE, json=invalid)
            else:
                event = _create(client)
                response = client.put(f"/events/{event['id']}", headers=ALICE, json=invalid)
            observed = {"response_status": response.status_code, "invariant": "end > start" if response.status_code == 422 else "not enforced"}
        elif requirement == "OBS-001":
            event = _create(client)
            client.get(f"/events/{event['id']}", headers=ALICE)
            events = [item["event"] for item in client.app.state.audit_events]
            observed = {"audit_event": "access_granted" if "access_granted" in events else "missing"}
        elif requirement == "PLATFORM-001":
            statuses = [client.get("/events/00000000-0000-0000-0000-000000000000", headers=ALICE).status_code for _ in range(61)]
            observed = {"max_requests_per_minute": 60 if statuses[:60] == [404] * 60 and statuses[60] == 429 else -1}
        else:
            raise RuntimeError(f"no verification adapter for {requirement}")
    if verification.adapter == "response_schema" and "response_fields" in expected:
        passed = response_schema_matches(expected, observed)
    else:
        passed = expected == observed
    return expected, observed, passed


def validate_product(root: Path, product: str) -> ValidationResult:
    compiler = Compiler(root)
    resolved = compiler.resolve(product)
    app_dir = root / "generated" / resolved.product.id / "app"
    manifest_path = root / "generated" / resolved.product.id / "implementation-manifest.json"
    if not app_dir.exists() or not manifest_path.exists():
        raise RuntimeError("generated implementation missing; run specforge generate first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("resolved_spec_hash") != resolved.content_hash:
        raise RuntimeError("stale generated implementation: run specforge generate again")
    create_app = _load_app(root)
    revision = _revision(root, app_dir)
    timestamp = datetime.now(timezone.utc).isoformat()
    entries: list[EvidenceEntry] = []
    status_by_instance: dict[str, str] = {}
    for instance in resolved.requirements:
        results = []
        for verification in instance.verifications:
            expected, observed, passed = _observe(create_app, resolved, instance.requirement, instance.target, verification)
            results.append(passed)
            display_target = Compiler._display_target(instance.target)
            verification_instance = f"{verification.id}@{display_target}"
            entry_id = "evidence-" + content_hash([instance.id, verification_instance, revision, resolved.content_hash]).split(":", 1)[1][:20]
            entries.append(EvidenceEntry(id=entry_id, requirement_instance=instance.id, verification_id=verification_instance, verification_definition=verification.id, verification_type=verification.adapter, expected=expected, observed=observed, result="PASS" if passed else "FAIL", git_commit=revision, resolved_spec_hash=resolved.content_hash, knowledge_packages=resolved.knowledge.packages, tool="specforge-verifier", tool_version="2.0.0", timestamp=timestamp))
        status_by_instance[instance.id] = RequirementStatus.VERIFIED.value if all(results) else RequirementStatus.FAILED.value
    bundle = {
        "schema_version": "2",
        "product": resolved.product.model_dump(),
        "software_revision": revision,
        "resolved_spec_hash": resolved.content_hash,
        "entries": [entry.model_dump(mode="json") for entry in entries],
        "requirement_statuses": dict(sorted(status_by_instance.items())),
    }
    evidence_path = root / "evidence" / resolved.product.id / "latest.json"
    write_if_changed(evidence_path, pretty_json(bundle))
    passed = all(entry.result == "PASS" for entry in entries)
    failed = [entry for entry in entries if entry.result == "FAIL"]
    lines = [f"Validation {'PASS' if passed else 'FAIL'}", f"Requirements: {len(status_by_instance)}, Evidence: {len(entries)}"]
    for entry in failed:
        lines.append(f"{entry.requirement_instance} FAILED via {entry.verification_id}: expected {entry.expected}, observed {entry.observed}")
    return ValidationResult(passed, "\n".join(lines), evidence_path)
