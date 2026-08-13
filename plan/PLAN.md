# Requirements & Compliance Compiler – MVP-Plan

## Ziel

Der MVP beweist anhand einer kleinen Kalenderanwendung den vollständigen Pfad:

```text
Product Spec
→ normalisierte und semantisch ergänzte Fakten
→ deterministisch abgeleitete Requirements
→ Resolved System Specification
→ Anwendung und Tests
→ versionierte Evidenz und Report
```

Requirements, Implementierungsmuster und Evidenz bleiben getrennte, versionierte Objekte. Ein LLM darf Vorschläge, Erklärungen und Code liefern; über formalisierte Regeln und deren Erfüllung entscheidet ausschließlich deterministische Logik.

## Architektur

1. **Loader und Canonical Model**
   - Lädt Product Specs und Knowledge Packages.
   - Validiert Schemas, IDs, Referenzen, Versionen und Abhängigkeiten.
   - Erzeugt eine typisierte interne Repräsentation.

2. **Semantic Enricher**
   - Modelliert Begriffe, `isA`, Felder, Beziehungen und Klassifikationen.
   - Berechnet eine kleine, kontrollierte semantische Closure.
   - MVP: YAML und Pydantic statt RDF/OWL.

3. **Requirement Resolver**
   - Wertet eine beschränkte deklarative YAML-Regel-DSL aus.
   - Verarbeitet deklarierte und semantisch abgeleitete Fakten.
   - Erzeugt Derived Requirements samt vollständigem Ableitungspfad.
   - Meldet Konflikte; kein implizites „letzte Regel gewinnt“.

4. **Traceability Graph**
   - Verknüpft Quellen, Fakten, Regeln, Requirements, Patterns, Tests und Evidenz.
   - MVP: normale typisierte Strukturen und JSON, keine Graphdatenbank.

5. **Pattern Selector und Generator**
   - Ordnet technologieunabhängigen Requirements passende technische Patterns zu.
   - Generiert kontrollierte Gerüste, Konfigurationen und Tests aus Templates.
   - Handgeschriebene Fachlogik bleibt hinter stabilen Schnittstellen erhalten.

6. **Verification und Evidence**
   - Trennt „Welche Anforderungen gelten?“ von „Sind sie nachweislich erfüllt?“.
   - Führt Tests und andere Prüfer aus.
   - Erzeugt Evidence mit Requirement, Test, Ergebnis, Git-Commit, Input-Hashes und Einschränkungen.

7. **CLI und Reporting**
   - Geplante Befehle: `resolve`, `explain`, `generate`, `validate`, `evidence`, `report`.
   - `explain` zeigt die vollständige Herleitung eines Requirements.

## Zentrales Datenmodell

- **ProductSpec:** Entitäten, Operationen, deklarierte Requirements und Knowledge-Abhängigkeiten.
- **Concept:** Begriff, Elternbegriffe, Klassifikationen, Felder und Provenance.
- **Fact:** Subjekt, Prädikat, Objekt, Origin und Provenance.
- **Rule:** Bedingungen, Variablenbindungen, resultierendes Requirement und Quelle.
- **RequirementDefinition:** stabile fachliche Aussage, Quelle und Verifizierbarkeit.
- **RequirementInstance:** konkretes Requirement für ein Systemelement samt Status und Derivation.
- **ImplementationPattern:** technische Option, die ein Requirement adressiert und Verifikationen vorgibt.
- **Evidence:** konkrete Beobachtung für eine Requirement-Instanz und einen bestimmten Softwarestand.

Statuswerte:

```text
NOT_EVALUATED
REQUIRED
IMPLEMENTED
VERIFIED
FAILED
```

Alle Requirements müssen maschinell entscheidbar formuliert sein. Kann der Compiler aus einer Definition keine eindeutige, ausführbare Verifikation ableiten, ist dies kein Requirement-Status, sondern ein Validierungsfehler des Knowledge Packages. Die Definition muss dann präzisiert werden, bevor sie veröffentlicht oder verwendet werden kann.

## Beispielableitung

```text
GET /events/{id} returns Event
Event has field owner
owner has type User and is classified as PersonalData
→ Event contains PersonalData
→ security/authenticated-personal-data applies
→ SEC-001: authenticated access required
→ FastAPI authentication dependency selected
→ anonymous request integration test selected
→ HTTP 401 observed
→ SEC-001 VERIFIED for the recorded Git commit
```

Zusätzlich folgt aus `scope: own` und der Ownership-Beziehung `SEC-002`: Der Benutzer darf nur eigene Events lesen.

## Technologiestack

- Compiler: Python, Pydantic, Typer, PyYAML, pytest.
- Regelauflösung: kleiner eigener Forward-Chaining Resolver mit eingeschränkter DSL.
- Backend: FastAPI, SQLAlchemy, SQLite.
- Frontend: React, TypeScript, Vite.
- Ausführung: Docker Compose.
- Autorenformate: YAML; kanonische Zwischenartefakte und Evidence: JSON.

## Geplante Repository-Struktur

```text
src/specforge/          Compiler
knowledge/              Concepts, Requirements, Rules und Patterns
products/calendar/      Product Spec
templates/              deterministische Generator-Templates
generated/calendar/     Resolved Spec, Trace und generierte Anwendung
evidence/calendar/      versionierte Prüfergebnisse
tests/                  Compiler-, Knowledge- und Integrationstests
docs/adr/               Architekturentscheidungen
plan/                   Aufgabenbeschreibung und dieser Plan
```

Knowledge-Bereiche erhalten Namespaces und Versionen, sodass sie später in getrennte, schreibgeschützte Repositories ausgelagert werden können.

## Implementierungsphasen

### 1. Canonical Model und Product Spec

CLI-Grundgerüst, Pydantic-Modelle, Calendar Product Spec und verständliche Schema-/Referenzvalidierung. Sichtbares Ergebnis: deterministisch normalisierte Product Spec.

### 2. Semantisches Concept Model

Concepts, `isA`, Feldtypen und Klassifikationspropagation. Sichtbares Ergebnis: aus `Event.owner → User → PersonalData` folgt nachvollziehbar `Event contains PersonalData`.

### 3. Rule Resolver und Explain

Requirement-Katalog, eingeschränkte Regel-DSL, Resolver, Konflikterkennung und Trace. Sichtbares Ergebnis: `resolve` erzeugt die Resolved Spec; `explain SEC-001` zeigt die komplette Herleitung.

### 4. Patterns und Calendar-Backend

FastAPI-Patterns, Event CRUD, lokale Demo-Authentifizierung, Ownership-Autorisierung und SQLite. Sichtbares Ergebnis: lokal startbare API.

### 5. Verification

Tests werden Requirements zugeordnet und über `validate` ausgeführt. Sichtbares Ergebnis: anonymer oder fremder Zugriff scheitert; eine absichtlich entfernte Prüfung erzeugt einen Requirement-Fehler.

### 6. Evidence und Report

Evidence Bundles mit Versionen, Hashes und Einschränkungen sowie menschenlesbarer Report. Nicht eindeutig maschinell auswertbare Requirement-Definitionen werden beim Laden abgelehnt.

### 7. Frontend und Demo

Kleine React-CRUD-Oberfläche, Docker Compose und dokumentierter End-to-End-Flow. Eine rein visuelle Änderung wie ein grüner Button ändert die Product Spec nicht, löst aber erneute Validierung aus.

Jede Phase umfasst Implementierung, Tests, ausgeführte Prüfung und eine dokumentierte Architekturentscheidung, bevor die nächste Phase beginnt.

## MVP-Abgrenzung

Version 1 enthält insbesondere keine:

- allgemeine Generierung beliebiger Anwendungen,
- vollständige DSGVO- oder Rechtsprüfung,
- Compliance-Entscheidung durch ein LLM,
- Graphdatenbank oder vollständige RDF/OWL-Infrastruktur,
- große externe Rule Engine,
- automatische Konfliktauflösung,
- perfekte Change Classification oder inkrementelle Auswertung,
- produktionsreife Identity-Provider-Integration,
- komplexen Kalenderfunktionen wie Sharing, Wiederholungen und Erinnerungen.

Der Report darf niemals pauschal behaupten, die Anwendung sei rechtskonform. Er berichtet nur über den Umfang, die Versionen und die Evidenz der formalisierten Prüfungen.

Die Architekturdokumentation folgt arc42. Systemkontext, Container und wichtige Komponenten werden als C4-Diagramme dokumentiert.

## Hauptrisiken und Leitplanken

- **Ontologie-Komplexität:** Nur Semantik modellieren, die konkrete Ableitungen ermöglicht.
- **Regel-Explosion:** Namespaces, stabile IDs, Linter, Deduplikation und Knowledge-Package-Tests.
- **Policy-Konflikte:** Compilation abbrechen und beide Quellen transparent anzeigen.
- **LLM-Nichtdeterminismus:** LLM-Ausgaben bleiben überprüfbare Vorschläge außerhalb des Entscheidungskerns.
- **Scheinsicherheit:** Scope, Wissensversionen, offene Reviews und Grenzen jeder Evidenz ausweisen.
- **Spec-/Code-Drift:** Verhaltensbasierte Tests, statische Prüfungen und generierte Manifeste.
- **Versionsdrift:** Lockfile, Content-Hashes und Git-Commit in jedem Evidence Bundle.

## Default-Entscheidungen

- YAML/Pydantic statt OWL für den MVP.
- In-Memory-Graph statt Graphdatenbank.
- Kleine deklarative Regel-DSL statt Drools, Rego oder Datalog.
- SQLite statt PostgreSQL.
- Vollständige Revalidierung statt inkrementeller Auswertung.
- Lokale Bearer-Token-Demo-Authentifizierung statt externem Identity Provider.
- Hybrid-Generierung: kontrollierte generierte Artefakte plus handgeschriebene Fachlogik.

Diese Defaults können später über klar abgegrenzte Adapter ersetzt werden, ohne das Requirement- und Traceability-Modell zu verändern.
