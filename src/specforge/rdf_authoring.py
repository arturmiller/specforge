from __future__ import annotations

from pathlib import Path
from urllib.parse import quote, unquote
from hashlib import sha256

from rdfcanon import RDFCanon
from rdfcanon.rdfcanon_time_ticker import RDFCanonTimeTicker
from rdflib import Dataset, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import DCAT, DCTERMS, PROV, RDF, RDFS, SKOS

from .errors import SpecForgeError
from .datalog import Atom, Equality, compile_requirement_rules
from .io import canonical_json, write_if_changed
from .model import (
    DeclaredRequirement, Entity, EntityField, Operation, PackageIntegration,
    PackageManifest, PackageReference, ProductIdentity, ProductSpec, Provenance,
    RequirementDefinition, Expectation, VerificationSpec, AssertionSpec, Pattern,
    Concept,
    Condition, FactPattern, Rule, RuleResult,
)
from .rif import export_rules, import_rules
from .semantic import SF


def _one(dataset: Dataset, subject: URIRef, predicate: URIRef, *, required: bool = True):
    values = sorted({value for value in dataset.objects(subject, predicate)}, key=str)
    if len(values) != 1:
        if not required and not values:
            return None
        raise SpecForgeError("SF3301", str(subject), str(predicate), f"expected exactly one value, found {len(values)}")
    return values[0]


def _identifier(dataset: Dataset, subject: URIRef) -> str:
    return str(_one(dataset, subject, DCTERMS.identifier))


def _local(value: URIRef) -> str:
    return unquote(str(value).rstrip("/").rsplit("/", 1)[-1])


def _term_value(value) -> str:
    """Project a standard IRI term to the compatibility model's local name."""
    return _local(value) if isinstance(value, URIRef) else str(value)


def _validated_dataset(path: Path, format: str) -> Dataset:
    dataset = Dataset(default_union=True)
    try:
        dataset.parse(path, format=format)
    except Exception as exc:
        raise SpecForgeError("SF3300", str(path), "/", str(exc)) from exc
    from .shacl import validate_graph

    validation = validate_graph(dataset, authoring=True)
    if not validation.conforms:
        raise SpecForgeError("SF3101", str(path), "/", validation.report_text)
    return dataset


def load_product(path: Path) -> ProductSpec:
    """Load the standard RDF authoring representation into the compatibility model."""
    dataset = _validated_dataset(path, "trig")
    products = sorted({subject for subject in dataset.subjects(RDF.type, SF.Product)}, key=str)
    if len(products) != 1:
        raise SpecForgeError("SF3301", str(path), "/Product", f"expected exactly one Product, found {len(products)}")
    product = products[0]
    product_id = _identifier(dataset, product)

    entities: list[Entity] = []
    for entity_iri in sorted(dataset.objects(product, SF.defines), key=str):
        if (entity_iri, RDF.type, SF.Entity) not in dataset:
            continue
        fields: list[EntityField] = []
        for field_iri in sorted(dataset.objects(entity_iri, SF.hasField), key=str):
            fields.append(EntityField(
                name=_identifier(dataset, field_iri),
                type=_local(_one(dataset, field_iri, SF.valueType)),
                relation=str(value) if (value := _one(dataset, field_iri, SF.relation, required=False)) else None,
                classification=_local(value) if (value := _one(dataset, field_iri, SF.classifiedAs, required=False)) else None,
                optional=bool(value.toPython()) if (value := _one(dataset, field_iri, SF.optional, required=False)) else False,
                response_name=str(value) if (value := _one(dataset, field_iri, SF.responseName, required=False)) else None,
            ))
        entities.append(Entity(id=_identifier(dataset, entity_iri), fields=fields))

    operations: list[Operation] = []
    for operation_iri in sorted(dataset.objects(product, SF.offers), key=str):
        operations.append(Operation(
            id=_identifier(dataset, operation_iri),
            action=_local(_one(dataset, operation_iri, SF.action)),
            acts_on=_identifier(dataset, _one(dataset, operation_iri, SF.actsOn)),
            returns=_identifier(dataset, value) if (value := _one(dataset, operation_iri, SF.returns, required=False)) else None,
            actor=_identifier(dataset, _one(dataset, operation_iri, SF.actor)),
            scope=str(_one(dataset, operation_iri, SF.scope)),
        ))

    declared: list[DeclaredRequirement] = []
    for declaration in sorted(dataset.objects(product, SF.declaresRequirement), key=str):
        requirement = _one(dataset, declaration, SF.requirement)
        operation = _one(dataset, declaration, SF.appliesTo)
        declared.append(DeclaredRequirement(
            id=_local(requirement),
            operation=_identifier(dataset, operation),
            statement=str(_one(dataset, declaration, DCTERMS.description)),
        ))

    dependencies: dict[str, str] = {}
    for package in dataset.objects(product, DCTERMS.requires):
        parts = str(package).rstrip("/").rsplit("/", 2)
        if len(parts) < 3:
            raise SpecForgeError("SF3301", str(path), str(DCTERMS.requires), f"invalid package version IRI {package}")
        dependencies[unquote(parts[-2])] = unquote(parts[-1])

    return ProductSpec(
        schema_version="2",
        product=ProductIdentity(
            id=product_id,
            version=str(_one(dataset, product, DCTERMS.hasVersion)),
            stack=_local(_one(dataset, product, SF.usesStack)),
        ),
        entities=entities,
        operations=operations,
        declared_requirements=declared,
        knowledge_dependencies=dependencies,
    )


def load_skos_glossary(path: Path) -> dict[str, str]:
    dataset = _validated_dataset(path, "turtle")
    result: dict[str, str] = {}
    for concept in dataset.subjects(RDF.type, SKOS.Concept):
        labels = sorted(dataset.objects(concept, SKOS.prefLabel), key=lambda item: (item.language != "de", str(item)))
        definitions = sorted(dataset.objects(concept, SKOS.definition), key=lambda item: (item.language != "de", str(item)))
        if labels and definitions:
            result[str(labels[0])] = str(definitions[0])
    return result


def load_package_manifest(path: Path) -> PackageManifest:
    dataset = _validated_dataset(path, "trig")
    packages = sorted({subject for subject in dataset.subjects(RDF.type, DCAT.Dataset)}, key=str)
    if len(packages) != 1:
        raise SpecForgeError("SF3301", str(path), "/Package", f"expected exactly one dcat:Dataset, found {len(packages)}")
    package = packages[0]
    role_types = {
        SF.PolicyPackage: "policy",
        SF.DomainPackage: "domain",
        SF.ImplementationPackage: "implementation",
        SF.IntegrationPackage: "integration",
    }
    roles = [role for rdf_type, role in role_types.items() if (package, RDF.type, rdf_type) in dataset]
    if len(roles) != 1:
        raise SpecForgeError(
            "SF3301", str(path), str(RDF.type),
            f"package must have exactly one SpecForge role, found {len(roles)}",
        )

    def reference(predicate: URIRef) -> PackageReference | None:
        value = _one(dataset, package, predicate, required=False)
        if value is None:
            return None
        parts = str(value).rstrip("/").rsplit("/", 2)
        if len(parts) < 3:
            raise SpecForgeError("SF3301", str(path), str(predicate), f"invalid package version IRI {value}")
        return PackageReference(package=unquote(parts[-2]), version=unquote(parts[-1]))

    domain, implementation = reference(SF.bindsDomain), reference(SF.bindsImplementation)
    if roles[0] == "integration" and not (domain and implementation):
        raise SpecForgeError(
            "SF3301", str(path), "sf:bindsDomain/sf:bindsImplementation",
            "integration package must bind exactly one domain and one implementation package",
        )
    if roles[0] != "integration" and (domain or implementation):
        raise SpecForgeError(
            "SF3301", str(path), "sf:bindsDomain/sf:bindsImplementation",
            "only an integration package may declare integration bindings",
        )
    integration = PackageIntegration(domain=domain, implementation=implementation) if domain and implementation else None
    return PackageManifest(
        name=_identifier(dataset, package),
        version=str(_one(dataset, package, DCTERMS.hasVersion)),
        owner=str(value) if (value := _one(dataset, package, DCTERMS.publisher, required=False)) else None,
        kind=roles[0] if roles else None,
        purpose=str(value) if (value := _one(dataset, package, DCTERMS.description, required=False)) else None,
        integrates=integration,
    )


ASSERTION_PROPERTIES = {
    "response_status": SF.responseStatus,
    "response_fields": SF.responseField,
    "response_fields_from": SF.responseFieldsFrom,
    "invariant": SF.invariant,
    "stored_matches": SF.storedMatches,
    "resource_matches": SF.resourceMatches,
    "after_status": SF.afterStatus,
    "audit_event": SF.auditEvent,
    "max_requests_per_minute": SF.maxRequestsPerMinute,
}


def _provenance(dataset: Dataset, resource: URIRef) -> Provenance:
    source = _one(dataset, resource, PROV.wasDerivedFrom)
    return Provenance(
        type=str(_one(dataset, source, SF.sourceType)),
        document=str(_one(dataset, source, DCTERMS.identifier)),
        version=str(_one(dataset, source, DCTERMS.hasVersion)),
        section=str(_one(dataset, source, SF.sourceSection)),
    )


def load_requirements(path: Path) -> list[RequirementDefinition]:
    dataset = _validated_dataset(path, "turtle")
    requirements: list[RequirementDefinition] = []
    for resource in sorted(dataset.subjects(RDF.type, SF.RequirementDefinition), key=str):
        list_head = _one(dataset, resource, SF.expectedValueList, required=False)
        if list_head is not None:
            expected = [value.toPython() for value in Collection(dataset, list_head)]
        else:
            values = sorted(dataset.objects(resource, SF.expectedValue), key=str)
            expected = [value.toPython() for value in values]
        verifications: list[VerificationSpec] = []
        for verification in sorted(dataset.objects(resource, SF.verifiedBy), key=str):
            assertion = _one(dataset, verification, SF.assertion)
            assertion_data: dict[str, object] = {}
            for name, predicate in ASSERTION_PROPERTIES.items():
                items = sorted(dataset.objects(assertion, predicate), key=str)
                if items:
                    assertion_data[name] = [item.toPython() for item in items] if name == "response_fields" else items[0].toPython()
            mandatory = _one(dataset, verification, SF.mandatory, required=False)
            verifications.append(VerificationSpec(
                id=_identifier(dataset, verification),
                adapter=_term_value(_one(dataset, verification, SF.verificationAdapter)),
                setup=str(_one(dataset, verification, SF.setup)),
                assertion=AssertionSpec.model_validate(assertion_data),
                mandatory=bool(mandatory.toPython()) if mandatory is not None else True,
            ))
        requirements.append(RequirementDefinition(
            id=_identifier(dataset, resource),
            version=str(_one(dataset, resource, DCTERMS.hasVersion)),
            statement=str(_one(dataset, resource, DCTERMS.description)),
            expectation=Expectation(
                control=_term_value(_one(dataset, resource, SF.control)),
                operator=_term_value(_one(dataset, resource, SF.operator)),
                value=expected if len(expected) > 1 else expected[0],
            ),
            verifications=verifications,
            source=_provenance(dataset, resource),
        ))
    return requirements


def load_patterns(path: Path) -> list[Pattern]:
    dataset = _validated_dataset(path, "turtle")
    patterns: list[Pattern] = []
    for resource in sorted(dataset.subjects(RDF.type, SF.ImplementationPattern), key=str):
        controls: dict[str, object] = {}
        for binding in dataset.objects(resource, SF.controlBinding):
            name = _term_value(_one(dataset, binding, SF.control))
            list_head = _one(dataset, binding, SF.expectedValueList, required=False)
            if list_head is not None:
                controls[name] = [value.toPython() for value in Collection(dataset, list_head)]
            else:
                controls[name] = _one(dataset, binding, SF.expectedValue).toPython()
        constraints: dict[str, list[str]] = {}
        for constraint in dataset.objects(resource, SF.constraint):
            kind = str(_one(dataset, constraint, SF.constraintKind))
            constraints.setdefault(kind, []).append(str(_one(dataset, constraint, DCTERMS.description)))
        patterns.append(Pattern(
            id=_identifier(dataset, resource),
            version=str(_one(dataset, resource, DCTERMS.hasVersion)),
            owner=str(value) if (value := _one(dataset, resource, DCTERMS.publisher, required=False)) else None,
            satisfies=sorted(_local(value) for value in dataset.objects(resource, SF.satisfies)),
            stack=_local(value) if (value := _one(dataset, resource, SF.usesStack, required=False)) else None,
            controls=controls,
            verifications=sorted(_local(value) for value in dataset.objects(resource, SF.verifiedBy)),
            artifacts=sorted(str(value) for value in dataset.objects(resource, SF.artifact)),
            constraints={key: sorted(values) for key, values in constraints.items()},
            recommendations=sorted(str(value) for value in dataset.objects(resource, SF.recommendation)),
        ))
    return patterns


def load_concepts(path: Path) -> list[Concept]:
    dataset = _validated_dataset(path, "turtle")
    concepts: list[Concept] = []
    for resource in sorted(dataset.subjects(RDF.type, RDFS.Class), key=str):
        if _one(dataset, resource, DCTERMS.identifier, required=False) is None:
            continue
        concepts.append(Concept(
            id=_identifier(dataset, resource),
            version=str(_one(dataset, resource, DCTERMS.hasVersion)),
            is_a=sorted(_identifier(dataset, value) for value in dataset.objects(resource, RDFS.subClassOf)),
            classifications=sorted(_local(value) for value in dataset.objects(resource, SF.classifiedAs)),
            source=_provenance(dataset, resource),
        ))
    return concepts


def _condition_from_term(term) -> Condition:
    if isinstance(term, Atom):
        return Condition(fact=FactPattern(subject=str(term.terms[0]), predicate=term.relation, object=term.terms[1]))
    if isinstance(term, Equality):
        return Condition(equals=[term.left, term.right])
    raise TypeError(term)


def load_rules(package: Path) -> list[Rule]:
    metadata_path = package / "rules.ttl"
    rif_path = package / "rules.rif.xml"
    dataset = _validated_dataset(metadata_path, "turtle")
    metadata = {
        _identifier(dataset, resource): (str(_one(dataset, resource, DCTERMS.hasVersion)), _provenance(dataset, resource))
        for resource in dataset.subjects(RDF.type, SF.Rule)
    }
    grouped: dict[str, list] = {}
    for branch in import_rules(rif_path):
        rule_id = branch.id.split("#branch-", 1)[0]
        grouped.setdefault(rule_id, []).append(branch)
    result: list[Rule] = []
    for rule_id, branches in sorted(grouped.items()):
        if rule_id not in metadata:
            raise SpecForgeError("SF3301", str(metadata_path), "/Rule", f"missing metadata for {rule_id}")
        version, source = metadata[rule_id]
        if any(branch.version != version for branch in branches):
            raise SpecForgeError("SF3301", str(rif_path), "/Rule", f"version mismatch for {rule_id}")
        ordered_branches = sorted(branches, key=lambda item: item.id)
        common_terms = [
            term for term in ordered_branches[0].body
            if all(term in branch.body for branch in ordered_branches[1:])
        ]
        remainders = [
            [_condition_from_term(term) for term in branch.body if term not in common_terms]
            for branch in ordered_branches
        ]
        alternatives = [
            terms[0] if len(terms) == 1 else Condition(all=terms)
            for terms in remainders if terms
        ]
        common = [_condition_from_term(term) for term in common_terms]
        if len(alternatives) > 1:
            common.append(Condition(any=alternatives))
        elif alternatives:
            common.append(alternatives[0])
        when = common[0] if len(common) == 1 else Condition(all=common)
        head = branches[0].head
        if head.relation != "requires" or len(head.terms) != 2:
            raise SpecForgeError("SF3201", str(rif_path), "/then", "Rule head must be requires(target, requirement)")
        result.append(Rule(
            id=rule_id,
            version=version,
            when=when,
            then=RuleResult(target=str(head.terms[0]), requirement=str(head.terms[1])),
            source=source,
        ))
    return result


def migrate_rule_package(package: Path, destination: Path | None = None) -> tuple[Path, Path]:
    """Mechanically migrate legacy YAML Rules to commented RIF Core plus RDF metadata."""
    from .io import read_yaml

    legacy = [
        _normalize_legacy_rule(Rule.model_validate(read_yaml(path)))
        for path in sorted((package / "rules").glob("*.yaml"))
    ]
    if not legacy:
        raise ValueError(f"no legacy rules found in {package}")
    target = destination or package
    target.mkdir(parents=True, exist_ok=True)
    rif_path = target / "rules.rif.xml"
    write_if_changed(rif_path, export_rules(compile_requirement_rules(legacy)))
    prefix = """@prefix sf: <https://specforge.dev/vocab/> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix rule: <https://specforge.dev/rule/> .
@prefix source: <https://specforge.dev/source/> .

"""
    blocks: list[str] = []
    for rule in legacy:
        slug = rule.id.replace("/", "-")
        source_slug = f"{slug}-{rule.source.section}"
        blocks.append(
            f"# Diese Rule leitet {rule.then.requirement} für ein durch positive Facts gebundenes Target ab.\n"
            f"rule:{slug} a sf:Rule ;\n"
            f"  dcterms:identifier {Literal(rule.id).n3()} ;\n"
            f"  dcterms:hasVersion {Literal(rule.version).n3()} ;\n"
            f"  prov:wasDerivedFrom source:{source_slug} .\n\n"
            f"# Diese Quelle bezeichnet den normativen Abschnitt für die Rule {rule.id}.\n"
            f"source:{source_slug} a prov:Entity ;\n"
            f"  sf:sourceType {Literal(rule.source.type).n3()} ;\n"
            f"  dcterms:identifier {Literal(rule.source.document).n3()} ;\n"
            f"  dcterms:hasVersion {Literal(rule.source.version).n3()} ;\n"
            f"  sf:sourceSection {Literal(rule.source.section).n3()} .\n"
        )
    metadata_path = target / "rules.ttl"
    write_if_changed(metadata_path, prefix + "\n".join(blocks))
    return metadata_path, rif_path


def _normalize_legacy_condition(condition: Condition) -> Condition:
    """Replace the retired action negation with its finite positive equivalent."""
    if condition.not_ is not None:
        fact = condition.not_.fact
        if fact is None or fact.predicate != "action" or fact.object not in {"create", "read", "update", "delete"}:
            raise SpecForgeError("SF1203", "migration", "/when/not", "only legacy action exclusions can be normalized")
        return Condition(any=[
            Condition(fact=FactPattern(subject=fact.subject, predicate="action", object=action))
            for action in ("create", "read", "update", "delete") if action != fact.object
        ])
    if condition.all is not None:
        return Condition(all=[_normalize_legacy_condition(child) for child in condition.all])
    if condition.any is not None:
        return Condition(any=[_normalize_legacy_condition(child) for child in condition.any])
    return condition


def _normalize_legacy_rule(rule: Rule) -> Rule:
    return rule.model_copy(update={"when": _normalize_legacy_condition(rule.when)})


def _literal(value) -> str:
    if isinstance(value, list):
        return "( " + " ".join(Literal(item).n3() for item in value) + " )"
    return Literal(value).n3()


def add_package_distributions(package: Path) -> int:
    """Describe every authored RDF/RIF payload file as a local DCAT Distribution."""
    manifest_path = package / "package.trig"
    source = manifest_path.read_text(encoding="utf-8")
    if "dcat:distribution" in source:
        return 0
    manifest = load_package_manifest(manifest_path)
    payloads = sorted([
        path for path in package.iterdir()
        if path.is_file() and path.name != "package.trig"
        and path.name.endswith((".ttl", ".trig", ".rif.xml", ".rq"))
    ], key=lambda path: path.name)
    if not payloads:
        return 0
    media_types = {
        ".ttl": "text/turtle", ".trig": "application/trig",
        ".rq": "application/sparql-query", ".rif.xml": "application/rif+xml",
    }
    dataset = f"<https://specforge.dev/package/{manifest.name}/{manifest.version}>"
    blocks: list[str] = []
    for path in payloads:
        slug = quote(path.name, safe="-._~")
        distribution = f"<https://specforge.dev/package/{manifest.name}/{manifest.version}/distribution/{slug}>"
        suffix = next(key for key in media_types if path.name.endswith(key))
        blocks.extend([
            f"  # Diese Aussage katalogisiert {path.name} als Distribution dieser Package-Version.",
            f"  {dataset} dcat:distribution {distribution} .",
            "",
            f"  # Diese Ressource beschreibt die lokal ausgelieferte Datei {path.name}.",
            f"  {distribution} a dcat:Distribution ;",
            "    # Diese Aussage legt den stabilen Dateinamen der Distribution fest.",
            f"    dcterms:identifier {_literal(path.name)} ;",
            "    # Diese Aussage nennt den standardisierten Medientyp der Distribution.",
            f"    dcat:mediaType {_literal(media_types[suffix])} .",
            "",
        ])
    closing = source.rfind("}")
    if closing < 0:
        raise SpecForgeError("SF3300", str(manifest_path), "/", "package Named Graph is not closed")
    rendered = source[:closing].rstrip() + "\n\n" + "\n".join(blocks).rstrip() + "\n" + source[closing:]
    write_if_changed(manifest_path, rendered)
    return len(payloads)


def migrate_legacy_package(package: Path, destination: Path | None = None) -> list[Path]:
    """Convert one legacy YAML package into the standard RDF/RIF authoring files."""
    from .io import read_yaml

    target = destination or package
    target.mkdir(parents=True, exist_ok=True)
    manifest = PackageManifest.model_validate(read_yaml(package / "package.yaml"))
    role = {
        "policy": "sf:PolicyPackage", "domain": "sf:DomainPackage",
        "implementation": "sf:ImplementationPackage", "integration": "sf:IntegrationPackage",
    }.get(manifest.kind)
    types = "dcat:Dataset" + (f", {role}" if role else "")
    manifest_lines = [
        "@prefix dcat: <http://www.w3.org/ns/dcat#> .",
        "@prefix dcterms: <http://purl.org/dc/terms/> .",
        "@prefix sf: <https://specforge.dev/vocab/> .",
        f"@prefix package: <https://specforge.dev/package/{manifest.name}/> .", "",
        f"# Dieser Named Graph beschreibt Identität und Metadaten des Knowledge Packages {manifest.name}.",
        "package:graph-metadata {",
        f"  # Diese Dataset-Ressource bezeichnet {manifest.name} in Version {manifest.version}.",
        f"  package:{manifest.version} a {types} ;",
        f"    dcterms:identifier {_literal(manifest.name)} ;",
        f"    dcterms:hasVersion {_literal(manifest.version)} ;",
        f"    dcterms:title {_literal(manifest.name + ' Knowledge')}" + (" ;" if manifest.owner or manifest.purpose or manifest.integrates else " ."),
    ]
    tail: list[str] = []
    if manifest.owner:
        tail.append(f"    dcterms:publisher {_literal(manifest.owner)}")
    if manifest.purpose:
        tail.append(f"    dcterms:description {_literal(manifest.purpose)}")
    if manifest.integrates:
        tail.extend([
            f"    sf:bindsDomain <https://specforge.dev/package/{manifest.integrates.domain.package}/{manifest.integrates.domain.version}>",
            f"    sf:bindsImplementation <https://specforge.dev/package/{manifest.integrates.implementation.package}/{manifest.integrates.implementation.version}>",
        ])
    if tail:
        manifest_lines.extend(f"{line}{' .' if index == len(tail)-1 else ' ;'}" for index, line in enumerate(tail))
    manifest_lines.append("}")
    outputs = [target / "package.trig"]
    write_if_changed(outputs[0], "\n".join(manifest_lines) + "\n")

    legacy_requirements = [RequirementDefinition.model_validate(read_yaml(path)) for path in sorted((package / "requirements").glob("*.yaml"))]
    if legacy_requirements:
        header = """@prefix sf: <https://specforge.dev/vocab/> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix requirement: <https://specforge.dev/requirement/> .
@prefix verification: <https://specforge.dev/verification/> .
@prefix assertion: <https://specforge.dev/assertion/> .
@prefix source: <https://specforge.dev/source/> .

"""
        blocks: list[str] = []
        for item in legacy_requirements:
            slug = f"{item.id}-{item.version}"
            source_slug = f"{item.source.document}-{item.source.section}"
            verification_iris = ", ".join(f"verification:{v.id}" for v in item.verifications)
            value_property = "sf:expectedValueList" if isinstance(item.expectation.value, list) else "sf:expectedValue"
            block = [
                f"# {item.id} beschreibt die überprüfbare Erwartung: {item.statement}",
                f"requirement:{slug} a sf:RequirementDefinition ; dcterms:identifier {_literal(item.id)} ; dcterms:hasVersion {_literal(item.version)} ;",
                f"  dcterms:description {_literal(item.statement)} ; sf:control <https://specforge.dev/control/{item.expectation.control}> ; sf:operator <https://specforge.dev/operator/{item.expectation.operator}> ;",
                f"  {value_property} {_literal(item.expectation.value)} ; sf:verifiedBy {verification_iris} ; prov:wasDerivedFrom source:{source_slug} .", "",
            ]
            for verification in item.verifications:
                block.extend([
                    f"# Diese Verification führt {verification.id} mit dem Adapter {verification.adapter} aus.",
                    f"verification:{verification.id} a sf:Verification ; dcterms:identifier {_literal(verification.id)} ; sf:verificationAdapter <https://specforge.dev/verification-adapter/{verification.adapter}> ; sf:setup {_literal(verification.setup)} ; sf:mandatory {_literal(verification.mandatory)} ; sf:assertion assertion:{verification.id} .", "",
                    f"# Diese Assertion beschreibt die maschinenlesbaren Erwartungen von {verification.id}.",
                ])
                assertions = verification.assertion.model_dump(exclude_none=True)
                properties: list[str] = []
                for name, value in assertions.items():
                    predicate = ASSERTION_PROPERTIES[name]
                    local = str(predicate).rsplit("/", 1)[-1]
                    if name == "response_fields":
                        properties.extend(f"sf:{local} {_literal(entry)}" for entry in value)
                    else:
                        properties.append(f"sf:{local} {_literal(value)}")
                block.extend([f"assertion:{verification.id} a sf:AssertionSpec ; " + " ; ".join(properties) + " .", ""])
            block.extend([
                f"# Diese Quelle bezeichnet den normativen Abschnitt {item.source.section} in {item.source.document}.",
                f"source:{source_slug} a prov:Entity ; sf:sourceType {_literal(item.source.type)} ; dcterms:identifier {_literal(item.source.document)} ; dcterms:hasVersion {_literal(item.source.version)} ; sf:sourceSection {_literal(item.source.section)} .",
            ])
            blocks.append("\n".join(block))
        output = target / "requirements.ttl"
        write_if_changed(output, header + "\n\n".join(blocks) + "\n")
        outputs.append(output)

    legacy_patterns = [Pattern.model_validate(read_yaml(path)) for path in sorted((package / "patterns").glob("*.yaml"))]
    if legacy_patterns:
        header = """@prefix sf: <https://specforge.dev/vocab/> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix pattern: <https://specforge.dev/pattern/> .
@prefix requirement: <https://specforge.dev/requirement/> .
@prefix verification: <https://specforge.dev/verification/> .
@prefix stack: <https://specforge.dev/stack/> .
@prefix binding: <https://specforge.dev/control-binding/> .
@prefix constraint: <https://specforge.dev/constraint/> .

"""
        blocks = []
        for item in legacy_patterns:
            slug = item.id.replace("/", "-")
            bindings = [f"binding:{slug}-{key}" for key in item.controls]
            properties = [
                f"dcterms:identifier {_literal(item.id)}", f"dcterms:hasVersion {_literal(item.version)}",
            ]
            if item.owner: properties.append(f"dcterms:publisher {_literal(item.owner)}")
            if item.stack: properties.append(f"sf:usesStack stack:{item.stack}")
            if item.satisfies: properties.append("sf:satisfies " + ", ".join(f"requirement:{value}" for value in item.satisfies))
            if bindings: properties.append("sf:controlBinding " + ", ".join(bindings))
            if item.verifications: properties.append("sf:verifiedBy " + ", ".join(f"verification:{value}" for value in item.verifications))
            if item.artifacts: properties.append("sf:artifact " + ", ".join(_literal(value) for value in item.artifacts))
            blocks.append(f"# Dieses Pattern beschreibt die technische Umsetzung {item.id}.\npattern:{slug} a sf:ImplementationPattern ; " + " ; ".join(properties) + " .")
            for key, value in item.controls.items():
                predicate = "sf:expectedValueList" if isinstance(value, list) else "sf:expectedValue"
                blocks.append(f"# Dieses Binding verlangt für {key} den vom Requirement erwarteten Wert.\nbinding:{slug}-{key} a sf:ControlBinding ; sf:control <https://specforge.dev/control/{key}> ; {predicate} {_literal(value)} .")
        output = target / "patterns.ttl"
        write_if_changed(output, header + "\n\n".join(blocks) + "\n")
        outputs.append(output)

    legacy_concepts = [Concept.model_validate(read_yaml(path)) for path in sorted((package / "concepts").glob("*.yaml"))]
    if legacy_concepts:
        header = """@prefix sf: <https://specforge.dev/vocab/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix concept: <https://specforge.dev/concept/> .
@prefix classification: <https://specforge.dev/classification/> .
@prefix source: <https://specforge.dev/source/> .

"""
        blocks = []
        for item in legacy_concepts:
            source_slug = f"{item.source.document}-{item.source.section}"
            props = [f"dcterms:identifier {_literal(item.id)}", f"dcterms:hasVersion {_literal(item.version)}"]
            if item.is_a: props.append("rdfs:subClassOf " + ", ".join(f"concept:{value}" for value in item.is_a))
            if item.classifications: props.append("sf:classifiedAs " + ", ".join(f"classification:{value}" for value in item.classifications))
            props.append(f"prov:wasDerivedFrom source:{source_slug}")
            blocks.append(f"# {item.id} ist eine formal adressierbare Klasse des Knowledge Packages.\nconcept:{item.id} a rdfs:Class ; " + " ; ".join(props) + " .")
            blocks.append(f"# Diese Quelle bezeichnet die Definition von {item.id} in {item.source.document}.\nsource:{source_slug} a prov:Entity ; sf:sourceType {_literal(item.source.type)} ; dcterms:identifier {_literal(item.source.document)} ; dcterms:hasVersion {_literal(item.source.version)} ; sf:sourceSection {_literal(item.source.section)} .")
        output = target / "vocabulary.ttl"
        write_if_changed(output, header + "\n\n".join(blocks) + "\n")
        outputs.append(output)

    if list((package / "rules").glob("*.yaml")):
        outputs.extend(migrate_rule_package(package, target))
    add_package_distributions(target)
    from .authoring import add_missing_rdf_comments

    for output in outputs:
        if output.name.endswith((".ttl", ".trig")):
            add_missing_rdf_comments(output)
    return outputs


def migrate_legacy_product(source: Path, destination: Path) -> Path:
    """Convert one legacy Product YAML file to a commented TriG source."""
    from .io import read_yaml

    product = ProductSpec.model_validate(read_yaml(source))
    identity = product.product
    lines = [
        "@prefix sf: <https://specforge.dev/vocab/> .",
        "@prefix dcterms: <http://purl.org/dc/terms/> .", "",
        f"# Dieser Named Graph beschreibt Identität und Knowledge-Abhängigkeiten des Products {identity.id}.",
        f"<https://specforge.dev/product/{identity.id}/graph-metadata> {{",
        f"  # Diese Product-Ressource bezeichnet {identity.id} in Version {identity.version}.",
        f"  <https://specforge.dev/product/{identity.id}/{identity.version}> a sf:Product ;",
        f"    dcterms:identifier {_literal(identity.id)} ;",
        f"    dcterms:hasVersion {_literal(identity.version)} ;",
        f"    sf:usesStack <https://specforge.dev/stack/{identity.stack}> ;",
    ]
    if product.knowledge_dependencies:
        dependencies = ",\n      ".join(
            f"<https://specforge.dev/package/{name}/{version}>"
            for name, version in sorted(product.knowledge_dependencies.items())
        )
        lines.extend(["    dcterms:requires", f"      {dependencies} ;"])
    lines.extend([
        "    sf:defines " + ", ".join(f"<https://specforge.dev/entity/{identity.id}/{item.id}>" for item in product.entities) + " ;",
        "    sf:offers " + ", ".join(f"<https://specforge.dev/operation/{identity.id}/{item.id}>" for item in product.operations) + (" ;" if product.declared_requirements else " ."),
    ])
    if product.declared_requirements:
        lines.extend([
            "    sf:declaresRequirement " + ", ".join(
                f"<https://specforge.dev/product/{identity.id}/declared-{item.id}>" for item in product.declared_requirements
            ) + " ."
        ])
    lines.extend(["}", "", f"# Dieser Named Graph enthält das fachliche Modell des Products {identity.id}.", f"<https://specforge.dev/product/{identity.id}/graph-model> {{"])
    for entity in product.entities:
        entity_iri = f"<https://specforge.dev/entity/{identity.id}/{entity.id}>"
        lines.extend([
            f"  # {entity.id} ist eine fachliche Entity mit {len(entity.fields)} deklarierten Feldern.",
            f"  {entity_iri} a sf:Entity ; dcterms:identifier {_literal(entity.id)} ; sf:hasField " + ", ".join(
                f"<https://specforge.dev/entity/{identity.id}/{entity.id}-{field.name}>" for field in entity.fields
            ) + " .", "",
        ])
        for field in entity.fields:
            props = [f"dcterms:identifier {_literal(field.name)}"]
            type_iri = f"https://specforge.dev/entity/{identity.id}/{field.type}" if field.type in {item.id for item in product.entities} else f"https://specforge.dev/datatype/{field.type}"
            props.append(f"sf:valueType <{type_iri}>")
            if field.relation: props.append(f"sf:relation {_literal(field.relation)}")
            if field.classification: props.append(f"sf:classifiedAs <https://specforge.dev/classification/{field.classification}>")
            if field.optional: props.append("sf:optional true")
            if field.response_name: props.append(f"sf:responseName {_literal(field.response_name)}")
            lines.extend([
                f"  # Das Feld {entity.id}.{field.name} besitzt Typ und fachliche Metadaten aus der Product Spec.",
                f"  <https://specforge.dev/entity/{identity.id}/{entity.id}-{field.name}> a sf:Field ; " + " ; ".join(props) + " .", "",
            ])
    for operation in product.operations:
        props = [
            f"dcterms:identifier {_literal(operation.id)}",
            f"sf:action <https://specforge.dev/action/{operation.action}>",
            f"sf:actsOn <https://specforge.dev/entity/{identity.id}/{operation.acts_on}>",
        ]
        if operation.returns: props.append(f"sf:returns <https://specforge.dev/entity/{identity.id}/{operation.returns}>")
        props.extend([f"sf:actor <https://specforge.dev/entity/{identity.id}/{operation.actor}>", f"sf:scope {_literal(operation.scope)}"])
        lines.extend([f"  # {operation.id} ist eine ausführbare Product-Operation mit explizitem Target und Actor.", f"  <https://specforge.dev/operation/{identity.id}/{operation.id}> a sf:Operation ; " + " ; ".join(props) + " .", ""])
    for declared in product.declared_requirements:
        lines.extend([
            f"  # {declared.id} wird für die Operation {declared.operation} unmittelbar vom Product deklariert.",
            f"  <https://specforge.dev/product/{identity.id}/declared-{declared.id}> a sf:DeclaredRequirement ; sf:requirement <https://specforge.dev/requirement/{declared.id}> ; sf:appliesTo <https://specforge.dev/operation/{identity.id}/{declared.operation}> ; dcterms:description {_literal(declared.statement)} .", "",
        ])
    lines.append("}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    write_if_changed(destination, "\n".join(lines) + "\n")
    from .authoring import add_missing_rdf_comments

    add_missing_rdf_comments(destination)
    return destination


def package_content_hash(package: Path) -> str:
    """Hash semantic RDF and normalized RIF content, excluding comments and layout."""
    dataset = Dataset(default_union=False)
    for path in sorted([*package.glob("*.ttl"), *package.glob("*.trig")]):
        dataset.parse(path, format="trig" if path.suffix == ".trig" else "turtle")
    rules = []
    rif_path = package / "rules.rif.xml"
    if rif_path.exists():
        rules = [
            {"id": rule.id, "version": rule.version, "head": repr(rule.head), "body": [repr(term) for term in rule.body]}
            for rule in import_rules(rif_path)
        ]
    canonical = RDFCanon("sha256", dataset, RDFCanonTimeTicker(max_time=60_000)).canonize()
    payload = canonical + canonical_json(rules)
    return "sha256:" + sha256(payload.encode("utf-8")).hexdigest()
