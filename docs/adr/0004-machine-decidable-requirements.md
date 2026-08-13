# ADR 0004: Reject non-machine-decidable requirements

Status: Accepted

## Context

Vague policy language cannot produce a deterministic verification result.

## Decision

Every accepted Requirement Definition must contain a formal expectation and at least one mandatory executable verification. Invalid definitions fail package validation with a diagnostic instead of becoming a runtime status.

## Consequences

All resolved requirements can be evaluated by the machine. The report's scope is narrower than the source policy universe and must state that boundary explicitly.
