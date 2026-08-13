from pathlib import Path

import pytest
from typer.testing import CliRunner
from types import SimpleNamespace

from specforge.compiler import Compiler
from specforge.errors import SpecForgeError
from specforge.v2 import (
    AgentWorkOrder,
    ImplementationObligation,
    MergeStrategy,
    ObligationConsolidator,
    ObligationSource,
    PathPermissions,
    TypedTarget,
    VerificationPlan,
    build_plan,
    semantic_diff,
)
from specforge.agents.protocol import AgentExecution, AgentRunStatus
from specforge.agents.codex import CodexAdapter
from specforge.runs import GateResult, RunManager, create_repair_order
from specforge.cli import app


ROOT = Path(__file__).parents[1]
PRODUCT = "products/calendar"


def obligation(control, value, requirement="REQ-1"):
    return ImplementationObligation(
        id=f"obligation:operation:read_event:{control}",
        target=TypedTarget.parse("operation:read_event"),
        surface="test",
        control=control,
        expectation=value,
        derived_from=[ObligationSource(requirement_instance=f"{requirement}@operation:read_event")],
    )


def test_typed_target_accepts_v1_and_v2_notation():
    assert TypedTarget.parse("operation.read_event").canonical() == "operation:read_event"
    assert TypedTarget.parse("field:Event.location").id == "Event.location"


def test_consolidator_deduplicates_and_preserves_all_sources():
    result = ObligationConsolidator().consolidate([
        obligation("authentication", "required", "SEC-1"),
        obligation("authentication", "required", "SEC-2"),
    ])
    assert len(result.obligations) == 1
    assert [item.requirement_instance for item in result.obligations[0].derived_from] == [
        "SEC-1@operation:read_event",
        "SEC-2@operation:read_event",
    ]


@pytest.mark.parametrize(
    ("control", "values", "expected", "strategy"),
    [
        ("allowed_fields", [["id", "title"], ["id", "description"]], ["id"], MergeStrategy.INTERSECTION),
        ("audit_events", [["allowed"], ["denied"]], ["allowed", "denied"], MergeStrategy.UNION),
        ("retention_days", [30, 14], 14, MergeStrategy.MINIMUM),
    ],
)
def test_control_merge_semantics(control, values, expected, strategy):
    result = ObligationConsolidator().consolidate([obligation(control, value, f"REQ-{index}") for index, value in enumerate(values)])
    assert result.obligations[0].expectation == expected
    assert result.decisions[0].strategy == strategy


def test_incompatible_equal_controls_fail_before_agent_execution():
    with pytest.raises(SpecForgeError, match="SF2301"):
        ObligationConsolidator().consolidate([
            obligation("authentication", "required", "SEC-1"),
            obligation("authentication", "forbidden", "SEC-2"),
        ])


def test_semantic_diff_uses_field_target_not_text_lines():
    before = Compiler(ROOT).resolve(PRODUCT, write=False)
    after = before.model_copy(deep=True)
    after.entities[0].fields[0].classification = "Changed"
    after.content_hash = "sha256:changed"
    result = semantic_diff(before, after)
    assert any(change.target.type.value == "field" and change.kind.value == "CHANGED" for change in result.changes)


def test_work_order_hash_is_stable_and_tamper_evident():
    data = dict(
        id="work-order-1",
        product={"id": "calendar"},
        objective={"type": "implement"},
        targets=[TypedTarget.parse("operation:read_event")],
        obligations=["obligation:operation:read_event:authentication"],
        guidance=[],
        permissions=PathPermissions(may_modify=["app/**"], read_only=["products/**"], must_not_modify=["evidence/**"]),
        verification_plan=VerificationPlan(mandatory=["TEST-1"]),
    )
    first = AgentWorkOrder(**data)
    second = AgentWorkOrder(**data)
    assert first.content_hash == second.content_hash
    with pytest.raises(ValueError, match="hash mismatch"):
        AgentWorkOrder(**data, content_hash="sha256:wrong")


def test_build_plan_is_byte_deterministic(tmp_path):
    resolved = Compiler(ROOT).resolve(PRODUCT, write=False)
    first_plan, first_order = build_plan(tmp_path, resolved, resolved)
    first_bytes = (tmp_path / "generated/calendar/implementation-plan.json").read_bytes()
    second_plan, second_order = build_plan(tmp_path, resolved, resolved)
    assert first_plan == second_plan
    assert first_order.content_hash == second_order.content_hash
    assert (tmp_path / "generated/calendar/implementation-plan.json").read_bytes() == first_bytes


def test_plan_includes_changed_field_target(tmp_path):
    after = Compiler(ROOT).resolve(PRODUCT, write=False)
    before = after.model_copy(deep=True)
    event = next(entity for entity in before.entities if entity.id == "Event")
    event.fields = [field for field in event.fields if field.name != "location"]
    before.content_hash = "sha256:before-location"
    plan, order = build_plan(tmp_path, before, after)
    assert "field:Event.location" in [target.canonical() for target in plan.targets]
    assert "field:Event.location" in [target.canonical() for target in order.targets]


def test_read_event_consolidates_at_least_five_requirements_from_five_packages():
    resolved = Compiler(ROOT).resolve(PRODUCT, write=False)
    applicable = [item for item in resolved.requirements if item.target == "operation.read_event"]
    assert len(applicable) >= 5
    assert {item.requirement.split("-")[0] for item in applicable} >= {"PRODUCT", "SEC", "PRIVACY", "OBS", "PLATFORM"}
    result = ObligationConsolidator().from_resolved_spec(resolved)
    read_obligations = [item for item in result.obligations if item.target.canonical() == "operation:read_event"]
    assert len(read_obligations) >= 5


def test_implement_dry_run_does_not_change_application(monkeypatch):
    monkeypatch.chdir(ROOT)
    app_root = ROOT / "generated/calendar/app"
    before = {path.relative_to(app_root): path.read_bytes() for path in app_root.rglob("*") if path.is_file() and "node_modules" not in path.parts and "dist" not in path.parts}
    result = CliRunner().invoke(app, ["implement", PRODUCT, "--agent", "codex", "--dry-run"])
    after = {path.relative_to(app_root): path.read_bytes() for path in app_root.rglob("*") if path.is_file() and "node_modules" not in path.parts and "dist" not in path.parts}
    assert result.exit_code == 0, result.output
    assert '"schema_version": "2"' in result.output
    assert after == before


class WritingAdapter:
    provider = "test"

    def __init__(self, path):
        self.path = path

    def execute(self, work_order, workspace, configuration):
        target = workspace / self.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("changed", encoding="utf-8")
        return AgentExecution(status=AgentRunStatus.COMPLETED, provider="test", model="fake", version="1", exit_code=0)


class PassingGates:
    def run(self, root, work_order):
        return [GateResult(id="test", result="PASS", expected={}, observed={})]


def run_order():
    return AgentWorkOrder(
        id="work-order-run",
        product={"id": "calendar", "base_revision": "sha256:base"},
        objective={"type": "implement"},
        targets=[TypedTarget.parse("operation:read_event")],
        obligations=[],
        guidance=[],
        permissions=PathPermissions(may_modify=["app/**"], read_only=["products/**"], must_not_modify=["evidence/**"]),
        verification_plan=VerificationPlan(mandatory=[]),
    )


def test_permission_gate_accepts_only_may_modify(tmp_path):
    result = RunManager(tmp_path).execute(run_order(), WritingAdapter("app/service.py"), gate_runner=PassingGates())
    assert result.status == AgentRunStatus.COMPLETED
    assert result.work_order_status.value == "ACCEPTED"
    assert result.changes[0].path == "app/service.py"
    run_dir = tmp_path / "runs/calendar" / result.id
    assert (run_dir / "changes.patch").read_text(encoding="utf-8").startswith("--- a/app/service.py")
    assert (run_dir / "evidence.json").exists()


def test_permission_gate_rejects_out_of_scope_changes(tmp_path):
    result = RunManager(tmp_path).execute(run_order(), WritingAdapter("products/calendar/product.yaml"), gate_runner=PassingGates())
    assert result.status == AgentRunStatus.PERMISSION_VIOLATION
    assert result.work_order_status.value == "REJECTED"
    assert result.permission_violations == ["products/calendar/product.yaml"]


def test_repair_order_contains_only_original_scope_and_failures(tmp_path):
    order = run_order()
    run = RunManager(tmp_path).execute(order, WritingAdapter("products/calendar/product.yaml"), gate_runner=PassingGates())
    repair = create_repair_order(order, run, attempt=1)
    assert repair.original_work_order.permissions == order.permissions
    assert [gate.id for gate in repair.failed_gates] == ["permission"]
    assert repair.remaining_attempts == 1
    with pytest.raises(ValueError, match="repair limit exhausted"):
        create_repair_order(order, run, attempt=3)


def test_repository_has_no_template_resources():
    assert not (ROOT / "templates").exists() or not any(path.is_file() for path in (ROOT / "templates").rglob("*"))
    source_mentions = []
    for path in (ROOT / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        if "template_root" in text or "jinja" in text:
            source_mentions.append(path)
    assert source_mentions == []


def test_codex_adapter_passes_immutable_context_and_sandbox(monkeypatch, tmp_path):
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["input"] = kwargs["input"]
        return SimpleNamespace(returncode=0, stdout='{"type":"done"}\n')

    monkeypatch.setattr("specforge.agents.codex.subprocess.run", fake_run)
    result = CodexAdapter().execute(run_order(), tmp_path, {})
    assert result.status == AgentRunStatus.COMPLETED
    assert "workspace-write" in captured["args"]
    assert "sandbox_workspace_write.network_access=false" in captured["args"]
    assert '"work_order"' in captured["input"]
    assert '"resolved_spec"' in captured["input"]
    assert '"selected_patterns"' in captured["input"]
