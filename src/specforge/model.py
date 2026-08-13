from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Provenance(StrictModel):
    type: str
    document: str
    version: str
    section: str


class ProductIdentity(StrictModel):
    id: str
    version: str


class EntityField(StrictModel):
    name: str
    type: str
    relation: str | None = None
    classification: str | None = None
    optional: bool = False


class Entity(StrictModel):
    id: str
    fields: list[EntityField]


class Operation(StrictModel):
    id: str
    action: Literal["create", "read", "update", "delete"]
    resource: str
    actor: str
    scope: str


class DeclaredRequirement(StrictModel):
    id: str
    operation: str
    statement: str


class ProductSpec(StrictModel):
    schema_version: Literal["1"]
    product: ProductIdentity
    entities: list[Entity]
    operations: list[Operation]
    declared_requirements: list[DeclaredRequirement]
    knowledge_dependencies: dict[str, str]

    @model_validator(mode="after")
    def references_and_ids(self) -> "ProductSpec":
        entities = {entity.id for entity in self.entities}
        operations = {operation.id for operation in self.operations}
        if len(entities) != len(self.entities) or len(operations) != len(self.operations):
            raise ValueError("SF1002 duplicate id within target type")
        for entity in self.entities:
            names = [field.name for field in entity.fields]
            if len(names) != len(set(names)):
                raise ValueError(f"SF1002 duplicate field id in {entity.id}")
        for operation in self.operations:
            if operation.resource not in entities or operation.actor not in entities:
                raise ValueError(f"SF1003 unresolved operation reference: {operation.id}")
        for requirement in self.declared_requirements:
            if requirement.operation not in operations:
                raise ValueError(f"SF1003 unresolved operation: {requirement.operation}")
        return self


class Concept(StrictModel):
    id: str
    version: str
    is_a: list[str] = Field(default_factory=list)
    classifications: list[str] = Field(default_factory=list)
    source: Provenance


class Expectation(StrictModel):
    control: str
    operator: Literal["equals"]
    value: Any


class AssertionSpec(StrictModel):
    response_status: int | None = None
    response_fields: list[str] | None = None
    invariant: str | None = None
    stored_matches: bool | None = None
    resource_matches: bool | None = None
    after_status: int | None = None
    audit_event: str | None = None
    max_requests_per_minute: int | None = None

    @model_validator(mode="after")
    def nonempty(self) -> "AssertionSpec":
        if not self.model_dump(exclude_none=True):
            raise ValueError("SF1101 verification assertion must be executable")
        return self


class VerificationSpec(StrictModel):
    id: str
    adapter: Literal["http_request", "response_schema", "domain_invariant", "audit_log", "rate_limit"]
    setup: str
    assertion: AssertionSpec
    mandatory: bool = True


class RequirementDefinition(StrictModel):
    id: str
    version: str
    statement: str
    expectation: Expectation
    verifications: list[VerificationSpec]
    source: Provenance

    @model_validator(mode="after")
    def executable(self) -> "RequirementDefinition":
        if not self.verifications or not any(v.mandatory for v in self.verifications):
            raise ValueError("SF1101 requirement has no mandatory executable verification")
        return self


class FactPattern(StrictModel):
    subject: str
    predicate: str
    object: Any


class Condition(StrictModel):
    fact: FactPattern | None = None
    all: list["Condition"] | None = None
    any: list["Condition"] | None = None
    not_: "Condition | None" = Field(default=None, alias="not")
    equals: list[Any] | None = None

    @model_validator(mode="after")
    def exactly_one(self) -> "Condition":
        values = [self.fact is not None, self.all is not None, self.any is not None, self.not_ is not None, self.equals is not None]
        if sum(values) != 1:
            raise ValueError("SF1201 condition must have exactly one supported operator")
        return self


class RuleResult(StrictModel):
    requirement: str
    target: str


class Rule(StrictModel):
    id: str
    version: str
    when: Condition
    then: RuleResult
    source: Provenance


class Pattern(StrictModel):
    id: str
    version: str
    owner: str | None = None
    satisfies: list[str] = Field(default_factory=list)
    stack: str | None = None
    controls: dict[str, Any] = Field(default_factory=dict)
    verifications: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    addresses: dict[str, Any] | None = None
    compatible_with: dict[str, str] = Field(default_factory=dict)
    requires: list[str] = Field(default_factory=list)
    constraints: dict[str, list[str]] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    examples: list[dict[str, str]] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def contains_no_templates(self) -> "Pattern":
        resources = [*self.artifacts, *(item.get("resource", "") for item in self.examples)]
        if any("template" in resource.lower() for resource in resources):
            raise ValueError("SF2501 templates are forbidden in V2 patterns")
        return self


class FactOrigin(str, Enum):
    DECLARED = "DECLARED"
    NORMALIZED = "NORMALIZED"
    ONTOLOGY_DERIVED = "ONTOLOGY_DERIVED"


class Fact(StrictModel):
    id: str
    subject: str
    predicate: str
    object: Any
    origin: FactOrigin
    premises: list[str] = Field(default_factory=list)
    derivation: str | None = None
    provenance: str


class RequirementStatus(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    REQUIRED = "REQUIRED"
    IMPLEMENTED = "IMPLEMENTED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


class Derivation(StrictModel):
    rule: str
    rule_version: str
    facts: list[str]
    bindings: dict[str, Any]


class RequirementInstance(StrictModel):
    id: str
    requirement: str
    requirement_version: str
    statement: str
    source: Provenance
    target: str
    kind: Literal["declared", "derived"]
    status: RequirementStatus
    expectation: Expectation
    derivations: list[Derivation] = Field(default_factory=list)
    pattern: str | None = None
    verifications: list[VerificationSpec]


class KnowledgeVersions(StrictModel):
    packages: dict[str, dict[str, str]]


class ResolvedSpec(StrictModel):
    schema_version: Literal["1"] = "1"
    product: ProductIdentity
    knowledge: KnowledgeVersions
    entities: list[Entity]
    operations: list[Operation]
    classifications: dict[str, list[str]]
    facts: list[Fact]
    requirements: list[RequirementInstance]
    controls: dict[str, dict[str, Any]]
    trace_file: str
    content_hash: str = ""


class EvidenceEntry(StrictModel):
    id: str
    requirement_instance: str
    verification_id: str
    verification_definition: str
    verification_type: str
    expected: dict[str, Any]
    observed: dict[str, Any]
    result: Literal["PASS", "FAIL"]
    git_commit: str
    resolved_spec_hash: str
    knowledge_packages: dict[str, dict[str, str]]
    tool: str
    tool_version: str
    timestamp: str


Condition.model_rebuild()
