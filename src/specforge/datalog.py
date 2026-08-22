from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Any, Callable, Iterable

from .errors import SpecForgeError
from .io import canonical_json
from .model import Concept, Condition, Fact, FactOrigin, Rule


def is_variable(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("$")


@dataclass(frozen=True)
class Atom:
    relation: str
    terms: tuple[Any, ...]


@dataclass(frozen=True)
class Equality:
    left: Any
    right: Any


BodyTerm = Atom | Equality


@dataclass(frozen=True)
class DatalogRule:
    id: str
    version: str
    head: Atom
    body: tuple[BodyTerm, ...]
    source_id: str | None = None


@dataclass(frozen=True)
class Proof:
    rule: str
    rule_version: str
    bindings: tuple[tuple[str, str], ...]
    premises: tuple[str, ...]

    def binding_values(self) -> dict[str, Any]:
        return {name: _decode(value) for name, value in self.bindings}


@dataclass
class RelationRow:
    values: tuple[Any, ...]
    witnesses: set[tuple[str, ...]] = field(default_factory=set)
    proofs: set[Proof] = field(default_factory=set)


def _key(values: tuple[Any, ...]) -> tuple[str, ...]:
    return tuple(canonical_json(value) for value in values)


def _decode(value: str) -> Any:
    import json
    return json.loads(value)


class DatalogEngine:
    """Finite, positive, range-restricted Datalog with proof retention."""

    def __init__(self):
        self.relations: dict[str, dict[tuple[str, ...], RelationRow]] = {}

    def add_fact(self, relation: str, values: tuple[Any, ...], *, fact_id: str) -> None:
        relation_rows = self.relations.setdefault(relation, {})
        row = relation_rows.setdefault(_key(values), RelationRow(values))
        row.witnesses.add((fact_id,))

    def rows(self, relation: str) -> list[RelationRow]:
        return [self.relations[relation][key] for key in sorted(self.relations.get(relation, {}))]

    def evaluate(self, rules: Iterable[DatalogRule]) -> None:
        ordered = sorted(rules, key=lambda rule: (rule.id, rule.version, repr(rule.body)))
        for rule in ordered:
            validate_rule(rule)
        changed = True
        while changed:
            changed = False
            for rule in ordered:
                for bindings, premises in self._matches(rule.body):
                    values = tuple(_resolve(term, bindings) for term in rule.head.terms)
                    relation = self.relations.setdefault(rule.head.relation, {})
                    key = _key(values)
                    row = relation.setdefault(key, RelationRow(values))
                    proof = Proof(
                        rule=rule.source_id or rule.id,
                        rule_version=rule.version,
                        bindings=tuple(sorted((name, canonical_json(value)) for name, value in bindings.items())),
                        premises=tuple(sorted(premises)),
                    )
                    if proof not in row.proofs:
                        row.proofs.add(proof)
                        row.witnesses.add(proof.premises)
                        changed = True

    def _matches(self, body: tuple[BodyTerm, ...]) -> list[tuple[dict[str, Any], set[str]]]:
        states: list[tuple[dict[str, Any], set[str]]] = [({}, set())]
        for term in body:
            next_states: list[tuple[dict[str, Any], set[str]]] = []
            if isinstance(term, Atom):
                for bindings, premises in states:
                    for row in self.rows(term.relation):
                        candidate = dict(bindings)
                        if _match_terms(term.terms, row.values, candidate):
                            witness_sets = row.witnesses or {()}
                            for witnesses in witness_sets:
                                next_states.append((candidate, premises | set(witnesses)))
            else:
                for bindings, premises in states:
                    if _resolve(term.left, bindings) == _resolve(term.right, bindings):
                        next_states.append((bindings, premises))
            states = next_states
            if not states:
                break
        return states


def _resolve(term: Any, bindings: dict[str, Any]) -> Any:
    if is_variable(term):
        return bindings[term[1:]]
    return term


def _match_terms(patterns: tuple[Any, ...], values: tuple[Any, ...], bindings: dict[str, Any]) -> bool:
    if len(patterns) != len(values):
        return False
    for pattern, value in zip(patterns, values):
        if is_variable(pattern):
            name = pattern[1:]
            if name in bindings and bindings[name] != value:
                return False
            bindings[name] = value
        elif pattern != value:
            return False
    return True


def validate_rule(rule: DatalogRule) -> None:
    positive: set[str] = set()
    for term in rule.body:
        if isinstance(term, Atom):
            if is_variable(term.relation):
                raise SpecForgeError("SF1204", rule.id, "/when", "variable predicates are forbidden")
            positive.update(item[1:] for item in term.terms if is_variable(item))
        else:
            used = {item[1:] for item in (term.left, term.right) if is_variable(item)}
            if not used <= positive:
                raise SpecForgeError("SF1204", rule.id, "/when/equals", "built-in variables must be positively bound first")
    head_variables = {item[1:] for item in rule.head.terms if is_variable(item)}
    if not head_variables <= positive:
        raise SpecForgeError("SF1204", rule.id, "/then", "head variables must be positively bound")


def condition_alternatives(condition: Condition, rule_id: str) -> list[tuple[BodyTerm, ...]]:
    if condition.fact:
        if is_variable(condition.fact.predicate):
            raise SpecForgeError("SF1204", rule_id, "/when/fact/predicate", "variable predicates are forbidden")
        return [(Atom(condition.fact.predicate, (condition.fact.subject, condition.fact.object)),)]
    if condition.equals:
        return [(Equality(condition.equals[0], condition.equals[1]),)]
    if condition.not_ is not None:
        raise SpecForgeError("SF1203", rule_id, "/when/not", "negation is unsupported in positive Datalog")
    if condition.any is not None:
        return [alternative for child in condition.any for alternative in condition_alternatives(child, rule_id)]
    if condition.all is not None:
        child_alternatives = [condition_alternatives(child, rule_id) for child in condition.all]
        return [tuple(item for alternative in choices for item in alternative) for choices in product(*child_alternatives)]
    raise SpecForgeError("SF1201", rule_id, "/when", "empty condition")


def compile_requirement_rules(rules: Iterable[Rule]) -> list[DatalogRule]:
    compiled: list[DatalogRule] = []
    for rule in rules:
        for index, body in enumerate(condition_alternatives(rule.when, rule.id)):
            compiled.append(DatalogRule(
                id=f"{rule.id}#branch-{index + 1}",
                version=rule.version,
                head=Atom("requires", (rule.then.target, rule.then.requirement)),
                body=body,
                source_id=rule.id,
            ))
    return compiled


SEMANTIC_RULES = (
    DatalogRule("semantic/transitive-is-a", "1.0.0", Atom("is_a", ("$child", "$ancestor")), (
        Atom("is_a", ("$child", "$parent")), Atom("is_a", ("$parent", "$ancestor")),
    )),
    DatalogRule("semantic/classification-inheritance", "1.0.0", Atom("classified_as", ("$child", "$classification")), (
        Atom("is_a", ("$child", "$parent")), Atom("classified_as", ("$parent", "$classification")),
    )),
    DatalogRule("semantic/type-classification", "1.0.0", Atom("classified_as", ("$field", "$classification")), (
        Atom("has_type", ("$field", "$type")), Atom("classified_as", ("$type", "$classification")),
    )),
    DatalogRule("semantic/field-classification-propagation", "1.0.0", Atom("contains_classification", ("$entity", "$classification")), (
        Atom("has_field", ("$entity", "$field")), Atom("classified_as", ("$field", "$classification")),
    )),
)


@dataclass
class DatalogResult:
    facts: list[Fact]
    proofs: dict[str, list[Proof]]
    requirement_rows: list[RelationRow]


def evaluate(
    facts: list[Fact],
    concepts: Iterable[Concept],
    rules: Iterable[Rule],
    fact_id: Callable[[str, str, Any], str],
) -> DatalogResult:
    fact_by_key = {(fact.subject, fact.predicate, canonical_json(fact.object)): fact for fact in facts}
    for concept in concepts:
        for parent in concept.is_a:
            key = (concept.id, "is_a", canonical_json(parent))
            fact_by_key.setdefault(key, Fact(
                id=fact_id(concept.id, "is_a", parent), subject=concept.id, predicate="is_a", object=parent,
                origin=FactOrigin.ONTOLOGY_DERIVED, derivation="concept-declaration",
                provenance=f"{concept.source.document}@{concept.version}",
            ))
        for classification in concept.classifications:
            key = (concept.id, "classified_as", canonical_json(classification))
            fact_by_key.setdefault(key, Fact(
                id=fact_id(concept.id, "classified_as", classification), subject=concept.id,
                predicate="classified_as", object=classification, origin=FactOrigin.ONTOLOGY_DERIVED,
                derivation="concept-declaration", provenance=f"{concept.source.document}@{concept.version}",
            ))

    engine = DatalogEngine()
    for fact in fact_by_key.values():
        engine.add_fact(fact.predicate, (fact.subject, fact.object), fact_id=fact.id)
    engine.evaluate(SEMANTIC_RULES)

    proofs: dict[str, list[Proof]] = {}
    for relation, rows in engine.relations.items():
        for row in rows.values():
            if not row.proofs:
                continue
            subject, obj = row.values
            key = (str(subject), relation, canonical_json(obj))
            identifier = fact_id(str(subject), relation, obj)
            ordered_proofs = sorted(row.proofs, key=repr)
            proofs[identifier] = ordered_proofs
            first = ordered_proofs[0]
            fact_by_key.setdefault(key, Fact(
                id=identifier, subject=str(subject), predicate=relation, object=obj,
                origin=FactOrigin.ONTOLOGY_DERIVED, premises=list(first.premises),
                derivation=first.rule.removeprefix("semantic/"), provenance="semantic-closure",
            ))
            # Downstream rules cite the derived assertion itself. Its own proof
            # retains the complete preceding step, producing an inspectable chain.
            row.witnesses = {(identifier,)}

    # Requirement Rules consume the semantic closure and may recursively derive
    # only additional positive relations. Existing Facts remain immutable.
    engine.evaluate(compile_requirement_rules(rules))
    return DatalogResult(
        facts=sorted(fact_by_key.values(), key=lambda fact: (fact.subject, fact.predicate, canonical_json(fact.object))),
        proofs=proofs,
        requirement_rows=engine.rows("requires"),
    )
