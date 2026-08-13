# SPEC_V2 acceptance evidence

This matrix maps the normative V2 acceptance criteria to executable evidence. The authoritative wording remains in `plan/SPEC_V2.md`.

| # | Evidence |
|---|---|
| 1 | `tests/test_v2.py::test_typed_target_accepts_v1_and_v2_notation`; generic `TypedTarget` inventory in `semantic_diff` |
| 2 | `tests/test_v2.py::test_read_event_consolidates_at_least_five_requirements_from_five_packages` |
| 3 | `tests/test_v2.py::test_consolidator_deduplicates_and_preserves_all_sources` |
| 4 | `tests/test_v2.py::test_control_merge_semantics` and `test_incompatible_equal_controls_fail_before_agent_execution` |
| 5 | `tests/test_v2.py::test_incompatible_equal_controls_fail_before_agent_execution` |
| 6 | `tests/test_v2.py::test_build_plan_is_byte_deterministic` |
| 7 | `tests/test_v2.py::test_implement_dry_run_does_not_change_application` |
| 8 | `tests/test_v2.py::test_codex_adapter_passes_immutable_context_and_sandbox` |
| 9 | `tests/test_calendar_api.py::test_event_crud_for_owner`; `test_plan_includes_changed_field_target`; frontend contains the editable Location field |
| 10 | `tests/test_v2.py::test_permission_gate_rejects_out_of_scope_changes` |
| 11 | Product, knowledge, resolved spec, and verifier sources are outside `MAY_MODIFY`; changes are rejected by the Permission Gate |
| 12 | `tests/test_v2.py::test_permission_gate_accepts_only_may_modify` verifies run patch and V2 evidence creation |
| 13 | Existing mutation test `tests/test_end_to_end.py::test_removed_read_authentication_fails_sec_001_with_observation` |
| 14 | `tests/test_v2.py::test_repair_order_contains_only_original_scope_and_failures` |
| 15 | `tests/test_v2.py::test_repair_order_contains_only_original_scope_and_failures` verifies exhausted repair limits |
| 16 | Acceptance depends only on deterministic gates and obligations, not byte identity of agent output |
| 17 | `tests/test_end_to_end.py::test_frontend_color_change_does_not_change_resolved_spec_hash` |
| 18 | `tests/test_v2.py::test_repository_has_no_template_resources` |
| 19 | V2 run evidence and `create_report` include adapter, model, work order, diff, and gates |
| 20 | `tests/test_end_to_end.py::test_report_is_scoped_and_uses_matching_evidence` |

Run the complete automated suite with:

```powershell
.\.venv\Scripts\python -m pytest -q
```

Run the deterministic gates against the current work order with `DeterministicGates.run(...)`. The gate set is Permission, Schema, Build, Static, Requirement, Regression, and Evidence.
