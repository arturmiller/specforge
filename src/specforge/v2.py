from __future__ import annotations

from collections import defaultdict
from enum import Enum
from pathlib import Path
import subprocess
from typing import Any, Literal

from pydantic import Field, model_validator

from .errors import SpecForgeError
from .io import content_hash, pretty_json, write_if_changed
from .model import ResolvedSpec, StrictModel


class TargetType(str, Enum):
    PRODUCT = "product"
    ENTITY = "entity"
    FIELD = "field"
    OPERATION = "operation"
    COMPONENT = "component"
    DEPLOYMENT = "deployment"
    ARTIFACT = "artifact"


class TypedTarget(StrictModel):
    type: TargetType
    id: str

    @classmethod
    def parse(cls, value: str | dict[str, str] | "TypedTarget") -> "TypedTarget":
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls.model_validate(value)
        kind, separator, identifier = value.partition(":")
        if not separator:
            kind, separator, identifier = value.partition(".")
        if not separator or not identifier:
            raise ValueError(f"invalid typed target: {value}")
        return cls(type=TargetType(kind), id=identifier)

    def canonical(self) -> str:
        return f"{self.type.value}:{self.id}"


class ObligationSource(StrictModel):
    requirement_instance: str
    package: str | None = None
    rule: str | None = None


class ImplementationObligation(StrictModel):
    id: str
    target: TypedTarget
    surface: str
    control: str
    expectation: Any
    derived_from: list[ObligationSource]
    dependencies: list[str] = Field(default_factory=list)


class MergeStrategy(str, Enum):
    EQUAL = "equal"
    INTERSECTION = "intersection"
    UNION = "union"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"


class ControlSemantics(StrictModel):
    surface: str
    strategy: MergeStrategy = MergeStrategy.EQUAL


DEFAULT_CONTROL_SEMANTICS: dict[str, ControlSemantics] = {
    "authentication": ControlSemantics(surface="identity"),
    "authorization": ControlSemantics(surface="data_access"),
    "ownership_enforced": ControlSemantics(surface="data_access"),
    "event_create": ControlSemantics(surface="persistence"),
    "event_read": ControlSemantics(surface="response"),
    "event_update": ControlSemantics(surface="persistence"),
    "event_delete": ControlSemantics(surface="persistence"),
    "event_time_interval": ControlSemantics(surface="input"),
    "response_data_minimization": ControlSemantics(surface="response"),
    "response_fields": ControlSemantics(surface="response", strategy=MergeStrategy.INTERSECTION),
    "allowed_fields": ControlSemantics(surface="response", strategy=MergeStrategy.INTERSECTION),
    "retention_days": ControlSemantics(surface="persistence", strategy=MergeStrategy.MINIMUM),
    "rate_limit": ControlSemantics(surface="traffic", strategy=MergeStrategy.MINIMUM),
    "audit_events": ControlSemantics(surface="observability", strategy=MergeStrategy.UNION),
}


class ConsolidationDecision(StrictModel):
    target: TypedTarget
    control: str
    strategy: MergeStrategy
    inputs: list[Any]
    result: Any
    sources: list[str]


class ConsolidationResult(StrictModel):
    semantics_version: Literal["2.0.0"] = "2.0.0"
    obligations: list[ImplementationObligation]
    decisions: list[ConsolidationDecision]


class ObligationConsolidator:
    def __init__(self, semantics: dict[str, ControlSemantics] | None = None):
        self.semantics = {**DEFAULT_CONTROL_SEMANTICS, **(semantics or {})}

    def from_resolved_spec(self, resolved: ResolvedSpec) -> ConsolidationResult:
        candidates: list[ImplementationObligation] = []
        package_by_document = {
            name: data for name, data in resolved.knowledge.packages.items()
        }
        for instance in resolved.requirements:
            target = TypedTarget.parse(instance.target)
            control = instance.expectation.control
            semantics = self.semantics.get(control, ControlSemantics(surface="implementation"))
            prefixes = {"SEC": "security", "PRIVACY": "privacy", "DATA": "data", "PRODUCT": "calendar", "OBS": "observability", "PLATFORM": "platform"}
            package = prefixes.get(instance.requirement.partition("-")[0])
            if package not in package_by_document:
                package = None
            candidates.append(
                ImplementationObligation(
                    id=f"obligation:{target.type.value}:{target.id}:{control.replace('_', '-')}",
                    target=target,
                    surface=semantics.surface,
                    control=control,
                    expectation=instance.expectation.value,
                    derived_from=[ObligationSource(requirement_instance=instance.id, package=package)],
                )
            )
        return self.consolidate(candidates)

    def consolidate(self, obligations: list[ImplementationObligation]) -> ConsolidationResult:
        groups: dict[tuple[str, str], list[ImplementationObligation]] = defaultdict(list)
        for obligation in obligations:
            groups[(obligation.target.canonical(), obligation.control)].append(obligation)
        merged: list[ImplementationObligation] = []
        decisions: list[ConsolidationDecision] = []
        for (target_key, control), items in sorted(groups.items()):
            items.sort(key=lambda item: tuple(source.requirement_instance for source in item.derived_from))
            target = TypedTarget.parse(target_key)
            semantics = self.semantics.get(control, ControlSemantics(surface=items[0].surface))
            values = [item.expectation for item in items]
            result = self._merge(semantics.strategy, values, target, control, items)
            sources = sorted({source.requirement_instance for item in items for source in item.derived_from})
            derived = sorted(
                {source.requirement_instance: source for item in items for source in item.derived_from}.values(),
                key=lambda source: source.requirement_instance,
            )
            merged.append(
                ImplementationObligation(
                    id=f"obligation:{target.type.value}:{target.id}:{control.replace('_', '-')}",
                    target=target,
                    surface=semantics.surface,
                    control=control,
                    expectation=result,
                    derived_from=derived,
                    dependencies=sorted({dep for item in items for dep in item.dependencies}),
                )
            )
            decisions.append(
                ConsolidationDecision(target=target, control=control, strategy=semantics.strategy, inputs=values, result=result, sources=sources)
            )
        return ConsolidationResult(obligations=merged, decisions=decisions)

    @staticmethod
    def _merge(
        strategy: MergeStrategy,
        values: list[Any],
        target: TypedTarget,
        control: str,
        items: list[ImplementationObligation],
    ) -> Any:
        canonical = {pretty_json(value) for value in values}
        if strategy == MergeStrategy.EQUAL:
            if len(canonical) != 1:
                sources = sorted(source.requirement_instance for item in items for source in item.derived_from)
                raise SpecForgeError("SF2301", target.canonical(), f"/{control}", f"incompatible values {values!r}; sources: {', '.join(sources)}; options (not applied): change a source expectation or define an explicit versioned merge semantic")
            return values[0]
        if strategy in {MergeStrategy.INTERSECTION, MergeStrategy.UNION}:
            sets = [set(value) for value in values]
            result = set.intersection(*sets) if strategy == MergeStrategy.INTERSECTION else set.union(*sets)
            return sorted(result)
        if strategy == MergeStrategy.MINIMUM:
            return min(values)
        if strategy == MergeStrategy.MAXIMUM:
            return max(values)
        raise AssertionError(strategy)


class DiffKind(str, Enum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    CHANGED = "CHANGED"


class SemanticChange(StrictModel):
    kind: DiffKind
    target: TypedTarget
    before: Any = None
    after: Any = None


class SemanticDiff(StrictModel):
    from_hash: str
    to_hash: str
    changes: list[SemanticChange]


def semantic_diff(before: ResolvedSpec, after: ResolvedSpec) -> SemanticDiff:
    def inventory(spec: ResolvedSpec) -> dict[str, Any]:
        result: dict[str, Any] = {f"product:{spec.product.id}": spec.product.model_dump(mode="json")}
        for entity in spec.entities:
            result[f"entity:{entity.id}"] = {"id": entity.id}
            for field in entity.fields:
                result[f"field:{entity.id}.{field.name}"] = field.model_dump(mode="json")
        for operation in spec.operations:
            result[f"operation:{operation.id}"] = operation.model_dump(mode="json")
        return result

    old, new = inventory(before), inventory(after)
    changes: list[SemanticChange] = []
    for key in sorted(set(old) | set(new)):
        if key not in old:
            changes.append(SemanticChange(kind=DiffKind.ADDED, target=TypedTarget.parse(key), after=new[key]))
        elif key not in new:
            changes.append(SemanticChange(kind=DiffKind.REMOVED, target=TypedTarget.parse(key), before=old[key]))
        elif old[key] != new[key]:
            changes.append(SemanticChange(kind=DiffKind.CHANGED, target=TypedTarget.parse(key), before=old[key], after=new[key]))
    return SemanticDiff(from_hash=before.content_hash, to_hash=after.content_hash, changes=changes)


class PathPermissions(StrictModel):
    may_modify: list[str]
    read_only: list[str]
    must_not_modify: list[str]


class VerificationPlan(StrictModel):
    mandatory: list[str]


class WorkOrderLimits(StrictModel):
    max_agent_runs: int = Field(default=1, ge=1)
    max_repair_runs: int = Field(default=2, ge=0)


class AgentWorkOrder(StrictModel):
    schema_version: Literal["2"] = "2"
    id: str
    product: dict[str, str]
    objective: dict[str, str]
    targets: list[TypedTarget]
    obligations: list[str]
    guidance: list[str]
    permissions: PathPermissions
    verification_plan: VerificationPlan
    limits: WorkOrderLimits = Field(default_factory=WorkOrderLimits)
    content_hash: str = ""

    @model_validator(mode="after")
    def validate_and_hash(self) -> "AgentWorkOrder":
        may_modify = set(self.permissions.may_modify)
        protected = set(self.permissions.read_only) | set(self.permissions.must_not_modify)
        if may_modify & protected:
            raise ValueError("modifiable and protected path rules overlap exactly")
        expected = content_hash(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash and self.content_hash != expected:
            raise ValueError("work order content hash mismatch")
        self.content_hash = expected
        return self


class ImpactScope(StrictModel):
    read_only: list[str]
    may_modify: list[str]
    must_not_modify: list[str]
    must_verify: list[str]


class ImplementationPlan(StrictModel):
    schema_version: Literal["2"] = "2"
    product: str
    resolved_spec_before: str
    resolved_spec_after: str
    targets: list[TypedTarget]
    obligations: list[ImplementationObligation]
    guidance: list[str]
    impact_scope: ImpactScope
    verification_plan: VerificationPlan
    risks: list[str]


def build_plan(root: Path, before: ResolvedSpec, after: ResolvedSpec) -> tuple[ImplementationPlan, AgentWorkOrder]:
    diff = semantic_diff(before, after)
    consolidation = ObligationConsolidator().from_resolved_spec(after)
    changed = {target.target.canonical() for target in diff.changes}
    obligations = [item for item in consolidation.obligations if item.target.canonical() in changed or item.target.type == TargetType.OPERATION]
    targets_by_id = {item.target.canonical(): item.target for item in obligations}
    targets_by_id.update({change.target.canonical(): change.target for change in diff.changes})
    targets = sorted(targets_by_id.values(), key=lambda item: item.canonical())
    verification_ids = sorted({verification.id for req in after.requirements for verification in req.verifications if verification.mandatory})
    guidance = sorted({req.pattern for req in after.requirements if req.pattern})
    scope = ImpactScope(
        read_only=["products/**", "knowledge/**", "generated/**/resolved-spec.json"],
        may_modify=["generated/*/app/**", "tests/**"],
        must_not_modify=["evidence/**"],
        must_verify=verification_ids,
    )
    plan = ImplementationPlan(
        product=after.product.id,
        resolved_spec_before=before.content_hash,
        resolved_spec_after=after.content_hash,
        targets=targets,
        obligations=obligations,
        guidance=guidance,
        impact_scope=scope,
        verification_plan=VerificationPlan(mandatory=verification_ids),
        risks=[],
    )
    order = AgentWorkOrder(
        id=f"work-order-{after.product.id}-{after.content_hash.split(':')[-1][:12]}",
        product={
            "id": after.product.id,
            "base_revision": workspace_revision(root),
            "resolved_spec_before": before.content_hash,
            "resolved_spec_after": after.content_hash,
        },
        objective={"type": "implement_resolved_spec_delta", "summary": f"Implement {len(diff.changes)} semantic change(s)."},
        targets=targets,
        obligations=[item.id for item in obligations],
        guidance=guidance,
        permissions=PathPermissions(
            may_modify=scope.may_modify,
            read_only=scope.read_only,
            must_not_modify=scope.must_not_modify,
        ),
        verification_plan=plan.verification_plan,
    )
    output = root / "generated" / after.product.id
    write_if_changed(output / "obligations.json", pretty_json(consolidation.model_dump(mode="json")))
    write_if_changed(output / "implementation-plan.json", pretty_json(plan.model_dump(mode="json")))
    write_if_changed(output / "impact-scope.json", pretty_json(scope.model_dump(mode="json")))
    write_if_changed(output / "work-orders" / f"{order.id}.json", pretty_json(order.model_dump(mode="json")))
    return plan, order


def workspace_revision(root: Path) -> str:
    """Bind a run to both HEAD and relevant uncommitted workspace bytes."""
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unversioned"
    ignored = {".git", ".venv", "node_modules", "dist", "__pycache__", ".pytest_cache", "generated", "evidence", "runs"}
    files = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_file() and not any(part in ignored for part in relative.parts):
            files.append((relative.as_posix(), content_hash(path.read_bytes().hex())))
    return f"{commit}+worktree.{content_hash(files).split(':', 1)[1][:20]}"
