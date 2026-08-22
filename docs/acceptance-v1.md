# V1 Acceptance Matrix

This matrix maps every acceptance criterion from `plan/SPEC_V1.md` to executable evidence.

| # | Criterion | Automated evidence |
|---|---|---|
| 1 | Calendar Product Spec loads and normalizes | `tests/test_compiler.py::test_calendar_resolves_declared_and_derived_requirements`; `generated/calendar/normalized-product.json` and `normalized-facts.json` |
| 2 | `Event contains PersonalData` is inferred | `tests/test_compiler.py::test_semantic_closure_classifies_event_as_containing_personal_data`; `semantic-facts.json` |
| 3 | Product, Security, Privacy, and Data requirements resolve | `tests/test_compiler.py::test_calendar_resolves_declared_and_derived_requirements` |
| 4 | `explain SEC-001` provides the complete chain | `tests/test_compiler.py::test_explain_has_full_security_derivation_and_verification` |
| 5 | Generated Calendar application starts locally | API construction and requests in `tests/test_calendar_api.py`; frontend production build; `docker compose config --quiet` |
| 6 | CRUD, authentication, ownership, privacy, and interval checks pass | `tests/test_calendar_api.py`; `specforge validate products/calendar` |
| 7 | Removed GET authentication fails with precise evidence | `tests/test_end_to_end.py::test_removed_read_authentication_fails_sec_001_with_observation` |
| 8 | Button color does not change the Resolved Spec | `tests/test_end_to_end.py::test_frontend_color_change_does_not_change_resolved_spec_hash` |
| 9 | Requirement without executable Verification is rejected | `tests/test_compiler.py::test_requirement_without_executable_verification_is_rejected` |
| 10 | Identical inputs produce byte-identical canonical artifacts | `tests/test_compiler.py::test_resolve_is_byte_deterministic` |
| 11 | Report is scoped and makes no global compliance claim | `tests/test_end_to_end.py::test_report_is_scoped_and_uses_matching_evidence` |

Additional governance coverage:

- legacy DSL projection operators: `test_legacy_match_projection_still_reads_all_any_not_and_equals`,
- conflicting policies: `tests/test_conflicts.py`,
- exact application observations and revision-bound Evidence: `test_generation_and_validation_produce_complete_evidence`.

Canonical release verification:

```bash
uv sync --extra dev
uv run specforge resolve products/calendar
uv run specforge generate products/calendar
uv run specforge validate products/calendar
uv run specforge report products/calendar
uv run pytest -q
cd generated/calendar/app/frontend
npm install
npm run build
docker compose config --quiet
```

Building or starting the containers additionally requires a running Docker daemon.
