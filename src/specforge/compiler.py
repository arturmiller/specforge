from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .errors import SpecForgeError
from .io import canonical_json, content_hash, directory_hash, pretty_json, read_yaml, write_if_changed
from .model import (
    Concept, Condition, Derivation, Fact, FactOrigin, KnowledgeVersions, Pattern,
    ProductSpec, RequirementDefinition, RequirementInstance, RequirementStatus,
    ResolvedSpec, Rule,
)


class Compiler:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def product_file(self, product: str | Path) -> Path:
        path = Path(product)
        if not path.is_absolute():
            path = self.root / path
        if path.is_dir():
            path /= "product.yaml"
        return path

    def load_model(self, path: Path, model: type[Any]) -> Any:
        try:
            return model.model_validate(read_yaml(path))
        except (ValidationError, ValueError) as exc:
            raise SpecForgeError("SF1001", str(path.relative_to(self.root)), "/", str(exc)) from exc

    def load_inputs(self, product: str | Path):
        product_path = self.product_file(product)
        spec = self.load_model(product_path, ProductSpec)
        concepts: list[Concept] = []
        requirements: dict[str, RequirementDefinition] = {}
        rules: list[Rule] = []
        patterns: list[Pattern] = []
        packages: dict[str, dict[str, str]] = {}
        for namespace, version in sorted(spec.knowledge_dependencies.items()):
            package = self.root / "knowledge" / namespace / version
            if not package.is_dir():
                raise SpecForgeError("SF1004", str(product_path.relative_to(self.root)), "/knowledge_dependencies", f"missing {namespace}@{version}")
            manifest_path = package / "package.yaml"
            manifest = read_yaml(manifest_path)
            if manifest.get("name") != namespace or manifest.get("version") != version:
                raise SpecForgeError("SF1005", str(manifest_path.relative_to(self.root)), "/", "package identity/version mismatch")
            packages[namespace] = {"version": version, "hash": directory_hash(package)}
            for path in sorted(package.glob("concepts/*.yaml")):
                concepts.append(self.load_model(path, Concept))
            for path in sorted(package.glob("requirements/*.yaml")):
                requirement = self.load_model(path, RequirementDefinition)
                if requirement.id in requirements:
                    raise SpecForgeError("SF1002", str(path.relative_to(self.root)), "/id", f"duplicate requirement {requirement.id}")
                requirements[requirement.id] = requirement
            for path in sorted(package.glob("rules/*.yaml")):
                rules.append(self.load_model(path, Rule))
            for path in sorted(package.glob("patterns/*.yaml")):
                patterns.append(self.load_model(path, Pattern))
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
            add(entity.id, "is_entity", True, f"product.yaml#/entities/{entity.id}")
            for field in sorted(entity.fields, key=lambda x: x.name):
                field_id = f"{entity.id}.{field.name}"
                add(entity.id, "has_field", field_id, f"product.yaml#/entities/{entity.id}/fields/{field.name}")
                add(field_id, "has_type", field.type, f"product.yaml#/entities/{entity.id}/fields/{field.name}/type")
                if field.classification:
                    add(field_id, "classified_as", field.classification, f"product.yaml#/entities/{entity.id}/fields/{field.name}/classification")
                if field.relation:
                    add(field_id, "relation", field.relation, f"product.yaml#/entities/{entity.id}/fields/{field.name}/relation")
        for op in sorted(spec.operations, key=lambda x: x.id):
            prefix = f"operation.{op.id}"
            provenance = f"product.yaml#/operations/{op.id}"
            add(prefix, "action", op.action, provenance)
            add(prefix, "returns", op.resource, provenance)
            add(prefix, "actor", op.actor, provenance)
            add(prefix, "scope", op.scope, provenance)
        return sorted(facts.values(), key=lambda f: (f.subject, f.predicate, str(f.object)))

    def enrich(self, facts: list[Fact], concepts: list[Concept]) -> list[Fact]:
        by_key = {(f.subject, f.predicate, canonical_json(f.object)): f for f in facts}
        def add(subject: str, predicate: str, obj: Any, premises: list[Fact], derivation: str, provenance: str) -> bool:
            key = (subject, predicate, canonical_json(obj))
            if key in by_key:
                return False
            by_key[key] = Fact(id=self.fact_id(subject, predicate, obj), subject=subject, predicate=predicate, object=obj, origin=FactOrigin.ONTOLOGY_DERIVED, premises=sorted(f.id for f in premises), derivation=derivation, provenance=provenance)
            return True
        for concept in concepts:
            for parent in concept.is_a:
                add(concept.id, "is_a", parent, [], "concept-declaration", f"{concept.source.document}@{concept.version}")
            for classification in concept.classifications:
                add(concept.id, "classified_as", classification, [], "concept-declaration", f"{concept.source.document}@{concept.version}")
        changed = True
        while changed:
            changed = False
            current = list(by_key.values())
            is_a = [f for f in current if f.predicate == "is_a"]
            classified = [f for f in current if f.predicate == "classified_as"]
            types = [f for f in current if f.predicate == "has_type"]
            fields = [f for f in current if f.predicate == "has_field"]
            for left in is_a:
                for right in is_a:
                    if left.object == right.subject:
                        changed |= add(left.subject, "is_a", right.object, [left, right], "transitive-is-a", "semantic-closure")
                for cls in classified:
                    if left.object == cls.subject:
                        changed |= add(left.subject, "classified_as", cls.object, [left, cls], "classification-inheritance", "semantic-closure")
            for typed in types:
                for cls in classified:
                    if typed.object == cls.subject:
                        changed |= add(typed.subject, "classified_as", cls.object, [typed, cls], "type-classification", "semantic-closure")
            current_classified = [f for f in by_key.values() if f.predicate == "classified_as"]
            for field in fields:
                for cls in current_classified:
                    if field.object == cls.subject:
                        changed |= add(field.subject, "contains_classification", cls.object, [field, cls], "field-classification-propagation", "semantic-closure")
        return sorted(by_key.values(), key=lambda f: (f.subject, f.predicate, str(f.object)))

    def match(self, condition: Condition, facts: list[Fact], bindings: dict[str, Any]) -> list[tuple[dict[str, Any], list[Fact]]]:
        if condition.fact:
            results = []
            for fact in facts:
                candidate = dict(bindings)
                if self._match_value(condition.fact.subject, fact.subject, candidate) and self._match_value(condition.fact.predicate, fact.predicate, candidate) and self._match_value(condition.fact.object, fact.object, candidate):
                    results.append((candidate, [fact]))
            return results
        if condition.equals:
            left, right = condition.equals
            left = bindings.get(left[1:], left) if isinstance(left, str) and left.startswith("$") else left
            right = bindings.get(right[1:], right) if isinstance(right, str) and right.startswith("$") else right
            return [(dict(bindings), [])] if left == right else []
        if condition.all is not None:
            states = [(dict(bindings), [])]
            for child in condition.all:
                states = [(new_b, used + new_f) for old_b, used in states for new_b, new_f in self.match(child, facts, old_b)]
            return states
        if condition.any is not None:
            return [item for child in condition.any for item in self.match(child, facts, dict(bindings))]
        if condition.not_ is not None:
            return [] if self.match(condition.not_, facts, dict(bindings)) else [(dict(bindings), [])]
        return []

    @staticmethod
    def _match_value(pattern: Any, actual: Any, bindings: dict[str, Any]) -> bool:
        if isinstance(pattern, str) and pattern.startswith("$"):
            key = pattern[1:]
            if key in bindings:
                return bindings[key] == actual
            bindings[key] = actual
            return True
        return pattern == actual

    def resolve(self, product: str | Path, write: bool = True) -> ResolvedSpec:
        spec, concepts, definitions, rules, patterns, packages = self.load_inputs(product)
        facts = self.enrich(self.normalize(spec), concepts)
        instances: dict[tuple[str, str], RequirementInstance] = {}
        for declared in sorted(spec.declared_requirements, key=lambda x: x.id):
            definition = definitions[declared.id]
            target = f"operation.{declared.operation}"
            instances[(declared.id, target)] = RequirementInstance(id=f"{declared.id}@{target}", requirement=declared.id, requirement_version=definition.version, statement=definition.statement, source=definition.source, target=target, kind="declared", status=RequirementStatus.REQUIRED, expectation=definition.expectation, verifications=definition.verifications)
        for rule in rules:
            for bindings, used in self.match(rule.when, facts, {}):
                target = rule.then.target
                if target.startswith("$"):
                    target = str(bindings[target[1:]])
                definition = definitions[rule.then.requirement]
                key = (definition.id, target)
                derivation = Derivation(rule=rule.id, rule_version=rule.version, facts=sorted({f.id for f in used}), bindings=dict(sorted(bindings.items())))
                if key not in instances:
                    instances[key] = RequirementInstance(id=f"{definition.id}@{target}", requirement=definition.id, requirement_version=definition.version, statement=definition.statement, source=definition.source, target=target, kind="derived", status=RequirementStatus.REQUIRED, expectation=definition.expectation, verifications=definition.verifications, derivations=[derivation])
                elif derivation not in instances[key].derivations:
                    instances[key].derivations.append(derivation)
        selected_patterns: dict[str, Pattern] = {}
        for instance in instances.values():
            def supports(pattern: Pattern) -> bool:
                legacy = (
                    instance.requirement in pattern.satisfies
                    and pattern.stack == "fastapi-react"
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
                return (legacy or addressed) and all(v.id in pattern.verifications for v in instance.verifications)

            matching = [pattern for pattern in patterns if supports(pattern)]
            if not matching:
                raise SpecForgeError("SF1501", instance.requirement, instance.target, "no compatible implementation pattern")
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
        hash_input = result.model_dump(mode="json", exclude={"content_hash"})
        result.content_hash = content_hash(hash_input)
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
        return result

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
                predicate = "returns" if group_by == "resource" else group_by.removeprefix("fact.")
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
