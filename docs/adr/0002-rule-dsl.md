# ADR 0002: Restricted declarative rule DSL

Status: Accepted

## Context

Requirements must be derived reproducibly without embedding technology or arbitrary executable code in policy packages.

## Decision

V1 supports fact matching, variables, `all`, `any`, `not`, and equality. Evaluation is stable and side-effect free. Requirement definitions must include executable verification specifications.

## Consequences

The model is explainable and safe to evaluate. The DSL intentionally cannot express every possible policy; definitions that cannot be made machine-decidable remain outside the accepted package.

