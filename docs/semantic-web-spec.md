# Spec: Semantic-Web-Grundlage für SpecForge

Status: Superseded in its authoring-format decisions by ADR 0007
Version: 0.3
Datum: 2026-08-22

Hinweis: Diese Spec bleibt die Grundlage für Dataset, Semantik und
Conformance-Profil. Ihre Aussagen zur fortgesetzten YAML-Autorenschaft wurden
durch [`standard-authoring-formats-spec.md`](standard-authoring-formats-spec.md)
und ADR 0007 ersetzt.

## 1. Ziel

SpecForge soll sein Wissensmodell nicht als proprietären Graphen neu erfinden.
Produktwissen, Policies, Requirements, Rules, Patterns, Verifications und
Evidence werden auf etablierte Semantic-Web-Standards abgebildet. TriG,
Turtle, RIF Core und SPARQL sind zugleich normative Quellen; eine zusätzliche
fachliche YAML-Autorenansicht existiert nach ADR 0007 nicht mehr.

Das Ergebnis muss:

- mit existierenden RDF-, Datalog-, SHACL-, SKOS-, PROV- und
  SPARQL-Werkzeugen nutzbar sein,
- weiterhin ohne Graphdatenbank lokal und deterministisch funktionieren,
- die bestehende Nachvollziehbarkeit bis zu Facts und Quellen erhalten,
- schrittweise eingeführt werden können,
- SpecForge-eigene Begriffe nur dort einführen, wo kein passender Standardbegriff
  existiert.

## 2. Nicht-Ziele

- Eine Graphdatenbank wird nicht vorausgesetzt.
- Ein allgemeiner Editor für RDF und RIF ist nicht Teil dieser Grundlage.
- OWL wird nicht als allgemeine Programmiersprache für Requirements verwendet.
- Nicht jede Privacy- oder Security-Anforderung wird künstlich in ODRL gepresst.
- SHACL Advanced Features und RDF 1.2 sind in Version 1 nicht normativ.
- RIF-XML wird nicht zum primären Autorenformat.
- SWRL wird in Version 1 weder als Autorenformat noch als Austausch- oder
  Ausführungsformat unterstützt. Die allgemeine Verbindung von OWL DL und
  SWRL-Rules gefährdet Entscheidbarkeit und würde eine zweite Rule-Semantik
  neben Datalog einführen.
- Der Spec Explorer wird nicht selbst zum semantischen Speicher; er visualisiert
  das standardisierte Dataset.

## 3. Normative Standards

| Aufgabe | Standard | Verwendung in SpecForge |
|---|---|---|
| Graph-Datenmodell | [RDF 1.1](https://www.w3.org/TR/rdf11-concepts/) | Knoten, Aussagen, IRIs und RDF-Datasets |
| Austauschformat | [JSON-LD 1.1](https://www.w3.org/TR/json-ld11/) | kanonisches öffentliches JSON-Format |
| Lesbare RDF-Darstellung | [Turtle](https://www.w3.org/TR/turtle/) | Dokumentation, Debugging und Tests |
| Struktur und Constraints | [SHACL](https://www.w3.org/TR/shacl/) | Schema- und Requirement-Validierung |
| Begriffe und Glossare | [SKOS](https://www.w3.org/TR/skos-reference/) | Labels, Definitionen, Synonyme und Begriffshierarchien |
| Herkunft | [PROV-O](https://www.w3.org/TR/prov-o/) | Ableitungen, Compilerläufe, Quellen und Verantwortliche |
| Regelableitungen | sicheres positives Datalog; [RIF Core](https://www.w3.org/TR/rif-core/) für Austausch | Fixpunkt, semantische Hülle und Requirement-Anwendbarkeit |
| Abfragen | [SPARQL 1.1](https://www.w3.org/TR/sparql11-query/) | Explorer-Ansichten und Ad-hoc-Abfragen |
| Deterministische Hashes | [RDFC-1.0](https://www.w3.org/TR/rdf-canon/) | kanonische N-Quads vor SHA-256 |
| Paketkatalog | [DCAT 3](https://www.w3.org/TR/vocab-dcat-3/) | Knowledge-Pakete und ihre Distributionen |
| Formale Typbeziehungen | [RDFS](https://www.w3.org/TR/rdf-schema/) | Klassen, Properties und Unterklassen |
| Optionale Zugriffspolicies | [ODRL 2.2](https://www.w3.org/TR/odrl-model/) | nur echte Permissions, Prohibitions und Duties |

OWL 2 RL darf später als optionales, explizites Reasoning-Profil ergänzt werden.
Version 1 benötigt nur RDF-, RDFS- und die von SpecForge definierten
Ableitungsregeln.

## 4. Identitäten und IRIs

Jede fachlich adressierbare Ressource erhält eine stabile IRI. Die Basis-IRI ist
konfigurierbar; Beispiele verwenden `https://specforge.dev/`.

```text
https://specforge.dev/vocab/                         SpecForge-Vokabular
https://specforge.dev/product/calendar/2.0.0         Product
https://specforge.dev/entity/calendar/Event          Entity
https://specforge.dev/operation/calendar/read_event  Operation
https://specforge.dev/package/privacy/1.1.0           Package-Version
https://specforge.dev/requirement/PRIVACY-001/1.1.0   Requirement Definition
https://specforge.dev/rule/privacy/minimize-personal-data/1.1.0
https://specforge.dev/run/<uuid>                      Compiler-/Verifier-Lauf
```

Regeln:

1. IDs werden nicht aus Labels erzeugt.
2. Versionierte Definitionen besitzen versionierte IRIs.
3. Eine unversionierte IRI darf mit `dcterms:hasVersion` auf Versionen zeigen.
4. Blank Nodes sind nur für lokale SHACL-Strukturen erlaubt. Alle Elemente, die
   in Trace, Evidence oder UI referenziert werden, benötigen eine IRI.
5. Produktinterne Namen werden durch die Product-ID qualifiziert.

## 5. RDF-Dataset und Named Graphs

Ein Resolve-Lauf erzeugt ein RDF-Dataset mit benannten Graphen:

| Named Graph | Inhalt |
|---|---|
| `…/graph/product` | deklarierte Product Spec |
| `…/graph/package/<name>/<version>` | Inhalt einer Knowledge-Paketversion |
| `…/graph/inferred` | deterministisch abgeleitete Aussagen |
| `…/graph/resolved` | Requirement-Instanzen und Pattern-Auswahl |
| `…/graph/provenance` | PROV-O-Herkunft des Laufs |
| `…/graph/evidence` | Verification-Ergebnisse und SHACL-Reports |

Der Default Graph enthält nur Dataset-Metadaten und Links auf die Named Graphs.
Ein Paketgraph ist unveränderlich. Eine neue Paketversion erhält eine neue IRI.

## 6. Wiederverwendete Vokabulare

### 6.1 Knowledge-Pakete

Eine Paketversion ist `dcat:Dataset`. TriG und Turtle sind normative lokale
`dcat:Distribution`-Darstellungen; JSON-LD ist eine generierte Austauschansicht. Name, Beschreibung,
Version und Owner verwenden nach Möglichkeit `dcterms:title`,
`dcterms:description`, `dcat:version` und `dcterms:publisher`.

Die SpecForge-Paketrollen bleiben als kleine kontrollierte SKOS Concept Scheme
erhalten: `sf:PolicyPackage`, `sf:DomainPackage`,
`sf:IntegrationPackage`, `sf:ImplementationPackage`.

Allgemeine Abhängigkeiten verwenden `dcterms:requires`. Nur die fachlich
notwendige Präzisierung bleibt SpecForge-spezifisch:

```turtle
calimpl:1.0.0 a dcat:Dataset, sf:IntegrationPackage ;
  dcterms:requires calendar:1.1.0, fastapi:1.0.0 ;
  sf:bindsDomain calendar:1.1.0 ;
  sf:bindsImplementation fastapi:1.0.0 .
```

`sf:bindsDomain` und `sf:bindsImplementation` sind Unterproperties von
`dcterms:relation`. Der Explorer darf daraus die verständlichen Texte
„verbindet Domäne“ und „verbindet Implementierung“ erzeugen.

### 6.2 Begriffe und Glossare

Glossarbegriffe sind `skos:Concept` in einem `skos:ConceptScheme`.

- sichtbarer Name: `skos:prefLabel` mit Sprach-Tag,
- Synonym: `skos:altLabel`,
- Suchalias oder verbreiteter Schreibfehler: `skos:hiddenLabel`,
- Erklärung: `skos:definition`,
- lockere Hierarchie: `skos:broader` und `skos:narrower`,
- verwandter Begriff: `skos:related`.

Eine formale Typbeziehung darf nicht stillschweigend aus `skos:broader`
abgeleitet werden. Fachliche Typen verwenden `rdfs:Class` und
`rdfs:subClassOf`. Damit trennt SpecForge künftig „Begriff zur Erklärung“ von
„Klasse für maschinelles Reasoning“.

### 6.3 Product, Entity, Field und Operation

- Product: `sf:Product` und `prov:Entity`
- Entity-Typ: `rdfs:Class`
- Field: eine SHACL Property Shape; bei globaler Semantik zusätzlich
  `rdf:Property`
- Datentyp: XSD-Datentyp oder IRI einer `rdfs:Class`
- Operation: `sf:Operation`
- `acts_on`: `sf:actsOn`
- `returns`: `sf:returns`
- `actor`: `prov:wasAssociatedWith`, soweit semantisch passend; andernfalls
  `sf:actorType`

Feldpflicht, Optionalität, Kardinalität, Datentyp und erlaubte Werte werden mit
SHACL ausgedrückt (`sh:minCount`, `sh:maxCount`, `sh:datatype`, `sh:class`,
`sh:in`). `response_name` bleibt eine SpecForge-Annotation an der Property
Shape, weil es ein Serialisierungsalias und keine neue fachliche Property ist.

### 6.4 Requirements, Rules und Patterns

Für diese Konzepte existiert kein einzelnes W3C-Vokabular mit der benötigten
Bedeutung. SpecForge definiert deshalb ein kleines Vokabular:

- `sf:RequirementDefinition`
- `sf:RequirementInstance`
- `sf:Rule`
- `sf:ImplementationPattern`
- `sf:Verification`

Gemeinsame Metadaten verwenden weiterhin Standards: `dcterms:identifier`,
`dcterms:description`, `dcterms:source`, `dcterms:conformsTo` und PROV-O.

Ein Requirement, das eine Datenform beschreibt, wird als SHACL Shape
ausgedrückt. Zugriffspolitiken dürfen ODRL verwenden, wenn sie tatsächlich eine
Permission, Prohibition oder Duty beschreiben. Andere Requirements bleiben
`sf:RequirementDefinition`; ODRL wird nicht als universelles Requirement-Modell
missbraucht.

### 6.5 Facts und Herkunft

Normale Tatsachen sind gewöhnliche RDF-Tripel. Für eine einzeln adressierbare
Trace-Einheit erzeugt SpecForge zusätzlich eine `sf:Assertion` mit stabiler IRI
und `rdf:subject`, `rdf:predicate`, `rdf:object`. Dies erlaubt die bestehende
Fact-ID, ohne RDF-star vorauszusetzen.

Ein Resolve- oder Validate-Lauf ist `prov:Activity`. Eingaben und Ausgaben sind
`prov:Entity`; Compiler und Verifier sind `prov:SoftwareAgent`. Herkunft wird
mit `prov:used`, `prov:wasGeneratedBy`, `prov:wasDerivedFrom`,
`prov:wasAssociatedWith` und bei Bedarf qualifizierten Derivationsbeziehungen
modelliert.

## 7. Validierung mit SHACL

SHACL übernimmt zwei getrennte Aufgaben:

1. **Metamodell-Validierung:** Sind Product Specs, Package Manifests, Rules und
   Requirements vollständig und typkorrekt?
2. **Requirement-Validierung:** Erfüllen aufgelöste Product- oder Evidence-Daten
   die anwendbaren Shapes?

Jeder Lauf erzeugt einen standardkonformen `sh:ValidationReport`. Die heutige
Evidence darf als menschenfreundliche Projektion bestehen, muss aber auf den
Report und seine `sh:ValidationResult`-Knoten verweisen.

Pydantic bleibt während der Migration als frühe Autorenvalidierung erlaubt.
SHACL ist jedoch die normative, exportierbare Validierungsschicht. Pydantic und
SHACL müssen durch gemeinsame Contract-Tests dieselben Pflichtfelder und
Kardinalitäten akzeptieren beziehungsweise ablehnen.

## 8. Rules und Ableitungen mit Datalog

SHACL Core validiert Daten, ist aber keine allgemeine Rule Engine. SPARQL ist
eine RDF-Abfragesprache, definiert jedoch keine allgemeine iterative
Rule-Ausführung. SpecForge verwendet deshalb Datalog als normative Semantik für
Ableitungen:

1. deklarierte RDF-Aussagen werden in endliche Datalog-Relationen projiziert,
2. sichere positive Datalog-Regeln werden bis zum kleinsten Fixpunkt ausgewertet,
3. abgeleitete Relationen werden als RDF-Aussagen und PROV-O-Herkunft exportiert,
4. SHACL validiert den resultierenden Graphen,
5. SPARQL fragt deklarierte und abgeleitete Graphen ab.

### 8.1 OWL-Integration

OWL-Kompatibilität erfolgt ausschließlich über das für regelbasierte
Auswertung vorgesehene Profil OWL 2 RL. Wenn SpecForge OWL-2-RL-Axiome
unterstützt, werden deren standardisierte Ableitungsregeln in die gleiche
sichere Datalog-/RIF-Core-Ausführung eingebracht. Sie bilden keinen zweiten
Reasoner mit abweichender Rule-Semantik.

OWL-Axiome außerhalb des unterstützten OWL-2-RL-Profils müssen mit einem
diagnostischen Fehler abgelehnt werden. SpecForge darf sie nicht stillschweigend
ignorieren oder nur teilweise auswerten. Die Nutzung von OWL 2 RL bleibt bis
zur Implementierung des entsprechenden Conformance-Profils optional.

RIF Core ist der normative Persistenz- und Austauschstandard für Rules, soweit
die SpecForge-Teilmenge darin ausdrückbar ist. Eine kompakte Datalog-Darstellung
ist eine generierte Leseansicht, keine zweite normative Quelle.

### 8.2 Relationen

RDF-Tripel werden nicht ausschließlich in einer universellen
`triple(subject, predicate, object)`-Relation verarbeitet. Häufig verwendete
Predicates erhalten typisierte Relationen:

```prolog
acts_on(Operation, Resource).
returns(Operation, Resource).
has_field(Entity, Field).
classified_as(Resource, Classification).
contains_classification(Resource, Classification).
requires(Operation, Requirement).
```

Die Abbildung zwischen RDF-Property-IRI und Datalog-Relation wird im
SpecForge-Vokabular deklariert. Dadurch bleibt der RDF-Export interoperabel,
während Rules lesbar und effizient auswertbar bleiben.

### 8.3 Rule-Semantik

Eine SpecForge Rule besteht aus einem Rule-Kopf und einer endlichen Konjunktion
von Bedingungen. `any` wird in mehrere Rules mit demselben Kopf übersetzt.
`equals` wird als typisierter Built-in ausgedrückt.

Beispiel:

```prolog
requires(Operation, privacy_001) :-
    returns(Operation, Resource),
    contains_classification(Resource, personal_data),
    response_action(Operation).

response_action(Operation) :- action(Operation, create).
response_action(Operation) :- action(Operation, read).
response_action(Operation) :- action(Operation, update).
```

Rules erzeugen ausschließlich neue Aussagen. Sie dürfen keine Aussagen
löschen, überschreiben oder externe Aktionen ausführen. Das Ergebnis ist eine
Menge; Dateireihenfolge und Rule-Reihenfolge dürfen es nicht beeinflussen.

### 8.4 Sicherheit und Terminierung

Version 1 unterstützt sicheres positives Datalog. Jede akzeptierte Rule muss
folgende Bedingungen erfüllen:

1. Jede Variable im Rule-Kopf kommt in mindestens einem positiven Atom des
   Rule-Körpers vor.
2. Variablen in Built-ins sind zuvor durch positive Atome gebunden.
3. Funktionssymbole, die neue verschachtelte Terme erzeugen, sind verboten.
4. Alle Ausgangsrelationen und Wertebereiche sind endlich.
5. Netzwerk-, Datei-, Zeit-, Zufalls- und andere nicht-deterministische
   Funktionen sind verboten.
6. Rules haben keine Seiteneffekte.

Unter diesen Bedingungen terminiert die Auswertung auf einem endlichen Dataset
am kleinsten Fixpunkt. Ein Implementierungslimit darf Ressourcenverbrauch
begrenzen, ist aber kein Bestandteil der fachlichen Semantik. Das Überschreiten
des Limits ist ein Fehler und darf kein partielles Ergebnis als gültig ausgeben.

### 8.5 Negation und Closed World

Fehlende RDF-Aussagen sind unter der Open-World-Annahme nicht automatisch
falsch. Das heutige `not` darf deshalb nicht unmarkiert als globale Negation
weitergeführt werden.

Version 1 bevorzugt positive Relationen oder explizite Wertemengen. Die
Privacy-Ausnahme für `delete` wird beispielsweise durch positive
`response_action`-Facts für `create`, `read` und `update` modelliert.

Stratifizierte Negation darf später nur für Relationen eingeführt werden, die
im Package Manifest ausdrücklich als `closed` deklariert sind. Dann gilt:

- jede Variable eines negierten Atoms ist zuvor positiv gebunden,
- ein negativer Abhängigkeitszyklus ist verboten,
- die Strata werden in topologischer Reihenfolge ausgewertet,
- Closed-World-Geltungsbereich und Herkunft werden im RDF-Export festgehalten.

Stratifizierte Negation ist eine SpecForge-Erweiterung über die positive
RIF-Core-Teilmenge hinaus und muss beim RIF-Export entweder als Erweiterung
gekennzeichnet oder abgelehnt werden.

### 8.6 Provenance

Für jede abgeleitete Assertion speichert die Engine mindestens:

- die Rule-IRI und Rule-Version,
- die gebundenen Variablen,
- die IRIs der verwendeten Ausgangs- oder abgeleiteten Assertions,
- den Resolve-Lauf als `prov:Activity`.

Mehrere Beweise derselben Aussage werden konsolidiert, aber nicht verworfen.
Der RDF-Export beschreibt sie als getrennte qualifizierte PROV-O-Ableitungen.

### 8.7 Nicht normative Rule-Adapter

SPARQL `CONSTRUCT` und SHACL Advanced Features dürfen als Import- oder
Exportadapter angeboten werden. Sie definieren nicht die Ausführungssemantik.
Ein Adapter muss nachweisen, dass sein Ergebnis für die unterstützte Teilmenge
dem Datalog-Fixpunkt entspricht; andernfalls muss er die Rule ablehnen.

SWRL ist in Version 1 ausdrücklich kein solcher Adapter. Eine spätere
Unterstützung erfordert eine neue Version dieser Spec, ein definiertes
Entscheidbarkeitsprofil, eine vollständige Abbildung auf die normative
Datalog-Semantik und eigene Conformance-Tests. Das Vorhandensein von
SWRL-Elementen in einem importierten OWL-Dokument führt zu einem diagnostischen
Fehler; sie dürfen nicht stillschweigend übersprungen werden.

## 9. Kanonisierung und Hashes

Der bisherige Hash über proprietäres kanonisches JSON wird für semantische
Artefakte ersetzt durch:

1. Dataset ohne Laufzeitfelder wie Zeitstempel bilden,
2. mit RDFC-1.0 kanonisieren,
3. kanonische N-Quads als UTF-8 serialisieren,
4. SHA-256 berechnen,
5. Algorithmus explizit als `rdfc-1.0+sha256` speichern.

Semantisch isomorphe RDF-Datasets erhalten damit unabhängig von
Serialisierung, Tripelreihenfolge und Blank-Node-Namen denselben Hash.

## 10. Ein- und Ausgabeformate

### 10.1 Autoreneingabe

Version 1 akzeptiert TriG für RDF-Datasets, Turtle für einzelne Graphen und
Shapes, RIF Core für Rules sowie SPARQL 1.1 für gespeicherte Views. JSON-LD 1.1
und N-Quads bleiben standardisierte Austausch- beziehungsweise Hashformate.

Alle Formate werden zuerst in dasselbe RDF-Dataset geparst. Semantik darf nicht
vom Eingabeformat abhängen.

### 10.2 Compiler-Ausgabe

Normative Ausgaben:

- `resolved-spec.jsonld`
- `resolved-spec.nq` als kanonische N-Quads
- `shacl-report.ttl` oder `shacl-report.jsonld`
- `provenance.jsonld`

Die bisherigen JSON-Dateien bleiben während einer Übergangsphase als
kompatible Projektionen verfügbar und enthalten `conformsTo` sowie den Hash des
zugrunde liegenden RDF-Datasets.

## 11. Spec Explorer

Der Explorer konsumiert das RDF-Dataset über eine interne SPARQL-Seam. Seine
Ansichten sind gespeicherte, versionierte SPARQL-Queries statt hart codierter
Python-Kantenlisten.

Mindestens folgende Ansichten werden definiert:

- Pakete und ihre `dcterms:requires`-/`sf:binds…`-Beziehungen,
- Product, Entities, Fields und Operations,
- Rule-Prämissen und erzeugte Requirement-Instanzen,
- Requirements, Patterns und Verifications,
- PROV-O-Ableitungskette,
- SHACL-Verletzungen.

Labels, Definitionen und Tooltips stammen aus SKOS sowie `rdfs:label` und
`rdfs:comment`. Die UI darf keine zweite, unabhängig gepflegte
Beziehungsdefinition enthalten.

## 12. Kompatibilität und Migration

### Phase 1: Export und Contract-Tests

- SpecForge-Vokabular und SHACL Shapes veröffentlichen.
- Bestehende Modelle verlustfrei nach JSON-LD exportieren.
- Roundtrip-Tests für TriG, Turtle, JSON-LD und N-Quads ergänzen.
- Bestehende Rule-DSL verlustfrei in Datalog normalisieren und Snapshot-Tests
  für die erzeugten Relationen ergänzen.
- Alte und neue Hashes parallel ausgeben.

### Phase 2: RDF als Compiler-IR

- RDF-Dataset wird die kanonische interne Repräsentation.
- Aktuelle Python-Modelle werden Adapter an der Autoren-Seam.
- Rules werden als sicheres positives Datalog bis zum Fixpunkt ausgewertet.
- RIF-Core-Import und -Export werden für die unterstützte Teilmenge ergänzt.
- Explorer liest gespeicherte SPARQL-Ansichten.

### Phase 3: Standardisierte Evidence

- SHACL Validation Reports und PROV-O werden normative Evidence.
- Alte Evidence-JSONs werden nur noch als Projektion erzeugt.
- RDFC-1.0-Hash ersetzt den proprietären Content Hash.

### Phase 4: Alternative Adapter

- JSON-LD- und Turtle-Autorenadapter stabilisieren.
- Optional: externer SPARQL Endpoint oder Triplestore.
- Optional: OWL-2-RL-Conformance-Profil über dieselbe Datalog Engine sowie
  SHACL-AF-Import/Export.

## 13. Conformance

Eine Implementierung erfüllt diese Spec, wenn sie:

1. alle adressierbaren Ressourcen mit stabilen IRIs exportiert,
2. ein valides JSON-LD-1.1-Dokument und RDF-Dataset erzeugt,
3. die definierten Named Graphs trennt,
4. Paketmetadaten als DCAT und Begriffe als SKOS ausdrückt,
5. Validierungsergebnisse als SHACL Validation Report bereitstellt,
6. Ableitungen und Läufe mit PROV-O nachvollziehbar macht,
7. sichere positive Datalog-Regeln unabhängig von ihrer Reihenfolge bis zum
   kleinsten Fixpunkt auswertet,
8. die unterstützte Rule-Teilmenge als RIF Core austauschen kann,
9. SPARQL Queries auf dem aufgelösten Dataset ausführen kann,
10. den Dataset-Hash mittels RDFC-1.0 und SHA-256 berechnet,
11. semantisch isomorphe RDF-Serialisierungen mit demselben Hash auflöst,
12. ohne Graphdatenbank lauffähig bleibt.

## 14. Akzeptanzbeispiel

Für das Calendar-Produkt muss eine SPARQL-Abfrage zeigen können:

```text
calendar · Product
  dcterms:requires calendar-fastapi-react@1.0.0

calendar-fastapi-react@1.0.0 · sf:IntegrationPackage
  sf:bindsDomain calendar@1.1.0
  sf:bindsImplementation fastapi-react@1.0.0
```

Eine zweite Abfrage muss für `PRIVACY-001@read_event` lückenlos liefern:

```text
Product-Facts
→ angewendete Datalog Rule
→ Requirement-Instanz
→ Implementation Pattern
→ Verification
→ SHACL Validation Result
→ PROV-O-Quellen und Compilerlauf
```

Der Spec Explorer muss diese Daten ausschließlich aus dem RDF-Dataset und den
SKOS-Erklärungen darstellen können.

## 15. Implementierungsentscheidungen

1. Die öffentliche Basis-IRI ist `https://specforge.dev/`.
2. RDFLib implementiert RDF und SPARQL, pySHACL SHACL Core und `rdfcanon`
   RDFC-1.0. Die Datalog Engine bleibt hinter dem `SemanticDataset`-Interface,
   weil sie vollständige SpecForge-Provenance liefern muss.
3. RIF Core ist das einzige persistierte Rule-Autorenformat; Datalog ist die
   interne Ausführungssemantik und eine generierte Leseansicht.
4. Version 1 unterstützt keine Negation. Rules müssen positiv formuliert sein.
5. Term-IRIs unter `https://specforge.dev/vocab/` bleiben stabil; die erste
   Ontologie- und Shapes-Version ist `1.0.0`.
6. Alte JSON-, Trace- und Evidence-Projektionen bleiben für einen
   Major-Version-Übergang erhalten.
