# SpecForge Version 2 – Agentische Implementierung

Status: Draft 1

Diese Spezifikation baut auf `SPEC_V1.md` auf. Soweit sie keine abweichende Regel enthält, bleiben die Anforderungen aus Version 1 gültig.

Die Begriffe **MUSS**, **DARF NICHT**, **SOLL** und **KANN** sind normativ.

## 1. Ziel

SpecForge V2 MUSS demonstrieren, dass ein Coding Agent eine bestehende Anwendung aus einer deterministisch aufgelösten Systemspezifikation weiterentwickeln kann, ohne selbst über die Gültigkeit oder Erfüllung formalisierter Requirements zu entscheiden.

Die verbindliche Pipeline lautet:

```text
Product Spec + Knowledge Packages
              ↓
Deterministische Requirement Resolution
              ↓
Konsolidierte Implementation Obligations
              ↓
Impact Scope und Agent Work Order
              ↓
Codex implementiert oder verändert Anwendungscode
              ↓
Deterministische Verifikation
              ↓
Akzeptierte Änderung oder begrenzte Reparaturschleife
              ↓
Versionierte Evidence und Report
```

V2 verfolgt insbesondere diese Ziele:

- Codex ist der primäre Generator für Anwendungscode.
- Viele gleichzeitig wirkende Requirements werden vor der Agent-Ausführung konsolidiert.
- Requirements, technische Leitplanken und Verifikationen begrenzen den Lösungsraum, schreiben aber nicht den vollständigen Code vor.
- Die Akzeptanz einer Implementierung erfolgt ausschließlich maschinell und deterministisch.
- Bestehender handgeschriebener Code bleibt erhalten und kann inkrementell geändert werden.
- Templates und Template-Engines sind in V2 nicht zulässig; Artefakte werden entweder programmatisch deterministisch erzeugt oder durch den Coding Agent implementiert.

## 2. Verbindliche Prinzipien

1. Der Requirement Resolver MUSS ohne LLM deterministisch arbeiten.
2. Der Coding Agent DARF keine Requirements hinzufügen, entfernen, abschwächen oder als erfüllt markieren.
3. Alle auf den Code wirkenden Requirements MÜSSEN vor der Agent-Ausführung zu konfliktfreien Implementation Obligations konsolidiert werden.
4. Der Agent MUSS einen versionierten, maschinenlesbaren Work Order erhalten.
5. Der Agent DARF ausschließlich die im Work Order erlaubten Pfade verändern.
6. Product Specs, Knowledge Packages, Resolved Specs und Verifikationsdefinitionen MÜSSEN während einer Agent-Ausführung schreibgeschützt sein.
7. Eine Agent-Ausgabe DARF erst nach erfolgreicher deterministischer Verifikation akzeptiert werden.
8. Fehlgeschlagene Verifikation MUSS konkrete Requirement- und Verification-Instanzen nennen.
9. Reparaturversuche MÜSSEN begrenzt, nachvollziehbar und versioniert sein.
10. Templates, Template-Dateien und Template-Engines DÜRFEN weder Bestandteil von SpecForge V2 noch seiner Knowledge Packages oder Generatorpfade sein.
11. Eine erfolgreiche Agent-Ausführung DARF nicht als allgemeiner Compliance-Nachweis bezeichnet werden.
12. Nicht eindeutig maschinell entscheidbare Requirements bleiben unzulässig.

## 3. Verantwortungsgrenzen

### 3.1 Deterministischer Compiler

Der Compiler entscheidet:

- welche Requirements gelten,
- auf welche typisierten Targets sie wirken,
- welche Controls und Invarianten daraus folgen,
- ob Requirements oder Controls miteinander kollidieren,
- welche technischen Leitplanken gelten,
- welche Verifikationen obligatorisch sind,
- welcher Codebereich verändert werden darf,
- ob die erzeugte Implementierung akzeptiert wird.

### 3.2 Coding Agent

Codex entscheidet innerhalb der vorgegebenen Grenzen:

- wie Verantwortlichkeiten auf Module verteilt werden,
- welche geeigneten Framework-Mechanismen verwendet werden,
- wie bestehender Code erweitert oder refaktoriert wird,
- wie interne Funktionen, Klassen und Variablen benannt werden,
- wie Benutzeroberflächen innerhalb der definierten Invarianten gestaltet werden,
- welche zusätzlichen nicht widersprüchlichen Tests sinnvoll sind.

Codex DARF Vorschläge für fehlende Requirements oder Patterns erzeugen. Solche Vorschläge DÜRFEN nicht automatisch in den verbindlichen Wissensbestand übernommen werden.

### 3.3 Deterministische Verifikation

Die Verifikation entscheidet:

- ob der Build erfolgreich ist,
- ob obligatorische Tests und statische Prüfungen bestehen,
- ob erlaubte Änderungsgrenzen eingehalten wurden,
- ob alle erwarteten Controls beobachtbar erfüllt sind,
- ob verbotene Änderungen stattgefunden haben,
- ob die Evidence zum aktuellen Code-, Spec- und Knowledge-Stand gehört.

## 4. Begriffsmodell

### 4.1 Requirement Definition

Eine versionierte, technologieunabhängige und maschinell prüfbare Aussage.

### 4.2 Requirement Instance

Die Anwendung einer Requirement Definition auf ein typisiertes Target, zum Beispiel:

```text
SEC-001@operation:read_event
PRIVACY-004@field:Event.description
ARCH-002@component:calendar-api
PLATFORM-003@deployment:production
```

### 4.3 Implementation Obligation

Eine normalisierte technische Verpflichtung, die aus einer oder mehreren Requirement Instances entsteht. Sie beschreibt einen invarianten technischen Zustand, nicht dessen vollständige Implementierung.

Beispiel:

```yaml
id: obligation:operation:read_event:authorization
target:
  type: operation
  id: read_event
surface: data_access
control: authorization
expectation:
  type: ownership
  owner_field: Event.owner
derived_from:
  - SEC-002@operation:read_event
```

### 4.4 Implementation Guidance

Versioniertes technisches Wissen, das eine oder mehrere Obligations adressiert. Guidance enthält Voraussetzungen, Empfehlungen, Verbote, Beispiele und Verifikationsbezüge. Sie ist keine vollständige Codevorlage.

Der bisherige Begriff `Implementation Pattern` wird in V2 für diese Rolle weiterverwendet. Pattern-Auswahl bedeutet nicht, dass Code automatisch als erfüllt gilt.

### 4.5 Agent Work Order

Ein unveränderlicher, maschinenlesbarer Arbeitsauftrag für genau eine Agent-Ausführung. Er enthält Ausgangsversion, Zielzustand, Obligations, Änderungsgrenzen und Abnahmekriterien.

### 4.6 Agent Run

Eine konkrete Ausführung eines Agent Adapters mit einem Work Order. Jeder Run besitzt eine eindeutige ID, Eingabe-Hashes, Agent- und Modellinformationen sowie ein Änderungsmanifest.

### 4.7 Repair Run

Ein Folge-Run, der ausschließlich zuvor beobachtete Verifikationsfehler adressiert. Er referenziert den ursprünglichen Agent Run und die fehlgeschlagenen Evidence-Einträge.

## 5. Typisierte Targets

Targets MÜSSEN strukturiert modelliert werden:

```yaml
type: operation
id: read_event
```

V2 MUSS mindestens folgende Target-Typen unterstützen:

- `product`,
- `entity`,
- `field`,
- `operation`,
- `component`,
- `deployment`,
- `artifact`.

Target-IDs MÜSSEN innerhalb ihres Typs eindeutig sein. Erweiterungen um neue Target-Typen DÜRFEN keine Änderung am Requirement-, Verification- oder Evidence-Grundmodell erfordern.

Gruppierungen in CLI und Reports sind ausschließlich Projektionen. Die kanonischen Requirement- und Verification-Instanzen bleiben ungruppiert.

## 6. Konsolidierung vieler Requirements

### 6.1 Motivation

Der Agent DARF nicht für jedes Requirement einen isolierten Änderungsauftrag erhalten. Alle Requirements, die dieselbe technische Fläche beeinflussen, MÜSSEN vorher gemeinsam betrachtet werden.

Beispiel:

```text
SEC-001 Authentication
SEC-002 Ownership
PRIVACY-001 Response minimization
OBS-001 Audit logging
PLATFORM-001 Rate limiting
```

werden zu:

```yaml
target: {type: operation, id: read_event}
surfaces:
  identity:
    authentication: required
  data_access:
    authorization: ownership
  response:
    allowed_fields: [id, owner_id, title, description, start, end]
  observability:
    audit_events: [access_granted, access_denied]
  traffic:
    requests_per_minute: 60
```

### 6.2 Obligation Surfaces

V2 MUSS mindestens folgende erweiterbare technische Flächen kennen:

- `identity`,
- `data_access`,
- `input`,
- `response`,
- `persistence`,
- `observability`,
- `traffic`,
- `user_interface`,
- `deployment`.

Eine Obligation MUSS genau eine primäre Surface besitzen. Sie KANN Abhängigkeiten zu Obligations anderer Surfaces erklären.

### 6.3 Konsolidierungsregeln

Der Consolidator MUSS:

- semantisch identische Controls deduplizieren,
- alle Quellen erhalten,
- kompatible Werte zusammenführen,
- Mengen nach expliziter Mengenoperation kombinieren,
- numerische Grenzwerte nach definierter Strategie kombinieren,
- nicht kombinierbare Erwartungen als Konflikt melden,
- das Ergebnis stabil sortieren,
- jede Konsolidierungsentscheidung erklären können.

Für jeden Control-Typ MUSS eine versionierte Merge-Semantik existieren. Ein generisches „letzter Wert gewinnt“ ist unzulässig.

Beispiele:

```text
authentication required + authentication required
→ required

allowed_fields {id,title} ∩ allowed_fields {id,title,description}
→ {id,title}

retention_days <= 30 + retention_days <= 14
→ retention_days <= 14

authentication required + authentication forbidden
→ CONFLICT
```

### 6.4 Konfliktdiagnose

Ein Konflikt MUSS vor dem Agent-Aufruf erkannt werden. Die Diagnose MUSS enthalten:

- betroffene Targets und Surfaces,
- unvereinbare Werte,
- Requirement Instances,
- Regeln und Paketversionen,
- Provenance,
- mögliche, aber nicht automatisch angewandte Lösungsoptionen.

## 7. Implementation Patterns in V2

Ein Pattern MUSS folgende Struktur unterstützen:

```yaml
id: fastapi/ownership-authorization
version: 2.0.0
owner: security-platform-team

addresses:
  surface: data_access
  control: authorization
  expectation:
    type: ownership

compatible_with:
  language: python
  framework: fastapi
  persistence: sqlalchemy

requires:
  - resource
  - owner_field
  - authenticated_actor

constraints:
  required:
    - Authorization is enforced server-side.
    - Resource lookup is constrained by resource ID and owner ID.
    - Foreign resources return HTTP 404.
  forbidden:
    - Loading a foreign resource before checking ownership.
    - Trusting an owner ID supplied by the client.

recommendations:
  - Use a repository query with both resource and owner predicates.

examples:
  - language: python
    resource: examples/sqlalchemy-owned-query.py

verifications:
  - TEST-SEC-002
```

Patterns DÜRFEN:

- technische Empfehlungen liefern,
- kleine Referenzbeispiele enthalten,
- auf Framework-Dokumentation verweisen,
- statische Analyse- und Testadapter auswählen,
- optionale Agent Skills referenzieren.

Patterns DÜRFEN NICHT:

- die Gültigkeit eines Requirements bestimmen,
- obligatorische Verifikationen abschwächen,
- Templates oder templateartige Codegerüste enthalten oder referenzieren,
- Schreibzugriff auf zentrale Knowledge Packages verlangen,
- freie Anweisungen enthalten, die den Work Order überschreiben.

## 8. Deterministische Generatoren ohne Templates

Templates, Template-Dateien, Template-Verzeichnisse und Template-Engines sind in V2 unzulässig und MÜSSEN aus bestehenden Generatorpfaden entfernt werden. Dies gilt auch für initiale Repository-Gerüste, CI-Konfigurationen, API-Clients, Deployment-Manifeste und Testhüllen.

Diese Regel ersetzt sämtliche Template-bezogenen Anforderungen aus V1. Eine V2-Implementierung MUSS bestehende Template-Ressourcen und die zugehörige Lade-, Auswahl- und Rendering-Logik entfernen.

Strukturierte, vollständig regenerierbare Artefakte wie kanonische JSON- und YAML-Dokumente sowie Reports DÜRFEN durch deterministische, programmatische Serializer und Generatoren erzeugt werden. Diese Generatoren DÜRFEN keine externen oder eingebetteten Textvorlagen verwenden und keine Requirement- oder Policy-Entscheidungen treffen.

Anwendungscode, Konfigurationen und Tests MÜSSEN durch den Coding Agent innerhalb des Work Orders implementiert oder durch ausdrücklich spezifizierte programmatische Transformationen erzeugt werden. Pattern-Beispiele dienen ausschließlich als begrenzte Referenz und DÜRFEN nicht als ausfüllbare Codevorlagen verwendet werden.

## 9. Implementation Plan

Vor dem Agent Work Order MUSS SpecForge einen deterministischen Implementation Plan erzeugen.

Dieser MUSS enthalten:

- alle betroffenen typisierten Targets,
- konsolidierte Obligations nach Surface,
- ausgewählte Patterns und Versionen,
- erwartete betroffene Komponenten und Artefakte,
- obligatorische Verifikationen,
- erlaubte und schreibgeschützte Pfade,
- erkannte Risiken und Konflikte,
- Ausgangs- und Ziel-Hash der Resolved Spec.

CLI:

```bash
specforge plan products/calendar
specforge plan products/calendar --format json
specforge plan products/calendar --explain obligation:operation:read_event:authorization
```

`plan` DARF keinen Anwendungscode verändern.

## 10. Impact Scope

V2 MUSS einen konservativen Impact Scope berechnen. Er darf mehr Dateien und Tests einschließen als tatsächlich notwendig, aber keine bekannte relevante Abhängigkeit auslassen.

Impact-Facts können stammen aus:

- Traceability Graph,
- Resolved-Spec-Diff,
- Implementation Manifest,
- import- beziehungsweise modulbasierten Codeanalysen,
- expliziten Pattern-Beziehungen,
- Zuordnungen zwischen Verifications und Targets.

Der Scope MUSS unterscheiden:

```text
READ_ONLY
MAY_MODIFY
MUST_NOT_MODIFY
MUST_VERIFY
```

Änderungen außerhalb von `MAY_MODIFY` MÜSSEN die Agent-Ausführung ungültig machen.

V2 muss noch keine minimale inkrementelle Validierung garantieren. Standardmäßig DÜRFEN weiterhin alle Verifikationen ausgeführt werden.

## 11. Agent Work Order

Ein Work Order MUSS mindestens enthalten:

```yaml
schema_version: "2"
id: work-order-calendar-location-001

product:
  id: calendar
  base_revision: <git-commit-and-worktree-hash>
  resolved_spec_before: sha256:...
  resolved_spec_after: sha256:...

objective:
  type: implement_resolved_spec_delta
  summary: Add Event.location and preserve all applicable controls.

targets:
  - {type: field, id: Event.location}
  - {type: operation, id: create_event}
  - {type: operation, id: read_event}
  - {type: operation, id: update_event}

obligations:
  - obligation:field:Event.location:classification
  - obligation:operation:read_event:response-minimization

guidance:
  - pattern: fastapi/pydantic-resource-field@2.0.0
  - pattern: react/form-field@2.0.0

permissions:
  may_modify:
    - app/backend/**
    - app/frontend/**
    - tests/**
  read_only:
    - products/**
    - knowledge/**
    - generated/**/resolved-spec.json
  must_not_modify:
    - evidence/**

verification_plan:
  mandatory:
    - TEST-PRODUCT-LOCATION-CREATE
    - TEST-PRIVACY-001@operation:read_event
    - TEST-SEC-001@operation:read_event

limits:
  max_agent_runs: 1
  max_repair_runs: 2
```

Der Work Order MUSS vor Ausführung schema-validiert und mit einem Content-Hash versehen werden.

## 12. Agent Adapter

SpecForge MUSS Coding Agents über eine klar abgegrenzte Adapter-Schnittstelle aufrufen. V2 MUSS einen Codex Adapter bereitstellen.

Die logische Schnittstelle lautet:

```text
execute(work_order, workspace, agent_configuration)
→ AgentRunResult
```

Der Codex Adapter MUSS:

- den Work Order vollständig übergeben,
- die Resolved Spec und ausgewählte Patterns lesbar machen,
- Schreibzugriffe technisch auf erlaubte Pfade begrenzen, soweit die Laufzeit dies unterstützt,
- Modell- und Agent-Version aufzeichnen,
- Agent-Ausgaben und Tool-Aktivitäten referenzierbar protokollieren,
- den finalen Dateidiff und geänderte Pfade erfassen,
- Netzwerk- und Befehlsrechte explizit konfigurieren,
- bei Berechtigungsverletzungen den Run abbrechen.

Die fachliche Spezifikation DARF nicht an eine proprietäre Codex-Aufrufsform gekoppelt sein. Weitere Adapter müssen später ohne Änderung des Work-Order-Modells ergänzt werden können.

## 13. Agent Run Result

Ein Agent Run Result MUSS enthalten:

- Run-ID,
- Work-Order-ID und -Hash,
- Ausgangsrevision,
- Agent-Anbieter, Modell und Version,
- Start- und Endzeit,
- Exitstatus,
- geänderte, erstellte und entfernte Dateien,
- Hashes der Änderungen,
- vom Agent gemeldete Zusammenfassung,
- ausgeführte Agent-Tools, soweit verfügbar,
- Berechtigungsverletzungen,
- nachfolgende Verification-Run-ID.

Eine Agent-Zusammenfassung ist keine Evidence für ein Requirement.

## 14. Verifikations-Gate

Nach jedem Agent Run MUSS SpecForge mindestens folgende Gates ausführen:

1. **Permission Gate** – ausschließlich erlaubte Pfade wurden verändert.
2. **Schema Gate** – alle generierten Manifeste und strukturierten Artefakte sind gültig.
3. **Build Gate** – Anwendung und Frontend lassen sich bauen.
4. **Static Gate** – konfigurierte Linter, Typprüfer und Architekturprüfungen bestehen.
5. **Requirement Gate** – alle obligatorischen Verification Instances bestehen.
6. **Regression Gate** – zuvor verifizierte weiterhin relevante Requirements bleiben verifiziert.
7. **Evidence Gate** – Evidence referenziert exakt Work Order, Agent Run, Softwarestand und Wissensversionen.

Ein fehlgeschlagenes obligatorisches Gate MUSS den Agent Run als `REJECTED` markieren.

## 15. Reparaturschleife

Ein fehlgeschlagener Run KANN eine begrenzte Reparaturschleife auslösen.

Der Repair Work Order MUSS ausschließlich enthalten:

- ursprünglichen Work Order,
- aktuellen Code-Diff,
- fehlgeschlagene Verification Instances,
- erwartete und beobachtete Werte,
- relevante Logs und Diagnosen,
- verbleibende Anzahl erlaubter Reparaturversuche.

Der Agent DARF während einer Reparatur den Scope nicht eigenständig erweitern. Nach jedem Repair Run MÜSSEN alle Gates erneut ausgeführt werden.

Nach Ausschöpfung der konfigurierten Versuche MUSS der Zustand `REJECTED` lauten. Es DARF keine automatische Akzeptanz oder unbeschränkte Schleife geben.

## 16. Zustandsmodell

### 16.1 Work Order

```text
PLANNED
READY
RUNNING
VERIFYING
ACCEPTED
REJECTED
```

### 16.2 Agent Run

```text
STARTED
COMPLETED
FAILED
PERMISSION_VIOLATION
```

### 16.3 Requirement Instances

Das Statusmodell aus V1 bleibt gültig. Ein `ACCEPTED` Agent Run setzt Requirements nicht unmittelbar auf `VERIFIED`; maßgeblich ist ausschließlich das Requirement Gate und die zugehörige Evidence.

## 17. CLI

V2 MUSS zusätzlich zu den V1-Befehlen mindestens bereitstellen:

```bash
specforge diff <product> --from <revision> --to <revision>
specforge plan <product>
specforge implement <product> --agent codex
specforge implement <product> --agent codex --dry-run
specforge repair <run-id>
specforge runs <product>
specforge show-run <run-id>
```

### `diff`

Erzeugt einen semantischen Diff aus typisierten Targets, Facts, Requirement Instances, Obligations und Verifications. Ein reiner Textdiff reicht nicht aus.

### `plan`

Erzeugt Implementation Plan, Impact Scope und Work Order, verändert aber keinen Anwendungscode.

### `implement`

Validiert den Work Order, ruft den Agent Adapter auf und startet anschließend alle Gates. `--dry-run` zeigt den vollständigen Auftrag und die vorgesehenen Rechte, ohne Codex aufzurufen.

### `repair`

Erzeugt einen begrenzten Repair Work Order aus einem abgelehnten Run.

### `runs` und `show-run`

Zeigen Agent Runs, Änderungen, Gates und zugehörige Evidence nachvollziehbar an.

## 18. Evidence und Traceability

Der Traceability Graph MUSS in V2 folgende Kette darstellen können:

```text
Policy Source
→ Requirement Definition
→ Requirement Instance
→ Implementation Obligation
→ Implementation Pattern
→ Agent Work Order
→ Agent Run
→ Code Change
→ Verification Instance
→ Evidence
→ ACCEPTED oder REJECTED
```

Evidence für agentisch erzeugten Code MUSS zusätzlich zu V1 enthalten:

- Work-Order-ID und -Hash,
- Agent-Run-ID,
- Agent-Adapter und Modellkennung,
- Ausgangs- und Ergebnisrevision,
- Hash des angewandten Diffs,
- Gate-ID,
- Verification Instance,
- erwartete und beobachtete Werte.

Die Verwendung von Codex MUSS sichtbar sein. Der Report DARF daraus keine höhere Beweiskraft ableiten.

## 19. Änderungs- und Dateistrategie

V2 MUSS bestehende Anwendungen inkrementell bearbeiten können.

Dateien werden in drei Klassen eingeteilt:

```text
GENERATED
AGENT_MANAGED
HUMAN_MANAGED
```

- `GENERATED` wird vollständig durch deterministische Generatoren kontrolliert.
- `AGENT_MANAGED` darf innerhalb eines Work Orders durch Codex verändert werden.
- `HUMAN_MANAGED` ist standardmäßig schreibgeschützt und benötigt eine explizite Freigabe im Work Order.

Die Klassifikation MUSS in einem versionierten Implementation Manifest stehen. Unklassifizierte bestehende Dateien gelten standardmäßig als `HUMAN_MANAGED`.

SpecForge DARF lokale Änderungen nicht stillschweigend überschreiben. Vor dem Agent-Aufruf MUSS der Ausgangszustand einschließlich uncommitted changes eindeutig gehasht werden.

## 20. Security und Governance des Agenten

- Knowledge Packages MÜSSEN für den Agent schreibgeschützt sein.
- Credentials DÜRFEN weder in Work Orders noch in Agent-Logs oder Evidence geschrieben werden.
- Netzwerkzugriff MUSS standardmäßig deaktiviert oder auf explizit erlaubte Ziele begrenzt sein.
- Ausführbare Befehle und Dateirechte MÜSSEN nach dem Prinzip minimaler Rechte konfiguriert werden.
- Der Agent DARF keine Verifikationen löschen, deaktivieren oder durch schwächere Assertions ersetzen.
- Änderungen an Dependency-Dateien MÜSSEN im Work Order erlaubt und im Report gesondert ausgewiesen werden.
- Neu eingeführte Dependencies MÜSSEN durch eine deterministische Policy geprüft werden können.
- Prompt-Injection-Inhalte aus Produktdaten oder Quelldokumenten DÜRFEN den Work Order und die Systemgrenzen nicht überschreiben.

## 21. Reproduzierbarkeit

Agentisch erzeugter Quellcode muss nicht byte-identisch reproduzierbar sein. Reproduzierbar sein MÜSSEN jedoch:

- Requirement Resolution,
- Obligation Consolidation,
- Implementation Plan,
- Work Order,
- Impact Scope,
- Verification Plan,
- Gate-Auswertung,
- Evidence-Schema und Statusberechnung.

Jeder Agent Run MUSS vollständig an seine konkreten Eingaben und Ergebnisse gebunden sein. Zwei unterschiedliche gültige Implementierungen DÜRFEN dieselben Obligations erfüllen.

## 22. V2-Demo-Use-Case

Die Calendar Product Spec wird um folgendes Feld erweitert:

```yaml
Event.location:
  type: Text
  optional: true
  classification: PersonalData
```

### Erwarteter Ablauf

1. `specforge diff` erkennt `field:Event.location` als semantische Änderung.
2. Der Resolver leitet weiterhin Security- und Privacy-Requirements ab.
3. Der Consolidator ergänzt Response- und Persistence-Obligations.
4. `specforge plan` zeigt betroffene Backend-, Frontend- und Testflächen.
5. `specforge implement --agent codex` lässt Codex Modelle, API, Persistenz, UI und Tests ändern.
6. Permission-, Build-, Static-, Requirement- und Regression-Gates laufen.
7. Evidence verknüpft die Location-Requirements mit Work Order, Codeänderungen und Tests.

### Fehlerszenario

Codex ergänzt `location` im Backend, vergisst aber das Frontend.

Erwartung:

```text
Agent Run: REJECTED
Verification: TEST-PRODUCT-LOCATION-UI FAILED
Expected: editable field Event.location
Observed: field absent
```

Ein Repair Work Order darf genau diesen Fehler adressieren. Nach erfolgreicher Reparatur werden alle Gates erneut ausgeführt.

### Mehrfachanforderungs-Szenario

Für `operation:read_event` gelten gleichzeitig Authentication, Ownership, Response Minimization, Audit Logging und Rate Limiting. SpecForge MUSS daraus einen konsolidierten Auftrag erzeugen. Codex erhält keinen separaten Prompt pro Requirement.

## 23. Abnahmekriterien

V2 ist abgenommen, wenn automatisiert nachgewiesen ist:

1. Typisierte Targets werden ohne operationenspezifische Sonderlogik verarbeitet.
2. Mindestens fünf Requirements aus unterschiedlichen Knowledge Packages werden für dasselbe Target konsolidiert.
3. Identische Obligations werden dedupliziert, wobei alle Quellen erhalten bleiben.
4. Mengen-, Grenzwert- und Konflikt-Merge-Semantiken funktionieren deterministisch.
5. Ein Policy-Konflikt stoppt die Verarbeitung vor dem Agent-Aufruf.
6. `specforge plan` erzeugt bei gleichen Eingaben byte-identische Work Orders.
7. `implement --dry-run` ruft keinen Agenten auf und verändert keine Anwendungdatei.
8. Der Codex Adapter erhält Work Order, Resolved Spec, Patterns und Schreibgrenzen.
9. Codex erweitert die Calendar-Anwendung um `Event.location` in Backend, Persistenz, API und Frontend.
10. Änderungen außerhalb von `MAY_MODIFY` werden als Permission Violation abgelehnt.
11. Entfernen oder Abschwächen einer obligatorischen Verification wird abgelehnt.
12. Ein vollständiger erfolgreicher Agent Run erzeugt alle vorgeschriebenen Evidence-Verknüpfungen.
13. Eine unvollständige Implementierung wird durch das Requirement Gate abgelehnt.
14. Ein Repair Run erhält ausschließlich den ursprünglichen Scope und konkrete Fehlerbeobachtungen.
15. Nach der konfigurierten maximalen Anzahl fehlgeschlagener Reparaturen endet der Prozess mit `REJECTED`.
16. Zwei unterschiedliche Implementierungen können akzeptiert werden, sofern sie dieselben Obligations erfüllen.
17. Eine rein visuelle, erlaubte Änderung verändert weder Product Spec noch Requirement Resolution.
18. Repository, Knowledge Packages und Generatorpfade enthalten keine Templates, Template-Dateien oder Template-Engines.
19. Der Report weist Codex-Nutzung, Modellkennung, Work Order, Diff und Verifikationsumfang aus.
20. Der Report enthält keine globale Compliance-Aussage.

## 24. Nichtziele von V2

V2 umfasst ausdrücklich keine:

- autonome Änderung zentraler Policies durch Codex,
- Akzeptanz aufgrund einer Selbsteinschätzung des Agenten,
- unbegrenzten Reparaturschleifen,
- vollständige automatische Rechtsauslegung,
- Garantie byte-identischer agentischer Codegenerierung,
- perfekte minimale Impact Analysis,
- universelle Unterstützung aller Programmiersprachen und Frameworks,
- automatische Produktionsfreigabe oder Deployment,
- vollständige Multi-Repository-Orchestrierung mit organisationsweiter Rechteverwaltung,
- Ersetzung deterministischer, programmatischer Serializer für kanonische strukturierte Artefakte.

## 25. Geplante Architekturbausteine

V2 ergänzt die V1-Architektur um:

```text
src/specforge/
├── diff/                 Semantischer Spec-Diff
├── obligations/          Normalisierung und Konsolidierung
├── impact/               konservativer Impact Scope
├── planning/             Implementation Plan und Work Order
├── agents/
│   ├── protocol.py       Agent-Adapter-Schnittstelle
│   └── codex.py          Codex Adapter
├── gates/                Permission, Build, Static, Requirement, Regression
├── runs/                 Agent- und Repair-Run-Verwaltung
└── evidence/             erweiterte Traceability

knowledge/
└── */*/patterns/         Guidance, Constraints und Verification-Bezüge

generated/<product>/
├── obligations.json
├── implementation-plan.json
├── impact-scope.json
└── work-orders/

runs/<product>/<run-id>/
├── work-order.json
├── agent-result.json
├── changes.patch
├── gate-results.json
└── evidence.json
```

## 26. Implementierungsphasen

### Phase 1: Typisierte Targets und semantischer Diff

V1-Target-Strings werden migriert. `diff` zeigt fachliche Änderungen zwischen zwei Resolved Specs.

### Phase 2: Implementation Obligations und Consolidator

Controls werden nach Surface normalisiert, deterministisch kombiniert und auf Konflikte geprüft.

### Phase 3: Patterns als Agent Guidance

Pattern-Schema wird um Constraints, Empfehlungen, Verbote und Beispiele erweitert. Sämtliche Templates, Template-Dateien, Template-Verzeichnisse und Template-Engines werden entfernt; Generatorpfade werden auf programmatische Serialisierung oder agentische Implementierung umgestellt.

### Phase 4: Implementation Plan, Impact Scope und Work Order

`plan` und `implement --dry-run` erzeugen reproduzierbare, schema-validierte Agent-Eingaben.

### Phase 5: Codex Adapter und Permission Gate

Codex bearbeitet einen isolierten Workspace. Änderungen außerhalb des erlaubten Scopes werden abgelehnt.

### Phase 6: Build-, Static-, Requirement- und Regression-Gates

Agent-Ergebnisse werden ausschließlich anhand deterministischer Gates akzeptiert.

### Phase 7: Repair Runs, Evidence und Demo

Begrenzte Reparaturschleife, vollständige Traceability und der Calendar-Location-Demo-Flow werden umgesetzt.

## 27. Leitentscheidung

SpecForge V2 verwendet keine Templates und ist kein autonomer Compliance-Agent.

Es ist ein deterministischer Requirements Compiler mit einem agentischen Implementierungsbackend:

```text
Deterministic systems define and verify the obligations.
Codex integrates them into real software.
Only evidence decides acceptance.
```
