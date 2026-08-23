# Spec: Standardbasierte Autorenformate für SpecForge

Status: Accepted and implemented
Version: 1.0
Datum: 2026-08-23
Ersetzt: die Autorenformat-Entscheidungen aus ADR 0001, ADR 0002
und den entsprechenden Teilen von ADR 0006

## 1. Ziel

SpecForge soll fachliche Eingaben nicht länger primär in einer eigenen
YAML-Struktur beschreiben. Autoren sollen etablierte Formate und Vokabulare
verwenden können, die auch außerhalb von SpecForge mit Standardwerkzeugen
geparst, geprüft und abgefragt werden können.

Nach der Migration gilt:

- RDF ist nicht nur Compiler-IR und Export, sondern auch das normative
  Autorenmodell für Product und Knowledge.
- TriG ist das primäre, menschenlesbare Containerformat für versionierte
  RDF-Datasets und Named Graphs.
- SHACL Core beschreibt die zulässige Form der Eingaben.
- SKOS und RDFS beschreiben Begriffe und formale Beziehungen.
- DCAT 3 und Dublin Core Terms beschreiben Pakete, Versionen, Abhängigkeiten
  und Distributionen, soweit deren Vokabulare ausreichen.
- PROV-O beschreibt Herkunft.
- RIF Core ist das normative Austauschformat der unterstützten Rule-Teilmenge.
- SPARQL-Dateien beschreiben gespeicherte Abfragen und Views.
- SpecForge definiert nur die noch fehlende Domänensemantik, nicht erneut deren
  Dateiformate.

YAML bleibt ausschließlich für lokale, nicht-fachliche Werkzeugkonfiguration
zulässig. Eine Product Spec, ein Knowledge Package, eine Rule, ein Requirement,
ein Pattern oder eine Verification darf nach dem Cutover nicht mehr nur als
YAML vorliegen.

## 2. Problem des heutigen Zustands

Heute existieren drei Schichten:

```text
proprietäre YAML-Struktur
→ Pydantic-Objekte
→ kanonisches RDF-Dataset
```

Das erzeugt eine unnötige zweite Modellierungssprache:

- Beziehungen sind in YAML zunächst nur verschachtelte Schlüssel und Strings.
- Identität entsteht erst durch Compilerlogik statt unmittelbar durch IRIs.
- RDF-, SHACL- und SPARQL-Werkzeuge können die Quellen nicht direkt lesen.
- Pydantic- und SHACL-Constraints können auseinanderlaufen.
- Neue Semantic-Web-Funktionen müssen zuerst in der YAML-DSL nachgebaut werden.
- Ein semantischer Roundtrip kann die ursprüngliche YAML-Formatierung ohnehin
  nicht sinnvoll bewahren.

Die Migration beseitigt nicht jede SpecForge-eigene Semantik. Es gibt keinen
allgemeinen W3C-Begriff für eine SpecForge Requirement Instance, ein
Implementation Pattern oder einen Verification Adapter. Diese Begriffe bleiben
im kleinen SpecForge-Vokabular, werden aber als RDF-Ressourcen in
Standardformaten dargestellt.

## 3. Normative Formatmatrix

| Artefakt | Normatives Autorenformat | Normative Vokabulare | Generierte Darstellungen |
|---|---|---|---|
| Product | TriG (`product.trig`) | RDF, RDFS, SHACL, DCTERMS, `sf:` | JSON-LD, N-Quads, Kompatibilitäts-JSON |
| Package Manifest | TriG (`package.trig`) | DCAT 3, DCTERMS, PROV-O, SPDX-Checksum, `sf:` | Katalog-JSON-LD |
| Begriffe/Glossar | Turtle (`vocabulary.ttl`) | SKOS, SKOS-XL optional, RDFS | JSON-LD, Explorer-View |
| Domain-/Policy-Aussagen | TriG oder Turtle | RDF, RDFS und publizierte Fachvokabulare | kanonische N-Quads |
| Requirement Definition | Turtle oder Paket-TriG | DCTERMS, PROV-O, SHACL sofern datenförmig, `sf:` | Explorer- und Reporting-Views |
| Rule | RIF Core XML (`*.rif.xml`) | RIF Core und RIF-RDF/OWL Compatibility | generierte Datalog-Leseansicht |
| Implementation Pattern | Turtle oder Paket-TriG | DCTERMS, SPDX optional, `sf:` | Agent-Work-Order-Projektion |
| Verification Definition | Turtle oder Paket-TriG | SHACL, EARL wo passend, PROV-O, `sf:` | ausführbare Adapter-Projektion |
| gespeicherte View | SPARQL 1.1 Query (`*.rq`) | SPARQL 1.1 | JSON-Ergebnisprojektion |
| Validation Result | Turtle oder TriG | SHACL Validation Report | menschenfreundliche Evidence |
| Laufzeit-Evidence | TriG | PROV-O, SHACL, EARL, DCTERMS | Report-HTML/JSON |
| kanonischer Hash-Input | N-Quads | RDFC-1.0 | SHA-256-Digest |

TriG wird gewählt, weil ein TriG-Dokument ein vollständiges RDF-Dataset aus
Default Graph und Named Graphs darstellen kann. Turtle bleibt für Dokumente
geeignet, die genau einen Graphen enthalten. JSON-LD 1.1 bleibt ein
standardisiertes Austauschformat, aber nicht die primäre handgeschriebene
Syntax: Kontexte und verschachtelte Frames verschleiern für diesen Anwendungsfall
häufig die tatsächlich gespeicherten Aussagen.

Normative Grundlagen:

- [RDF 1.1 Concepts](https://www.w3.org/TR/rdf11-concepts/)
- [RDF 1.1 TriG](https://www.w3.org/TR/trig/)
- [JSON-LD 1.1](https://www.w3.org/TR/json-ld11/)
- [SHACL](https://www.w3.org/TR/shacl/)
- [SKOS](https://www.w3.org/TR/skos-reference/)
- [PROV-O](https://www.w3.org/TR/prov-o/)
- [SPARQL 1.1 Query](https://www.w3.org/TR/sparql11-query/)
- [DCAT 3](https://www.w3.org/TR/vocab-dcat-3/)
- [RIF Core](https://www.w3.org/TR/rif-core/)
- [RIF RDF and OWL Compatibility](https://www.w3.org/TR/rif-rdf-owl/)
- [RDFC-1.0](https://www.w3.org/TR/rdf-canon/)

SHACL 1.0 bleibt das verbindliche Profil. Neuere SHACL-Entwürfe werden erst
nach einer separaten Conformance-Entscheidung übernommen.

## 4. Zielstruktur eines Products

```text
products/calendar/
├── product.trig
└── glossary.ttl
```

Der versionierte, öffentliche Autorenvertrag liegt zentral unter
`vocabulary/1.0.0/shapes.ttl`; wiederverwendbare Views werden als `.rq`-
Ressourcen mit SpecForge ausgeliefert. Product-spezifische Shapes oder Views
dürfen zusätzlich neben `product.trig` liegen.

`product.trig` enthält mindestens zwei Named Graphs:

```trig
@prefix sf: <https://specforge.dev/vocab/> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix product: <https://specforge.dev/product/calendar/> .

 # Dieser Graph enthält Identität, Stack und gepinnte Knowledge-Abhängigkeiten.
product:graph-metadata {
  # Diese Aussage deklariert die Ressource als Product.
  product:1.0.0 a sf:Product ;
    # Diese Aussage legt die stabile Product-Kennung fest.
    dcterms:identifier "calendar" ;
    # Diese Aussage pinnt die konkrete Product-Version.
    dcterms:hasVersion "1.0.0" ;
    # Diese Aussage benennt den verwendeten technischen Stack.
    sf:usesStack <https://specforge.dev/stack/fastapi-react> ;
    # Diese Aussage pinnt das app-unabhängige Privacy Package.
    dcterms:requires <https://specforge.dev/package/privacy/1.1.0> ;
    # Diese Aussage pinnt das fachliche Calendar Package.
    dcterms:requires <https://specforge.dev/package/calendar/1.1.0> .
}

# Dieser Graph enthält das fachliche Modell des Products.
product:graph-model {
  # Diese Aussage deklariert Event als fachliche Entity.
  product:Event a sf:Entity ;
    # Diese Aussage ordnet Event das owner-Feld zu.
    sf:hasField product:Event-owner ;
    # Diese Aussage ordnet Event das description-Feld zu.
    sf:hasField product:Event-description .

  # Diese Aussage deklariert Event-description als Field.
  product:Event-description a sf:Field ;
    # Diese Aussage legt Text als Wertetyp des Feldes fest.
    sf:valueType <https://specforge.dev/datatype/Text> ;
    # Diese Aussage klassifiziert den Feldinhalt als personenbezogen.
    sf:classifiedAs <https://specforge.dev/classification/PersonalData> .

  # Diese Aussage deklariert read_event als ausführbare Operation.
  product:read_event a sf:Operation ;
    # Diese Aussage benennt Event als bearbeitete Ressource.
    sf:actsOn product:Event ;
    # Diese Aussage benennt Event als zurückgegebene Ressource.
    sf:returns product:Event ;
    # Diese Aussage legt Lesen als positive Aktion fest.
    sf:action <https://specforge.dev/action/read> .
}
```

Felder werden zusätzlich durch SHACL Property Shapes beschrieben. RDF-Klassen
und SHACL Shapes dürfen dieselbe fachliche Ressource referenzieren, bleiben aber
unterschiedliche Aussagen: RDFS beschreibt Bedeutung und Typbeziehungen, SHACL
beschreibt erwartete Datenform.

Produktdeklarierte Requirements werden über ihre IRI und ihr Target verknüpft;
Statement, Erwartung und Verification werden nicht im Product dupliziert.

## 5. Zielstruktur eines Knowledge Packages

```text
knowledge/privacy/1.2.0/
├── package.trig
├── vocabulary.ttl
├── requirements.ttl
├── rules.ttl
├── rules.rif.xml
└── patterns.ttl
```

Die Dateiaufteilung ist redaktionell. Normativ ist das zusammengeführte
RDF-Dataset plus die geladenen RIF-Dokumente. Zwei anders aufgeteilte Pakete
sind semantisch gleich, wenn ihre kanonisierten Datasets und Rules gleich sind.

### 5.1 Paketmanifest

Eine Paketversion ist ein `dcat:Dataset`; ihre Dateien sind
`dcat:Distribution`. Titel, Beschreibung, Version und Herausgeber verwenden
Dublin Core Terms. Der Inhaltsdigest wird als SPDX-Checksum beschrieben.

```trig
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix spdx: <http://spdx.org/rdf/terms#> .
@prefix sf: <https://specforge.dev/vocab/> .
@prefix pkg: <https://specforge.dev/package/privacy/> .

# Diese Aussage deklariert die Version als DCAT Dataset und Policy Package.
pkg:1.2.0 a dcat:Dataset, sf:PolicyPackage ;
  # Diese Aussage legt die stabile Package-Kennung fest.
  dcterms:identifier "privacy" ;
  # Diese Aussage pinnt die konkrete Package-Version.
  dcterms:hasVersion "1.2.0" ;
  # Diese Aussage gibt dem Package einen verständlichen Titel.
  dcterms:title "Privacy Knowledge"@en ;
  # Diese Aussage benennt die RDF-Distribution des Packages.
  dcat:distribution pkg:1.2.0-rdf ;
  # Diese Aussage benennt die RIF-Distribution des Packages.
  dcat:distribution pkg:1.2.0-rules .
```

`sf:PolicyPackage`, `sf:DomainPackage`, `sf:ImplementationPackage` und
`sf:IntegrationPackage` bleiben notwendige SpecForge-Klassen. Für
`binds domain` und `binds implementation` gibt es in DCAT keinen ausreichend
präzisen Ersatz; hierfür bleiben `sf:bindsDomain` und
`sf:bindsImplementation` bestehen. Allgemeine Abhängigkeiten verwenden
`dcterms:requires`.

### 5.2 Begriffe

Glossare werden als SKOS Concept Scheme gepflegt. Labels dürfen nicht parallel
in JSON oder JavaScript gepflegt werden.

```turtle
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix privacy: <https://specforge.dev/knowledge/privacy/concept/> .

# Diese Aussage deklariert PersonalData als standardisierten SKOS-Begriff.
privacy:PersonalData a skos:Concept ;
  # Dieses Label ist der bevorzugte deutsche Begriff.
  skos:prefLabel "Personenbezogene Daten"@de ;
  # Diese Definition erklärt den Begriff in Alltagssprache.
  skos:definition "Daten mit Bezug zu einer identifizierten oder identifizierbaren Person."@de .
```

Eine formale Klassenbeziehung wird nicht mit `skos:broader` modelliert, sondern
mit `rdfs:subClassOf`. SKOS organisiert Begriffe; RDFS beschreibt formale
Typsemantik.

### 5.3 Requirement Definitions

Ein Requirement bleibt eine `sf:RequirementDefinition`, weil RDF, DCAT und
SHACL keinen allgemeinen Begriff für eine ausführbare Systemanforderung
definieren. Bestehende Vokabulare werden für Metadaten wiederverwendet:

```turtle
@prefix sf: <https://specforge.dev/vocab/> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix prov: <http://www.w3.org/ns/prov#> .

# Diese Aussage deklariert eine ausführbare Requirement Definition.
<https://specforge.dev/requirement/PRIVACY-001/1.2.0> a sf:RequirementDefinition ;
  # Diese Aussage legt die stabile Requirement-Kennung fest.
  dcterms:identifier "PRIVACY-001" ;
  # Diese Aussage pinnt die konkrete Definition-Version.
  dcterms:hasVersion "1.2.0" ;
  # Diese Aussage formuliert die Erwartung für Menschen.
  dcterms:description "API responses expose only fields declared by the resolved resource schema."@en ;
  # Diese Aussage benennt das app-unabhängige Control per stabiler IRI.
  sf:control <https://specforge.dev/control/response_data_minimization> ;
  # Diese Aussage wählt den standardisierten Gleichheitsoperator.
  sf:operator <https://specforge.dev/operator/equals> ;
  # Diese Aussage legt den erwarteten Control-Wert fest.
  sf:expectedValue "declared_fields_only" ;
  # Diese Aussage verbindet die Definition mit ihrer ausführbaren Verification.
  sf:verifiedBy <https://specforge.dev/verification/TEST-PRIVACY-001> ;
  # Diese Aussage bewahrt die maschinenlesbare Herkunft der Definition.
  prov:wasDerivedFrom <https://specforge.dev/source/privacy-policy/response-minimization> .
```

Blank Nodes sind nur für lokale, nicht extern referenzierte Strukturen erlaubt.
Requirement Definitions, Controls, Verifications und Quellen besitzen IRIs.

ReqIF wird nicht zum primären Format. Es ist für den Austausch klassischer
Requirements-Management-Dokumente geeignet, bildet aber RDF-Datasets, Rules,
Named Graphs und semantische Ableitungen nicht direkt ab. Ein späterer
ReqIF-Import/Export darf als Adapter ergänzt werden.

### 5.4 Rules

RDF selbst definiert keine Rule-Ausführung. Datalog beschreibt die gewünschte
Semantik gut, besitzt aber keine universell standardisierte Dateisyntax. Eine
proprietäre `.dlog`-Syntax würde das Ziel dieser Spec verfehlen.

Deshalb gilt:

1. RIF Core XML ist das normative persistierte Rule-Austauschformat.
2. Die unterstützte Teilmenge bleibt sicheres positives Datalog.
3. RIF Frames bilden RDF-Aussagen gemäß RIF-RDF/OWL Compatibility ab.
4. Der Compiler normalisiert RIF vor der Ausführung in seine interne
   positive Datalog-Repräsentation.
5. Eine kompakte Datalog-Ansicht wird für Menschen generiert, aber nicht als
   zweite normative Quelle gespeichert.
6. Eine Rule, die nicht verlustfrei zwischen RIF Core und der internen Teilmenge
   abgebildet werden kann, wird beim Import abgelehnt.

Das ist ein bewusster Ergonomie-Trade-off: RIF Core ist standardisiert, aber
XML ist deutlich schwerer zu schreiben als die alte YAML-DSL. Der Explorer und
Editor müssen deshalb eine verständliche WENN-/DANN-Ansicht über dem RIF-Modell
anbieten. Komfort wird in Werkzeugen gelöst, nicht durch ein neues Dateiformat.

SWRL bleibt ausgeschlossen. Es würde eine zweite Rule-Semantik einführen und
ist für das aktive positive Datalog-Profil nicht erforderlich. OWL 2 RL bleibt
ebenfalls inaktiv, bis ein eigenes Conformance-Profil beschlossen wird.

### 5.5 Implementation Patterns

Für SpecForge-Implementation-Patterns existiert kein ausreichendes
Standardvokabular. Sie bleiben `sf:ImplementationPattern`, verwenden aber:

- `dcterms:identifier`, `dcterms:description` und `dcterms:requires`,
- IRIs statt String-IDs für Requirements, Controls und Verifications,
- SPDX-Begriffe für Softwareartefakte und Checksums, wenn anwendbar,
- SHACL Shapes für maschinenprüfbare Kompatibilitätsbedingungen,
- SKOS-Begriffe für redaktionelle Kategorien.

Freie Empfehlungen bleiben sprachmarkierte RDF-Literale. Maschinenentscheidende
Constraints dürfen nicht ausschließlich in freiem Text stehen.

### 5.6 Verifications und Evidence

SHACL wird nur für RDF-Datenform und Metamodell-Constraints verwendet. Eine
HTTP-Beobachtung wird nicht künstlich als SHACL Constraint implementiert.

- `sf:Verification` beschreibt Adapter, Setup und erwartete Beobachtung.
- ein Verification-Lauf ist `prov:Activity`,
- verwendete Product-, Knowledge- und Softwarestände sind `prov:Entity`,
- der konkrete Testausgang kann zusätzlich mit EARL beschrieben werden,
- Modellvalidierung erzeugt einen normgerechten `sh:ValidationReport`,
- alle Resultate werden in einem Evidence-Named-Graph zusammengeführt.

Ein bestandenes Resultat beweist nur die bezeichnete Erwartung am bezeichneten
Softwarestand, keine allgemeine Compliance.

## 6. Lernkommentare in Autoren- und Leseformaten

Alle fachlichen Quelldateien müssen gleichzeitig als Lernmaterial lesbar sein.
Deshalb erhält jede handgeschriebene semantische Aussage eine unmittelbar
zugeordnete Erklärung in Alltagssprache. Die Erklärung beschreibt, was die
Aussage im SpecForge-Modell bedeutet, nicht bloß, wie ihre Syntax heißt.

Diese Erklärungen heißen **Lernkommentare**.

### 6.1 Verbindliche Regeln

1. Jede handgeschriebene fachliche Aussage besitzt genau an ihrer Fundstelle
   einen Lernkommentar. Bei RDF ist eine Aussage ein Triple, bei RIF ein Head-
   oder Bedingungsatom, bei Datalog/Prolog ein Head- oder Body-Literal und bei
   SPARQL ein fachlich relevantes Triple Pattern, ein Filter oder eine Bindung.
2. Der Kommentar steht unmittelbar in der Zeile vor der Aussage. Zwischen
   Kommentar und Aussage dürfen weder eine Leerzeile noch eine andere Aussage
   stehen. Inline-Kommentare sind nicht ausreichend, weil ihre Zuordnung bei
   Umformatierungen mehrdeutig werden kann.
3. Kompakte Syntax ändert diese Granularität nicht: Erzeugt eine Turtle- oder
   TriG-Predicate-List mehrere RDF-Triples, erhält jede Predicate-Object-Zeile
   ihren eigenen Kommentar. Mehrere Objekte hinter einem Komma werden auf
   getrennte, jeweils kommentierte Predicate-Object-Zeilen verteilt.
4. Jede Bedingung und jeder Head einer Rule besitzt einen eigenen Kommentar.
5. Jeder Named Graph wird zusätzlich durch einen Kommentar eingeleitet, der
   seinen fachlichen Kontext erklärt.
6. Kommentare verwenden zunächst Alltagssprache und dürfen danach den
   Standardbegriff nennen.
7. Ein Kommentar wiederholt nicht nur Bezeichner. „Definiert ein Event“ ist
   hilfreich; „Event definition“ ist es nicht.
8. Kommentare müssen zusammen mit der Aussage geändert werden. Ein nachweislich
   widersprüchlicher Kommentar ist ein Validierungsfehler.
9. Maschinell erzeugte kanonische Formate wie N-Quads benötigen keine
   Kommentare. Menschenorientierte generierte Leseansichten müssen sie aus
   Labels, Definitionen und Templates reproduzierbar erzeugen.
10. Ein fehlender Kommentar verändert nicht den RDFC-Hash, lässt aber Authoring
   Lint und CI fehlschlagen.
11. Kommentare dürfen niemals die einzige Quelle fachlicher Bedeutung,
    Herkunft oder einer Constraint sein.
12. Reine Syntax benötigt keinen Lernkommentar. Dazu gehören Prefix- und Base-
    Deklarationen, öffnende und schließende Klammern, XML-Container sowie
    Satzzeichen. Kommentare erklären Semantik, nicht Zeichensetzung.

### 6.2 Turtle und TriG

Turtle und TriG verwenden `#`. Auch bei Predicate Lists wird jedes erzeugte
Triple einzeln erklärt:

```trig
@prefix sf: <https://specforge.dev/vocab/> .
@prefix product: <https://specforge.dev/product/calendar/> .

# Dieser Named Graph enthält Aussagen, die das Calendar-Produkt selbst deklariert.
product:graph-model {
  # read_event ist eine ausführbare Produktoperation.
  product:read_event a sf:Operation ;
    # Die Operation gibt ein Event zurück.
    sf:returns product:Event .

  # Event-description ist ein Feld des Produktmodells.
  product:Event-description a sf:Field ;
    # Das Feld ist als personenbezogen klassifiziert.
    sf:classifiedAs <https://specforge.dev/classification/PersonalData> .
}
```

Für Satzzeichen ist kein Kommentar nötig. Bei derselben Ressource darf die
Subjektangabe ausgelassen werden, aber nicht die Erklärung des nächsten
Prädikat-Objekt-Paars. Diese Schreibweise lässt Leser Aussage und Bedeutung
zeilenweise zuordnen und bringt ihnen zugleich die kompakte RDF-Syntax bei.

### 6.3 SHACL

Eine Shape erklärt zuerst ihr Prüfziel. Jede nicht triviale Constraint-Gruppe
erklärt anschließend Erwartung und Fehlerbedeutung:

```turtle
# Diese Shape prüft, dass jede Operation genau eine fachliche Aktion besitzt.
sf:OperationShape a sh:NodeShape ;
  # Diese Aussage richtet die Shape auf alle Operationen.
  sh:targetClass sf:Operation ;
  # Diese Aussage bindet die konkrete action-Prüfung ein.
  sh:property sf:OperationShape-action .

# Fehlt sf:action oder kommt es mehrfach vor, ist die Operation nicht eindeutig ausführbar.
sf:OperationShape-action a sh:PropertyShape ;
  # Diese Aussage wählt sf:action als zu prüfendes Prädikat.
  sh:path sf:action ;
  # Diese Aussage verlangt mindestens genau einen Wert.
  sh:minCount 1 ;
  # Diese Aussage erlaubt höchstens genau einen Wert.
  sh:maxCount 1 ;
  # Diese Meldung erklärt einen Verstoß im Validation Report.
  sh:message "Eine Operation benötigt genau eine fachliche Aktion."@de .
```

`sh:message` bleibt zusätzlich verpflichtend, weil ein RDF-Kommentar nicht Teil
des Validation Reports ist.

### 6.4 RIF Core und Datalog-/Prolog-Leseansicht

RIF Core XML verwendet XML-Kommentare. Jede Rule erklärt vor dem Rule-Element
WENN und DANN in einem verständlichen Satz. Innerhalb komplexer Konjunktionen
werden einzelne Bedingungen ebenfalls kommentiert, sofern der RIF-Parser an
dieser Stelle XML-Kommentare verlustfrei akzeptiert.

Die generierte Datalog-/Prolog-Leseansicht verwendet `%` als
Zeilenkommentar. Sie ist nicht normativ, muss aber jede Rule und jedes Literal
erklären:

```prolog
% PRIVACY-001 gilt für eine Operation, wenn diese personenbezogene Daten zurückgibt.
applies('PRIVACY-001', Operation) :-
    % Die Operation liefert die Ressource als Response.
    returns(Operation, Resource),
    % Die zurückgegebene Ressource enthält personenbezogene Daten.
    contains_classification(Resource, 'PersonalData'),
    % Nur positiv aufgezählte Response-Aktionen lösen diese Rule aus.
    response_action(Operation).
```

Die Kommentare dieser Ansicht werden aus SKOS-/RDFS-Definitionen,
Rule-Metadaten und stabilen redaktionellen Erklärungstexten generiert. Sie
dürfen keine unabhängig gepflegte Rule-Semantik enthalten.

### 6.5 SPARQL

Gespeicherte `.rq`-Dateien erklären Zweck, Ergebnisvariablen und jeden
nicht-trivialen Graph Pattern Block mit `#`:

```sparql
# Findet für jede Requirement Instance die Rule und ihre verwendeten Prämissen.
SELECT ?instance ?rule ?premise WHERE {
  # Die qualifizierte PROV-Ableitung verbindet Instance, Rule und Assertion.
  ?instance prov:qualifiedDerivation ?derivation .
  # Diese Aussage liefert die bei der Ableitung verwendete Rule.
  ?derivation sf:usedRule ?rule .
  # Diese Aussage liefert eine konkret verwendete Prämisse.
  ?derivation prov:entity ?premise .
}
```

### 6.6 Formate ohne Kommentare

JSON-LD und N-Quads besitzen keine portable Kommentarsyntax. Sie sind deshalb
nicht das primäre handgeschriebene Autorenformat. Verständliche Erklärungen
werden dort als `rdfs:comment`, `skos:definition`, `sh:message` oder
`dcterms:description` modelliert und bleiben Teil des Datasets.

Lernkommentare und maschinenlesbare Beschreibungen ergänzen sich:

- Lernkommentar: erklärt die konkrete Zeile beim Lesen der Datei,
- `skos:definition`/`rdfs:comment`: erklärt einen wiederverwendbaren Begriff,
- `sh:message`: erklärt ein konkretes Validierungsergebnis,
- PROV-O: hält maschinenlesbare Herkunft fest.

### 6.7 Prüfung

`specforge lint-comments` prüft mindestens:

- jeden Named Graph auf einen einleitenden Kommentar,
- jede handgeschriebene RDF-Subjektgruppe auf einen zugeordneten Kommentar,
- jede RIF Rule und jedes Rule-Literal auf eine Erklärung,
- jede gespeicherte SPARQL Query auf Zweck und kommentierte Graph Patterns,
- verbotene Platzhalter wie `TODO`, bloße ID-Wiederholungen und leere
  Kommentare.

Ob ein Kommentar inhaltlich widersprüchlich ist, kann nicht allein syntaktisch
vollständig entschieden werden. CI prüft deshalb deterministische Mindestregeln;
fachliche Reviews prüfen die Aussagequalität. Eine automatische Bewertung
durch ein Sprachmodell ist nicht Teil des normativen Builds.

## 7. Parser- und Compilerarchitektur

Die heutige Kette wird ersetzt:

```text
Vorher
YAML → Pydantic → RDF

Nachher
TriG/Turtle ─┐
JSON-LD ─────┼→ RDF Dataset → SHACL → Datalog-Fixpunkt → SHACL → PROV/Evidence
RIF Core ────┘                    ↑
                               Rule IR
```

Normative Reihenfolge:

1. lokale RDF-Dateien ohne Netzwerkzugriff parsen,
2. alle IRIs auflösen und erlaubte Named Graphs zuordnen,
3. das Source Dataset gegen die SpecForge Authoring Shapes validieren,
4. RIF-Core-Dokumente parsen und ihre Referenzen gegen das Dataset prüfen,
5. sichere positive Rules bis zum kleinsten Fixpunkt auswerten,
6. abgeleitete Assertions mit PROV-O ergänzen,
7. das Resolved Dataset erneut mit SHACL validieren,
8. mit RDFC-1.0 kanonisieren und SHA-256 berechnen,
9. optionale Kompatibilitätsprojektionen erzeugen.

Pydantic darf intern für Python-Datentransferobjekte verbleiben, ist aber weder
Quelle noch normativer Validator. SHACL ist der öffentlich überprüfbare
Autorenvertrag.

## 8. Lokale und sichere Ausführung

Standardformate dürfen keine implizite Netzwerkabhängigkeit erzeugen:

- Remote JSON-LD Contexts sind verboten; Kontexte werden lokal ausgeliefert.
- `owl:imports` wird nicht automatisch aus dem Netzwerk geladen.
- SPARQL `SERVICE` ist verboten.
- RIF `Import` darf nur auf im Package manifestierte lokale Distributionen
  zeigen.
- Relative IRIs werden nur gegen die deklarierte Package-Basis aufgelöst.
- Zulässige Dateiendungen und MIME Types werden strikt geprüft.

Eine Graphdatenbank bleibt unnötig. Das Dataset kann vollständig im Prozess
liegen.

## 9. CLI und Dateierkennung

Die CLI akzeptiert nach Phase 2:

```text
specforge resolve products/calendar/product.trig
specforge validate products/calendar/product.trig
specforge sparql products/calendar/product.trig --query views/proof.rq
specforge rdf-check knowledge/privacy/1.2.0/package.trig
specforge rif-check knowledge/privacy/1.2.0/rules.rif.xml
```

Dateierkennung geschieht anhand Endung plus Parservalidierung:

| Endung | Format |
|---|---|
| `.trig` | TriG / RDF Dataset |
| `.ttl` | Turtle / einzelner RDF Graph |
| `.jsonld` | JSON-LD 1.1 |
| `.nq` | N-Quads, primär generiert |
| `.rif.xml` | RIF Core XML |
| `.rq` | SPARQL 1.1 Query |

Ein generisches `.json` oder `.xml` wird nicht geraten. Parserfehler nennen
Datei, Graph, Fokusressource, Shape und Constraint statt eines Pydantic-Pfads.

## 10. Migration

### Phase 0: Contracts einfrieren

- aktuelle YAML-Beispiele, Resolved Datasets, Rule-Ableitungen und Hashes als
  Golden Tests sichern,
- SpecForge Authoring Shapes vollständig machen,
- Vokabular-IRIs versionieren und publizieren,
- ADR 0001, 0002 und 0006 nach Annahme dieser Spec aktualisieren.

### Phase 1: verlustfreier Konverter

- `specforge migrate-format <yaml> --to trig` implementieren,
- Knowledge und Products einschließlich Quellen in RDF überführen,
- Rules separat als RIF Core XML ausgeben,
- jedes Ergebnis erneut importieren,
- Gleichheit über Requirement Instances, Controls, Bindungen, Patterns,
  Verifications, Provenance und RDFC-Hash prüfen.

Der Konverter überschreibt keine Quelldateien. Er schreibt in ein explizites
Zielverzeichnis und erzeugt einen Migrationsreport.

### Phase 2: begrenzter Migrations-Leseweg

- der getrennte `migrate-format`-Befehl liest alte YAML-Quellen,
- der normale Compiler liest ausschließlich Standardformate,
- alle neuen Beispiele und Tests verwenden ausschließlich Standardformate,
- der Konverter erzeugt nie gleichzeitig eine zweite normative Quelle im
  ursprünglichen Verzeichnis.

### Phase 3: Repository-Cutover

- alle vorhandenen Products und Knowledge Packages migrieren,
- `docs/knowledge.md`, Training und Explorer auf Standardquellen umstellen,
- YAML-Golden-Tests durch RDF-/RIF-Conformance-Tests ersetzen,
- neue Package-Versionen veröffentlichen, statt bestehende Versionen heimlich
  inhaltlich umzuschreiben.

### Phase 4: YAML entfernen

- YAML-Loader für fachliche Inputs entfernen,
- Pydantic-Modelle auf interne Projektionen begrenzen,
- alte YAML-Unterstützung bei Bedarf in ein separates Importwerkzeug auslagern,
- lokale Werkzeugkonfiguration darf YAML bleiben.

## 11. Rückwärtskompatibilität

Während genau einer Major-Version gilt:

- YAML bleibt ausschließlich über `migrate-format` importierbar,
- `resolved-spec.json` bleibt eine generierte Kompatibilitätsprojektion,
- seine Feldreihenfolge und internen Fact-IDs sind nicht semantisch normativ,
- der RDFC-Hash des RDF-Datasets ist die Identität des fachlichen Inhalts,
- alte und neue Inputs müssen dieselben Requirement-Anwendungen erzeugen.

Der Produktionspfad benötigt bereits nach dem Repository-Cutover kein YAML.
Ein permanenter dualer Stack ist ausdrücklich kein Ziel.

## 12. Tests und Conformance

Automatisiert zu prüfen sind mindestens:

1. TriG-, Turtle-, JSON-LD- und N-Quads-Roundtrips erhalten Dataset-Isomorphie.
2. SHACL Authoring Shapes lehnen fehlende IDs, Versionen und ungültige
   Paketrollen ab.
3. Jede fachlich adressierbare Ressource besitzt eine IRI.
4. Package-Abhängigkeiten und Integration Bindings referenzieren exakt geladene
   Versionen.
5. SKOS-, RDFS- und SHACL-Beziehungen werden nicht semantisch vermischt.
6. RIF Core importiert und exportiert die vollständige unterstützte
   positive-Datalog-Teilmenge verlustfrei.
7. unsichere Variablen, Negation und nicht unterstützte RIF-Konstrukte werden
   mit stabilen Fehlercodes abgewiesen.
8. Der getrennte YAML-Konverter erzeugt dieselben Requirement Instances,
   Bindungen, Patterns und Verifications wie die frühere Quelle.
9. eine geänderte Serialisierungsreihenfolge verändert den RDFC-Hash nicht.
10. eine fachlich geänderte Aussage verändert den RDFC-Hash.
11. Remote Contexts, Imports und SPARQL SERVICE werden abgewiesen.
12. Explorer und Training lesen Labels und Beziehungen nur aus dem
    SKOS-/RDFS-Vokabular.
13. Validation Reports sind SHACL-konform und Evidence besitzt PROV-Herkunft.
14. das vollständige Calendar-Produkt lässt sich ohne YAML, Netzwerk und
    Graphdatenbank auflösen, prüfen und visualisieren.
15. der Comment Linter erkennt unkommentierte Named Graphs, RDF-Subjektgruppen,
    Rule-Literale und SPARQL Graph Patterns.
16. Beispiele und generierte Datalog-/Prolog-Leseansichten enthalten für jede
    Aussage einen verständlichen Lernkommentar.

Conformance wird gegen die offiziellen W3C-Test-Suites geprüft, soweit diese
für RDF-Parser, JSON-LD, SPARQL, SHACL und RDFC anwendbar sind. SpecForge-eigene
Vokabularregeln erhalten zusätzlich publizierte SHACL Shapes.

## 13. Akzeptanzkriterien

Die Migration ist abgeschlossen, wenn:

1. Product und sämtliche Knowledge Packages im Repository keine fachlichen
   YAML-Dateien mehr enthalten,
2. alle Package-Metadaten als DCAT-/DCTERMS-RDF vorliegen,
3. Begriffe ausschließlich aus SKOS-/RDFS-Quellen stammen,
4. Requirements, Patterns und Verifications als RDF-Ressourcen mit stabilen
   IRIs vorliegen,
5. Rules ausschließlich aus RIF Core geladen und intern als sicheres positives
   Datalog ausgewertet werden,
6. SHACL der normative Autorenvertrag ist,
7. PROV-O alle Ableitungen und Läufe bis zu lokalen Quelldistributionen
   zurückverfolgbar macht,
8. gespeicherte Views normale `.rq`-Dateien sind,
9. alle bisherigen Calendar-Ableitungen semantisch unverändert bleiben,
10. der normale Resolve-Pfad weder Pydantic-YAML-Modelle noch proprietäre
    Knowledge-Parser benötigt,
11. ein frischer Checkout ausschließlich mit lokalen Dateien gebaut und
    validiert werden kann,
12. Dokumentation und Training keine YAML-Autorenschaft mehr lehren.
13. alle handgeschriebenen Turtle-, TriG-, RIF- und SPARQL-Quellen den
    Lernkommentar-Contract erfüllen,
14. ein fehlender Lernkommentar den Authoring-Lint fehlschlagen lässt, ohne die
    RDF-Semantik oder den RDFC-Hash zu verändern.

## 14. Bewusste Grenzen

- Standardformat bedeutet nicht, dass jedes Fachvokabular bereits existiert.
  Das kleine `sf:`-Vokabular bleibt erforderlich und wird durch RDFS, SKOS und
  SHACL formal dokumentiert.
- RDF/XML wird unterstützt, falls es durch RDFLib eingelesen wird, aber weder
  empfohlen noch in Beispielen verwendet.
- JSON-LD ist Austauschformat, nicht kanonische Byte-Darstellung.
- N-Quads ist Hash- und Debugformat, nicht Autorenformat.
- RIF Core wird gewählt, obwohl sein Autorenkomfort schwach ist. Ein eigener
  Editor darf RIF erzeugen, aber keine zweite normative Rule-Datei pflegen.
- ODRL wird nur für tatsächliche Permissions, Prohibitions und Duties verwendet,
  nicht als Universalmodell für Privacy- und Security-Requirements.
- ReqIF darf als Adapter entstehen, ersetzt aber nicht das semantische Dataset.
- OWL 2 RL, SWRL, SHACL Advanced Features und externe Triplestores bleiben
  außerhalb dieser Migration.

## 15. Getroffene Ergonomieentscheidung

Knowledge-Autoren speichern ausschließlich RIF Core. Bestehende Rules werden
durch `migrate-format` erzeugt; `export-prolog`, Explorer und Training bieten
kommentierte WENN-/DANN-Leseansichten. Ein späterer visueller Editor darf RIF
Core erzeugen, speichert aber keine zweite Rule-Quelle. Eine zusätzliche
persistierte SpecForge-Rule-DSL ist nicht zulässig.

## 16. Umsetzungsnachweis

Der Repository-Cutover ist abgeschlossen:

- Product und alle 13 Knowledge-Package-Versionen verwenden ausschließlich
  TriG, Turtle und RIF Core als fachliche Quellen.
- `vocabulary/1.0.0/specforge.ttl` und `shapes.ttl` sind die vom Compiler und
  vom Wheel tatsächlich geladenen öffentlichen Verträge.
- gespeicherte Views liegen als ausgelieferte `.rq`-Ressourcen vor.
- `lint-comments`, `rdf-check`, `rif-check`, `migrate-format` und die
  kommentierte `export-prolog`-Leseansicht sind implementiert.
- der normale Resolve-Pfad lädt das optionale YAML-Modul nicht; nur der
  getrennte Legacy-Konverter verwendet die optionale `legacy`-Dependency.
- `specforge resolve`, `generate`, `validate`, `visualize` und `training`
  funktionieren vollständig lokal auf den Standardquellen.

Die ausführbaren Nachweise liegen insbesondere in `tests/test_authoring.py`,
`tests/test_semantic.py`, `tests/test_compiler.py`,
`tests/test_visualization.py` und `tests/test_training.py`.
