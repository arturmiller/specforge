from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable
from urllib.parse import quote

from rdfcanon import RDFCanon
from rdfcanon.rdfcanon_time_ticker import RDFCanonTimeTicker
from rdflib import Dataset, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCAT, DCTERMS, OWL, PROV, RDF, RDFS, SH, SKOS, XSD

from .io import write_if_changed
from .datalog import Atom, Equality, Proof, compile_requirement_rules
from .model import (
    Concept,
    Fact,
    FactOrigin,
    PackageManifest,
    Pattern,
    ProductSpec,
    RequirementDefinition,
    ResolvedSpec,
    Rule,
)


BASE = "https://specforge.dev/"
SF = Namespace(f"{BASE}vocab/")
VOCABULARY_IRI = URIRef(f"{BASE}vocab/1.0.0")

GRAPH_NAMES = {
    "product": URIRef(f"{BASE}graph/product"),
    "inferred": URIRef(f"{BASE}graph/inferred"),
    "resolved": URIRef(f"{BASE}graph/resolved"),
    "provenance": URIRef(f"{BASE}graph/provenance"),
    "evidence": URIRef(f"{BASE}graph/evidence"),
    "vocabulary": URIRef(f"{BASE}graph/vocabulary"),
}

RUNTIME_GRAPHS = {GRAPH_NAMES["provenance"], GRAPH_NAMES["evidence"]}

CONTEXT: dict[str, Any] = {
    "@version": 1.1,
    "sf": str(SF),
    "rdf": str(RDF),
    "rdfs": str(RDFS),
    "xsd": str(XSD),
    "dcterms": str(DCTERMS),
    "dcat": str(DCAT),
    "skos": str(SKOS),
    "prov": str(PROV),
    "sh": str(SH),
    "owl": str(OWL),
}


RELATION_PREDICATES = {
    "depends_on": DCTERMS.requires, "binds_domain": SF.bindsDomain,
    "binds_implementation": SF.bindsImplementation, "defines": SF.defines,
    "has_field": SF.hasField, "classified_as": SF.classifiedAs,
    "is_a": RDFS.subClassOf, "offers": SF.offers, "acts_on": SF.actsOn,
    "returns": SF.returns, "actor": SF.actorType, "derives": SF.derives,
    "supports": PROV.wasDerivedFrom, "instantiated_as": SF.instantiatedAs,
    "applies_to": SF.appliesTo, "matches": SF.matches,
    "implemented_by": SF.implementedBy, "verified_by": SF.verifiedBy,
    "provides": SF.provides, "touches": SF.touches, "contains": DCTERMS.hasPart,
}


def published_vocabulary() -> Graph:
    """Load the versioned public vocabulary shipped with source and wheels."""
    repository_copy = Path(__file__).parents[2] / "vocabulary" / "1.0.0" / "specforge.ttl"
    bundled_copy = Path(__file__).with_name("vocabulary") / "1.0.0" / "specforge.ttl"
    source = repository_copy if repository_copy.exists() else bundled_copy
    if not source.exists():
        raise FileNotFoundError("published SpecForge vocabulary is missing")
    return Graph().parse(source, format="turtle")


def _localized(graph: Graph, subject: URIRef, predicate: URIRef, language: str) -> str:
    values = [value for value in graph.objects(subject, predicate) if getattr(value, "language", None) == language]
    if len(values) != 1:
        raise ValueError(f"published vocabulary needs exactly one {language} {predicate} for {subject}")
    return str(values[0])


_PUBLIC_VOCABULARY = published_vocabulary()
RELATION_DEFINITIONS = {
    key: (
        predicate,
        _localized(_PUBLIC_VOCABULARY, predicate, RDFS.label, "en"),
        _localized(_PUBLIC_VOCABULARY, predicate, RDFS.comment, "de"),
    )
    for key, predicate in RELATION_PREDICATES.items()
}


def _segment(value: Any) -> str:
    return quote(str(value), safe="-._~")


class IriFactory:
    def product(self, product_id: str, version: str | None = None) -> URIRef:
        suffix = f"/{_segment(version)}" if version else ""
        return URIRef(f"{BASE}product/{_segment(product_id)}{suffix}")

    def entity(self, product_id: str, entity_id: str) -> URIRef:
        return URIRef(f"{BASE}entity/{_segment(product_id)}/{_segment(entity_id)}")

    def field(self, product_id: str, entity_id: str, field: str) -> URIRef:
        return URIRef(f"{BASE}field/{_segment(product_id)}/{_segment(entity_id)}/{_segment(field)}")

    def operation(self, product_id: str, operation_id: str) -> URIRef:
        return URIRef(f"{BASE}operation/{_segment(product_id)}/{_segment(operation_id)}")

    def package(self, name: str, version: str) -> URIRef:
        return URIRef(f"{BASE}package/{_segment(name)}/{_segment(version)}")

    def package_graph(self, name: str, version: str) -> URIRef:
        return URIRef(f"{BASE}graph/package/{_segment(name)}/{_segment(version)}")

    def concept(self, concept_id: str, version: str | None = None) -> URIRef:
        suffix = f"/{_segment(version)}" if version else ""
        return URIRef(f"{BASE}concept/{_segment(concept_id)}{suffix}")

    def classification(self, classification: str) -> URIRef:
        return URIRef(f"{BASE}classification/{_segment(classification)}")

    def requirement(self, requirement_id: str, version: str | None = None) -> URIRef:
        suffix = f"/{_segment(version)}" if version else ""
        return URIRef(f"{BASE}requirement/{_segment(requirement_id)}{suffix}")

    def requirement_instance(self, product_id: str, instance_id: str) -> URIRef:
        return URIRef(f"{BASE}requirement-instance/{_segment(product_id)}/{_segment(instance_id)}")

    def rule(self, rule_id: str, version: str) -> URIRef:
        return URIRef(f"{BASE}rule/{_segment(rule_id)}/{_segment(version)}")

    def pattern(self, pattern_id: str, version: str) -> URIRef:
        return URIRef(f"{BASE}pattern/{_segment(pattern_id)}/{_segment(version)}")

    def verification(self, verification_id: str) -> URIRef:
        return URIRef(f"{BASE}verification/{_segment(verification_id)}")

    def assertion(self, fact_id: str) -> URIRef:
        return URIRef(f"{BASE}assertion/{_segment(fact_id)}")

    def artifact(self, path: str) -> URIRef:
        return URIRef(f"{BASE}artifact/{_segment(path)}")

    def run(self, run_id: str) -> URIRef:
        return URIRef(f"{BASE}run/{_segment(run_id)}")


class SemanticDataset:
    """Canonical semantic IR; callers do not depend on RDFLib details."""

    def __init__(self, *, base_iri: str = BASE):
        if base_iri != BASE:
            raise ValueError("SF3001 version 1 requires base IRI https://specforge.dev/")
        self.dataset = Dataset(default_union=False)
        self.iris = IriFactory()
        self._entity_ids: set[str] = set()
        self._bind_namespaces()
        self._add_vocabulary()

    def _finalize_metadata(self) -> None:
        metadata = self.dataset.default_graph
        dataset_iri = URIRef(f"{BASE}dataset")
        metadata.add((dataset_iri, RDF.type, DCAT.Dataset))
        metadata.add((dataset_iri, DCTERMS.title, Literal("SpecForge resolved dataset")))
        metadata.add((dataset_iri, DCTERMS.conformsTo, VOCABULARY_IRI))
        for graph in self.dataset.graphs():
            if graph.identifier != self.dataset.default_graph.identifier:
                metadata.add((dataset_iri, DCTERMS.hasPart, graph.identifier))

    def finalize(self) -> None:
        """Materialize deterministic Dataset metadata before validation/export."""
        self._finalize_metadata()

    def _bind_namespaces(self) -> None:
        for prefix, namespace in {
            "sf": SF, "rdf": RDF, "rdfs": RDFS, "xsd": XSD,
            "dcterms": DCTERMS, "dcat": DCAT, "skos": SKOS,
            "prov": PROV, "sh": SH, "owl": OWL,
        }.items():
            self.dataset.bind(prefix, namespace)

    def graph(self, name: str | URIRef) -> Graph:
        identifier = GRAPH_NAMES[name] if isinstance(name, str) and name in GRAPH_NAMES else URIRef(name)
        return self.dataset.graph(identifier)

    def _add_vocabulary(self) -> None:
        graph = self.graph("vocabulary")
        for triple in _PUBLIC_VOCABULARY:
            graph.add(triple)

    def add_source_models(
        self,
        spec: ProductSpec,
        manifests: dict[str, PackageManifest],
        concepts: Iterable[Concept],
        requirements: Iterable[RequirementDefinition],
        rules: Iterable[Rule],
        patterns: Iterable[Pattern],
        package_files: dict[str, list[tuple[str, str]]] | None = None,
    ) -> None:
        graph = self.graph("product")
        product = self.iris.product(spec.product.id, spec.product.version)
        graph.add((product, RDF.type, SF.Product))
        graph.add((product, RDF.type, PROV.Entity))
        product_source = URIRef(f"{product}/distribution/product.trig")
        graph.add((product_source, RDF.type, DCAT.Distribution))
        graph.add((product_source, DCTERMS.identifier, Literal("product.trig")))
        graph.add((product_source, DCAT.mediaType, Literal("application/trig")))
        graph.add((product, PROV.wasDerivedFrom, product_source))
        graph.add((product, DCTERMS.identifier, Literal(spec.product.id)))
        graph.add((product, DCTERMS.hasVersion, Literal(spec.product.version)))
        graph.add((product, SF.usesStack, URIRef(f"{BASE}stack/{_segment(spec.product.stack)}")))

        entities = {entity.id for entity in spec.entities}
        self._entity_ids = entities
        for entity in spec.entities:
            entity_iri = self.iris.entity(spec.product.id, entity.id)
            graph.add((entity_iri, RDF.type, RDFS.Class))
            graph.add((entity_iri, RDF.type, SF.Entity))
            graph.add((entity_iri, RDFS.label, Literal(entity.id)))
            graph.add((product, SF.defines, entity_iri))
            shape = URIRef(f"{entity_iri}/shape")
            graph.add((shape, RDF.type, SH.NodeShape))
            graph.add((shape, SH.targetClass, entity_iri))
            for field in entity.fields:
                field_iri = self.iris.field(spec.product.id, entity.id, field.name)
                graph.add((field_iri, RDF.type, SH.PropertyShape))
                graph.add((field_iri, SH.name, Literal(field.name)))
                graph.add((field_iri, SH.path, field_iri))
                graph.add((field_iri, SH.minCount, Literal(0 if field.optional else 1)))
                graph.add((field_iri, SH.maxCount, Literal(1)))
                if field.type in entities:
                    graph.add((field_iri, SH["class"], self.iris.entity(spec.product.id, field.type)))
                else:
                    graph.add((field_iri, SH.datatype, self._datatype(field.type)))
                if field.response_name:
                    graph.add((field_iri, SF.responseName, Literal(field.response_name)))
                if field.classification:
                    graph.add((field_iri, SF.classifiedAs, self.iris.classification(field.classification)))
                if field.relation:
                    graph.add((field_iri, SF.relation, Literal(field.relation)))
                graph.add((shape, SH.property, field_iri))
                graph.add((entity_iri, SF.hasField, field_iri))

        for operation in spec.operations:
            operation_iri = self.iris.operation(spec.product.id, operation.id)
            graph.add((operation_iri, RDF.type, SF.Operation))
            graph.add((operation_iri, DCTERMS.identifier, Literal(operation.id)))
            graph.add((operation_iri, SF.action, URIRef(f"{BASE}action/{_segment(operation.action)}")))
            graph.add((operation_iri, SF.actsOn, self.iris.entity(spec.product.id, operation.acts_on)))
            if operation.returns:
                graph.add((operation_iri, SF.returns, self.iris.entity(spec.product.id, operation.returns)))
            graph.add((operation_iri, SF.actorType, self.iris.entity(spec.product.id, operation.actor)))
            graph.add((operation_iri, SF.scope, Literal(operation.scope)))
            graph.add((product, SF.offers, operation_iri))

        for name, version in sorted(spec.knowledge_dependencies.items()):
            manifest = manifests[name]
            package = self.iris.package(name, version)
            package_graph = self.graph(self.iris.package_graph(name, version))
            package_graph.add((package, RDF.type, DCAT.Dataset))
            if manifest.kind:
                package_graph.add((package, RDF.type, SF[f"{manifest.kind.title()}Package"]))
            package_graph.add((package, DCTERMS.title, Literal(name)))
            package_graph.add((package, DCTERMS.hasVersion, Literal(version)))
            if manifest.owner:
                package_graph.add((package, DCTERMS.publisher, Literal(manifest.owner)))
            if manifest.purpose:
                package_graph.add((package, DCTERMS.description, Literal(manifest.purpose)))
            for filename, media_type in (package_files or {}).get(name, []):
                distribution = URIRef(f"{package}/distribution/{_segment(filename)}")
                package_graph.add((package, DCAT.distribution, distribution))
                package_graph.add((distribution, RDF.type, DCAT.Distribution))
                package_graph.add((distribution, DCTERMS.identifier, Literal(filename)))
                package_graph.add((distribution, DCAT.mediaType, Literal(media_type)))
            graph.add((product, DCTERMS.requires, package))
            if manifest.integrates:
                domain = self.iris.package(manifest.integrates.domain.package, manifest.integrates.domain.version)
                implementation = self.iris.package(manifest.integrates.implementation.package, manifest.integrates.implementation.version)
                package_graph.add((package, DCTERMS.requires, domain))
                package_graph.add((package, DCTERMS.requires, implementation))
                package_graph.add((package, SF.bindsDomain, domain))
                package_graph.add((package, SF.bindsImplementation, implementation))

        concept_list = list(concepts)
        concept_versions = {concept.id: concept.version for concept in concept_list}
        for concept in concept_list:
            concept_iri = self.iris.concept(concept.id, concept.version)
            package_graph = self._source_graph(concept.source.document, manifests)
            package_graph.add((concept_iri, RDF.type, RDFS.Class))
            package_graph.add((self._package_for_graph(package_graph), DCTERMS.hasPart, concept_iri))
            package_graph.add((concept_iri, RDFS.label, Literal(concept.id)))
            package_graph.add((concept_iri, DCTERMS.source, Literal(f"{concept.source.document}#{concept.source.section}")))
            package_graph.add((concept_iri, PROV.wasDerivedFrom, self._distribution_for(package_graph, "vocabulary.ttl")))
            for parent in concept.is_a:
                package_graph.add((concept_iri, RDFS.subClassOf, self.iris.concept(parent, concept_versions[parent])))
            for classification in concept.classifications:
                package_graph.add((concept_iri, SF.classifiedAs, self.iris.classification(classification)))

        for requirement in requirements:
            requirement_iri = self.iris.requirement(requirement.id, requirement.version)
            package_graph = self._source_graph(requirement.source.document, manifests)
            package_graph.add((requirement_iri, RDF.type, SF.RequirementDefinition))
            package_graph.add((self._package_for_graph(package_graph), DCTERMS.hasPart, requirement_iri))
            package_graph.add((requirement_iri, DCTERMS.identifier, Literal(requirement.id)))
            package_graph.add((requirement_iri, DCTERMS.description, Literal(requirement.statement)))
            package_graph.add((requirement_iri, SF.control, URIRef(f"{BASE}control/{_segment(requirement.expectation.control)}")))
            package_graph.add((requirement_iri, SF.operator, URIRef(f"{BASE}operator/{_segment(requirement.expectation.operator)}")))
            expected = requirement.expectation.value
            if isinstance(expected, list):
                head = URIRef(f"{requirement_iri}/expected-values/0") if expected else RDF.nil
                package_graph.add((requirement_iri, SF.expectedValueList, head))
                for index, value in enumerate(expected):
                    item = URIRef(f"{requirement_iri}/expected-values/{index}")
                    rest = URIRef(f"{requirement_iri}/expected-values/{index + 1}") if index + 1 < len(expected) else RDF.nil
                    package_graph.add((item, RDF.first, Literal(value)))
                    package_graph.add((item, RDF.rest, rest))
            else:
                package_graph.add((requirement_iri, SF.expectedValue, Literal(expected)))
            package_graph.add((requirement_iri, PROV.wasDerivedFrom, self._distribution_for(package_graph, "requirements.ttl")))
            for verification in requirement.verifications:
                verification_iri = self.iris.verification(verification.id)
                package_graph.add((verification_iri, RDF.type, SF.Verification))
                package_graph.add((verification_iri, SF.verificationAdapter, URIRef(f"{BASE}verification-adapter/{_segment(verification.adapter)}")))
                package_graph.add((verification_iri, PROV.wasDerivedFrom, self._distribution_for(package_graph, "requirements.ttl")))
                package_graph.add((requirement_iri, SF.verifiedBy, verification_iri))

        for rule in rules:
            rule_iri = self.iris.rule(rule.id, rule.version)
            package_graph = self._source_graph(rule.source.document, manifests)
            package_graph.add((rule_iri, RDF.type, SF.Rule))
            package_graph.add((self._package_for_graph(package_graph), DCTERMS.hasPart, rule_iri))
            package_graph.add((rule_iri, DCTERMS.identifier, Literal(rule.id)))
            package_graph.add((rule_iri, SF.derives, self.iris.requirement(rule.then.requirement)))
            package_graph.add((rule_iri, PROV.wasDerivedFrom, self._distribution_for(package_graph, "rules.rif.xml")))

        for compiled in compile_requirement_rules(rules):
            source_id = compiled.source_id or compiled.id
            source_rule = self.iris.rule(source_id, compiled.version)
            branch = URIRef(f"{source_rule}/branch/{_segment(compiled.id.rsplit('#branch-', 1)[-1])}")
            package_graph = next(
                (graph for graph in self.dataset.graphs() if (source_rule, RDF.type, SF.Rule) in graph),
                self.graph("vocabulary"),
            )
            package_graph.add((branch, RDF.type, SF.DatalogRule))
            package_graph.add((branch, SF.sourceRule, source_rule))
            package_graph.add((branch, SF.headRelation, Literal(compiled.head.relation)))
            package_graph.add((branch, SF.headArguments, Literal(json.dumps(compiled.head.terms))))
            for index, term in enumerate(compiled.body):
                term_iri = URIRef(f"{branch}/body/{index}")
                package_graph.add((branch, SF.bodyTerm, term_iri))
                package_graph.add((term_iri, SF.position, Literal(index)))
                if isinstance(term, Atom):
                    package_graph.add((term_iri, RDF.type, SF.PositiveAtom))
                    package_graph.add((term_iri, SF.relationName, Literal(term.relation)))
                    package_graph.add((term_iri, SF.arguments, Literal(json.dumps(term.terms))))
                elif isinstance(term, Equality):
                    package_graph.add((term_iri, RDF.type, SF.Equality))
                    package_graph.add((term_iri, SF.arguments, Literal(json.dumps([term.left, term.right]))))

        for pattern in patterns:
            pattern_iri = self.iris.pattern(pattern.id, pattern.version)
            package_graph = self._pattern_graph(pattern, manifests)
            package_graph.add((pattern_iri, RDF.type, SF.ImplementationPattern))
            package_graph.add((self._package_for_graph(package_graph), DCTERMS.hasPart, pattern_iri))
            package_graph.add((pattern_iri, DCTERMS.identifier, Literal(pattern.id)))
            package_graph.add((pattern_iri, PROV.wasDerivedFrom, self._distribution_for(package_graph, "patterns.ttl")))
            if pattern.stack:
                package_graph.add((pattern_iri, SF.usesStack, URIRef(f"{BASE}stack/{_segment(pattern.stack)}")))
            for requirement_id in pattern.satisfies:
                package_graph.add((pattern_iri, SF.satisfies, self.iris.requirement(requirement_id)))
            for verification in pattern.verifications:
                package_graph.add((pattern_iri, SF.provides, self.iris.verification(verification)))
            for artifact in pattern.artifacts:
                package_graph.add((pattern_iri, SF.touches, self.iris.artifact(artifact)))

    def add_glossary(self, terms: dict[str, str], *, scheme_name: str) -> None:
        graph = self.graph("vocabulary" if scheme_name == "academy" else "product")
        scheme = URIRef(f"{BASE}concept-scheme/{_segment(scheme_name)}")
        graph.add((scheme, RDF.type, SKOS.ConceptScheme))
        graph.add((scheme, DCTERMS.identifier, Literal(scheme_name)))
        for term, definition in sorted(terms.items()):
            concept = URIRef(f"{scheme}/term/{_segment(term)}")
            graph.add((concept, RDF.type, SKOS.Concept))
            graph.add((concept, SKOS.inScheme, scheme))
            graph.add((concept, SKOS.prefLabel, Literal(term, lang="de")))
            graph.add((concept, SKOS.definition, Literal(definition, lang="de")))

    def _source_graph(self, document: str, manifests: dict[str, PackageManifest]) -> Graph:
        for name, manifest in manifests.items():
            if name in document or document.startswith(name):
                return self.graph(self.iris.package_graph(name, manifest.version))
        return self.graph("vocabulary")

    @staticmethod
    def _package_for_graph(graph: Graph) -> URIRef:
        value = str(graph.identifier)
        if "/graph/package/" in value:
            return URIRef(value.replace("/graph/package/", "/package/", 1))
        return VOCABULARY_IRI

    @classmethod
    def _distribution_for(cls, graph: Graph, filename: str) -> URIRef:
        package = cls._package_for_graph(graph)
        return URIRef(f"{package}/distribution/{_segment(filename)}")

    def _pattern_graph(self, pattern: Pattern, manifests: dict[str, PackageManifest]) -> Graph:
        for name, manifest in manifests.items():
            if pattern.id.startswith(name.split("-")[0] + "/"):
                return self.graph(self.iris.package_graph(name, manifest.version))
        for name, manifest in manifests.items():
            if manifest.kind in {"implementation", "integration"}:
                return self.graph(self.iris.package_graph(name, manifest.version))
        return self.graph("vocabulary")

    def add_resolved(
        self, resolved: ResolvedSpec, *, proofs: dict[str, list[Proof]] | None = None
    ) -> None:
        product_id = resolved.product.id
        direct_graph = self.graph("inferred")
        resolved_graph = self.graph("resolved")
        provenance = self.graph("provenance")
        run_id = f"resolve-{product_id}-{resolved.product.version}"
        run = self.iris.run(run_id)
        provenance.add((run, RDF.type, PROV.Activity))
        provenance.add((run, PROV.wasAssociatedWith, SF.compiler))
        provenance.add((SF.compiler, RDF.type, PROV.SoftwareAgent))
        for distribution, _, _, _ in self.dataset.quads((None, RDF.type, DCAT.Distribution, None)):
            provenance.add((run, PROV.used, distribution))

        assertions: dict[str, URIRef] = {}
        for fact in resolved.facts:
            graph = direct_graph if fact.origin == FactOrigin.ONTOLOGY_DERIVED else self.graph("product")
            subject = self._fact_resource(product_id, fact.subject)
            predicate = self._fact_predicate(fact.predicate)
            obj = self._fact_object(product_id, fact.object, fact.predicate)
            graph.add((subject, predicate, obj))
            assertion = self.iris.assertion(fact.id)
            assertions[fact.id] = assertion
            graph.add((assertion, RDF.type, SF.Assertion))
            graph.add((assertion, RDF.subject, subject))
            graph.add((assertion, RDF.predicate, predicate))
            graph.add((assertion, RDF.object, obj))
            graph.add((assertion, SF.origin, Literal(fact.origin.value)))
            graph.add((assertion, DCTERMS.source, Literal(fact.provenance)))
            if fact.origin == FactOrigin.ONTOLOGY_DERIVED:
                graph.add((assertion, PROV.wasGeneratedBy, run))
            for premise in fact.premises:
                graph.add((assertion, PROV.wasDerivedFrom, self.iris.assertion(premise)))
            for index, proof in enumerate((proofs or {}).get(fact.id, [])):
                derivation = URIRef(f"{assertion}/derivation/{index}")
                graph.add((derivation, RDF.type, PROV.Derivation))
                graph.add((derivation, SF.usedRule, self.iris.rule(proof.rule, proof.rule_version)))
                graph.add((derivation, SF.bindings, Literal(json.dumps(
                    proof.binding_values(), ensure_ascii=False, sort_keys=True
                ))))
                for premise in proof.premises:
                    graph.add((derivation, PROV.entity, self.iris.assertion(premise)))
                graph.add((assertion, PROV.qualifiedDerivation, derivation))

        for instance in resolved.requirements:
            instance_iri = self.iris.requirement_instance(product_id, instance.id)
            definition = self.iris.requirement(instance.requirement, instance.requirement_version)
            target = self._fact_resource(product_id, instance.target)
            resolved_graph.add((instance_iri, RDF.type, SF.RequirementInstance))
            resolved_graph.add((instance_iri, DCTERMS.identifier, Literal(instance.id)))
            resolved_graph.add((definition, SF.instantiatedAs, instance_iri))
            resolved_graph.add((instance_iri, SF.appliesTo, target))
            resolved_graph.add((instance_iri, SF.control, URIRef(f"{BASE}control/{_segment(instance.expectation.control)}")))
            expected = instance.expectation.value
            if isinstance(expected, list):
                head = URIRef(f"{instance_iri}/expected-values/0") if expected else RDF.nil
                resolved_graph.add((instance_iri, SF.expectedValueList, head))
                for value_index, value in enumerate(expected):
                    item = URIRef(f"{instance_iri}/expected-values/{value_index}")
                    rest = URIRef(f"{instance_iri}/expected-values/{value_index + 1}") if value_index + 1 < len(expected) else RDF.nil
                    resolved_graph.add((item, RDF.first, Literal(value)))
                    resolved_graph.add((item, RDF.rest, rest))
            else:
                resolved_graph.add((instance_iri, SF.expectedValue, Literal(expected)))
            if instance.pattern:
                pattern = next(
                    (subject for subject, _, _, _ in self.dataset.quads(
                        (None, DCTERMS.identifier, Literal(instance.pattern), None)
                    )),
                    None,
                )
                if pattern:
                    resolved_graph.add((instance_iri, SF.implementedBy, pattern))
            for verification in instance.verifications:
                resolved_graph.add((instance_iri, SF.verifiedBy, self.iris.verification(verification.id)))
            for index, derivation in enumerate(instance.derivations):
                derivation_iri = URIRef(f"{instance_iri}/derivation/{index}")
                resolved_graph.add((derivation_iri, RDF.type, PROV.Derivation))
                resolved_graph.add((derivation_iri, SF.usedRule, self.iris.rule(derivation.rule, derivation.rule_version)))
                resolved_graph.add((instance_iri, PROV.qualifiedDerivation, derivation_iri))
                for fact_id in derivation.facts:
                    resolved_graph.add((derivation_iri, PROV.entity, assertions[fact_id]))
                resolved_graph.add((derivation_iri, SF.bindings, Literal(json.dumps(derivation.bindings, ensure_ascii=False, sort_keys=True))))

    def _fact_resource(self, product_id: str, value: str) -> URIRef:
        if value.startswith("operation."):
            return self.iris.operation(product_id, value.removeprefix("operation."))
        if "." in value:
            entity, field = value.split(".", 1)
            return self.iris.field(product_id, entity, field)
        return self.iris.entity(product_id, value)

    def _fact_predicate(self, predicate: str) -> URIRef:
        return {
            "is_a": RDFS.subClassOf,
            "has_field": SF.hasField,
            "has_type": SF.valueType,
            "classified_as": SF.classifiedAs,
            "contains_classification": SF.containsClassification,
            "relation": SF.relation,
            "action": SF.action,
            "acts_on": SF.actsOn,
            "returns": SF.returns,
            "actor": SF.actorType,
            "scope": SF.scope,
            "is_entity": RDF.type,
        }.get(predicate, SF[_segment(predicate)])

    @staticmethod
    def _datatype(value: str) -> URIRef:
        return {
            "UUID": XSD.string,
            "Text": XSD.string,
            "String": XSD.string,
            "DateTime": XSD.dateTime,
            "Integer": XSD.integer,
            "Boolean": XSD.boolean,
        }.get(value, URIRef(f"{BASE}datatype/{_segment(value)}"))

    def _fact_object(self, product_id: str, value: Any, predicate: str):
        if isinstance(value, bool):
            return SF.Entity if value else Literal(False)
        if isinstance(value, (int, float)):
            return Literal(value)
        text = str(value)
        if predicate in {"acts_on", "returns", "actor", "has_field"}:
            return self._fact_resource(product_id, text)
        if predicate == "has_type":
            return self.iris.entity(product_id, text) if text in self._entity_ids else self._datatype(text)
        if predicate in {"classified_as", "contains_classification"}:
            return self.iris.classification(text)
        if predicate == "is_a":
            return self.iris.concept(text)
        return Literal(text)

    def query(self, sparql: str, *, init_bindings: dict[str, Any] | None = None):
        if re.search(r"\bSERVICE\b", sparql, flags=re.IGNORECASE):
            raise ValueError("SF3002 remote SPARQL SERVICE is forbidden")
        return self.dataset.query(sparql, initBindings=init_bindings or {})

    def _copy_for_hash(self) -> Dataset:
        semantic = Dataset(default_union=False)
        for prefix, namespace in self.dataset.namespaces():
            semantic.bind(prefix, namespace)
        for graph in self.dataset.graphs():
            if graph.identifier in RUNTIME_GRAPHS:
                continue
            target = semantic.graph(graph.identifier)
            for triple in graph:
                target.add(triple)
        return semantic

    def canonical_nquads(self, *, include_runtime: bool = True) -> str:
        self._finalize_metadata()
        return RDFCanon(
            "sha256",
            self.dataset if include_runtime else self._copy_for_hash(),
            RDFCanonTimeTicker(max_time=60_000),
        ).canonize()

    def content_hash(self) -> str:
        return "sha256:" + sha256(
            self.canonical_nquads(include_runtime=False).encode("utf-8")
        ).hexdigest()

    def serialize_jsonld(self) -> str:
        self._finalize_metadata()
        raw = self.dataset.serialize(format="json-ld", context=CONTEXT, auto_compact=True)
        parsed = json.loads(raw)
        return json.dumps(parsed, ensure_ascii=False, sort_keys=True, indent=2) + "\n"

    def serialize_nquads(self) -> str:
        return self.canonical_nquads(include_runtime=True)

    def serialize_trig(self) -> str:
        self._finalize_metadata()
        return self.dataset.serialize(format="trig")

    def write(self, destination: Path) -> dict[str, Path]:
        paths = {
            "jsonld": destination / "resolved-spec.jsonld",
            "nquads": destination / "resolved-spec.nq",
            "trig": destination / "resolved-spec.trig",
        }
        write_if_changed(paths["jsonld"], self.serialize_jsonld())
        write_if_changed(paths["nquads"], self.serialize_nquads())
        write_if_changed(paths["trig"], self.serialize_trig())
        provenance_graph = Graph()
        provenance_graph.bind("prov", PROV)
        selected = set()
        for subject, predicate, obj, _ in self.dataset.quads((None, None, None, None)):
            if (
                str(predicate).startswith(str(PROV))
                or str(obj).startswith(str(PROV))
                or predicate in {SF.contentHash, SF.hashAlgorithm}
            ):
                provenance_graph.add((subject, predicate, obj))
                selected.add(subject)
        for subject in selected:
            for _, predicate, obj, _ in self.dataset.quads((subject, None, None, None)):
                provenance_graph.add((subject, predicate, obj))
        provenance = provenance_graph.serialize(format="json-ld", context=CONTEXT)
        write_if_changed(
            destination / "provenance.jsonld",
            json.dumps(json.loads(provenance), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        )
        return paths

    def add_evidence_graph(self, report: Graph) -> None:
        evidence = self.graph("evidence")
        for triple in report:
            evidence.add(triple)

    def add_hash_metadata(self, value: str) -> None:
        metadata = self.graph("provenance")
        dataset_iri = URIRef(f"{BASE}dataset")
        metadata.add((dataset_iri, SF.contentHash, Literal(value)))
        metadata.add((dataset_iri, SF.hashAlgorithm, Literal("rdfc-1.0+sha256")))

    @classmethod
    def parse(cls, source: Path, *, format: str | None = None) -> "SemanticDataset":
        selected = format or {
            ".jsonld": "json-ld", ".json": "json-ld", ".ttl": "turtle",
            ".nq": "nquads", ".trig": "trig",
        }.get(source.suffix.lower())
        if selected not in {"json-ld", "turtle", "nquads", "trig"}:
            raise ValueError("SF3003 supported RDF formats: JSON-LD, Turtle, N-Quads, TriG")
        raw = source.read_text(encoding="utf-8")
        if re.search(r'"@context"\s*:\s*"https?://', raw, flags=re.IGNORECASE):
            raise ValueError("SF3004 remote JSON-LD contexts are forbidden")
        if "http://www.w3.org/2003/11/swrl" in raw or "http://www.w3.org/2003/11/swrlb" in raw:
            raise ValueError("SF3005 SWRL is unsupported")
        if re.search(r"owl:imports|http://www\.w3\.org/2002/07/owl#imports", raw, flags=re.IGNORECASE):
            raise ValueError("SF3006 OWL imports are forbidden")
        instance = cls()
        parsed = Dataset(default_union=False)
        parsed.parse(data=raw, format=selected, publicID=source.resolve().as_uri())
        allowed_owl = {(RDF.type, OWL.Ontology), (OWL.versionInfo, None)}
        for subject, predicate, obj, _ in parsed.quads((None, None, None, None)):
            uses_owl = str(predicate).startswith(str(OWL)) or str(obj).startswith(str(OWL))
            if uses_owl and not any(
                predicate == allowed_predicate and (allowed_object is None or obj == allowed_object)
                for allowed_predicate, allowed_object in allowed_owl
            ):
                raise ValueError(f"SF3007 unsupported OWL axiom on {subject}")
        instance.dataset = parsed
        instance._bind_namespaces()
        return instance
