from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .errors import SpecForgeError
from .datalog import evaluate as evaluate_datalog
from .io import canonical_json, content_hash, pretty_json, write_if_changed
from .model import (
    Concept, Condition, Derivation, Fact, FactOrigin, KnowledgeVersions, PackageManifest, Pattern,
    ProductSpec, RequirementDefinition, RequirementInstance, RequirementStatus,
    ResolvedSpec, Rule,
)
from .semantic import SemanticDataset
from .shacl import validate_dataset
from .glossary import load_academy_glossary, load_product_glossary


class Compiler:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self._semantic_cache: dict[Path, SemanticDataset] = {}

    def product_file(self, product: str | Path) -> Path:
        path = Path(product)
        if not path.is_absolute():
            path = self.root / path
        if path.is_dir():
            path /= "product.trig"
        return path

    def load_product_spec(self, path: Path) -> ProductSpec:
        if path.suffix != ".trig":
            raise SpecForgeError("SF3302", str(path), "/", "Product authoring format must be TriG")
        from .rdf_authoring import load_product

        return load_product(path)

    def load_inputs(self, product: str | Path):
        product_path = self.product_file(product)
        spec = self.load_product_spec(product_path)
        self._load_package_manifests(spec, product_path)
        concepts: list[Concept] = []
        requirements: dict[str, RequirementDefinition] = {}
        rules: list[Rule] = []
        patterns: list[Pattern] = []
        packages: dict[str, dict[str, str]] = {}
        for namespace, version in sorted(spec.knowledge_dependencies.items()):
            package = self.root / "knowledge" / namespace / version
            if not package.is_dir():
                raise SpecForgeError("SF1004", str(product_path.relative_to(self.root)), "/knowledge_dependencies", f"missing {namespace}@{version}")
            from .rdf_authoring import package_content_hash

            packages[namespace] = {"version": version, "hash": package_content_hash(package)}
            rdf_concepts = package / "vocabulary.ttl"
            if rdf_concepts.exists():
                from .rdf_authoring import load_concepts

                concepts.extend(load_concepts(rdf_concepts))
            rdf_requirements = package / "requirements.ttl"
            requirement_items = []
            if rdf_requirements.exists():
                from .rdf_authoring import load_requirements

                requirement_items = load_requirements(rdf_requirements)
            for requirement in requirement_items:
                if requirement.id in requirements:
                    raise SpecForgeError("SF1002", str(package.relative_to(self.root)), "/id", f"duplicate requirement {requirement.id}")
                requirements[requirement.id] = requirement
            if (package / "rules.ttl").exists() and (package / "rules.rif.xml").exists():
                from .rdf_authoring import load_rules

                rules.extend(load_rules(package))
            rdf_patterns = package / "patterns.ttl"
            if rdf_patterns.exists():
                from .rdf_authoring import load_patterns

                patterns.extend(load_patterns(rdf_patterns))
        for declared in spec.declared_requirements:
            if declared.id not in requirements:
                raise SpecForgeError("SF1003", str(product_path.relative_to(self.root)), "/declared_requirements", f"missing definition {declared.id}")
        concept_ids = {concept.id for concept in concepts}
        if len(concept_ids) != len(concepts):
            raise SpecForgeError("SF1002", "knowledge", "/concepts", "duplicate concept id")
        for concept in concepts:
            for parent in concept.is_a:
                if parent not in concept_ids:
                    raise SpecForgeError("SF1003", concept.id, "/is_a", f"unknown parent concept {parent}")
        self._reject_concept_cycles(concepts)
        rule_ids = [(rule.id, rule.version) for rule in rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise SpecForgeError("SF1002", "knowledge", "/rules", "duplicate rule id and version")
        for rule in rules:
            if rule.then.requirement not in requirements:
                raise SpecForgeError("SF1003", rule.id, "/then/requirement", f"missing definition {rule.then.requirement}")
        return spec, concepts, requirements, sorted(rules, key=lambda r: (r.id, r.version)), sorted(patterns, key=lambda p: (p.id, p.version)), packages

    def load_package_manifests(self, product: str | Path) -> dict[str, PackageManifest]:
        product_path = self.product_file(product)
        spec = self.load_product_spec(product_path)
        return self._load_package_manifests(spec, product_path)

    def _load_package_manifests(
        self, spec: ProductSpec, product_path: Path
    ) -> dict[str, PackageManifest]:
        manifests: dict[str, PackageManifest] = {}
        for namespace, version in sorted(spec.knowledge_dependencies.items()):
            package = self.root / "knowledge" / namespace / version
            if not package.is_dir():
                raise SpecForgeError(
                    "SF1004", str(product_path.relative_to(self.root)),
                    "/knowledge_dependencies", f"missing {namespace}@{version}",
                )
            manifest_path = package / "package.trig"
            from .rdf_authoring import load_package_manifest

            manifest = load_package_manifest(manifest_path)
            if manifest.name != namespace or manifest.version != version:
                raise SpecForgeError(
                    "SF1005", str(manifest_path.relative_to(self.root)), "/",
                    "package identity/version mismatch",
                )
            manifests[namespace] = manifest
        for namespace, manifest in manifests.items():
            if manifest.integrates is None:
                continue
            for role, reference in (
                ("domain", manifest.integrates.domain),
                ("implementation", manifest.integrates.implementation),
            ):
                active_version = spec.knowledge_dependencies.get(reference.package)
                if active_version != reference.version:
                    raise SpecForgeError(
                    "SF1006", f"knowledge/{namespace}/{manifest.version}/{manifest_path.name}",
                        f"/integrates/{role}",
                        f"requires active dependency {reference.package}@{reference.version}",
                    )
        return manifests

    @staticmethod
    def _reject_concept_cycles(concepts: list[Concept]) -> None:
        graph = {concept.id: concept.is_a for concept in concepts}
        visiting: set[str] = set()
        visited: set[str] = set()
        def visit(node: str) -> None:
            if node in visiting:
                raise SpecForgeError("SF1202", node, "/is_a", "concept inheritance cycle")
            if node in visited:
                return
            visiting.add(node)
            for parent in graph[node]:
                visit(parent)
            visiting.remove(node)
            visited.add(node)
        for node in sorted(graph):
            visit(node)

    @staticmethod
    def fact_id(subject: str, predicate: str, obj: Any) -> str:
        return "fact-" + content_hash([subject, predicate, obj]).split(":", 1)[1][:16]

    def normalize(self, spec: ProductSpec) -> list[Fact]:
        facts: dict[tuple[str, str, str], Fact] = {}
        def add(subject: str, predicate: str, obj: Any, provenance: str, origin=FactOrigin.DECLARED):
            key = (subject, predicate, canonical_json(obj))
            facts[key] = Fact(id=self.fact_id(subject, predicate, obj), subject=subject, predicate=predicate, object=obj, origin=origin, provenance=provenance)
        for entity in sorted(spec.entities, key=lambda x: x.id):
            add(entity.id, "is_entity", True, f"product.trig#/entities/{entity.id}")
            for field in sorted(entity.fields, key=lambda x: x.name):
                field_id = f"{entity.id}.{field.name}"
                add(entity.id, "has_field", field_id, f"product.trig#/entities/{entity.id}/fields/{field.name}")
                add(field_id, "has_type", field.type, f"product.trig#/entities/{entity.id}/fields/{field.name}/type")
                if field.classification:
                    add(field_id, "classified_as", field.classification, f"product.trig#/entities/{entity.id}/fields/{field.name}/classification")
                if field.relation:
                    add(field_id, "relation", field.relation, f"product.trig#/entities/{entity.id}/fields/{field.name}/relation")
        for op in sorted(spec.operations, key=lambda x: x.id):
            prefix = f"operation.{op.id}"
            provenance = f"product.trig#/operations/{op.id}"
            add(prefix, "action", op.action, provenance)
            add(prefix, "acts_on", op.acts_on, provenance)
            if op.returns is not None:
                add(prefix, "returns", op.returns, provenance)
            add(prefix, "actor", op.actor, provenance)
            add(prefix, "scope", op.scope, provenance)
        return sorted(facts.values(), key=lambda f: (f.subject, f.predicate, str(f.object)))

    def resolve(self, product: str | Path, write: bool = True) -> ResolvedSpec:
        spec, concepts, definitions, rules, patterns, packages = self.load_inputs(product)
        manifests = self.load_package_manifests(product)
        datalog = evaluate_datalog(self.normalize(spec), concepts, rules, self.fact_id)
        facts = datalog.facts
        instances: dict[tuple[str, str], RequirementInstance] = {}
        for declared in sorted(spec.declared_requirements, key=lambda x: x.id):
            definition = definitions[declared.id]
            target = f"operation.{declared.operation}"
            instances[(declared.id, target)] = RequirementInstance(id=f"{declared.id}@{target}", requirement=declared.id, requirement_version=definition.version, statement=definition.statement, source=definition.source, target=target, kind="declared", status=RequirementStatus.REQUIRED, expectation=definition.expectation, verifications=definition.verifications)
        rule_versions = {rule.id: rule.version for rule in rules}
        for row in datalog.requirement_rows:
            target, requirement_id = map(str, row.values)
            definition = definitions[requirement_id]
            for proof in sorted(row.proofs, key=repr):
                key = (definition.id, target)
                derivation = Derivation(
                    rule=proof.rule,
                    rule_version=rule_versions[proof.rule],
                    facts=list(proof.premises),
                    bindings=proof.binding_values(),
                )
                if key not in instances:
                    instances[key] = RequirementInstance(id=f"{definition.id}@{target}", requirement=definition.id, requirement_version=definition.version, statement=definition.statement, source=definition.source, target=target, kind="derived", status=RequirementStatus.REQUIRED, expectation=definition.expectation, verifications=definition.verifications, derivations=[derivation])
                elif derivation not in instances[key].derivations:
                    instances[key].derivations.append(derivation)
        selected_patterns: dict[str, Pattern] = {}
        for instance in instances.values():
            def supports(pattern: Pattern) -> bool:
                legacy = (
                    instance.requirement in pattern.satisfies
                    and pattern.controls.get(instance.expectation.control) == instance.expectation.value
                )
                addressed = bool(
                    pattern.addresses
                    and pattern.addresses.get("control") == instance.expectation.control
                    and (
                        "expectation" not in pattern.addresses
                        or pattern.addresses["expectation"] == instance.expectation.value
                        or pattern.addresses["expectation"] == {"value": instance.expectation.value}
                        or (isinstance(pattern.addresses["expectation"], dict) and pattern.addresses["expectation"].get("type") == instance.expectation.value)
                    )
                )
                return (
                    pattern.stack == spec.product.stack
                    and (legacy or addressed)
                    and all(v.id in pattern.verifications for v in instance.verifications)
                )

            matching = [pattern for pattern in patterns if supports(pattern)]
            if not matching:
                raise SpecForgeError("SF1501", instance.requirement, instance.target, "no compatible implementation pattern")
            if len(matching) > 1:
                choices = ", ".join(f"{pattern.id}@{pattern.version}" for pattern in matching)
                raise SpecForgeError("SF1502", instance.requirement, instance.target, f"ambiguous implementation patterns for stack {spec.product.stack}: {choices}")
            instance.pattern = matching[0].id
            selected_patterns[matching[0].id] = matching[0]
        controls: dict[str, dict[str, Any]] = defaultdict(dict)
        control_sources: dict[tuple[str, str], RequirementInstance] = {}
        for instance in sorted(instances.values(), key=lambda x: x.id):
            control = instance.expectation.control
            value = instance.expectation.value
            key = (instance.target, control)
            if key in control_sources and controls[instance.target][control] != value:
                previous = control_sources[key]
                current_rules = ", ".join(f"{d.rule}@{d.rule_version}" for d in instance.derivations) or "declared"
                previous_rules = ", ".join(f"{d.rule}@{d.rule_version}" for d in previous.derivations) or "declared"
                versions = ", ".join(f"{name}@{item['version']}" for name, item in sorted(packages.items()))
                raise SpecForgeError("SF1301", instance.requirement, instance.target, f"conflicts with {previous.requirement}: {control}={value!r} via {current_rules} vs {previous.expectation.value!r} via {previous_rules}; packages: {versions}")
            controls[instance.target][control] = value
            control_sources[key] = instance
        classifications: dict[str, list[str]] = defaultdict(list)
        for fact in facts:
            if fact.predicate in {"classified_as", "contains_classification"}:
                classifications[fact.subject].append(str(fact.object))
        result = ResolvedSpec(product=spec.product, knowledge=KnowledgeVersions(packages=packages), entities=sorted(spec.entities, key=lambda x: x.id), operations=sorted(spec.operations, key=lambda x: x.id), classifications={k: sorted(set(v)) for k, v in sorted(classifications.items())}, facts=facts, requirements=sorted(instances.values(), key=lambda x: x.id), controls={k: dict(sorted(v.items())) for k, v in sorted(controls.items())}, trace_file="trace.json")
        result.legacy_content_hash = content_hash(result.model_dump(
            mode="json",
            exclude={"content_hash", "legacy_content_hash", "conforms_to", "hash_algorithm"},
        ))
        semantic = SemanticDataset()
        media_types = {
            ".ttl": "text/turtle", ".trig": "application/trig",
            ".rq": "application/sparql-query", ".rif.xml": "application/rif+xml",
        }
        package_files = {
            name: [
                (path.name, next(media for suffix, media in media_types.items() if path.name.endswith(suffix)))
                for path in sorted((self.root / "knowledge" / name / manifest.version).iterdir())
                if path.is_file() and path.name != "package.trig" and path.name.endswith(tuple(media_types))
            ]
            for name, manifest in manifests.items()
        }
        semantic.add_source_models(
            spec, manifests, concepts, definitions.values(), rules, patterns,
            package_files=package_files,
        )
        semantic.add_glossary(load_academy_glossary(self.root), scheme_name="academy")
        semantic.add_glossary(load_product_glossary(self.product_file(product)), scheme_name="product")
        semantic.add_resolved(result, proofs=datalog.proofs)
        semantic.finalize()
        shacl = validate_dataset(semantic)
        if not shacl.conforms:
            raise SpecForgeError("SF3101", str(product), "/", shacl.report_text)
        semantic.add_evidence_graph(shacl.report_graph)
        result.content_hash = semantic.content_hash()
        semantic.add_hash_metadata(result.content_hash)
        self._semantic_cache[self.product_file(product).resolve()] = semantic
        if write:
            out = self.root / "generated" / spec.product.id
            data = result.model_dump(mode="json")
            write_if_changed(out / "resolved-spec.json", pretty_json(data))
            trace = {"schema_version": "1", "product": spec.product.model_dump(), "facts": [f.model_dump(mode="json") for f in facts], "requirements": [{"id": i.id, "derivations": [d.model_dump(mode="json") for d in i.derivations]} for i in result.requirements]}
            write_if_changed(out / "trace.json", pretty_json(trace))
            normalized = spec.model_dump(mode="json")
            write_if_changed(out / "normalized-product.json", pretty_json(normalized))
            declared_facts = [f.model_dump(mode="json") for f in facts if f.origin != FactOrigin.ONTOLOGY_DERIVED]
            semantic_facts = [f.model_dump(mode="json") for f in facts]
            write_if_changed(out / "normalized-facts.json", pretty_json(declared_facts))
            write_if_changed(out / "semantic-facts.json", pretty_json(semantic_facts))
            semantic.write(out)
            write_if_changed(out / "shacl-report.ttl", shacl.report_graph.serialize(format="turtle"))
        return result

    def semantic_dataset(self, product: str | Path) -> SemanticDataset:
        """Resolve the product and return its canonical RDF Dataset."""
        cache_key = self.product_file(product).resolve()
        if cache_key not in self._semantic_cache:
            self.resolve(product, write=False)
        return self._semantic_cache[cache_key]

    @staticmethod
    def _display_target(target: str) -> str:
        """Render the internal target key as a typed external identifier."""
        kind, separator, identifier = target.partition(".")
        return f"{kind}:{identifier}" if separator else target

    @staticmethod
    def _normalize_target(target: str) -> str:
        kind, separator, identifier = target.partition(":")
        return f"{kind}.{identifier}" if separator else target

    def explain(
        self,
        product: str | Path,
        requirement_id: str,
        *,
        target: str | None = None,
        group_by: str | None = None,
    ) -> str:
        resolved = self.resolve(product)
        by_id = {f.id: f for f in resolved.facts}
        instances = [i for i in resolved.requirements if i.requirement == requirement_id]
        if not instances:
            raise SpecForgeError("SF1404", requirement_id, "/", "requirement does not apply")
        if target:
            normalized_target = self._normalize_target(target)
            instances = [instance for instance in instances if instance.target == normalized_target]
            if not instances:
                raise SpecForgeError("SF1404", requirement_id, "/target", f"requirement does not apply to {target}")
        instances.sort(key=lambda instance: instance.target)
        supported_groupings = {None, "target.type", "rule", "resource"}
        if group_by not in supported_groupings and not (group_by or "").startswith("fact."):
            raise SpecForgeError("SF1410", requirement_id, "/group-by", "supported values: target.type, rule, resource, fact.<predicate>")
        lines: list[str] = []
        definition = instances[0]
        lines.extend([
            f"Requirement {definition.requirement}@{definition.requirement_version}",
            f"statement: {definition.statement}",
            f"source: {definition.source.document}@{definition.source.version}#{definition.source.section}",
            f"expectation: {definition.expectation.control} {definition.expectation.operator} {definition.expectation.value!r}",
            f"applies to: {len(instances)} target(s)",
        ])

        def group_keys(instance) -> list[str]:
            if group_by == "target.type":
                return [instance.target.partition(".")[0] or "untyped"]
            if group_by == "rule":
                return sorted({derivation.rule for derivation in instance.derivations}) or ["declared"]
            if group_by:
                predicate = "acts_on" if group_by == "resource" else group_by.removeprefix("fact.")
                values = sorted({str(fact.object) for fact in resolved.facts if fact.subject == instance.target and fact.predicate == predicate})
                return values or ["(none)"]
            return []

        if group_by:
            groups: dict[str, list[str]] = defaultdict(list)
            for instance in instances:
                for key in group_keys(instance):
                    groups[key].append(self._display_target(instance.target))
            lines.extend(["", f"Groups by {group_by}:"])
            for key, targets in sorted(groups.items()):
                lines.append(f"  {key}: {', '.join(sorted(targets))}")

        lines.extend(["", "Instances:"])

        def render_fact(fid: str, indent: int = 6):
            fact = by_id[fid]
            lines.append(" " * indent + f"{fact.subject} {fact.predicate} {fact.object!r} [{fact.origin.value}]")
            lines.append(" " * (indent + 2) + f"source: {fact.provenance}")
            for premise in fact.premises:
                render_fact(premise, indent + 2)
        for instance in instances:
            display_target = self._display_target(instance.target)
            lines.append(f"  {instance.id}")
            lines.append(f"    applies_to: {display_target}")
            for derivation in instance.derivations:
                lines.append(f"    derived_by: {derivation.rule}@{derivation.rule_version}")
                for fid in derivation.facts:
                    render_fact(fid)
            lines.append(f"    implementation_pattern: {instance.pattern}")
            lines.append("    verification_instances:")
            for verification in instance.verifications:
                lines.append(f"      {verification.id}@{display_target} ({verification.adapter})")
        return "\n".join(lines) + "\n"
