from pathlib import Path

import pytest

from specforge.compiler import Compiler
from specforge.errors import SpecForgeError
from specforge.model import (
    AssertionSpec, Expectation, Operation, Pattern, ProductIdentity, Provenance,
    RequirementInstance, RequirementStatus, VerificationSpec,
)


def test_conflicting_controls_are_reported_with_both_sources(monkeypatch, tmp_path: Path):
    # Exercise the public resolution conflict path with a deliberately conflicting
    # package assembled from the production calendar fixture.
    import shutil
    root = Path(__file__).parents[1]
    for name in ["knowledge", "products"]:
        shutil.copytree(root / name, tmp_path / name)
    requirement = tmp_path / "knowledge/security/1.1.0/requirements/SEC-003.yaml"
    requirement.write_text(
        "id: SEC-003\nversion: '1.0.0'\nstatement: Authentication is forbidden.\n"
        "expectation: {control: authentication, operator: equals, value: forbidden}\n"
        "verifications:\n  - {id: TEST-SEC-003, adapter: http_request, setup: public, assertion: {response_status: 200}}\n"
        "source: {type: internal_policy, document: conflicting-policy, version: '1.0.0', section: public}\n",
        encoding="utf-8",
    )
    rule = tmp_path / "knowledge/security/1.1.0/rules/conflict.yaml"
    rule.write_text(
        "id: security/conflict\nversion: '1.0.0'\nwhen: {fact: {subject: '$operation', predicate: returns, object: Event}}\n"
        "then: {requirement: SEC-003, target: '$operation'}\n"
        "source: {type: internal_policy, document: conflicting-policy, version: '1.0.0', section: public}\n",
        encoding="utf-8",
    )
    pattern = tmp_path / "knowledge/fastapi-react/1.0.0/patterns/conflict.yaml"
    pattern.write_text(
        "id: fastapi/public\nversion: '1.0.0'\nsatisfies: [SEC-003]\nstack: fastapi-react\n"
        "controls: {authentication: forbidden}\nverifications: [TEST-SEC-003]\nartifacts: [backend/app.py]\n",
        encoding="utf-8",
    )
    with pytest.raises(SpecForgeError) as caught:
        Compiler(tmp_path).resolve("products/calendar", write=False)
    message = str(caught.value)
    assert caught.value.code == "SF1301"
    assert "SEC-001" in message and "SEC-003" in message
    assert "security/authenticated-personal-data@1.1.0" in message
    assert "security/conflict@1.0.0" in message
    assert "security@1.1.0" in message
