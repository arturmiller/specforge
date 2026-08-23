# ADR 0006: Canonical semantic dataset and Datalog

Status: Superseded in its authoring-format decisions by ADR 0007

## Context

SpecForge's typed JSON graph, hard-coded semantic closure, Rule matcher,
Explorer graph and Evidence format duplicate concepts already standardized by
the Semantic Web. The accepted Semantic-Web Spec 0.3 requires interoperable
RDF, SHACL, SKOS, PROV-O, SPARQL, safe Datalog and RDFC-1.0 while retaining
deterministic local operation without a graph database.

## Decision

An in-memory RDF Dataset is the canonical compiler IR. A deep
`SemanticDataset` module owns stable IRIs, named graphs, vocabulary mappings,
serialization, SPARQL queries, SHACL reports, provenance and RDFC-1.0 hashing.
Pydantic models and the existing `ResolvedSpec` remain adapters and compatible
projections during one major-version transition.

The public base IRI is `https://specforge.dev/`. Term IRIs under
`https://specforge.dev/vocab/` remain stable; the ontology resource is versioned
as `https://specforge.dev/vocab/1.0.0`.

Safe positive Datalog is the only normative Rule semantics in version 1. The
existing YAML Rule syntax compiles to a canonical Rule IR. `any` expands to
multiple Rules. Unmarked negation is rejected; current Rules are migrated to
positive relations. The evaluator is local and provenance-aware. RIF Core is
the interchange format for the supported Rule subset.

RDFLib provides the RDF Dataset, JSON-LD, Turtle, N-Quads and local SPARQL
implementation. pySHACL provides SHACL Core validation with advanced features
disabled. `rdfcanon` provides the W3C RDFC-1.0 algorithm. Remote JSON-LD
contexts, remote RDF imports and SPARQL `SERVICE` are forbidden.

Knowledge authors may use YAML, JSON-LD or Turtle. YAML comments and original
formatting are not semantic and are not required to round-trip. A round-trip is
lossless when it preserves the canonical RDF Dataset and RDFC-1.0 hash.

OWL is unsupported until an explicit OWL-2-RL conformance profile is
implemented through the same Datalog engine. SWRL is rejected.

## Consequences

ADR 0001 is superseded: Pydantic remains an authoring adapter, not the
canonical IR, and RDFC-1.0 replaces canonical JSON as the semantic hash.

ADR 0002 is superseded: the readable YAML interface remains, but positive safe
Datalog defines Rule behavior and unmarked `not` is no longer accepted.

ADR 0003 remains valid in its deployment decision—no graph database is
required—but its proprietary typed graph and JSON trace are replaced by a
standards-based in-memory RDF Dataset and compatibility projections.

The minimum supported Python version becomes 3.12 because the conformant
RDFC-1.0 implementation requires it. Existing JSON and Evidence projections
remain for one major-version transition, after which their removal requires a
separate decision.
