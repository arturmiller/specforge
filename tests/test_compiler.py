from pathlib import Path
import shutil

import pytest

from specforge.compiler import Compiler
from specforge.errors import SpecForgeError
from specforge.model import FactOrigin, PackageManifest
from specforge.rdf_authoring import load_requirements, migrate_legacy_product


ROOT = Path(__file__).parents[1]
PRODUCT = "products/calendar"


def test_calendar_resolves_declared_and_derived_requirements():
    result = Compiler(ROOT).resolve(PRODUCT)
    ids = [item.requirement for item in result.requirements]
    assert len(result.requirements) == 18
    assert {"PRODUCT-001", "PRODUCT-002", "PRODUCT-003", "PRODUCT-004", "SEC-001", "SEC-002", "PRIVACY-001", "DATA-001", "OBS-001", "PLATFORM-001"} <= set(ids)
    assert all(item.pattern for item in result.requirements)


def test_semantic_closure_classifies_event_as_containing_personal_data():
    result = Compiler(ROOT).resolve(PRODUCT)
    fact = next(item for item in result.facts if item.subject == "Event" and item.predicate == "contains_classification" and item.object == "PersonalData")
    assert fact.origin == FactOrigin.ONTOLOGY_DERIVED
    assert fact.derivation == "field-classification-propagation"
    assert len(fact.premises) == 2
    assert "PersonalDataSubject" in result.classifications["User"]


def test_operations_distinguish_acted_on_resource_from_response_type():
    result = Compiler(ROOT).resolve(PRODUCT, write=False)
    facts = {(fact.subject, fact.predicate, fact.object) for fact in result.facts}

    assert ("operation.read_event", "acts_on", "Event") in facts
    assert ("operation.read_event", "returns", "Event") in facts
    assert ("operation.delete_event", "acts_on", "Event") in facts
    assert not any(
        subject == "operation.delete_event" and predicate == "returns"
        for subject, predicate, _ in facts
    )


def test_security_uses_acted_on_resource_while_privacy_uses_response_type():
    result = Compiler(ROOT).resolve(PRODUCT, write=False)
    by_requirement = {
        requirement: {item.target for item in result.requirements if item.requirement == requirement}
        for requirement in ["SEC-001", "PRIVACY-001"]
    }

    assert by_requirement["SEC-001"] == {
        "operation.create_event",
        "operation.read_event",
        "operation.update_event",
        "operation.delete_event",
    }
    assert by_requirement["PRIVACY-001"] == {
        "operation.create_event",
        "operation.read_event",
        "operation.update_event",
    }


def test_product_stack_selects_patterns_from_implementation_package():
    result = Compiler(ROOT).resolve(PRODUCT, write=False)

    assert result.product.stack == "fastapi-react"
    assert all(item.pattern and item.pattern.startswith("fastapi/") for item in result.requirements)
    assert not list((ROOT / "knowledge").rglob("*.yaml"))
    assert (ROOT / "knowledge/fastapi-react/1.0.0/package.trig").exists()


def test_privacy_rule_resolves_for_a_non_calendar_product(tmp_path: Path):
    shutil.copytree(ROOT / "knowledge/privacy", tmp_path / "knowledge/privacy")
    shutil.copytree(ROOT / "knowledge/fastapi-react", tmp_path / "knowledge/fastapi-react")
    legacy = tmp_path / "legacy-product.yaml"
    legacy.write_text(
        """schema_version: "2"
product: {id: documents, version: "1.0.0", stack: fastapi-react}
entities:
  - {id: Account, fields: [{name: id, type: UUID}]}
  - id: Document
    fields:
      - {name: id, type: UUID}
      - {name: secret, type: Text, classification: PersonalData}
operations:
  - {id: read_document, action: read, acts_on: Document, returns: Document, actor: Account, scope: own}
declared_requirements: []
knowledge_dependencies: {fastapi-react: "1.0.0", privacy: "1.1.0"}
""",
        encoding="utf-8",
    )
    product = tmp_path / "products/documents/product.trig"
    migrate_legacy_product(legacy, product)

    result = Compiler(tmp_path).resolve("products/documents", write=False)

    privacy = next(item for item in result.requirements if item.requirement == "PRIVACY-001")
    assert privacy.target == "operation.read_document"
    assert privacy.pattern == "fastapi/declared-response-schema"
    assert {fact.object for fact in result.facts if fact.subject == "Document" and fact.predicate == "contains_classification"} == {"PersonalData"}


def test_unknown_product_stack_cannot_select_fastapi_patterns(tmp_path: Path):
    shutil.copytree(ROOT / "knowledge", tmp_path / "knowledge")
    shutil.copytree(ROOT / "products", tmp_path / "products")
    product = tmp_path / "products/calendar/product.trig"
    product.write_text(product.read_text(encoding="utf-8").replace("stack:fastapi-react", "stack:django"), encoding="utf-8")

    with pytest.raises(SpecForgeError) as caught:
        Compiler(tmp_path).resolve("products/calendar", write=False)

    assert caught.value.code == "SF1501"


def test_integration_manifest_requires_both_package_roles():
    with pytest.raises(ValueError, match="integration package must declare integrates"):
        PackageManifest.model_validate(
            {"name": "calendar-fastapi-react", "version": "1", "kind": "integration"}
        )


def test_integration_manifest_requires_exact_active_dependency_version(tmp_path: Path):
    shutil.copytree(ROOT / "knowledge", tmp_path / "knowledge")
    shutil.copytree(ROOT / "products", tmp_path / "products")
    manifest = tmp_path / "knowledge/calendar-fastapi-react/1.0.0/package.trig"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            'package/calendar/1.1.0',
            'package/calendar/9.9.9',
        ),
        encoding="utf-8",
    )

    with pytest.raises(SpecForgeError) as caught:
        Compiler(tmp_path).resolve("products/calendar", write=False)

    assert caught.value.code == "SF1006"
    assert "calendar@9.9.9" in str(caught.value)


def test_explain_has_full_security_derivation_and_verification():
    explanation = Compiler(ROOT).explain(PRODUCT, "SEC-001")
    assert explanation.count("Requirement SEC-001@1.0.0") == 1
    assert "applies to: 4 target(s)" in explanation
    assert "security/authenticated-personal-data@1.1.0" in explanation
    assert "Event contains_classification 'PersonalData'" in explanation
    assert "field-classification-propagation" not in explanation  # facts, not internal implementation details
    assert "TEST-SEC-001@operation:read_event (http_request)" in explanation
    assert "product.trig#/operations/read_event" in explanation


def test_explain_can_filter_by_typed_target():
    explanation = Compiler(ROOT).explain(PRODUCT, "SEC-001", target="operation:read_event")
    assert "applies to: 1 target(s)" in explanation
    assert "operation:read_event" in explanation
    assert "operation:create_event" not in explanation


@pytest.mark.parametrize(
    ("group_by", "expected"),
    [("target.type", "operation:"), ("rule", "security/authenticated-personal-data:"), ("resource", "Event:"), ("fact.action", "read:")],
)
def test_explain_groupings_are_generic_projections(group_by: str, expected: str):
    explanation = Compiler(ROOT).explain(PRODUCT, "SEC-001", group_by=group_by)
    assert f"Groups by {group_by}:" in explanation
    assert expected in explanation
    assert explanation.count("TEST-SEC-001@operation:read_event") == 1


def test_resolve_is_byte_deterministic():
    compiler = Compiler(ROOT)
    first = compiler.resolve(PRODUCT)
    first_bytes = (ROOT / "generated/calendar/resolved-spec.json").read_bytes()
    trace_bytes = (ROOT / "generated/calendar/trace.json").read_bytes()
    second = compiler.resolve(PRODUCT)
    assert second.content_hash == first.content_hash
    assert (ROOT / "generated/calendar/resolved-spec.json").read_bytes() == first_bytes
    assert (ROOT / "generated/calendar/trace.json").read_bytes() == trace_bytes


def test_generated_compiler_json_is_pretty_printed():
    Compiler(ROOT).resolve(PRODUCT)
    for path in sorted((ROOT / "generated/calendar").glob("*.json")):
        content = path.read_text(encoding="utf-8")
        assert content.endswith("\n")
        assert content == __import__("json").dumps(__import__("json").loads(content), ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def test_requirement_without_executable_verification_is_rejected(tmp_path: Path):
    path = tmp_path / "requirements.ttl"
    path.write_text(
        "@prefix sf: <https://specforge.dev/vocab/> .\n@prefix dcterms: <http://purl.org/dc/terms/> .\n"
        "<urn:bad> a sf:RequirementDefinition ; dcterms:identifier \"BAD\" ; dcterms:description \"vague\" ; sf:control \"x\" ; sf:operator \"equals\" .\n",
        encoding="utf-8",
    )
    with pytest.raises(SpecForgeError) as caught:
        load_requirements(path)
    assert caught.value.code == "SF3101"
    assert "verifiedBy" in str(caught.value)
