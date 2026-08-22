import json
from pathlib import Path

import pytest
from typer.testing import CliRunner
from rdflib import BNode, Literal
from rdflib.namespace import DCAT, DCTERMS, PROV, RDF, SH, SKOS

from specforge.compiler import Compiler
from specforge.cli import app
from specforge.datalog import Atom, DatalogEngine, DatalogRule, Equality, condition_alternatives, validate_rule
from specforge.errors import SpecForgeError
from specforge.semantic import GRAPH_NAMES, SF, SemanticDataset
from specforge.shacl import validate_dataset
from specforge.rif import export_rules, import_rules
from specforge.views import query_view


ROOT = Path(__file__).parents[1]
PRODUCT = "products/calendar"


def test_resolve_emits_canonical_semantic_artifacts() -> None:
    resolved = Compiler(ROOT).resolve(PRODUCT)
    output = ROOT / "generated/calendar"

    assert resolved.hash_algorithm == "rdfc-1.0+sha256"
    assert resolved.conforms_to == "https://specforge.dev/vocab/1.0.0"
    assert resolved.content_hash.startswith("sha256:")
    for name in [
        "resolved-spec.jsonld", "resolved-spec.nq", "resolved-spec.trig",
        "provenance.jsonld", "shacl-report.ttl",
    ]:
        assert (output / name).is_file()
    semantic = Compiler(ROOT).semantic_dataset(PRODUCT)
    assert any(semantic.dataset.quads((None, SF.contentHash, Literal(resolved.content_hash), GRAPH_NAMES["provenance"])))


def test_dataset_has_named_graphs_dcat_skos_prov_and_shacl() -> None:
    semantic = Compiler(ROOT).semantic_dataset(PRODUCT)
    graph_ids = {graph.identifier for graph in semantic.dataset.graphs()}

    assert set(GRAPH_NAMES.values()) <= graph_ids
    assert any(semantic.dataset.quads((None, RDF.type, DCAT.Dataset, None)))
    assert any(semantic.dataset.quads((None, RDF.type, SKOS.Concept, None)))
    assert any(semantic.dataset.quads((None, RDF.type, PROV.Activity, GRAPH_NAMES["provenance"])))
    assert validate_dataset(semantic).conforms
    assert not any(
        isinstance(term, BNode)
        for quad in semantic.dataset.quads((None, None, None, GRAPH_NAMES["evidence"]))
        for term in quad[:3]
    )


def test_pydantic_and_shacl_reject_an_operation_without_acted_on_resource() -> None:
    from specforge.model import ProductSpec

    with pytest.raises(ValueError):
        ProductSpec.model_validate({
            "schema_version": "2",
            "product": {"id": "x", "version": "1", "stack": "test"},
            "entities": [{"id": "Thing", "fields": [{"name": "id", "type": "UUID"}]}],
            "operations": [{"id": "read", "action": "read", "returns": "Thing", "actor": "Thing", "scope": "own"}],
            "knowledge_dependencies": {},
        })

    semantic = Compiler(ROOT).semantic_dataset(PRODUCT)
    operation = semantic.iris.operation("calendar", "read_event")
    product_graph = semantic.graph("product")
    product_graph.remove((operation, SF.actsOn, None))
    assert not validate_dataset(semantic).conforms


def test_package_relationships_are_queryable_with_sparql() -> None:
    semantic = Compiler(ROOT).semantic_dataset(PRODUCT)
    rows = list(semantic.query("""
        SELECT ?package ?domain ?implementation WHERE {
          GRAPH ?g {
            ?package sf:bindsDomain ?domain ;
                     sf:bindsImplementation ?implementation .
          }
        }
    """))

    assert len(rows) == 1
    assert str(rows[0].package).endswith("/calendar-fastapi-react/1.0.0")
    assert str(rows[0].domain).endswith("/calendar/1.1.0")
    assert str(rows[0].implementation).endswith("/fastapi-react/1.0.0")


def test_requirement_trace_is_queryable_from_rule_to_pattern_and_verification() -> None:
    semantic = Compiler(ROOT).semantic_dataset(PRODUCT)
    applications = list(query_view(semantic, "rule-applications"))
    requirements = list(query_view(semantic, "requirements"))
    privacy = "PRIVACY-001%40operation.read_event"

    assert any(privacy in str(row.instance) and "minimize-personal-data" in str(row.rule) for row in applications)
    assert any(
        privacy in str(row.instance)
        and "declared-response-schema" in str(row.pattern)
        and str(row.verification).endswith("TEST-PRIVACY-001")
        for row in requirements
    )


def test_remote_sparql_service_is_rejected() -> None:
    semantic = SemanticDataset()
    with pytest.raises(ValueError, match="SF3002"):
        semantic.query("SELECT * WHERE { SERVICE <https://example.org> { ?s ?p ?o } }")


def test_rdfc_hash_is_independent_of_triple_order() -> None:
    first, second = SemanticDataset(), SemanticDataset()
    triples = [(SF.a, SF.value, Literal("1")), (SF.b, DCTERMS.title, Literal("B"))]
    for triple in triples:
        first.graph("product").add(triple)
    for triple in reversed(triples):
        second.graph("product").add(triple)
    assert first.content_hash() == second.content_hash()


def test_nquads_roundtrip_preserves_semantic_hash(tmp_path: Path) -> None:
    original = Compiler(ROOT).semantic_dataset(PRODUCT)
    path = tmp_path / "resolved.nq"
    path.write_text(original.serialize_nquads(), encoding="utf-8")
    parsed = SemanticDataset.parse(path)
    assert parsed.content_hash() == original.content_hash()


def test_jsonld_roundtrip_preserves_semantic_hash(tmp_path: Path) -> None:
    original = Compiler(ROOT).semantic_dataset(PRODUCT)
    path = tmp_path / "resolved.jsonld"
    path.write_text(original.serialize_jsonld(), encoding="utf-8")
    parsed = SemanticDataset.parse(path)
    assert parsed.content_hash() == original.content_hash()


def test_rdf_adapter_rejects_remote_contexts_and_swrl(tmp_path: Path) -> None:
    remote = tmp_path / "remote.jsonld"
    remote.write_text('{"@context":"https://example.org/context","@id":"urn:x"}', encoding="utf-8")
    with pytest.raises(ValueError, match="SF3004"):
        SemanticDataset.parse(remote)
    swrl = tmp_path / "rule.ttl"
    swrl.write_text("<urn:r> a <http://www.w3.org/2003/11/swrl#Imp> .", encoding="utf-8")
    with pytest.raises(ValueError, match="SF3005"):
        SemanticDataset.parse(swrl)
    owl = tmp_path / "ontology.ttl"
    owl.write_text("@prefix owl: <http://www.w3.org/2002/07/owl#> . <urn:X> a owl:Class .", encoding="utf-8")
    with pytest.raises(ValueError, match="SF3007"):
        SemanticDataset.parse(owl)


def test_positive_datalog_reaches_fixpoint_independent_of_rule_order() -> None:
    rules = [
        DatalogRule("ancestor", "1", Atom("ancestor", ("$x", "$z")), (
            Atom("parent", ("$x", "$y")), Atom("ancestor", ("$y", "$z")),
        )),
        DatalogRule("base", "1", Atom("ancestor", ("$x", "$y")), (
            Atom("parent", ("$x", "$y")),
        )),
    ]
    results = []
    for ordering in (rules, list(reversed(rules))):
        engine = DatalogEngine()
        engine.add_fact("parent", ("a", "b"), fact_id="f1")
        engine.add_fact("parent", ("b", "c"), fact_id="f2")
        engine.evaluate(ordering)
        results.append([row.values for row in engine.rows("ancestor")])
    assert results[0] == results[1] == [("a", "b"), ("a", "c"), ("b", "c")]


def test_datalog_rejects_unsafe_builtin_and_head_variables() -> None:
    with pytest.raises(SpecForgeError, match="positively bound"):
        validate_rule(DatalogRule("unsafe", "1", Atom("out", ("$x",)), (
            Equality("$x", "value"),
        )))


def test_positive_datalog_rejects_closed_world_negation() -> None:
    from specforge.model import Condition

    condition = Condition.model_validate({
        "not": {"fact": {"subject": "$x", "predicate": "active", "object": True}}
    })
    with pytest.raises(SpecForgeError, match="SF1203"):
        condition_alternatives(condition, "no-negation")


def test_supported_datalog_roundtrips_through_rif_core_xml() -> None:
    rule = DatalogRule("copy", "1", Atom("out", ("$x",)), (Atom("source", ("$x", "ok")),))
    assert import_rules(export_rules([rule])) == [rule]


def test_rif_import_rejects_external_imports() -> None:
    document = (
        '<rif:Document xmlns:rif="http://www.w3.org/2007/rif#">'
        '<rif:directive><rif:Import><rif:location>https://example.org/rules</rif:location>'
        '</rif:Import></rif:directive></rif:Document>'
    )
    with pytest.raises(SpecForgeError, match="SF3202"):
        import_rules(document)


def test_semantic_cli_exposes_sparql_and_rif(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(ROOT)
    query = tmp_path / "packages.rq"
    query.write_text("SELECT ?p WHERE { GRAPH ?g { ?p a dcat:Dataset } } ORDER BY ?p", encoding="utf-8")
    runner = CliRunner()
    sparql = runner.invoke(app, ["sparql", PRODUCT, "--query", str(query)])
    assert sparql.exit_code == 0
    assert "calendar-fastapi-react/1.0.0" in sparql.stdout
    rif = runner.invoke(app, ["export-rif", PRODUCT])
    assert rif.exit_code == 0
    assert "<rif:Document" in rif.stdout
    semantic = Compiler(ROOT).semantic_dataset(PRODUCT)
    rdf = tmp_path / "resolved.jsonld"
    rdf.write_text(semantic.serialize_jsonld(), encoding="utf-8")
    checked = runner.invoke(app, ["rdf-check", str(rdf)])
    assert checked.exit_code == 0
    assert json.loads(checked.stdout)["conforms"] is True
