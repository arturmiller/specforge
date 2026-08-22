# Semantic Web Conformance

Stand: 2026-08-22 · Profil: SpecForge Semantic Web 1.0

Diese Matrix verbindet die zwölf Conformance-Kriterien aus
[`semantic-web-spec.md`](semantic-web-spec.md) mit Implementierung und Tests.

| # | Kriterium | Implementierung / Nachweis |
|---|---|---|
| 1 | Stabile IRIs | `semantic.IriFactory`; `test_dataset_has_named_graphs_dcat_skos_prov_and_shacl` |
| 2 | JSON-LD 1.1 und RDF Dataset | `SemanticDataset.serialize_jsonld`; JSON-LD-Roundtrip-Test |
| 3 | Named Graphs | Product-, Package-, Inferred-, Resolved-, Provenance- und Evidence-Graph; Named-Graph-Test |
| 4 | DCAT und SKOS | Package Distributions sowie Academy-/Produktglossare; Dataset-Test |
| 5 | SHACL Validation Report | `shacl.validate_dataset`, `shacl-report.ttl`; SHACL- und End-to-End-Tests |
| 6 | PROV-O | Assertions, qualifizierte Mehrfachableitungen und Compiler-/Verifier-Läufe; Trace-Test |
| 7 | Sicheres positives Datalog | `datalog.DatalogEngine`; Fixpunkt-, Reihenfolge-, Safety- und Negationstests |
| 8 | RIF Core | `rif.export_rules` / `rif.import_rules`; Roundtrip- und CLI-Test |
| 9 | SPARQL | `SemanticDataset.query`, versionierte Views und `specforge sparql`; Query-/CLI-Tests |
| 10 | RDFC-1.0 + SHA-256 | `rdfcanon`, `rdfc-1.0+sha256`; Isomorphie- und Roundtrip-Tests |
| 11 | YAML und JSON-LD semantisch gleich | YAML-Resolve → JSON-LD → RDF-Roundtrip mit identischem Dataset-Hash |
| 12 | Ohne Graphdatenbank | RDFLib Dataset im Prozess; gesamte Testsuite benötigt keinen externen Dienst |

Die bisherige JSON-, Trace- und Evidence-Struktur bleibt als
Kompatibilitätsprojektion erhalten. `content_hash` bezeichnet den RDFC-Hash;
`legacy_content_hash` hält während des Major-Version-Übergangs den bisherigen
kanonischen JSON-Hash fest.

OWL 2 RL besitzt noch kein aktiviertes Conformance-Profil. Importierte
OWL-Axiome außerhalb der reinen Ontologie-Metadaten werden deshalb mit
`SF3007` abgelehnt. SWRL wird gemäß Spec mit `SF3005` abgelehnt und nicht
stillschweigend ignoriert.
