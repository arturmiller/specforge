# ADR 0007: Standard semantic authoring formats

Status: Accepted

## Context

ADR 0006 standardized SpecForge's semantic intermediate representation but
still allowed the proprietary YAML model as an authoring language. That leaves
authors learning two representations and prevents ordinary Semantic Web tools
from validating the normative source directly.

## Decision

TriG is the Product and Package container format. Turtle contains single-graph
vocabularies, Requirements, Patterns, Verifications and SHACL Shapes. RIF Core
XML is the only persisted Rule format; safe positive Datalog remains its
execution semantics. Stored views are SPARQL 1.1 `.rq` resources. SKOS, RDFS,
DCAT, DCTERMS, PROV-O and SHACL are reused before introducing an `sf:` term.

Every hand-authored semantic statement has an immediately preceding learning
comment in everyday language. Comments are authoring lint, not RDF semantics,
and therefore do not affect the RDFC-1.0 content hash.

The normal compiler path accepts no fachliche YAML source. Legacy YAML is read
only by the explicit `migrate-format` command, which never overwrites its input.
Pydantic objects remain internal projections and validation adapters.

All processing remains local. Remote contexts, imports and SPARQL `SERVICE`
stay forbidden; a graph database is not required.

## Consequences

Standard RDF, RIF, SHACL and SPARQL tools can inspect the normative files
without a SpecForge parser. Authors must learn standard syntax, so the Explorer,
guided training and mandatory learning comments provide the readable layer.
JSON-LD, N-Quads and compatibility JSON remain generated representations.

This ADR supersedes the authoring-format decisions in ADR 0001, ADR 0002 and
ADR 0006. ADR 0006 remains authoritative for the canonical RDF Dataset,
positive-Datalog semantics, provenance and RDFC-1.0 hashing.
