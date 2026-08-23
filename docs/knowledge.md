# Knowledge in SpecForge

Knowledge ist der versionierte, wiederverwendbare Teil einer Spezifikation.
Ein Product beschreibt konkrete Entities und Operationen; Knowledge Packages
liefern Begriffe, Requirements, Rules und passende Implementation Patterns.

Fachliche Quellen verwenden ausschließlich standardisierte RDF-/RIF-Formate.
YAML ist kein Autorenformat mehr.

## Paketstruktur

```text
knowledge/privacy/1.1.0/
├── package.trig       # DCAT-Metadaten und Package-Rolle
├── vocabulary.ttl     # SKOS-Begriffe und RDFS-Klassen
├── requirements.ttl   # Requirement Definitions und Verifications
├── patterns.ttl       # optionale Implementation Patterns
├── rules.ttl          # Rule-Metadaten und Provenance
└── rules.rif.xml      # normative positive Rule-Logik in RIF Core
```

Nur `package.trig` ist zwingend. Die übrigen Dateien erscheinen, wenn das
Package entsprechende Ressourcen enthält. Die redaktionelle Dateiaufteilung
ist nicht semantisch: Entscheidend sind das zusammengeführte RDF-Dataset und
die normalisierten RIF Rules.

Jede handgeschriebene Aussage besitzt einen unmittelbar zugeordneten
Lernkommentar. `uv run specforge lint-comments knowledge` prüft diesen Vertrag.
Kommentare helfen beim Lernen, sind aber nicht Teil des RDFC- oder
Package-Content-Hashs.

## Package-Metadaten und Rollen

Eine Package-Version ist ein `dcat:Dataset`. `dcterms:identifier`,
`dcterms:hasVersion`, `dcterms:title`, `dcterms:publisher` und
`dcterms:description` beschreiben sie. SpecForge ergänzt vier präzise Rollen:

- `sf:PolicyPackage`: app-unabhängige Erwartungen und Rules,
- `sf:DomainPackage`: Wissen über eine Fachdomäne,
- `sf:ImplementationPackage`: technische Patterns eines Stacks,
- `sf:IntegrationPackage`: Verbindung genau einer Domain und Implementation.

Ein Integration Package verwendet `sf:bindsDomain` und
`sf:bindsImplementation`. Allgemeine Abhängigkeiten verwenden
`dcterms:requires`.

```trig
# Dieser Graph beschreibt die Verbindung der Calendar-Domäne mit FastAPI React.
<https://specforge.dev/package/calendar-fastapi-react/graph-metadata> {
  # Diese Package-Version bindet ihre Domain- und Implementation-Seite ausdrücklich.
  <https://specforge.dev/package/calendar-fastapi-react/1.0.0>
    a dcat:Dataset, sf:IntegrationPackage ;
    # Diese Kennung ist der stabile Name des Integration Packages.
    dcterms:identifier "calendar-fastapi-react" ;
    # Diese Version pinnt genau den gezeigten Package-Inhalt.
    dcterms:hasVersion "1.0.0" ;
    # Diese Beziehung benennt die fachliche Calendar-Seite der Integration.
    sf:bindsDomain <https://specforge.dev/package/calendar/1.1.0> ;
    # Diese Beziehung benennt die technische FastAPI-React-Seite der Integration.
    sf:bindsImplementation <https://specforge.dev/package/fastapi-react/1.0.0> .
}
```

Das Product pinnt Package-Versionen mit `dcterms:requires`. Der Compiler lehnt
fehlende Versionen und abweichende Integration Bindings mit `SF1004` bis
`SF1006` ab.

## Concepts und Glossare

`vocabulary.ttl` verwendet SKOS für Labels und Erklärungen sowie RDFS für
formale Klassenbeziehungen. `skos:broader` ist keine Alternative zu
`rdfs:subClassOf`: SKOS organisiert Begriffe, RDFS erzeugt formale
Typbeziehungen.

Das öffentliche Basisvokabular liegt in `vocabulary/1.0.0/specforge.ttl` und
wird vom Compiler selbst geladen. Beziehungstexte, Controls, Operatoren und
Verification Adapter werden dort als RDFS-/SKOS-Ressourcen gepflegt; Explorer
und Training besitzen dafür keine zweite JSON- oder Python-Definition.

```turtle
# User ist formal eine Unterklasse von Person und erbt deren Klassifikation.
concept:User a rdfs:Class, skos:Concept ;
  # Diese Kennung macht den Begriff unabhängig von seinem sichtbaren Label adressierbar.
  dcterms:identifier "User" ;
  # Diese formale Beziehung macht jeden User zugleich zu einer Person.
  rdfs:subClassOf concept:Person ;
  # Dieses deutsche Label wird im Explorer angezeigt.
  skos:prefLabel "User"@de ;
  # Diese Definition erklärt den Begriff beim Überfahren mit der Maus.
  skos:definition "Eine Person, die mit einer Anwendung interagiert."@de .
```

Der Compiler leitet transitive Unterklassen, geerbte Klassifikationen,
Typklassifikationen und Klassifikationen aus Feldern als positives Datalog ab.
Jede Ableitung erhält PROV-Herkunft.

## Requirement Definitions

Eine Requirement Definition ist eine `sf:RequirementDefinition` mit stabiler
IRI, Dublin-Core-Metadaten, Control, Erwartungswert, Provenance und mindestens
einer verpflichtenden Verification.

```turtle
# PRIVACY-001 begrenzt Responses auf die Felder des aufgelösten Resource-Schemas.
requirement:PRIVACY-001-1.1.0 a sf:RequirementDefinition ;
  # Diese Kennung verbindet Definition und abgeleitete Requirement Instances.
  dcterms:identifier "PRIVACY-001" ;
  # Diese Version pinnt die konkrete Requirement Definition.
  dcterms:hasVersion "1.1.0" ;
  # Dieses Control benennt die zu steuernde Systemeigenschaft.
  sf:control <https://specforge.dev/control/response_data_minimization> ;
  # Dieser Operator verlangt Gleichheit mit dem erwarteten Wert.
  sf:operator <https://specforge.dev/operator/equals> ;
  # Dieser Wert erlaubt ausschließlich deklarierte Response-Felder.
  sf:expectedValue "declared_fields_only" ;
  # Diese Beziehung benennt die ausführbare Prüfung der Erwartung.
  sf:verifiedBy verification:TEST-PRIVACY-001 ;
  # Diese Beziehung bewahrt die fachliche Herkunft der Definition.
  prov:wasDerivedFrom source:privacy-policy-response-minimization .
```

Listenwerte verwenden `sf:expectedValueList` mit einer RDF List. Dadurch bleibt
eine fachlich relevante Reihenfolge ausdrücklich erhalten.

Unterstützte Verification Adapter sind `http_request`, `response_schema`,
`domain_invariant`, `audit_log` und `rate_limit`. Eine `sf:AssertionSpec`
beschreibt deren maschinenlesbare Erwartung. SHACL prüft den Autorenvertrag;
Pydantic ist nur noch eine interne Python-Projektion.

## Rules

Rule-Logik liegt normativ als RIF Core XML vor. `rules.ttl` enthält Identität,
Version und PROV-Quelle. Der Compiler importiert die unterstützte RIF-Core-
Teilmenge und wertet sie als sicheres positives Datalog bis zum kleinsten
Fixpunkt aus.

- Jede Head-Variable muss positiv gebunden sein.
- Variable Prädikate sind verboten.
- Globale Negation ist verboten.
- Alternativen werden als mehrere positive RIF-Implikationen dargestellt.
- Remote RIF Imports sind verboten.

Der Export enthält XML-Lernkommentare. Eine generierte Datalog-/Prolog-Ansicht
darf die Rule verständlicher anzeigen, ist aber keine zweite Quelle.

## Implementation Patterns

Patterns sind `sf:ImplementationPattern`. Sie referenzieren Requirements,
Stack, Control Bindings, Verifications und betroffene Artefakte über RDF:

```turtle
# Dieses Pattern realisiert die Response-Minimierung im FastAPI-Stack.
pattern:fastapi-declared-response-schema a sf:ImplementationPattern ;
  # Diese Kennung ist der stabile Name des technischen Patterns.
  dcterms:identifier "fastapi/declared-response-schema" ;
  # Diese Beziehung begrenzt das Pattern auf den FastAPI-React-Stack.
  sf:usesStack stack:fastapi-react ;
  # Diese Beziehung benennt das vom Pattern adressierte Requirement.
  sf:satisfies requirement:PRIVACY-001 ;
  # Dieses Binding realisiert den konkreten erwarteten Control-Wert.
  sf:controlBinding binding:response-data-minimization ;
  # Diese Beziehung verbindet das Pattern mit seiner ausführbaren Prüfung.
  sf:verifiedBy verification:TEST-PRIVACY-001 .
```

Ein Pattern entscheidet nicht, ob ein Requirement gilt. Erst die Rule erzeugt
eine Requirement Instance; danach muss genau ein Stack-kompatibles Pattern alle
Controls und Verifications adressieren. Kein Treffer ergibt `SF1501`, mehrere
Treffer `SF1502`.

## Auflösung

`uv run specforge resolve products/calendar` führt aus:

1. `product.trig` und alle `package.trig` lokal parsen,
2. Autorenquellen mit SHACL Core validieren,
3. SKOS/RDFS-Concepts, Requirements und Patterns laden,
4. RIF Core in sicheres positives Datalog normalisieren,
5. Product-Aussagen und semantische Hülle bis zum Fixpunkt auswerten,
6. Requirement Instances erzeugen und Patterns auswählen,
7. das Resolved Dataset erneut mit SHACL validieren,
8. PROV-O-Herkunft ergänzen,
9. per RDFC-1.0 kanonisieren und mit SHA-256 hashen.

Package-Hashes beruhen ebenfalls auf kanonischem RDF plus normalisierter
RIF-Semantik. Kommentare, Dateireihenfolge und Turtle-Layout verändern sie
nicht; fachliche Aussagen schon.

## Sicherheit

- kein Netzwerkzugriff und keine Graphdatenbank,
- keine Remote JSON-LD Contexts,
- kein automatisches Remote-`owl:imports`,
- kein SPARQL `SERVICE`,
- kein SWRL,
- kein aktives OWL-2-RL-Profil,
- keine SHACL Advanced Features.

## Migration alter Quellen

Alte YAML-Quellen sind nur Eingabe des getrennten Migrationsbefehls:

```powershell
uv run specforge migrate-format legacy/product.yaml --to trig --output migrated/product.trig
uv run specforge migrate-format legacy/privacy-package --to trig --output migrated/privacy
```

Der Befehl überschreibt die Quelle nicht. Er importiert und lintet sein Ergebnis
erneut und schreibt daneben einen `migration-report.json`. Der normale
Compilerpfad akzeptiert keine fachlichen YAML-Dateien mehr.
