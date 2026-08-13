# SpecForge Version 1 – Produktspezifikation

Status: Draft 1

Normative Begriffe wie **MUSS**, **DARF NICHT**, **SOLL** und **KANN** sind verbindlich im Sinne dieser Spezifikation.

## 1. Zweck und Scope

SpecForge V1 MUSS demonstrieren, dass eine kleine Kalender-Product-Spec zusammen mit zentral gepflegten Concepts, Requirements, Regeln und Patterns deterministisch zu einer ausführbaren Resolved System Specification aufgelöst werden kann. Daraus MÜSSEN eine lokal lauffähige Kalenderanwendung, maschinelle Verifikationen, Evidence und ein nachvollziehbarer Report entstehen.

V1 umfasst ausschließlich:

- die Entitäten `User` und `Event`,
- Create, Read, Update und Delete für eigene Events,
- semantische Klassifikation personenbezogener Daten,
- Authentifizierungs- und Ownership-Anforderungen,
- mindestens eine Privacy-Anforderung mit vollständig maschineller Verifikation,
- Compiler-CLI, Generator, Verifikation, Evidence und Report.

## 2. Verbindliche Prinzipien

1. Requirements MÜSSEN First-Class Objects mit stabiler ID und Version sein.
2. Product Specs DÜRFEN zentrale Requirements nicht kopieren; sie MÜSSEN Knowledge Packages referenzieren.
3. Alle fachlichen Entscheidungen im Resolver MÜSSEN deterministisch erfolgen.
4. Jede Derived Requirement-Instanz MUSS vollständig erklärbar sein.
5. Jede Requirement-Definition MUSS mindestens eine maschinell ausführbare Verifikation besitzen.
6. Eine nicht eindeutig prüfbare Requirement-Definition MUSS als Package-Validierungsfehler abgelehnt werden.
7. Die in Abschnitt 3 aufgezählten Statuswerte sind abschließend; weitere Statuswerte sind unzulässig.
8. Ein Requirement DARF nur `VERIFIED` sein, wenn die obligatorische Evidence für denselben Softwarestand erfolgreich ist.
9. Reports DÜRFEN keine pauschale Rechts- oder Compliance-Konformität behaupten.
10. Ein LLM DARF nicht Teil des verbindlichen Resolution- oder Verification-Entscheidungspfads sein.

## 3. Statusmodell

Eine Requirement-Instanz MUSS genau einen der folgenden Status besitzen:

| Status | Bedeutung |
|---|---|
| `NOT_EVALUATED` | Requirement ist bekannt, Verifikation wurde noch nicht ausgeführt. |
| `REQUIRED` | Requirement gilt für ein konkretes Ziel. |
| `IMPLEMENTED` | Das deklarierte Pattern beziehungsweise Control ist in der Implementation Manifest gebunden. |
| `VERIFIED` | Alle obligatorischen maschinellen Verifikationen sind erfolgreich. |
| `FAILED` | Mindestens eine obligatorische Verifikation ist fehlgeschlagen. |

Ungültige, mehrdeutige oder nicht verifizierbare Definitionen sind Compilerdiagnosen und keine Statuswerte.

## 4. Eingabeartefakte

### 4.1 Product Spec

Die Product Spec MUSS enthalten:

- `schema_version`,
- Produkt-ID und Produktversion,
- Entitäten und typisierte Felder,
- Operationen mit Action, Resource, Actor und Scope,
- deklarierte Product Requirements,
- exakt gepinnte Knowledge-Abhängigkeiten.

V1 MUSS mindestens folgende Calendar Spec unterstützen:

```yaml
schema_version: "1"
product:
  id: calendar
  version: "1.0.0"

entities:
  - id: User
    fields:
      - { name: id, type: UUID }

  - id: Event
    fields:
      - { name: id, type: UUID }
      - { name: owner, type: User, relation: ownership, classification: PersonalData }
      - { name: title, type: Text }
      - { name: description, type: Text, classification: PersonalData }
      - { name: start, type: DateTime }
      - { name: end, type: DateTime }

operations:
  - { id: create_event, action: create, resource: Event, actor: User, scope: own }
  - { id: read_event, action: read, resource: Event, actor: User, scope: own }
  - { id: update_event, action: update, resource: Event, actor: User, scope: own }
  - { id: delete_event, action: delete, resource: Event, actor: User, scope: own }

declared_requirements:
  - { id: PRODUCT-001, operation: create_event, statement: "A user can create an event." }
  - { id: PRODUCT-002, operation: read_event, statement: "A user can read an owned event." }
  - { id: PRODUCT-003, operation: update_event, statement: "A user can update an owned event." }
  - { id: PRODUCT-004, operation: delete_event, statement: "A user can delete an owned event." }
```

### 4.2 Concept Package

Ein Concept MUSS eine stabile ID besitzen. Es KANN Elternbegriffe, Klassifikationen und Provenance enthalten. V1 MUSS folgende semantische Ableitungen unterstützen:

- transitive `isA`-Beziehungen,
- Feldtyp- und Feldklassifikationen,
- Propagation `Resource has field classified as X → Resource contains classification X`.

### 4.3 Requirement Definition

Eine Definition MUSS enthalten:

```yaml
id: SEC-001
version: "1.0.0"
statement: Resources containing PersonalData require authenticated access.
expectation:
  control: authentication
  operator: equals
  value: required
verification:
  adapter: http_request
  setup: anonymous
  assertion:
    response_status: 401
source:
  type: internal_policy
  document: security-policy
  version: "1.0.0"
  section: authenticated-personal-data
```

Freier Text allein ist keine gültige Requirement-Definition.

### 4.4 Rule

Eine Regel MUSS eine stabile ID, Version, strukturierte Bedingungen, ein resultierendes Requirement und Provenance besitzen. Die V1-DSL MUSS `all`, `any`, `not`, Faktenabfragen, Variablenbindung und Gleichheit unterstützen. Sie DARF keine Schleifen, Seiteneffekte oder beliebigen Code ausführen.

### 4.5 Implementation Pattern

Ein Pattern MUSS deklarieren:

- welche Controls beziehungsweise Requirements es adressiert,
- mit welchem Zielstack es kompatibel ist,
- welche Artefakte es erzeugt oder bindet,
- welche Verification Specifications es erfüllt.

Die Auswahl eines Patterns allein DARF ein Requirement nicht auf `VERIFIED` setzen.

## 5. Compilerverhalten

### 5.1 Validierung

Der Compiler MUSS vor Resolution prüfen:

- Schema-Gültigkeit,
- Eindeutigkeit aller IDs,
- Auflösbarkeit aller Referenzen,
- kompatible Schema- und Paketversionen,
- Existenz einer ausführbaren Verifikation für jedes Requirement,
- Zulässigkeit aller Regeloperatoren,
- Zyklen oder Widersprüche, die keine eindeutige Closure erlauben.

Bei einem Fehler MUSS der Prozess ungleich null enden und MUSS Artefakt, Pfad und Fehlercode ausgeben.

### 5.2 Normalisierung

Der Compiler MUSS aus der Product Spec eine kanonische Intermediate Representation und deklarierte Facts erzeugen. Collections MÜSSEN stabil sortiert und JSON-Objektschlüssel kanonisch serialisiert werden.

### 5.3 Semantische Closure

Der Compiler MUSS semantische Regeln bis zu einem Fixpunkt auswerten. Jedes neue Fact MUSS seine direkten Prämissen und seine Ableitungsoperation referenzieren.

### 5.4 Requirement Resolution

Der Resolver MUSS alle Regeln in stabiler Reihenfolge bis zum Fixpunkt auswerten. Eine Requirement-Instanz wird durch Requirement-ID und Ziel eindeutig identifiziert. Mehrfache Herleitungen MÜSSEN erhalten bleiben, dürfen aber keine duplizierten Instanzen erzeugen.

### 5.5 Konflikte

Widersprüchliche Erwartungen für dasselbe Ziel und Control MÜSSEN die Compilation abbrechen. Der Fehler MUSS beide Requirements, Regeln, Paketversionen und Ableitungspfade nennen. Eine implizite Priorität oder „last rule wins“ ist unzulässig.

### 5.6 Resolved System Specification

Die Resolved Spec MUSS enthalten:

- Produkt und Eingabeversionen,
- Entitäten und Operationen,
- alle relevanten Klassifikationen,
- Declared und Derived Requirements,
- konkrete Controls je Ziel,
- ausgewählte Implementation Patterns,
- Referenzen in den Traceability Graph,
- einen kanonischen Content-Hash.

## 6. CLI

V1 MUSS folgende Befehle bereitstellen:

```text
specforge resolve <product>
specforge explain <requirement> --product <product>
specforge generate <product>
specforge validate <product>
specforge evidence <product>
specforge report <product>
```

### `resolve`

MUSS Facts, semantische Closure, Requirements, Konflikte und Resolved Spec erzeugen beziehungsweise prüfen.

### `explain`

MUSS für eine Requirement-ID alle konkreten Instanzen anzeigen. Jede Erklärung MUSS Operation, Quell-Facts, semantische Ableitungen, Regel samt Version und resultierendes Control enthalten.

### `generate`

MUSS die ausgewählten Patterns deterministisch auf Templates anwenden und MUSS ein Implementation Manifest erzeugen.

### `validate`

MUSS alle obligatorischen Verifikationen für die aktuelle Resolved Spec ausführen. Der Exitcode MUSS bei mindestens einem `FAILED` ungleich null sein.

### `evidence`

MUSS ein vollständiges, schema-valides Evidence Bundle für den letzten passenden Validation Run erzeugen. Veraltete Testresultate aus einem anderen Commit oder Spec-Hash MÜSSEN abgelehnt werden.

### `report`

MUSS Declared und Derived Requirements, Status, Quellen, Implementation Patterns, Verifikationen, Evidence und Scope-Grenzen ausgeben.

## 7. Kalenderanwendung

### 7.1 Datenmodell

`Event` MUSS enthalten:

- UUID `id`,
- UUID `owner_id`,
- nicht leeren `title`,
- `description`,
- `start`,
- `end`.

Die Anwendung MUSS `end > start` erzwingen.

### 7.2 HTTP-API

V1 MUSS folgende Endpunkte anbieten:

```text
POST   /events
GET    /events/{id}
PUT    /events/{id}
DELETE /events/{id}
```

Alle Endpunkte MÜSSEN Authentifizierung verlangen. Zugriffe auf ein nicht eigenes Event DÜRFEN dessen Existenz oder Inhalt nicht offenlegen und MÜSSEN den für V1 festgelegten Status `404` liefern. Anonyme Zugriffe MÜSSEN `401` liefern.

### 7.3 Authentifizierung

V1 MUSS eine deterministische lokale Bearer-Token-Demo-Authentifizierung mit mindestens zwei festen Testidentitäten bereitstellen. Sie MUSS deutlich als nicht produktionsreif gekennzeichnet sein.

### 7.4 Frontend

Das React-Frontend MUSS eigene Events erstellen, anzeigen, bearbeiten und löschen können. Der Create-Event-Button MUSS ohne Änderung der Product Spec visuell geändert werden können. Nach einer solchen Änderung MUSS die Resolved Spec denselben Content-Hash behalten.

## 8. Verifikationen

V1 MUSS mindestens folgende maschinelle Verifikationen enthalten:

| ID | Requirement | Beobachtung |
|---|---|---|
| `TEST-PRODUCT-001` | Event erstellen | Eigentümer erhält `201`; gespeichertes Event stimmt überein. |
| `TEST-PRODUCT-002` | Eigenes Event lesen | Eigentümer erhält `200` und korrektes Event. |
| `TEST-PRODUCT-003` | Eigenes Event ändern | Eigentümer erhält `200`; Änderung ist gespeichert. |
| `TEST-PRODUCT-004` | Eigenes Event löschen | Eigentümer erhält Erfolg; nachfolgend `404`. |
| `TEST-SEC-001-*` | Authentifizierung | Jeder CRUD-Endpunkt liefert anonym `401`. |
| `TEST-SEC-002-*` | Ownership | Benutzer B erhält für Events von Benutzer A jeweils `404`. |
| `TEST-PRIVACY-001` | Datenminimierte API-Antwort | Response-Schema enthält ausschließlich die in der Resolved Spec erlaubten Event-Felder. |
| `TEST-DATA-001` | Zeitintervall | `end <= start` wird mit `422` abgelehnt. |

Für jede obligatorische Verification MUSS die Spezifikation erwartete Beobachtungen enthalten. Tests ohne formale Assertion gelten nicht als Verification.

## 9. Evidence

Ein Evidence-Eintrag MUSS enthalten:

- eindeutige Evidence-ID,
- Requirement-Instanz,
- Verification-ID und -Typ,
- erwartete und beobachtete Werte,
- `PASS` oder `FAIL`,
- Git-Commit,
- Resolved-Spec-Hash,
- Hashes und Versionen aller Knowledge Packages,
- Tool und Toolversion,
- Ausführungszeitpunkt.

Ein `PASS` MUSS zu `VERIFIED`, ein `FAIL` zu `FAILED` führen, sofern alle Daten zum gleichen Software- und Spezifikationsstand gehören. Evidence MUSS auch fehlgeschlagene Beobachtungen aufbewahren.

## 10. Determinismus und Reproduzierbarkeit

- `resolve` und `generate` MÜSSEN bei identischen Eingaben identische kanonische Artefakte erzeugen.
- Absolute Dateipfade, Laufzeitstempel und zufällige IDs DÜRFEN nicht in kanonische Compiler-Artefakte eingehen.
- Evidence DARF Laufzeitdaten enthalten, MUSS aber die deterministischen Eingaben per Hash referenzieren.
- Die Reihenfolge von YAML-Dateien im Dateisystem DARF das Ergebnis nicht beeinflussen.

## 11. Dokumentation

Die Architekturdokumentation MUSS der arc42-Gliederung folgen. Sie MUSS mindestens C4-Diagramme für System Context, Container und Compiler Components enthalten. Wesentliche Architekturentscheidungen MÜSSEN zusätzlich als ADR dokumentiert werden.

## 12. Nichtziele von V1

V1 baut keine:

- allgemeine Legal-Tech- oder DSGVO-Zertifizierung,
- universelle Anwendungsgenerierung,
- Graphdatenbank,
- RDF/OWL-Laufzeit,
- externe produktionsreife Identity-Provider-Integration,
- inkrementelle Impact Analysis,
- automatische Auswertung freien Rechtstextes,
- LLM-basierte Policy-Entscheidung,
- Teilnehmer, Orte, Sharing, Serientermine oder Erinnerungen.

Nicht formalisierte Aussagen liegen außerhalb des V1-Scopes. Sie dürfen weder als Requirements in die Resolved Spec aufgenommen noch im Report als geprüft dargestellt werden.

## 13. Abnahmekriterien

V1 ist abgenommen, wenn alle folgenden Punkte automatisiert demonstriert werden:

1. Eine Calendar Product Spec wird erfolgreich geladen und normalisiert.
2. `Event contains PersonalData` wird semantisch hergeleitet.
3. Mindestens vier Product Requirements und die definierten Security-, Privacy- und Data-Requirements werden aufgelöst.
4. `explain SEC-001` zeigt einen vollständigen Pfad von Product Fact über Semantik und Regel bis zur Verification.
5. Die generierte beziehungsweise vervollständigte Kalenderanwendung startet lokal.
6. Alle CRUD-, Authentifizierungs-, Ownership-, Privacy- und Zeitintervalltests bestehen.
7. Wird Authentifizierung für `GET /events/{id}` entfernt, schlägt `validate` fehl und nennt `SEC-001`, Erwartung, Beobachtung und Test-ID.
8. Wird nur die Farbe des Create-Event-Buttons geändert, bleibt der Resolved-Spec-Hash unverändert und alle Verifikationen bestehen weiterhin.
9. Eine Requirement-Definition ohne ausführbare Verification Specification wird mit einem definierten Fehlercode abgelehnt.
10. Zwei Resolution-Läufe mit denselben Eingaben erzeugen byte-identische kanonische Artefakte.
11. Der Report enthält keine globale Compliance-Aussage, sondern ausschließlich nachgewiesene Requirement-Instanzen und deren konkreten Scope.
