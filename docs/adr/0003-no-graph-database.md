# ADR 0003: No graph database in V1

Status: Accepted

## Context

Traceability and semantic closure need graph traversal, but V1 has a small bounded data set and no shared online query service.

## Decision

Use typed in-memory structures and emit a canonical JSON trace graph.

## Consequences

Deployment and reproducibility stay simple. A graph database can later consume the emitted graph without changing compiler semantics.

