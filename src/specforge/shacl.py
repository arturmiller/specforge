from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from pyshacl import validate
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCAT, DCTERMS, RDF, SH

from .semantic import SF, SemanticDataset


SHAPES = Namespace("https://specforge.dev/shapes/1.0.0/")


def metamodel_shapes() -> Graph:
    """Exportable SHACL Core contract for SpecForge's semantic IR."""
    graph = Graph()
    graph.bind("sf", SF)
    graph.bind("sh", SH)
    graph.bind("dcterms", DCTERMS)
    graph.bind("dcat", DCAT)

    def required(shape, target, path, *, node_kind=None) -> None:
        prop = SHAPES[f"{shape.split('/')[-1]}-{str(path).rsplit('/', 1)[-1]}"]
        graph.add((shape, RDF.type, SH.NodeShape))
        graph.add((shape, SH.targetClass, target))
        graph.add((shape, SH.property, prop))
        graph.add((prop, SH.path, path))
        graph.add((prop, SH.minCount, Literal(1)))
        if node_kind:
            graph.add((prop, SH.nodeKind, node_kind))

    required(SHAPES.ProductShape, SF.Product, DCTERMS.identifier)
    required(SHAPES.OperationShape, SF.Operation, DCTERMS.identifier)
    required(SHAPES.OperationShape, SF.Operation, SF.actsOn, node_kind=SH.IRI)
    required(SHAPES.RequirementShape, SF.RequirementDefinition, DCTERMS.identifier)
    required(SHAPES.RequirementShape, SF.RequirementDefinition, DCTERMS.description)
    required(SHAPES.RequirementInstanceShape, SF.RequirementInstance, SF.appliesTo, node_kind=SH.IRI)
    required(SHAPES.RequirementInstanceShape, SF.RequirementInstance, SF.implementedBy, node_kind=SH.IRI)
    required(SHAPES.PackageShape, DCAT.Dataset, DCTERMS.title)
    return graph


def authoring_shapes() -> Graph:
    """Load the same published SHACL Core contract used by external tools."""
    repository_copy = Path(__file__).parents[2] / "vocabulary" / "1.0.0" / "shapes.ttl"
    bundled_copy = Path(__file__).with_name("vocabulary") / "1.0.0" / "shapes.ttl"
    source = repository_copy if repository_copy.exists() else bundled_copy
    if not source.exists():
        raise FileNotFoundError("published SpecForge authoring shapes are missing")
    return Graph().parse(source, format="turtle")


@dataclass(frozen=True)
class ShaclResult:
    conforms: bool
    report_graph: Graph
    report_text: str


def validate_dataset(dataset: SemanticDataset) -> ShaclResult:
    return validate_graph(dataset.dataset)


def validate_graph(data_graph, *, authoring: bool = False) -> ShaclResult:
    """Validate a source or resolved RDF graph against the public Core contract."""
    conforms, report_graph, report_text = validate(
        data_graph=data_graph,
        shacl_graph=authoring_shapes() if authoring else metamodel_shapes(),
        advanced=False,
        allow_infos=False,
        allow_warnings=False,
        meta_shacl=False,
        inference="none",
    )
    report_nodes = set(report_graph.subjects(RDF.type, SH.ValidationReport))
    result_nodes = set(report_graph.subjects(RDF.type, SH.ValidationResult))
    mapping = {}
    for node in report_nodes:
        if isinstance(node, BNode):
            mapping[node] = URIRef("https://specforge.dev/shacl-report/metamodel")
    for node in result_nodes:
        if isinstance(node, BNode):
            signature = "|".join(sorted(
                f"{predicate.n3()}={obj.n3()}" for _, predicate, obj in report_graph.triples((node, None, None))
                if not isinstance(obj, BNode)
            ))
            mapping[node] = URIRef(
                "https://specforge.dev/shacl-result/" + sha256(signature.encode()).hexdigest()[:20]
            )
    skolemized = Graph()
    for prefix, namespace in report_graph.namespaces():
        skolemized.bind(prefix, namespace)
    for subject, predicate, obj in report_graph:
        skolemized.add((mapping.get(subject, subject), predicate, mapping.get(obj, obj)))
    return ShaclResult(bool(conforms), skolemized, str(report_text))
