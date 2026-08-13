from __future__ import annotations

import json
import os
import socket
import subprocess
import shutil
import sys
import time
from pathlib import Path

from specforge.compiler import Compiler
from specforge.generation import generate_product
from specforge.reporting import create_report
from specforge.verification import validate_product


ROOT = Path(__file__).parents[1]


def copy_project(tmp_path: Path) -> Path:
    for name in ["knowledge", "products"]:
        shutil.copytree(ROOT / name, tmp_path / name)
    shutil.copytree(
        ROOT / "generated/calendar/app",
        tmp_path / "generated/calendar/app",
        ignore=shutil.ignore_patterns("node_modules", "dist", "__pycache__"),
    )
    return tmp_path


def test_generation_and_validation_produce_complete_evidence(tmp_path: Path):
    root = copy_project(tmp_path)
    resolved = Compiler(root).resolve("products/calendar")
    manifest_path = generate_product(root, resolved)
    result = validate_product(root, "products/calendar")
    assert result.passed
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    evidence = json.loads(result.evidence_path.read_text(encoding="utf-8"))
    assert manifest["resolved_spec_hash"] == resolved.content_hash
    assert len(evidence["entries"]) == len(resolved.requirements) == 18
    assert set(evidence["requirement_statuses"].values()) == {"VERIFIED"}
    assert all(entry["git_commit"] and entry["resolved_spec_hash"] == resolved.content_hash for entry in evidence["entries"])
    assert all("@operation:" in entry["verification_id"] for entry in evidence["entries"])
    assert all(entry["verification_definition"].startswith("TEST-") for entry in evidence["entries"])


def test_generation_is_byte_deterministic(tmp_path: Path):
    root = copy_project(tmp_path)
    resolved = Compiler(root).resolve("products/calendar")
    manifest = generate_product(root, resolved)
    first = {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted((root / "generated/calendar").rglob("*")) if path.is_file()}
    generate_product(root, resolved)
    second = {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted((root / "generated/calendar").rglob("*")) if path.is_file()}
    assert manifest.exists()
    assert second == first
    for path, content in second.items():
        if path.endswith(".json") and "/app/" not in path:
            text = content.decode("utf-8")
            assert text == json.dumps(json.loads(text), ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def test_generated_api_starts_as_a_real_local_server(tmp_path: Path):
    import httpx
    root = copy_project(tmp_path)
    resolved = Compiler(root).resolve("products/calendar")
    generate_product(root, resolved)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "generated/calendar/app/backend")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "calendar_app:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=tmp_path,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        response = None
        for _ in range(40):
            try:
                response = httpx.get(f"http://127.0.0.1:{port}/openapi.json", timeout=0.5)
                break
            except httpx.TransportError:
                time.sleep(0.1)
        assert response is not None and response.status_code == 200
        anonymous = httpx.get(f"http://127.0.0.1:{port}/events/00000000-0000-0000-0000-000000000000")
        assert anonymous.status_code == 401
    finally:
        process.terminate()
        process.wait(timeout=10)


def test_removed_read_authentication_fails_sec_001_with_observation(tmp_path: Path):
    root = copy_project(tmp_path)
    resolved = Compiler(root).resolve("products/calendar")
    generate_product(root, resolved)
    app_path = root / "generated/calendar/app/backend/calendar_app/app.py"
    source = app_path.read_text(encoding="utf-8")
    source = source.replace(
        "def read_event(event_id: UUID, user: UUID = Depends(current_user), db: Session = Depends(session)) -> EventRow:\n        return owned_event(event_id, user, db)",
        "def read_event(event_id: UUID, db: Session = Depends(session)) -> EventRow:\n        return owned_event(event_id, DEMO_TOKENS[\"demo-token-alice\"], db)",
    )
    app_path.write_text(source, encoding="utf-8")
    result = validate_product(root, "products/calendar")
    assert not result.passed
    assert "SEC-001@operation.read_event FAILED" in result.summary
    assert "TEST-SEC-001" in result.summary
    assert "'response_status': 401" in result.summary
    assert "'response_status': 404" in result.summary


def test_frontend_color_change_does_not_change_resolved_spec_hash(tmp_path: Path):
    root = copy_project(tmp_path)
    compiler = Compiler(root)
    before = compiler.resolve("products/calendar")
    generate_product(root, before)
    css = root / "generated/calendar/app/frontend/src/styles.css"
    css.write_text(css.read_text(encoding="utf-8").replace("#16833e", "#0067c0"), encoding="utf-8")
    after = compiler.resolve("products/calendar")
    assert after.content_hash == before.content_hash


def test_report_is_scoped_and_uses_matching_evidence(tmp_path: Path):
    root = copy_project(tmp_path)
    resolved = Compiler(root).resolve("products/calendar")
    generate_product(root, resolved)
    validate_product(root, "products/calendar")
    report = create_report(root, "products/calendar").read_text(encoding="utf-8")
    assert "makes no general legal or regulatory compliance claim" in report
    assert "SEC-001@operation.read_event" in report
    assert "**VERIFIED**" in report
    assert resolved.content_hash in report


def test_report_rejects_evidence_from_an_old_resolved_spec(tmp_path: Path):
    root = copy_project(tmp_path)
    resolved = Compiler(root).resolve("products/calendar")
    generate_product(root, resolved)
    validate_product(root, "products/calendar")
    product = root / "products/calendar/product.yaml"
    product.write_text(product.read_text(encoding="utf-8").replace('version: "1.0.0"}', 'version: "1.0.1"}'), encoding="utf-8")
    import pytest
    with pytest.raises(RuntimeError, match="stale evidence"):
        create_report(root, "products/calendar")


def test_knowledge_content_change_changes_resolved_hash(tmp_path: Path):
    root = copy_project(tmp_path)
    compiler = Compiler(root)
    before = compiler.resolve("products/calendar").content_hash
    requirement = root / "knowledge/security/1.0.0/requirements/SEC-001.yaml"
    requirement.write_text(requirement.read_text(encoding="utf-8").replace("authenticated access", "verified authenticated access"), encoding="utf-8")
    after = compiler.resolve("products/calendar").content_hash
    assert after != before
