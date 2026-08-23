from pathlib import Path

import pytest

from specforge.compiler import Compiler
from specforge.errors import SpecForgeError
from specforge.datalog import Atom, DatalogRule
from specforge.rif import export_rules, import_rules
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
    requirement = tmp_path / "knowledge/security/1.1.0/requirements.ttl"
    requirement.write_text(
        requirement.read_text(encoding="utf-8") + """

# SEC-003 fordert absichtlich eine widersprüchliche öffentliche Authentifizierung.
requirement:SEC-003-1.0.0 a sf:RequirementDefinition ; dcterms:identifier "SEC-003" ; dcterms:hasVersion "1.0.0" ; dcterms:description "Authentication is forbidden." ; sf:control <https://specforge.dev/control/authentication> ; sf:operator <https://specforge.dev/operator/equals> ; sf:expectedValue "forbidden" ; sf:verifiedBy verification:TEST-SEC-003 ; prov:wasDerivedFrom source:conflicting-policy-public .

# Diese Verification beobachtet den absichtlich öffentlichen Testzugriff.
verification:TEST-SEC-003 a sf:Verification ; dcterms:identifier "TEST-SEC-003" ; sf:verificationAdapter <https://specforge.dev/verification-adapter/http_request> ; sf:setup "public" ; sf:mandatory true ; sf:assertion assertion:TEST-SEC-003 .

# Diese Assertion erwartet für den Konfliktfall einen erfolgreichen HTTP-Status.
assertion:TEST-SEC-003 a sf:AssertionSpec ; sf:responseStatus 200 .

# Diese Quelle bezeichnet die absichtlich widersprüchliche Testpolicy.
source:conflicting-policy-public a prov:Entity ; sf:sourceType "internal_policy" ; dcterms:identifier "conflicting-policy" ; dcterms:hasVersion "1.0.0" ; sf:sourceSection "public" .
""",
        encoding="utf-8",
    )
    package = tmp_path / "knowledge/security/1.1.0"
    metadata = package / "rules.ttl"
    metadata.write_text(metadata.read_text(encoding="utf-8") + """

# Diese Rule leitet absichtlich das widersprüchliche SEC-003 ab.
rule:security-conflict a sf:Rule ; dcterms:identifier "security/conflict" ; dcterms:hasVersion "1.0.0" ; prov:wasDerivedFrom source:security-conflict-public .

# Diese Quelle bezeichnet die absichtlich widersprüchliche Rule-Quelle.
source:security-conflict-public a prov:Entity ; sf:sourceType "internal_policy" ; dcterms:identifier "conflicting-policy" ; dcterms:hasVersion "1.0.0" ; sf:sourceSection "public" .
""",
        encoding="utf-8",
    )
    rif = package / "rules.rif.xml"
    rules = import_rules(rif)
    rules.append(DatalogRule("security/conflict#branch-1", "1.0.0", Atom("requires", ("$operation", "SEC-003")), (Atom("returns", ("$operation", "Event")),)))
    rif.write_text(export_rules(rules), encoding="utf-8")
    pattern = tmp_path / "knowledge/fastapi-react/1.0.0/patterns.ttl"
    pattern.write_text(
        pattern.read_text(encoding="utf-8") + """

# Dieses Pattern realisiert absichtlich die widersprüchliche öffentliche Authentifizierung.
pattern:fastapi-public a sf:ImplementationPattern ; dcterms:identifier "fastapi/public" ; dcterms:hasVersion "1.0.0" ; sf:usesStack stack:fastapi-react ; sf:satisfies requirement:SEC-003 ; sf:controlBinding binding:authentication-forbidden ; sf:verifiedBy verification:TEST-SEC-003 ; sf:artifact "backend/app.py" .

# Dieses Binding setzt Authentifizierung für den Konflikttest auf forbidden.
binding:authentication-forbidden a sf:ControlBinding ; sf:control <https://specforge.dev/control/authentication> ; sf:expectedValue "forbidden" .
""",
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
