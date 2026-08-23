# ADR 0001: Canonical typed intermediate model

Status: Superseded by ADR 0006 and ADR 0007

## Context

Product and knowledge authors need readable YAML while every compiler stage needs deterministic, validated inputs.

## Decision

Pydantic models form the compiler IR. YAML is validated at the boundary and canonical JSON is used for hashes and generated compiler artifacts.

## Consequences

Authors receive precise validation errors and file ordering cannot change results. Schema migrations must be explicit.
