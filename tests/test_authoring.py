from pathlib import Path
import json
import re
import subprocess
import sys

from typer.testing import CliRunner
from rdflib import Dataset, Graph, Literal
from rdflib.namespace import DCAT, DCTERMS, PROV, RDF, SH

from specforge.authoring import lint_comments
from specforge.cli import app
from specforge.datalog import Atom, DatalogRule
from specforge.compiler import Compiler
from specforge.rdf_authoring import load_package_manifest, load_product, load_requirements, package_content_hash
from specforge.rif import export_prolog, export_rules, import_rules
from specforge.semantic import SF
from specforge.views import available_views, load_view


ROOT = Path(__file__).parents[1]


def test_learning_comment_linter_accepts_explained_trig(tmp_path: Path) -> None:
    source = tmp_path / "product.trig"
    source.write_text(
        """@prefix ex: <https://example.org/> .

# Dieser Graph enthält die Aussagen des Calendar-Produkts.
ex:productGraph {
  # Diese Operation liefert ein Event als Antwort zurück.
  ex:read_event ex:returns ex:Event .
}
""",
        encoding="utf-8",
    )

    assert lint_comments(source) == []


def test_learning_comment_linter_rejects_unexplained_rdf_and_query(tmp_path: Path) -> None:
    trig = tmp_path / "product.trig"
    trig.write_text("@prefix ex: <https://example.org/> .\nex:g {\nex:a ex:b ex:c .\n}\n", encoding="utf-8")
    query = tmp_path / "view.rq"
    query.write_text("SELECT ?s WHERE { ?s ?p ?o }\n", encoding="utf-8")

    messages = [item.message for item in lint_comments(tmp_path)]

    assert any("Named Graph" in item for item in messages)
    assert any("RDF-Aussage" in item for item in messages)
    assert any("kommentierten Zweck" in item for item in messages)


def test_learning_comment_linter_requires_each_predicate_line_to_be_explained(tmp_path: Path) -> None:
    source = tmp_path / "model.ttl"
    source.write_text(
        """@prefix ex: <https://example.org/> .
# Diese Ressource ist eine ausführbare Operation.
ex:read a ex:Operation ;
  ex:returns ex:Event .
""",
        encoding="utf-8",
    )

    violations = lint_comments(source)

    assert len(violations) == 1
    assert violations[0].line == 4
    assert "RDF-Aussage" in violations[0].message


def test_learning_comment_linter_rejects_multiple_predicates_on_one_line(tmp_path: Path) -> None:
    source = tmp_path / "model.ttl"
    source.write_text(
        """@prefix ex: <https://example.org/> .
# Diese Zeile versucht zwei unterschiedliche fachliche Aussagen zu verstecken.
ex:read a ex:Operation ; ex:returns ex:Event .
""",
        encoding="utf-8",
    )

    messages = [item.message for item in lint_comments(source)]

    assert any("getrennten" in message for message in messages)


def test_learning_comment_cli_fails_for_missing_comments(tmp_path: Path) -> None:
    (tmp_path / "rule.prolog").write_text("applies(x) :- fact(x).\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["lint-comments", str(tmp_path)])

    assert result.exit_code == 1
    assert "Lernkommentar" in result.stderr


def test_learning_comment_linter_rejects_unexplained_rif_atom(tmp_path: Path) -> None:
    source = tmp_path / "rule.rif.xml"
    source.write_text(
        '<rif:Document xmlns:rif="http://www.w3.org/2007/rif#"><rif:Atom /></rif:Document>',
        encoding="utf-8",
    )

    messages = [item.message for item in lint_comments(source)]

    assert any("Bedingungsatom" in item for item in messages)


def test_calendar_product_is_loaded_from_standard_trig() -> None:
    product = load_product(ROOT / "products/calendar/product.trig")

    assert product.product.id == "calendar"
    assert product.product.stack == "fastapi-react"
    assert product.knowledge_dependencies["privacy"] == "1.1.0"
    assert {operation.id for operation in product.operations} == {
        "create_event", "read_event", "update_event", "delete_event"
    }
    assert next(operation for operation in product.operations if operation.id == "delete_event").returns is None


def test_all_repository_author_sources_satisfy_learning_comment_contract() -> None:
    assert lint_comments(ROOT / "products/calendar") == []
    assert lint_comments(ROOT / "knowledge") == []
    assert lint_comments(ROOT / "vocabulary") == []
    assert lint_comments(ROOT / "src/specforge/sparql_views") == []
    assert lint_comments(ROOT / "training-prototype/glossary.ttl") == []


def test_standard_format_spec_examples_follow_the_learning_comment_contract(tmp_path: Path) -> None:
    document = (ROOT / "docs/standard-authoring-formats-spec.md").read_text(encoding="utf-8")
    suffixes = {"turtle": ".ttl", "trig": ".trig", "sparql": ".rq", "prolog": ".prolog"}
    examples = re.findall(r"```(turtle|trig|sparql|prolog)\n(.*?)```", document, flags=re.S)
    assert examples
    violations = []
    for index, (language, source) in enumerate(examples):
        path = tmp_path / f"example-{index}{suffixes[language]}"
        path.write_text(source, encoding="utf-8")
        violations.extend(lint_comments(path))
    assert violations == []


def test_published_shacl_file_covers_the_authoring_contract() -> None:
    graph = Graph().parse(ROOT / "vocabulary/1.0.0/shapes.ttl", format="turtle")
    covered = {
        (target, path)
        for shape, _, target in graph.triples((None, SH.targetClass, None))
        for prop in graph.objects(shape, SH.property)
        for path in graph.objects(prop, SH.path)
    }
    assert {
        (SF.Product, DCTERMS.identifier), (SF.Product, DCTERMS.hasVersion),
        (SF.Operation, DCTERMS.identifier), (SF.Operation, SF.actsOn),
        (SF.Field, DCTERMS.identifier), (SF.Field, SF.valueType),
        (SF.RequirementDefinition, SF.control), (SF.RequirementDefinition, SF.verifiedBy),
        (SF.Verification, SF.verificationAdapter), (SF.Verification, SF.assertion),
        (SF.ImplementationPattern, DCTERMS.hasVersion), (SF.ImplementationPattern, SF.satisfies),
        (SF.Rule, DCTERMS.identifier), (DCAT.Dataset, DCTERMS.hasVersion),
    } <= covered
    package_shape = next(graph.subjects(SH.targetClass, DCAT.Dataset))
    assert next(graph.objects(package_shape, SH.xone), None) is not None


def test_active_package_manifests_are_loaded_from_dcat_trig() -> None:
    compiler = Compiler(ROOT)
    manifests = compiler.load_package_manifests("products/calendar")

    assert manifests["privacy"].kind == "policy"
    assert manifests["fastapi-react"].kind == "implementation"
    integration = manifests["calendar-fastapi-react"]
    assert integration.kind == "integration"
    assert integration.integrates is not None
    assert integration.integrates.domain.package == "calendar"
    assert integration.integrates.implementation.package == "fastapi-react"
    for name, manifest in manifests.items():
        path = ROOT / "knowledge" / name / manifest.version / "package.trig"
        assert load_package_manifest(path) == manifest

    result = CliRunner().invoke(app, ["rdf-check", str(ROOT / "knowledge/privacy/1.1.0/package.trig")])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["profile"] == "authoring"


def test_every_package_version_has_one_role_and_catalogs_each_payload() -> None:
    for package in sorted(path for path in ROOT.glob("knowledge/*/*") if path.is_dir()):
        manifest = load_package_manifest(package / "package.trig")
        assert manifest.kind in {"policy", "domain", "implementation", "integration"}
        dataset = Dataset(default_union=True).parse(package / "package.trig", format="trig")
        distributions = list(dataset.subjects(RDF.type, DCAT.Distribution))
        identifiers = {str(value) for item in distributions for value in dataset.objects(item, DCTERMS.identifier)}
        payloads = {
            path.name for path in package.iterdir()
            if path.is_file() and path.name != "package.trig"
            and path.name.endswith((".ttl", ".trig", ".rif.xml", ".rq"))
        }
        assert identifiers == payloads


def test_semantic_provenance_reaches_standard_source_distributions() -> None:
    semantic = Compiler(ROOT).semantic_dataset("products/calendar")
    dataset = semantic.dataset
    distributions = set(dataset.subjects(RDF.type, DCAT.Distribution))
    assert distributions
    assert not list(dataset.quads((None, DCAT.mediaType, Literal("application/yaml"), None)))
    for rdf_type in (SF.RequirementDefinition, SF.Rule, SF.ImplementationPattern, SF.Verification):
        for resource in dataset.subjects(RDF.type, rdf_type):
            sources = set(dataset.objects(resource, PROV.wasDerivedFrom))
            assert sources and sources <= distributions
    runs = set(dataset.subjects(RDF.type, PROV.Activity))
    assert runs
    for run in runs:
        assert set(dataset.objects(run, PROV.used)) & distributions


def test_package_manifest_requires_exactly_one_role(tmp_path: Path) -> None:
    source = tmp_path / "package.trig"
    source.write_text(
        """@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
# Dieser Graph beschreibt ein absichtlich rollenloses Test-Package.
<urn:graph> {
  # Diese Ressource besitzt Identität und Version, aber keine Package-Rolle.
  <urn:package> a dcat:Dataset ;
    # Diese Aussage legt die stabile Kennung der Ressource fest.
    dcterms:identifier "demo" ;
    # Diese Aussage pinnt die konkrete Version der Ressource.
    dcterms:hasVersion "1.0.0" ;
    # Diese Aussage gibt der Ressource einen verständlichen Titel.
    dcterms:title "Demo" .
}
""",
        encoding="utf-8",
    )

    import pytest
    from specforge.errors import SpecForgeError

    with pytest.raises(SpecForgeError, match=r"(?s)SF3101.*exactly one shape"):
        load_package_manifest(source)


def test_compiler_prefers_standard_product_source() -> None:
    assert Compiler(ROOT).product_file("products/calendar").name == "product.trig"


def test_normal_resolve_does_not_import_the_optional_yaml_parser() -> None:
    script = """
import builtins
from pathlib import Path
original_import = builtins.__import__
def guarded(name, *args, **kwargs):
    if name == 'yaml' or name.startswith('yaml.'):
        raise AssertionError('normal resolve attempted to import YAML')
    return original_import(name, *args, **kwargs)
builtins.__import__ = guarded
from specforge.compiler import Compiler
Compiler(Path('.')).resolve('products/calendar', write=False)
"""
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_generated_rif_has_learning_comments_and_remains_roundtrip_safe(tmp_path: Path) -> None:
    rule = DatalogRule("privacy/example", "1", Atom("requires", ("$operation", "PRIVACY-001")), (
        Atom("returns", ("$operation", "$resource")),
    ))
    path = tmp_path / "privacy.rif.xml"
    path.write_text(export_rules([rule]), encoding="utf-8")

    assert lint_comments(path) == []
    assert import_rules(path) == [rule]

    result = CliRunner().invoke(app, ["rif-check", str(path)])

    assert result.exit_code == 0, result.output
    assert '"conforms": true' in result.output
    assert '"rules": 1' in result.output

    prolog = tmp_path / "privacy.prolog"
    prolog.write_text(export_prolog([rule]), encoding="utf-8")
    assert "requires(Operation, 'PRIVACY-001') :-" in prolog.read_text(encoding="utf-8")
    assert lint_comments(prolog) == []


def test_active_requirement_definitions_are_loaded_from_rdf() -> None:
    requirements = {
        item.id: item
        for path in ROOT.glob("knowledge/*/*/requirements.ttl")
        for item in load_requirements(path)
    }

    assert len(requirements) == 10
    assert requirements["PRIVACY-001"].expectation.value == "declared_fields_only"
    assert requirements["OBS-001"].expectation.value == ["access_granted", "access_denied"]
    assert requirements["DATA-001"].verifications[0].assertion.invariant == "end > start"


def test_migrate_format_writes_commented_trig_without_overwriting_source(tmp_path: Path) -> None:
    source = tmp_path / "product.yaml"
    source.write_text(
        """schema_version: "2"
product: {id: demo, version: "1.0.0", stack: test}
entities:
  - {id: Actor, fields: [{name: id, type: UUID}]}
operations:
  - {id: read, action: read, acts_on: Actor, returns: Actor, actor: Actor, scope: own}
declared_requirements: []
knowledge_dependencies: {}
""",
        encoding="utf-8",
    )
    output = tmp_path / "standard" / "product.trig"

    result = CliRunner().invoke(app, ["migrate-format", str(source), "--to", "trig", "--output", str(output)])

    assert result.exit_code == 0, result.output
    assert source.exists()
    assert load_product(output).product.id == "demo"
    assert lint_comments(output) == []
    report = json.loads((output.parent / "migration-report.json").read_text(encoding="utf-8"))
    assert report["source_preserved"] is True
    assert report["status"] == "converted-parsed-and-comment-linted"


def test_package_hash_ignores_learning_comments(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    source = package / "package.trig"
    source.write_text(
        "# Dieser Kommentar erklärt den Package-Graph für lernende Personen.\n<urn:g> { # inline\n# Diese Aussage identifiziert das Package als Dataset.\n<urn:p> <urn:name> \"demo\" .\n}\n",
        encoding="utf-8",
    )
    first = package_content_hash(package)
    source.write_text(source.read_text(encoding="utf-8").replace("Dieser Kommentar", "Diese ausführliche Erklärung"), encoding="utf-8")

    assert package_content_hash(package) == first


def test_package_hash_preserves_named_graph_identity(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    source = package / "package.trig"
    source.write_text(
        "# Dieser Graph trennt eine fachliche Aussage in einem benannten Kontext.\n"
        "<urn:graph-a> {\n"
        "# Diese Aussage ordnet der Ressource einen stabilen Wert zu.\n"
        "<urn:subject> <urn:predicate> <urn:object> .\n}\n",
        encoding="utf-8",
    )
    first = package_content_hash(package)
    source.write_text(source.read_text(encoding="utf-8").replace("graph-a", "graph-b"), encoding="utf-8")

    assert package_content_hash(package) != first


def test_stored_views_are_commented_sparql_resources() -> None:
    assert set(available_views()) == {
        "glossary", "packages", "product-model", "provenance",
        "relationship-glossary", "requirements", "rule-applications", "violations",
    }
    for name in available_views():
        source = ROOT / "src" / "specforge" / "sparql_views" / f"{name}.rq"
        assert load_view(name) == source.read_text(encoding="utf-8")
        assert lint_comments(source) == []
