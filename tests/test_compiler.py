from pathlib import Path

import pytest

from specforge.compiler import Compiler
from specforge.errors import SpecForgeError
from specforge.model import Condition, Fact, FactOrigin


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


def test_explain_has_full_security_derivation_and_verification():
    explanation = Compiler(ROOT).explain(PRODUCT, "SEC-001")
    assert explanation.count("Requirement SEC-001@1.0.0") == 1
    assert "applies to: 4 target(s)" in explanation
    assert "security/authenticated-personal-data@1.0.0" in explanation
    assert "Event contains_classification 'PersonalData'" in explanation
    assert "field-classification-propagation" not in explanation  # facts, not internal implementation details
    assert "TEST-SEC-001@operation:read_event (http_request)" in explanation
    assert "product.yaml#/operations/read_event" in explanation


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


def test_rule_dsl_all_any_not_and_equals():
    compiler = Compiler(ROOT)
    facts = [Fact(id="f1", subject="x", predicate="kind", object="Event", origin=FactOrigin.DECLARED, provenance="test")]
    condition = Condition.model_validate({
        "all": [
            {"any": [{"fact": {"subject": "$x", "predicate": "kind", "object": "Event"}}, {"equals": [1, 2]}]},
            {"not": {"fact": {"subject": "$x", "predicate": "public", "object": True}}},
            {"equals": ["$x", "x"]},
        ]
    })
    matches = compiler.match(condition, facts, {})
    assert matches[0][0] == {"x": "x"}
    assert [fact.id for fact in matches[0][1]] == ["f1"]


def test_requirement_without_executable_verification_is_rejected(tmp_path: Path):
    path = tmp_path / "invalid.yaml"
    path.write_text("id: BAD\nversion: '1'\nstatement: vague\nexpectation: {control: x, operator: equals, value: y}\nverifications: []\nsource: {type: t, document: d, version: v, section: s}\n", encoding="utf-8")
    from specforge.model import RequirementDefinition
    with pytest.raises(SpecForgeError) as caught:
        Compiler(tmp_path).load_model(path, RequirementDefinition)
    assert caught.value.code == "SF1001"
    assert "SF1101" in str(caught.value)
