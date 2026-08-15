# ADR 0005: Separate policy, product, and implementation knowledge

Status: Accepted

## Context

Reusable Privacy and Security knowledge must apply to products without knowing
their domain entities or technology stack. Previously, operations exposed one
ambiguous `resource` as a `returns` fact, Privacy verification listed Calendar
response fields, and the compiler selected `fastapi-react` patterns through a
hard-coded stack name.

## Decision

SpecForge separates three knowledge layers:

- Product specifications declare domain entities, classifications, operations,
  the resource each operation `acts_on`, its optional response entity in
  `returns`, response-field names, and the selected implementation stack.
- Policy packages contain generic Concepts, Rules, Requirements, and symbolic
  Verifications. Security Rules match `acts_on`; response policies match
  `returns`. A response-schema Verification derives its allowed fields from the
  resolved response entity.
- Implementation packages contain stack-specific Patterns. Pattern selection
  must match the Product's declared stack and fails when no Pattern or more than
  one Pattern matches.

Domain-specific Rules remain with their domain package. Therefore the Event
interval Rule belongs to Calendar knowledge, not a generic Data package.

## Consequences

Privacy and Security Rules can resolve against unrelated products that provide
the same generic Facts. Deleting a resource no longer implies returning it.
Response aliases such as `owner_id` are explicit Product schema data. Adding a
stack requires an implementation package rather than a compiler change.

Changing these inputs changes the canonical resolved-spec hash. The operation
schema is intentionally breaking and identified as Product schema version 2:
authors must replace `resource` with `acts_on` and declare `returns` only when
a response entity exists.
