# Spec: Geführte Lernreise für SpecForge

Status: Proposed
Version: 1.0
Datum: 2026-08-23

## 1. Ziel

Das neue Training soll einer Person ohne SpecForge-Vorwissen ermöglichen,
innerhalb einer zusammenhängenden Lernreise zu verstehen:

1. welches Problem SpecForge löst,
2. wie Produktwissen und wiederverwendbares Knowledge zusammenwirken,
3. wie daraus nachvollziehbare Requirements und technische Verpflichtungen
   entstehen,
4. warum RDF, Datalog, SHACL und Provenance dabei unterschiedliche Aufgaben
   übernehmen,
5. wie ein Agent kontrolliert implementiert, ohne fachliche Entscheidungen zu
   improvisieren,
6. was ein erfolgreicher Verification-Lauf tatsächlich beweist – und was nicht.

Das Training ist keine vollständige Referenzdokumentation. Es vermittelt ein
stabiles mentales Modell, mit dem Lernende anschließend den Spec Explorer, die
CLI und die Knowledge-Dateien selbstständig untersuchen können.

## 2. Produktentscheidung

Es gibt genau eine Ansicht: **Geführte Lernreise**.

Die bisherigen Varianten Mission Control und Skill Map entfallen. Es gibt
keinen Variantenumschalter und keine parallelen Informationsarchitekturen. Die
Lernreise besitzt einen Anfang, einen sichtbaren Fortschritt und ein klares
Ende, erlaubt aber jederzeit den Rücksprung zu bereits absolvierten Stationen.

Der vorhandene Training-Prototype wird nicht inkrementell erweitert. Seine
fachlich weiterhin richtigen Inhalte dürfen als Rohmaterial dienen; Struktur,
Texte, Beispiele und Interaktionen werden anhand dieser Spec neu aufgebaut.

## 3. Leitidee: „Der Fall des zu offenen Kalenders“

Das Training erzählt eine einzige Untersuchung.

Eine Calendar-API liefert bei `read_event` mehr Daten als beabsichtigt. Eine
Person soll herausfinden:

- Woher weiß SpecForge, dass ein Event personenbezogene Daten enthält?
- Warum gilt eine allgemeine Privacy-Policy für diese konkrete Operation?
- Weshalb gilt sie nicht für `delete_event`?
- Welche Rolle spielen Calendar-, Privacy-, FastAPI- und
  Calendar-FastAPI-Pakete?
- Wie wird aus der Policy eine technische Umsetzung und eine prüfbare Aussage?
- Wie kann man die gesamte Entscheidung bis zu ihren Quellen zurückverfolgen?

Jede Station beantwortet einen Teil dieser Untersuchung. Neue Begriffe werden
erst eingeführt, wenn sie zur Lösung des Falls benötigt werden.

## 4. Didaktische Prinzipien

### 4.1 Erst Bedeutung, dann Standardname

Das Training erklärt zunächst die Aufgabe eines Mechanismus:

> „Wir brauchen eine gemeinsame Sprache für adressierbare Aussagen und
> Beziehungen.“

Erst danach erscheint der Name **RDF**. Dasselbe gilt für Datalog, SHACL,
SKOS, PROV-O, SPARQL und RDFC. Standards werden nicht als Akronymliste
eingeführt.

### 4.2 Ein wachsendes Modell

Die zentrale Visualisierung beginnt mit zwei Elementen – Product und Policy –
und wächst über die Reise zu einem vollständigen, aber überschaubaren
Entscheidungspfad. Bereits erklärte Elemente bleiben sichtbar. Neue Elemente
werden animiert ergänzt und kurz hervorgehoben.

### 4.3 Vorhersagen vor Erklärungen

Vor wichtigen Ableitungen fragt das Training nach einer Vorhersage, etwa:

> Sollte die Datenminimierungsregel auch für `delete_event` gelten?

Eine falsche Antwort blockiert nicht. Die anschließende Erklärung bezieht sich
konkret auf die Auswahl und macht das Missverständnis sichtbar.

### 4.4 Drei Ebenen strikt trennen

Jede Station kennzeichnet Aussagen als eine dieser Ebenen:

- **Bedeutung:** Was gilt fachlich?
- **Entscheidung:** Wie leitet SpecForge daraus etwas ab?
- **Umsetzung:** Wie wird das Ergebnis technisch realisiert und geprüft?

Privacy- und Security-Knowledge darf dadurch nicht versehentlich wie
FastAPI-Code wirken; ein Pattern darf nicht wie eine Policy erscheinen.

### 4.5 Herkunft ist Teil der Antwort

Jede abgeleitete Aussage besitzt eine sichtbare Schaltfläche „Warum?“. Sie
öffnet keine generische Dokumentation, sondern den konkreten Pfad aus
Ausgangsaussagen, Rule, Bindungen und Quelle.

### 4.6 Standards bleiben austauschbar sichtbar

Das Training zeigt sowohl die verständliche Darstellung als auch, auf Wunsch,
die standardisierte Repräsentation. Ein Umschalter „Unter der Haube“ blendet
für das aktuelle Element kleine RDF-, Datalog-, SHACL- oder SPARQL-Ausschnitte
ein. Diese Ebene ist optional und unterbricht die Lernreise nicht.

## 5. Aufbau der Lernreise

Die Reise besteht aus acht Stationen. Jede Station hat dasselbe Grundmuster:

1. konkrete Frage des Calendar-Falls,
2. kurze Erklärung in Alltagssprache,
3. interaktive Untersuchung,
4. eine Vorhersage oder Entscheidung,
5. sichtbares Ergebnis im wachsenden Modell,
6. optional „Unter der Haube“,
7. ein Satz „Das solltest du mitnehmen“.

### Station 1: Warum ein Compiler statt eines Chatbots?

**Frage:** Wer entscheidet, welche Anforderungen gelten?

Die Person vergleicht zwei Antworten auf dieselbe Produktänderung. Freier Text
wirkt plausibel, ist aber nicht reproduzierbar. SpecForge erzeugt aus
versionierten Eingaben dieselbe fachliche Entscheidung und lässt dem Agenten
nur Freiheit bei der Implementierung.

Ergebnis im Modell:

```text
Product Knowledge + Reusable Knowledge
                 ↓
      deterministische Entscheidung
                 ↓
      begrenzter Implementierungsauftrag
```

Kernbegriffe: Product Spec, Knowledge Package, Compiler.

### Station 2: Was weiß das Produkt – und was nicht?

**Frage:** Steht „Daten minimieren“ in der Calendar-Spec?

Die Person sortiert Aussagen in zwei Bereiche:

- `Event.description` ist als `PersonalData` klassifiziert.
- `read_event` bearbeitet und liefert ein `Event`.
- Responses mit personenbezogenen Daten sollen minimiert werden.
- Personenbezogene Ressourcen benötigen Authentifizierung.

Die ersten beiden Aussagen gehören zum Produkt, die anderen zu
wiederverwendbarem Knowledge. Keine Seite kennt allein die fertige Anwendung.

Kernbegriffe: Entity, Field, Operation, Classification, Policy Package.

### Station 3: Pakete sind Rollen, keine Ordner

**Frage:** Was verbindet `calendar-fastapi-react` eigentlich?

Die Person baut eine Paketbrücke:

```text
Calendar-Domäne ← Calendar-FastAPI-React → FastAPI-React-Implementierung
                           ↑
                  bindet beide Kontexte
```

Dabei werden vier Rollen unterschieden:

- Policy Package: app-unabhängige Regeln und Anforderungen,
- Domain Package: Wissen über die konkrete Fachdomäne,
- Implementation Package: technischer Stack und allgemeine Patterns,
- Integration Package: Patterns für genau die Verbindung aus Domäne und Stack.

`depends on` bedeutet, dass ein Paket geladen wird. `binds domain` und
`binds implementation` erklären dagegen die beiden Seiten einer fachlichen
Integration. Die Kanten erhalten dieselben Hover-Erklärungen wie im Spec
Explorer.

Kernbegriffe: Package Role, Dependency, Integration Package, Pattern.

### Station 4: Vom Satz zur adressierbaren Aussage

**Frage:** Wie kann eine Maschine dieselbe Beziehung eindeutig wiederfinden?

Ein natürlicher Satz wird schrittweise in eine Aussage zerlegt:

```text
read_event liefert Event
```

Danach werden stabile Identitäten eingeblendet:

```text
<operation/calendar/read_event> sf:returns <entity/calendar/Event>
```

Die Person verändert Reihenfolge oder Darstellung und sieht, dass die Bedeutung
gleich bleibt. Anschließend wird erklärt: RDF bildet Aussagen, IRIs geben ihnen
stabile Identitäten und Named Graphs halten Product, Packages, Ableitungen und
Evidence auseinander.

Kernbegriffe: RDF-Aussage, IRI, Named Graph, Dataset.

### Station 5: Die Rule-Maschine

**Frage:** Warum gilt `PRIVACY-001` für `read_event`, aber nicht für
`delete_event`?

Die Rule wird zunächst verständlich dargestellt:

```text
WENN
  Operation liefert eine Ressource
  UND Ressource enthält PersonalData
  UND Aktion ist create ODER read ODER update
DANN
  PRIVACY-001 gilt für diese Operation
```

Die Person führt die Rule einmal von Hand aus, indem sie konkrete Facts in die
Variablenplätze zieht. Danach zeigt das Training die Bindungen und den
entstandenen Requirement-Knoten.

„Unter der Haube“ zeigt die positive Datalog-Darstellung. Das Training erklärt
die Open-World-Annahme anhand einer fehlenden Aussage: „nicht gefunden“ ist
nicht dasselbe wie „falsch“. Deshalb wird `delete` nicht über globale Negation,
sondern über eine positive Menge erlaubter Response-Aktionen ausgeschlossen.

Kernbegriffe: Rule, Fact, Variable, Bindung, positives Datalog, Fixpunkt.

### Station 6: Requirement ist nicht gleich Umsetzung

**Frage:** Weiß die Privacy-Policy, dass FastAPI verwendet wird?

Die Person ordnet vier Karten in eine Kette:

```text
Requirement Definition
→ Requirement Instance für read_event
→ Implementation Pattern
→ Verification
```

Die Privacy-Definition verlangt nur, dass Responses auf deklarierte Felder
begrenzt werden. Das Product bestimmt über `returns`, welches Response-Schema
gilt. Erst das zum Stack passende Pattern beschreibt eine mögliche
FastAPI-Umsetzung.

Die erlaubten Response-Felder werden live aus der Entity-Deklaration abgeleitet.
Wird probeweise ein weiteres deklariertes Feld ergänzt, folgt die Erwartung dem
Schema, ohne dass die Privacy-Policy geändert wird.

Kernbegriffe: Requirement Definition, Requirement Instance, Target, Control,
Implementation Pattern, Verification.

### Station 7: Prüfen ist nicht ableiten

**Frage:** Welche Komponente entscheidet, ob die laufende Anwendung korrekt ist?

Zwei Werkzeuge werden bewusst getrennt:

- Datalog leitet aus bekannten Aussagen neue Aussagen ab.
- SHACL prüft, ob RDF-Daten eine deklarierte Form erfüllen.

Daneben führen Verification Adapter konkrete Beobachtungen an der Anwendung
aus. Das Ergebnis wird als SHACL Validation Report und menschenfreundliche
Evidence dargestellt.

Die Person untersucht drei Resultate:

- fehlendes Pflichtfeld im Modell,
- zusätzliches unerlaubtes Response-Feld,
- anonymer Request mit erwarteter HTTP-Antwort.

Für jedes Resultat muss erkennbar sein: erwarteter Zustand, beobachteter
Zustand, Fokus, Ergebnis und Softwarestand.

Kernbegriffe: SHACL Shape, Validation Result, Verification Adapter, Evidence.

### Station 8: Die vollständige Beweiskette

**Frage:** Kann die Entscheidung bis zu ihren Quellen erklärt werden?

Die Person startet bei `PRIVACY-001@operation.read_event` und reist rückwärts:

```text
Validation Result
← Verification
← Implementation Pattern
← Requirement Instance
← Datalog Rule und Variablenbindungen
← abgeleitete und deklarierte Assertions
← Product- und Package-Quellen
```

PROV-O wird als standardisierte Sprache für Herkunft eingeführt. Eine kleine
SPARQL-Abfrage beantwortet anschließend dieselbe Frage maschinell. Zum Schluss
verändert die Person nur die Reihenfolge der RDF-Serialisierung: Der
RDFC-Hash bleibt gleich. Eine fachliche Aussage wird geändert: Der Hash ändert
sich.

Kernbegriffe: Provenance, PROV-O, SPARQL, RDFC-1.0, Content Hash.

## 6. Abschluss: selbstständige Untersuchung

Statt eines klassischen Multiple-Choice-Abschlusstests erhält die Person einen
zweiten, kleinen Fall:

> `update_event` soll nur vom Eigentümer ausgeführt werden dürfen.

Sie muss im bestehenden Modell selbst finden:

1. welche Product Facts relevant sind,
2. welche Security Rule matcht,
3. welches Requirement entsteht,
4. welches Pattern ausgewählt wird,
5. welche Verification das Ergebnis prüft,
6. aus welchen Quellen die Entscheidung stammt.

Die Aufgabe gilt als gelöst, wenn die richtige Kette konstruiert wurde. Fehler
werden lokal erklärt; die Lösung wird nicht nach dem ersten Versuch vollständig
eingeblendet.

## 7. Informationsarchitektur

### 7.1 Desktop

```text
┌──────────────────────────────────────────────────────────────────────┐
│ SpecForge Training             Station 5 von 8          Fortschritt │
├──────────────────┬───────────────────────────────────────────────────┤
│ Reiseverlauf     │ Frage und kurze Erzählung                         │
│                  │                                                   │
│ ✓ 1 Compiler     │ Interaktive Untersuchung                          │
│ ✓ 2 Wissen       │                                                   │
│ ✓ 3 Pakete       ├───────────────────────────────────────────────────┤
│ ✓ 4 Aussagen     │ Wachsendes Modell / konkrete Beweiskette          │
│ ● 5 Rules        │                                                   │
│ ○ 6 Umsetzung    │                                                   │
│ ○ 7 Prüfung      ├───────────────────────────────────────────────────┤
│ ○ 8 Herkunft     │ [Unter der Haube]                  [Weiter →]     │
└──────────────────┴───────────────────────────────────────────────────┘
```

Die linke Navigation zeigt nur Stationen, keine alternative Produktansicht.
Der Hauptbereich darf innerhalb einer Station vertikal scrollen. Das wachsende
Modell bleibt als ruhiger visueller Anker sichtbar oder ist über „Modell
öffnen“ unmittelbar erreichbar.

### 7.2 Mobile

Der Reiseverlauf wird zu einer horizontalen, beschrifteten Fortschrittsleiste.
Erzählung, Interaktion und Modell stehen untereinander. Keine Interaktion darf
Hover voraussetzen; alle Tooltips sind auch per Fokus oder Tippen erreichbar.

## 8. Interaktionsmodell

Unterstützte Interaktionen:

- Karten zuordnen oder in eine Reihenfolge bringen,
- Vorhersage aus zwei bis vier klaren Möglichkeiten treffen,
- Facts in Variablenplätze einer Rule einsetzen,
- einen konkreten Provenance-Pfad schrittweise aufklappen,
- kleine, vorbereitete SPARQL-Abfragen ausführen und verändern,
- zwischen verständlicher und standardisierter Darstellung umschalten,
- Knoten und Beziehungen fokussieren und ihre Erklärung öffnen.

Nicht vorgesehen:

- freie Texteingaben, die durch ein Sprachmodell bewertet werden,
- eine vollständige Code-IDE,
- ein beliebiger RDF- oder SPARQL-Playground mit Netzwerkzugriff,
- Punkte, Badges, Streaks oder künstliche Gamification,
- Interaktionen, bei denen Drag-and-drop die einzige Bedienmöglichkeit ist.

## 9. Terminologie und Hilfen

Begriffe und Beziehungserklärungen stammen aus demselben SKOS-/RDFS-
Vokabular wie der Spec Explorer. Das Training pflegt keine zweite Definition
für Rule, Operation, Requirement oder Paketbeziehungen.

Darstellung:

- neuer Begriff beim ersten Auftreten fett und kurz im Satz erklärt,
- Fokus, Hover oder Tippen öffnet die vollständige Definition,
- Academy-Begriffe und Calendar-Begriffe bleiben visuell unterscheidbar,
- eine Definition enthält bei Bedarf „Nicht verwechseln mit …“,
- ein globales Glossar ist verfügbar, aber nicht Teil der primären Navigation.

## 10. Inhaltliche Grenzen

Das Training muss deutlich sagen:

- Ein bestandenes Requirement beweist keine allgemeine Compliance.
- Open World bedeutet nicht, dass jede unbekannte Aussage erlaubt ist.
- SHACL ist keine allgemeine Rule Engine.
- SPARQL definiert nicht die normative Rule-Ausführung.
- Ein Pattern entscheidet nicht, ob ein Requirement gilt.
- Ein Integration Package ist weder die Domain noch der technische Stack.
- Der Agent darf Implementierungsdetails wählen, aber keine Policy-Konflikte
  auflösen.
- OWL 2 RL ist noch kein aktives SpecForge-Conformance-Profil.
- SWRL gehört nicht zum unterstützten Rule-Modell.

RIF Core wird als normatives gespeichertes Rule-Format erwähnt, aber nicht als eigene Pflichtstation
unterrichtet. ODRL, SHACL Advanced Features und externe Triplestores liegen
außerhalb dieser Lernreise.

## 11. Technische Leitplanken

### 11.1 Datenquelle

Die Lernreise verwendet keine separat nachgebauten Calendar-Beispiele. Ein
Build-Schritt erzeugt ein versioniertes Training-Szenario aus:

- dem aufgelösten RDF-Dataset,
- gespeicherten SPARQL-Views,
- SKOS-/RDFS-Labels und Definitionen,
- SHACL Shapes und vorbereiteten Validation Results,
- PROV-O-Ableitungen,
- ausdrücklich als redaktionell markierten Erzähltexten und Aufgaben.

Fachliche IDs, Beziehungen, Rule-Bedingungen, Paketversionen, erwartete Felder
und Provenance dürfen nicht als unabhängige Kopien in JavaScript gepflegt
werden.

### 11.2 Ausführung

Das Training bleibt eine statische, lokal ausführbare Web-Anwendung. Es
benötigt keinen Server, keine Graphdatenbank und keinen Netzwerkzugriff. Die
vorbereiteten SPARQL-Abfragen laufen entweder beim Build oder in einer lokalen,
begrenzten RDF-Abfrageschicht.

### 11.3 Zustand

Fortschritt wird lokal gespeichert. Ein sichtbarer Befehl „Lernreise
zurücksetzen“ löscht ausschließlich diesen Trainingszustand. Ein neuer
Szenario-Hash invalidiert inkompatiblen alten Fortschritt, ohne andere
Browserdaten zu verändern.

### 11.4 Barrierefreiheit

- vollständig per Tastatur bedienbar,
- sichtbare Fokuszustände,
- semantische Überschriften und Landmarken,
- kein Pflicht-Hover und kein Pflicht-Drag-and-drop,
- Animationen respektieren `prefers-reduced-motion`,
- Statusänderungen werden über eine geeignete Live Region angekündigt,
- Farbe ist nie der einzige Bedeutungsträger,
- WCAG 2.2 AA als Zielniveau.

## 12. Redaktionelles Modell

Redaktionelle Inhalte werden getrennt von fachlich generierten Daten gehalten.
Jede Station definiert:

```json
{
  "id": "rule-machine",
  "title": "Die Rule-Maschine",
  "question": "Warum gilt PRIVACY-001 für read_event?",
  "learning_objectives": [
    "positive Rule-Bedingungen lesen",
    "konkrete Variablenbindungen nachvollziehen"
  ],
  "scenario_refs": [
    "rule:privacy/minimize-personal-data-response",
    "requirement-instance:PRIVACY-001@operation.read_event"
  ],
  "interaction": "bind-rule",
  "takeaway": "Eine Rule leitet Anwendbarkeit ab; sie implementiert nichts."
}
```

`scenario_refs` werden beim Build gegen das RDF-Dataset validiert. Fehlende oder
mehrdeutige Referenzen brechen den Build ab. Redaktioneller Text darf Bedeutung
erklären, aber keine maschinenlesbaren Facts ersetzen.

## 13. Erfolgskriterien

Nach Abschluss kann eine Person ohne Hilfestellung:

1. Product-, Policy-, Domain-, Implementation- und Integration-Wissen
   unterscheiden,
2. `acts_on` und `returns` korrekt auseinanderhalten,
3. eine positive WENN-/DANN-Rule inklusive UND/ODER lesen,
4. erklären, weshalb Privacy-Knowledge den Calendar oder FastAPI nicht kennen
   muss,
5. Requirement Definition, Instance, Pattern und Verification in die richtige
   Reihenfolge bringen,
6. Datalog-Ableitung, SHACL-Validierung und Verification-Beobachtung
   unterscheiden,
7. einen konkreten Provenance-Pfad im Explorer nachvollziehen,
8. die Aufgabe von RDF, SKOS, PROV-O, SPARQL und RDFC jeweils in einem Satz
   erklären,
9. die Aussagegrenze von Evidence benennen.

## 14. Akzeptanzkriterien

### Struktur

1. Es existiert genau eine Lernansicht und kein Variantenumschalter.
2. Die acht Stationen sind in definierter Reihenfolge erreichbar.
3. Bereits abgeschlossene Stationen können erneut geöffnet werden.
4. Mission Control und Skill Map sowie ihr variantenspezifischer Zustand sind
   entfernt.

### Fachliche Korrektheit

5. Alle `scenario_refs` werden gegen das aktuelle RDF-Dataset validiert.
6. Paketbeziehungen und ihre Erklärungen stammen aus dem SpecForge-Vokabular.
7. Rule-Anwendungen verwenden die realen Datalog-Bindungen und Prämissen.
8. Response-Felder werden aus dem aufgelösten Resource-Schema abgeleitet.
9. Der dargestellte Content Hash entspricht dem RDFC-Hash des Szenarios.
10. Mindestens ein vollständiger Pfad von Product Assertion bis Validation
    Result wird aus PROV-/RDF-Daten aufgebaut.

### Lernen

11. Jede Station enthält Frage, Interaktion und explizites Takeaway.
12. Vorhersagen dürfen falsch beantwortet werden, ohne Fortschritt zu sperren.
13. Die Abschlussuntersuchung kann nicht allein durch lineares Weiterklicken
    bestanden werden.
14. Technische Standardausschnitte sind optional und nicht Voraussetzung für
    das Verständnis der Haupterzählung.

### Qualität

15. Das Training funktioniert ohne Netzwerk und ohne Graphdatenbank.
16. Ein Reload stellt den Fortschritt wieder her.
17. Der Zustand kann gezielt zurückgesetzt werden.
18. Alle Funktionen sind per Tastatur und auf Touch-Geräten erreichbar.
19. Automatisierte Tests prüfen Szenario-Referenzen, Stationsnavigation,
    Fortschritt, falsche und richtige Antworten sowie den vollständigen
    Abschlussfall.
20. Der Produktionsbuild enthält keine Daten oder UI für die entfernten
    Varianten B und C.

## 15. Nicht-Ziele der ersten Version

- frei konfigurierbare Produkte oder Knowledge Packages,
- ein Autoren-WYSIWYG,
- Zertifikate, Nutzerkonten oder serverseitige Lernstände,
- automatische Bewertung freier Sprache,
- vollständige Ausbildung in RDF, Datalog, SHACL oder SPARQL,
- Ersatz für Spec Explorer, CLI-Referenz oder Architektur-Dokumentation.

## 16. Migration des bestehenden Prototypes

Bei der späteren Umsetzung gilt:

1. fachlich wiederverwendbare Erzähltexte und Glossardefinitionen identifizieren,
2. die Gewinneransicht „Geführte Lernreise“ als einzige Shell behalten,
3. Variantenrouter, Variantenschalter, Mission-Control- und Skill-Map-Code
   entfernen,
4. hart codierte fachliche Beispieldaten durch das generierte Szenario ersetzen,
5. die acht neuen Stationen implementieren,
6. alten Fortschrittszustand bewusst invalidieren,
7. die alte Prototype-README durch Start-, Build- und Szenariohinweise ersetzen.

Die Umsetzung darf erst beginnen, wenn diese Spec akzeptiert oder gezielt
geändert wurde.
