# Knowledge in SpecForge

Knowledge ist der versionierte, wiederverwendbare Teil einer Spezifikation. Ein
Produkt beschreibt seine konkreten Entitäten und Operationen; Knowledge-Pakete
liefern dazu Begriffe, formale Requirements, Regeln für deren Anwendbarkeit und
passende Implementierungsmuster. Beim Auflösen entsteht daraus eine
deterministische `resolved-spec.json`.

## Paketstruktur und Einbindung

Ein Paket liegt unter `knowledge/<namespace>/<version>/`:

```text
knowledge/privacy/1.0.0/
├── package.yaml
├── concepts/*.yaml
├── requirements/*.yaml
├── rules/*.yaml
└── patterns/*.yaml
```

Nur `package.yaml` ist zwingend vorhanden. Die vier Unterordner sind optional.
Das Manifest bezeichnet das Paket:

```yaml
name: privacy
version: "1.0.0"
owner: privacy-team
```

Ein Produkt pinnt Pakete über `knowledge_dependencies` auf eine exakte Version:

```yaml
knowledge_dependencies:
  privacy: "1.0.0"
  security: "1.0.0"
```

Beim Laden muss der Pfad existieren und `name` sowie `version` im Manifest
müssen dem Namespace und der gepinnten Version entsprechen. Der Compiler
berechnet zusätzlich einen SHA-256-Hash über relative Dateinamen und den
unveränderten Inhalt aller Dateien des Paketverzeichnisses. Version und Hash
werden in der aufgelösten Spec und später in der Evidence festgehalten. Damit
ändert auch eine inhaltliche Änderung ohne Versionswechsel den Hash der
aufgelösten Spec. `owner` ist derzeit Metadatum und wird nicht ausgewertet.

## Die vier Knowledge-Bausteine

### Concepts: Begriffe und semantische Beziehungen

Concepts definieren eine kleine Ontologie. Ein Concept hat eine global
eindeutige `id`, eine Version, optionale Oberbegriffe (`is_a`), optionale
Klassifikationen und eine Quellenangabe:

```yaml
id: User
version: "1.0.0"
is_a: [Person]
source:
  type: internal_taxonomy
  document: privacy-concepts
  version: "1.0.0"
  section: user
```

Der Compiler lehnt unbekannte Oberbegriffe, doppelte Concept-IDs und Zyklen in
`is_a` ab. Anschließend bildet er die semantische Hülle. Dabei werden

- transitive `is_a`-Beziehungen,
- geerbte Klassifikationen,
- Klassifikationen eines Feldes aus dessen Typ und
- Klassifikationen einer Entität aus ihren Feldern

als neue Fakten hergeleitet. Jedes hergeleitete Faktum nennt seine Prämissen
und die verwendete Ableitung. Diese Herkunft landet in `trace.json` und
`semantic-facts.json`.

### Requirements: entscheidbare Erwartungen

Eine Requirement-Datei ist die kanonische Definition einer Erwartung:

```yaml
id: PRIVACY-001
version: "1.0.0"
statement: API responses expose only fields declared by the resolved resource schema.
expectation:
  control: response_data_minimization
  operator: equals
  value: declared_fields_only
verifications:
  - id: TEST-PRIVACY-001
    adapter: response_schema
    setup: owner_read
    assertion:
      response_fields: [description, end, id, location, owner_id, start, title]
source:
  type: internal_policy
  document: privacy-policy
  version: "1.0.0"
  section: response-minimization
```

`expectation` ist der Sollwert eines Controls. Aktuell ist nur der Operator
`equals` erlaubt. Jede Definition braucht mindestens eine Verification und
mindestens eine davon muss verpflichtend sein (`mandatory` ist standardmäßig
`true`). Unterstützte Adapter sind `http_request`, `response_schema`,
`domain_invariant`, `audit_log` und `rate_limit`. Eine Assertion muss mindestens
ein ausführbares, vom Datenmodell unterstütztes Feld enthalten. Unbekannte
Felder werden in allen Knowledge-Modellen abgewiesen.

Die `statement`-Texte in `product.yaml` sind lesbare Produktdeklarationen. Für
die aufgelöste Instanz gelten jedoch Statement, Version, Erwartung, Quelle und
Verifications aus der zentralen Requirement-Definition.

### Rules: wann ein Requirement gilt

Regeln matchen deklarativ gegen Fakten und erzeugen Requirement-Instanzen:

```yaml
id: security/authenticated-personal-data
version: "1.0.0"
when:
  all:
    - fact: {subject: "$operation", predicate: returns, object: "$resource"}
    - fact: {subject: "$resource", predicate: contains_classification, object: PersonalData}
then:
  requirement: SEC-001
  target: "$operation"
source:
  type: internal_policy
  document: security-policy
  version: "1.0.0"
  section: authenticated-personal-data
```

Die eingeschränkte DSL kennt `fact`, `all`, `any`, `not` und `equals`. Ein mit
`$` beginnender Wert ist eine Variable; die erste passende Tatsache bindet sie,
weitere Bedingungen müssen dieselbe Bindung erfüllen. Die Auswertung ist
seiteneffektfrei. `then.requirement` muss auf eine geladene Definition zeigen;
`then.target` darf eine gebundene Variable verwenden. Doppelte Regel-IDs sind
in Kombination mit ihrer Version verboten.

Eine abgeleitete Instanz speichert Regel-ID und -Version, Variablenbindungen
und die IDs aller verwendeten Fakten. Treffen mehrere Ableitungen auf dasselbe
Paar aus Requirement und Target zu, werden sie in einer Instanz konsolidiert.

### Patterns: wie eine Erwartung umgesetzt werden kann

Patterns verbinden eine Requirement-Instanz mit einer kompatiblen Umsetzung:

```yaml
id: fastapi/declared-response-schema
version: "1.0.0"
satisfies: [PRIVACY-001]
stack: fastapi-react
controls: {response_data_minimization: declared_fields_only}
verifications: [TEST-PRIVACY-001]
artifacts: [backend/app.py]
```

Der Compiler wählt das erste nach ID und Version sortierte Pattern, das den
Control-Wert der Instanz adressiert und alle Verification-IDs der Definition
aufführt. Neben der gezeigten Form unterstützt das Modell eine explizite
`addresses`-Beschreibung sowie Metadaten wie Kompatibilitäten, Abhängigkeiten,
Constraints, Empfehlungen, Beispiele und Skills. Enthält ein Artifact- oder
Beispielpfad das Wort `template`, wird das Pattern abgewiesen. Gibt es für eine
Instanz kein kompatibles Pattern, bricht das Auflösen mit `SF1501` ab.

## Was beim Auflösen passiert

`uv run specforge resolve products/calendar` führt diese Schritte aus:

1. Die Product Spec wird strikt validiert und alle gepinnten Pakete werden in
   sortierter Reihenfolge geladen und gehasht.
2. Product-Entitäten, Felder und Operationen werden in atomare Fakten wie
   `has_field`, `has_type`, `classified_as`, `returns` und `scope` normalisiert.
3. Concepts ergänzen diese Fakten durch die semantische Hülle.
4. Explizit in `declared_requirements` genannte Requirements werden direkt für
   die dort genannte Operation instanziiert.
5. Rules werden gegen alle Fakten ausgewertet und erzeugen weitere, begründete
   Requirement-Instanzen.
6. Für jede Instanz wird ein kompatibles Pattern ausgewählt.
7. Expectations werden pro Target und Control konsolidiert. Fordern zwei
   Instanzen unterschiedliche Werte für dasselbe Control desselben Targets,
   stoppt der Compiler mit `SF1301` und nennt Requirements, Regeln und
   Paketversionen.
8. Das Ergebnis wird kanonisch sortiert und gehasht. Geschrieben werden
   `normalized-product.json`, `normalized-facts.json`, `semantic-facts.json`,
   `trace.json` und `resolved-spec.json` unter `generated/<product>/`.

Alle aufgelösten Requirements beginnen mit dem Status `REQUIRED`. Erst
`specforge validate` führt ihre Verification Adapter aus. Die daraus erzeugte
Evidence bindet Beobachtungen an den Hash der aufgelösten Spec, den Git-Stand
und die exakten Knowledge-Paketversionen und -Hashes.

## Nachvollziehen und Ändern

Warum ein Requirement gilt, zeigt `explain` einschließlich Regeln, Fakten und
deren Herkunft:

```bash
uv run specforge explain SEC-001 --product products/calendar
uv run specforge explain SEC-001 --product products/calendar --target operation:read_event
uv run specforge explain SEC-001 --product products/calendar --group-by resource
```

Eine Knowledge-Änderung sollte als neue semantische Paketversion unter einem
neuen Verzeichnis veröffentlicht und anschließend in
`knowledge_dependencies` gepinnt werden. `resolve` ist zugleich die praktische
Paketvalidierung: Es erkennt unter anderem Schemafehler, fehlende Referenzen,
Concept-Zyklen, doppelte IDs, nicht ausführbare Requirements, fehlende Patterns
und widersprüchliche Controls. Danach sollten mindestens `resolve` und die
Tests ausgeführt werden; bei geänderter Verifikation zusätzlich `validate`.

