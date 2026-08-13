// THROWAWAY PROTOTYPE: three training interfaces, switchable with ?variant=A|B|C.
const courses = [
  {
    id: "mental-model", icon: "01", title: "Das mentale Modell", duration: "25 min", xp: 120,
    summary: "Warum Requirements kein Prompt sind – und warum ein Agent niemals seine eigene Arbeit abnimmt.",
    goals: ["Compiler, Agent und Gates klar abgrenzen", "erklären, was bei SpecForge deterministisch sein muss"],
    lessons: [
      { title: "Die gefährliche Abkürzung", body: `<p>Stell dir vor, du gibst einem Coding Agent fünf lose Policies und sagst: „Baue das sicher.“ Der Agent interpretiert, implementiert und erklärt anschließend, dass alles erfüllt sei. Das klingt effizient – vermischt aber drei verschiedene Verantwortungen.</p><div class="concept-grid"><div class="concept"><b>Entscheiden</b>Welche Requirements gelten?</div><div class="concept"><b>Implementieren</b>Wie wird der Zielzustand in Code erreicht?</div><div class="concept"><b>Verifizieren</b>Ist der Zielzustand tatsächlich erreicht?</div><div class="concept"><b>Beweisen</b>Welche Evidence bindet Ergebnis und Eingaben?</div></div><div class="callout"><b>SpecForge-Prinzip:</b> Deterministische Systeme definieren und prüfen Obligations. Codex integriert sie in echte Software. Nur Evidence entscheidet über Akzeptanz.</div>` },
      { title: "Compiler statt Chatbot", body: `<p>SpecForge ist ein <b>deterministischer Requirements Compiler</b> mit agentischem Implementierungsbackend. Gleiche Product Spec plus gleiche Knowledge-Pakete erzeugen denselben Plan und denselben Work Order. Der Anwendungscode darf variieren – seine überprüfbaren Invarianten nicht.</p><pre class="terminal">Product Spec + Knowledge Packages\n              ↓\nRequirement Resolution → Obligations → Work Order\n              ↓                       ↓\n        deterministisch          Coding Agent\n              ↓                       ↓\n         Verification ← geänderter Code\n              ↓\n        Evidence: ACCEPTED | REJECTED</pre>` }
    ],
    quiz: { q: "Welche Aussage trifft den Kern von SpecForge?", options: ["Codex entscheidet, welche Policies relevant sind.", "Templates erzeugen reproduzierbaren Anwendungscode.", "Deterministik umschließt die kreative Implementierung.", "Ein erfolgreicher Build ist ein Compliance-Nachweis."], answer: 2, explain: "Resolution, Work Order und Gates sind deterministisch. Der Agent hat Freiheit innerhalb überprüfbarer Grenzen." }
  },
  {
    id: "knowledge", icon: "02", title: "Wissen wird ausführbar", duration: "32 min", xp: 160,
    summary: "Von Product Specs und Knowledge Packages zu typisierten Requirement Instances.",
    goals: ["Definition, Instance und Obligation unterscheiden", "Product Facts mit Knowledge-Regeln verbinden"],
    lessons: [
      { title: "Zwei Eingangsströme", body: `<p>Die <b>Product Spec</b> beschreibt das konkrete Produkt: Entitäten, Felder, Operationen und Komponenten. <b>Knowledge Packages</b> enthalten versionierte, wiederverwendbare Anforderungen aus Security, Privacy, Observability oder Plattformregeln.</p><div class="concept-grid"><div class="concept"><b>Product Fact</b><code>Event.location: PersonalData</code></div><div class="concept"><b>Knowledge Rule</b>Persönliche Daten im Response minimieren</div></div>` },
      { title: "Definition → Instance → Obligation", body: `<p>Eine Requirement Definition wird erst durch Anwendung auf ein typisiertes Target konkret. Daraus entsteht eine technische Verpflichtung. Bevor wir das Beispiel lesen, brauchen wir drei neue Begriffe:</p><div class="concept-grid"><div class="concept"><b>Surface</b>Der technische Bereich, in dem die Verpflichtung wirkt. <code>response</code> bedeutet: Sie betrifft die Daten, die eine Operation an den Aufrufer zurückgibt.</div><div class="concept"><b>Control</b>Die konkrete Eigenschaft, die in dieser Surface gesteuert wird. <code>response_minimization</code> bedeutet: Die Antwort soll auf ausdrücklich erlaubte Daten begrenzt werden.</div><div class="concept"><b>allowed_fields</b>Der konkrete Wert des Controls: eine Positivliste der Felder, die in der Response vorkommen dürfen. Nicht aufgeführte Felder dürfen nicht ausgegeben werden.</div><div class="concept"><b>Warum getrennt?</b>Surface sagt <em>wo</em> die Regel wirkt, Control sagt <em>was</em> dort geregelt wird und <code>allowed_fields</code> sagt <em>welcher konkrete Zustand</em> erwartet wird.</div></div><pre class="terminal annotated-code"><span>PRIVACY-001</span>                          <i># allgemeine Requirement Definition</i>\n<span>PRIVACY-001@operation:read_event</span>     <i># angewendet auf die Operation read_event</i>\n<span>obligation:read_event:allowed-fields</span> <i># daraus abgeleitete technische Pflicht</i>\n\n<span>target:</span>                              <i># worauf wirkt die Obligation?</i>\n  <span>type: operation</span>                     <i># Target-Art: eine ausführbare Operation</i>\n  <span>id: read_event</span>                     <i># konkrete Operation: Event lesen</i>\n<span>surface: response</span>                   <i># WO: in der ausgehenden API-Antwort</i>\n<span>control: response_minimization</span>       <i># WAS: Antwortdaten begrenzen</i>\n<span>allowed_fields:</span>                     <i># WIE GENAU: nur diese Felder erlauben</i>\n  <span>- id</span>                              <i># technische Event-ID</i>\n  <span>- owner_id</span>                        <i># ID des Besitzers</i>\n  <span>- title</span>                           <i># Titel des Events</i>\n  <span>- location</span>                        <i># Ort; hier bewusst freigegeben</i></pre><div class="reading-guide"><b>So liest du das von oben nach unten</b><ol><li><b>Welche allgemeine Regel?</b> <code>PRIVACY-001</code>.</li><li><b>Auf welchen konkreten Teil des Produkts?</b> Auf <code>operation:read_event</code>.</li><li><b>Wo im technischen Ablauf?</b> In der <code>response</code>.</li><li><b>Welche Eigenschaft wird verlangt?</b> <code>response_minimization</code>.</li><li><b>Woran erkennt eine Prüfung den Zielzustand?</b> Die Response enthält ausschließlich die Einträge aus <code>allowed_fields</code>.</li></ol></div><div class="callout"><b>Wichtige Abgrenzung:</b> <code>allowed_fields</code> beschreibt noch keinen Python- oder TypeScript-Code. Es beschreibt eine überprüfbare Invariante. Der Agent darf selbst entscheiden, wie er diese Positivliste technisch durchsetzt.</div>` }
    ],
    quiz: { q: "Was macht aus SEC-002 eine Requirement Instance?", options: ["Eine frei formulierte Agent-Anweisung", "Die Bindung an ein typisiertes Target", "Ein erfolgreicher pytest-Lauf", "Die Aufnahme in ein Pattern"], answer: 1, explain: "Eine Instance ist die Anwendung einer Definition auf ein Target, z. B. SEC-002@operation:read_event." }
  },
  {
    id: "resolution", icon: "03", title: "Resolution & Konflikte", duration: "35 min", xp: 190,
    summary: "Mehrere Policies werden konsolidiert, bevor ein Agent auch nur eine Datei berührt.",
    goals: ["Obligations nach Surface lesen", "Merge-Ergebnis und Konfliktstopp vorhersagen"],
    lessons: [
      { title: "Fünf Regeln, ein Auftrag", body: `<p>Authentication, Ownership, Response Minimization, Audit Logging und Rate Limiting können gleichzeitig auf <code>read_event</code> wirken. Der Agent bekommt nicht fünf unabhängige Prompts. SpecForge konsolidiert sie nach technischen Surfaces.</p><div class="concept-grid"><div class="concept"><b>identity</b>authentication: required</div><div class="concept"><b>data_access</b>authorization: ownership</div><div class="concept"><b>response</b>allowed_fields: Schnittmenge</div><div class="concept"><b>traffic</b>requests_per_minute: 60</div></div>` },
      { title: "Merge-Semantik statt Bauchgefühl", body: `<pre class="terminal">required + required       → required\n{id,title} ∩ {id,title,x} → {id,title}\nretention ≤ 30 + ≤ 14     → ≤ 14\nrequired + forbidden      → CONFLICT</pre><p>Jeder Control-Typ besitzt eine versionierte Merge-Semantik. „Letzter Wert gewinnt“ ist ausdrücklich verboten. Ein unauflösbarer Konflikt stoppt die Pipeline <em>vor</em> dem Agent-Aufruf.</p>` }
    ],
    quiz: { q: "Zwei Pakete erlauben Response-Felder {id, title} und {id, title, description}. Was gilt?", options: ["Die Vereinigungsmenge", "Das neuere Paket", "Die Schnittmenge {id, title}", "Der Agent entscheidet"], answer: 2, explain: "Response-Minimierung wird restriktiv über die explizite Mengenoperation konsolidiert." }
  },
  {
    id: "work-order", icon: "04", title: "Der begrenzte Auftrag", duration: "32 min", xp: 170,
    summary: "Implementation Plan, Impact Scope und Work Order machen Agentenarbeit kontrollierbar.",
    goals: ["Plan, Impact Scope und Work Order auseinanderhalten", "für eine Aufgabe den sicheren CLI-Befehl wählen"],
    lessons: [
      { title: "Erst planen, dann handeln", body: `<p><code>specforge plan products/calendar</code> verändert keinen Anwendungscode. Es erzeugt Plan, konservativen Impact Scope und einen gehashten Work Order.</p><div class="concept-grid"><div class="concept"><b>MAY_MODIFY</b>Agent darf diese Pfade ändern</div><div class="concept"><b>READ_ONLY</b>Kontext, aber unveränderlich</div><div class="concept"><b>MUST_NOT_MODIFY</b>Jede Änderung macht den Run ungültig</div><div class="concept"><b>MUST_VERIFY</b>Obligatorische Prüfungen</div></div>` },
      { title: "Freiheit im Zaun", body: `<p>Codex entscheidet über Module, Framework-Mechanismen, Namen und UI-Details. Es darf keine Requirements abschwächen, Verifikationen löschen oder den Scope erweitern. Das ist keine vollständige Codevorlage – SpecForge V2 verbietet Templates.</p><p><b>Patterns</b> liefern begrenzte Guidance: Voraussetzungen, Empfehlungen, Verbote und Verifikationsbezüge. Sie entscheiden weder, ob ein Requirement gilt, noch liefern sie ausfüllbare Codegerüste.</p><pre class="terminal">$ specforge implement products/calendar --agent codex --dry-run\n✓ work order schema valid\n✓ content hash: e1c1975814c6\n✓ 9 obligations consolidated\n→ agent invocation skipped (dry-run)\n→ application files unchanged</pre>` }
    ],
    quiz: { q: "Welche Datei darf Codex ohne explizite Freigabe verändern?", options: ["Eine HUMAN_MANAGED-Datei", "Eine Datei unter MAY_MODIFY", "Das Knowledge Package", "Die obligatorische Verification"], answer: 1, explain: "Der Work Order begrenzt Schreibrechte. Änderungen außerhalb MAY_MODIFY führen zur Ablehnung." }
  },
  {
    id: "gates", icon: "05", title: "Gates & Evidence", duration: "34 min", xp: 210,
    summary: "Ein Agent sagt nicht „fertig“. Eine überprüfbare Kette sagt ACCEPTED oder REJECTED.",
    goals: ["die sieben Gates in der richtigen Rolle einordnen", "Evidence von Behauptung und Compliance unterscheiden"],
    lessons: [
      { title: "Sieben deterministische Schranken", body: gateExplanation() },
      { title: "Evidence ist eine Kette", body: `<pre class="terminal">Policy Source → Requirement Definition → Instance\n→ Obligation → Pattern → Work Order → Agent Run\n→ Code Change → Verification → Evidence → ACCEPTED</pre><p>Evidence bindet Hashes von Spec, Work Order, Diff und Revision an konkrete beobachtete Werte. Sie ist kein allgemeiner Rechts- oder Compliance-Nachweis.</p>` }
    ],
    quiz: { q: "Codex meldet: ‚Alle Requirements erfüllt.‘ Welchen Evidenzwert hat das?", options: ["Vollwertige Evidence", "Evidence, wenn der Build grün ist", "Keinen – nur Gates und Evidence entscheiden", "Es ersetzt das Requirement Gate"], answer: 2, explain: "Eine Agent-Zusammenfassung ist ausdrücklich keine Requirement-Evidence." }
  },
  {
    id: "mission", icon: "★", title: "Abschlussmission", duration: "20 min", xp: 300,
    summary: "Du steuerst den Calendar-Location-Change durch eine echte SpecForge-Entscheidungskette.",
    goals: ["einen unvollständigen Agent Run korrekt behandeln", "Repair Scope und erneute Verifikation begründen"],
    mission: true,
    lessons: [{ title: "Mission: Event.location", body: `<p>Die Product Spec erhält <code>Event.location</code>: optionaler Text, klassifiziert als <code>PersonalData</code>. Codex ergänzt Backend und API, vergisst aber das Frontend. Stelle die richtige Reaktion zusammen.</p><div id="mission-builder"></div><div id="mission-result"></div>` }],
    quiz: { q: "Was ist nach erfolgreichem Repair Run zwingend?", options: ["Nur den zuvor fehlgeschlagenen UI-Test ausführen", "Alle Gates erneut ausführen", "Den ursprünglichen Run nachträglich umbenennen", "Die Evidence manuell freigeben"], answer: 1, explain: "Nach jedem Repair Run laufen alle Gates erneut; der Scope bleibt auf den ursprünglichen Auftrag begrenzt." }
  }
];

const state = { active: 0, completed: new Set(), answered: new Set(), attempts: {}, xp: 0, pipelineStep: 0, cliStep: 0, cliRewarded: false, mission: {}, missionPassed: false };
const variantNames = { A: "A — Geführte Lernreise", B: "B — Mission Control", C: "C — Skill-Map" };
const variants = Object.keys(variantNames);

function gateExplanation() {
  const gates = [
    ["Permission Gate", "Dateipfade vergleichen", "Hat der Agent ausschließlich freigegebene Dateien verändert?", "SpecForge erstellt vor und nach dem Run Datei-Snapshots. Jeder geänderte Pfad wird mit MAY_MODIFY, READ_ONLY und MUST_NOT_MODIFY aus dem Work Order verglichen.", "expected: changed_paths = MAY_MODIFY only\nobserved: violations = []\nrule: violations.length === 0 → PASS", "Eine Änderung an knowledge/security erzeugt eine Violation.", "Beweist nur die eingehaltene Schreibgrenze, nicht die fachliche Richtigkeit des Codes."],
    ["Schema Gate", "Struktur und Hashes prüfen", "Sind die strukturierten Artefakte lesbar und konsistent?", "Im Demo müssen Resolved Spec, Implementation Manifest, Plan und Impact Scope valides JSON sein. Manifest-Einträge werden außerdem auf AGENT_MANAGED, vorhandene Datei und passenden Content-Hash geprüft.", "expected: 4 gültige JSON-Artefakte\nobserved: invalid = []\nrule: invalid.length === 0 → PASS", "Eine kaputte JSON-Datei oder ein falscher Manifest-Hash führt zu FAIL.", "Die Zielspezifikation verlangt vollständige Schema-Validierung. Das Demo prüft derzeit JSON-Lesbarkeit und ausgewählte Manifest-Invarianten."],
    ["Build Gate", "Build-Befehle ausführen", "Lassen sich Backend und Frontend technisch bauen?", "Für das Python-Backend läuft compileall. Existiert das Frontend, läuft zusätzlich npm run build. Jeder erforderliche Prozess muss Exit Code 0 liefern.", "backend: python -m compileall → exit 0\nfrontend: npm run build       → exit 0\nrule: alle Exit Codes 0       → PASS", "Ein TypeScript-Compilerfehler erzeugt einen Frontend Exit Code ungleich 0.", "Ein grüner Build beweist kein korrektes Verhalten. Ownership kann fehlen, obwohl alles kompiliert."],
    ["Static Gate", "Quellcode ohne Ausführung untersuchen", "Verletzt der Code statisch prüfbare technische Regeln?", "Das Demo durchsucht Python-, TypeScript- und TSX-Dateien nach verbotenen Suppression-Markern wie # type: ignore und @ts-ignore.", "expected: suppression_markers = []\nobserved: gefundene Dateipfade\nrule: keine Marker → PASS", "Ein neues @ts-ignore macht das Gate rot.", "Die V2-Zielspezifikation sieht Linter, Typprüfer und Architekturchecks vor. Aktuell ist nur dieser Marker-Check implementiert."],
    ["Requirement Gate", "Verhalten gegen Requirements testen", "Sind alle obligatorischen Verification Instances erfüllt?", "Der Verifier startet die Calendar-App mit isolierter SQLite-Datenbank, sendet definierte HTTP-Anfragen und vergleicht strukturierte Beobachtungen exakt mit erwarteten Werten. Er prüft etwa Authentifizierung, fremden Zugriff, Response-Felder, Zeitintervalle, Audit Events und Rate Limit.", "SEC-001 ohne Token\nexpected: {response_status: 401}\nobserved: {response_status: 401}\nrule: expected === observed → PASS", "Bei PRIVACY-001 werden die tatsächlich gelieferten JSON-Keys mit der erlaubten Feldliste verglichen.", "Beweist nur die formalisierten und ausgeführten Verifications, keine unbekannten Anforderungen oder allgemeine Compliance."],
    ["Regression Gate", "Bestehendes erneut absichern", "Bestehen früher verifizierte und weiterhin relevante Eigenschaften noch?", "Im Zielbild werden die relevanten bisherigen Verification Instances auf dem neuen Softwarestand erneut ausgeführt. Eine neue Location-Funktion darf zum Beispiel Ownership nicht beschädigen.", "previously relevant: PASS\nnew revision: PASS\nrule: kein Rückschritt → PASS", "Der alte Test für fremden Event-Zugriff muss nach der Änderung weiterhin 404 beobachten.", "Im Demo übernimmt dieses Gate derzeit dasselbe Gesamtergebnis wie das Requirement Gate. Eine eigene historische Auswahl ist noch nicht vollständig implementiert."],
    ["Evidence Gate", "Belege an den Stand binden", "Gehören die Belege zum erwarteten Auftrag und Spec-Stand?", "Im Demo muss evidence/latest.json lesbar sein und sein resolved_spec_hash exakt resolved_spec_after aus dem Work Order entsprechen.", "expected: work_order.resolved_spec_after\nobserved: evidence.resolved_spec_hash\nrule: Hashes identisch → PASS", "Evidence einer alten Resolved Spec wird trotz grüner Tests abgelehnt.", "Das Zielbild bindet zusätzlich Work Order, Agent Run, Diff, Revision und Wissensversionen. Das aktuelle Gate vergleicht davon nur den Resolved-Spec-Hash."],
  ];
  return `<div class="determinism-answer"><p class="eyebrow">KURZE ANTWORT</p><h4>Die Gate-Entscheidung ist deterministisch, nicht stochastisch.</h4><p>Kein Gate fragt ein LLM nach einer Einschätzung, verwendet einen Confidence Score oder akzeptiert aufgrund einer Agent-Aussage. Jedes Gate vergleicht konkrete beobachtete Werte mit vorher festgelegten Erwartungen und liefert <code>PASS</code> oder <code>FAIL</code>.</p></div><div class="callout"><b>Wichtige Nuance:</b> Regelbasiert bedeutet nicht automatisch „niemals flaky“. Ein Test kann von Uhrzeit, Netzwerk, Race Conditions oder einer nicht isolierten Datenbank abhängen. Das wäre ein Problem der Prüfumgebung. Die Entscheidungsregel bleibt trotzdem fest, zum Beispiel <code>exit_code === 0</code>.</div><div class="gate-list">${gates.map((g, i) => `<details ${i === 0 ? "open" : ""}><summary><span class="gate-number">${i + 1}</span><b>${g[0]}</b><em>${g[1]}</em></summary><div class="gate-body"><p><b>Frage:</b> ${g[2]}</p><p><b>Konkrete Prüfung:</b> ${g[3]}</p><pre class="gate-code">${g[4]}</pre><p><b>Beispiel:</b> ${g[5]}</p><p class="gate-limit"><b>Grenze:</b> ${g[6]}</p></div></details>`).join("")}</div><div class="acceptance-formula"><b>Gesamtentscheidung</b><code>ACCEPTED = Agent Run COMPLETED ∧ jedes obligatorische Gate PASS</code><p>Es gibt keine Gewichtung und keinen Mehrheitsentscheid. Sechs grüne Gates können ein rotes Gate nicht überstimmen.</p></div>`;
}

const courseGuides = {
  "mental-model": {
    title: "Was SpecForge überhaupt lösen will",
    text: `<p>Software entsteht selten nur aus einer Feature-Idee. Zusätzlich gelten Regeln: Ein Nutzer muss angemeldet sein, fremde Datensätze dürfen nicht sichtbar werden, bestimmte Felder dürfen nicht in einer API-Antwort landen und Zugriffe müssen protokolliert werden. In einem normalen Projekt verteilen sich solche Regeln über Tickets, Wikis, Code Reviews und das Wissen einzelner Personen.</p><p>SpecForge versucht, diesen Teil explizit und maschinenlesbar zu machen. Dabei ist SpecForge <strong>nicht der Coding Agent</strong>. Es ist das System rund um den Agenten: Es ermittelt zuerst nachvollziehbar, welche Regeln für eine konkrete Änderung gelten. Danach darf ein Coding Agent eine technische Lösung bauen. Abschließend prüft SpecForge unabhängig vom Agenten, ob die verlangten Eigenschaften beobachtbar vorhanden sind.</p><p>Das Wort <strong>deterministisch</strong> bedeutet hier: Bei identischen Eingaben kommt dieselbe Entscheidung heraus. Ein Sprachmodell darf verschiedene sinnvolle Implementierungen schreiben. Es darf aber nicht spontan entscheiden, dass eine Sicherheitsregel heute unwichtig ist. Diese Trennung ist das zentrale mentale Modell für alle folgenden Kurse.</p>`,
    analogy: "Wie bei einer Bauabnahme: Die Bauordnung legt Anforderungen fest, ein Unternehmen baut, und eine unabhängige Prüfung nimmt das Ergebnis ab. Das Unternehmen stellt sich nicht selbst die Genehmigung aus.",
    terms: [["Requirement", "Eine überprüfbare Anforderung an das System, zum Beispiel: Lesen eines Events erfordert Authentifizierung."], ["Policy", "Eine übergeordnete Regel oder Vorgabe, aus der konkrete Requirements abgeleitet werden können."], ["Compiler", "Ein Programm, das strukturierte Eingaben nach festen Regeln in andere strukturierte Artefakte übersetzt. Hier: Specs und Wissen in Obligations und Work Orders."], ["Coding Agent", "Ein KI-gestütztes Werkzeug wie Codex, das innerhalb eines begrenzten Auftrags Anwendungscode verändert."], ["deterministisch", "Gleiche Eingaben führen reproduzierbar zur gleichen Entscheidung oder zum gleichen Artefakt."], ["Evidence", "Maschinenlesbare Belege, die eine konkrete Prüfung mit Eingaben, Codezustand und Ergebnis verbinden."]]
  },
  "knowledge": {
    title: "Vom allgemeinen Wissen zum konkreten Fall",
    text: `<p>SpecForge verarbeitet zwei Arten von Wissen. Die <strong>Product Spec</strong> sagt, was es in diesem Produkt gibt: zum Beispiel die Entität <code>Event</code>, das Feld <code>location</code> und die Operation <code>read_event</code>. Ein <strong>Knowledge Package</strong> enthält dagegen wiederverwendbares Wissen, etwa Regeln für persönliche Daten oder Authentifizierung.</p><p>Allein sind beide Seiten unvollständig. Die Aussage „persönliche Daten müssen minimiert werden“ kennt das Calendar-Produkt nicht. Die Aussage „Event.location ist ein persönliches Datum“ sagt noch nicht, welche technische Behandlung daraus folgt. Die Resolution verbindet beides. So wird aus einer allgemeinen Definition eine konkrete <strong>Requirement Instance</strong> für ein bestimmtes Target.</p><p>Anschließend übersetzt SpecForge die fachliche Anforderung in eine <strong>Implementation Obligation</strong>. Eine Obligation beschreibt einen technischen Zustand, der erfüllt sein muss – aber nicht den vollständigen Quellcode. „Die Antwort von <code>read_event</code> darf nur diese Felder enthalten“ ist eine Obligation. Ob das mit einem Pydantic-Schema, einer Mapper-Funktion oder einer anderen sauberen Lösung umgesetzt wird, darf der Agent entscheiden.</p>`,
    analogy: "Eine allgemeine Verkehrsregel wird erst an einer konkreten Kreuzung relevant. Die Regel ist die Definition, die Anwendung auf diese Kreuzung die Instance, und die dort notwendige Ampelschaltung die technische Obligation.",
    terms: [["Product Spec", "Maschinenlesbare Beschreibung des konkreten Produkts: Entitäten, Felder, Operationen, Komponenten und weitere Fakten."], ["Knowledge Package", "Versioniertes Paket mit wiederverwendbaren Requirements, Regeln und technischer Guidance aus einer Domäne."], ["Target", "Das konkrete Objekt, auf das eine Anforderung wirkt, etwa operation:read_event oder field:Event.location."], ["Requirement Definition", "Die allgemeine, technologieunabhängige Form einer Anforderung."], ["Requirement Instance", "Eine Requirement Definition, angewendet auf genau ein typisiertes Target."], ["Obligation", "Eine konkrete technische Verpflichtung, die der Code erfüllen muss. Mehrere Obligations werden im nächsten Kurs konsolidiert."], ["Surface", "Der technische Wirkungsbereich einer Obligation. Beispiele: response für Ausgaben, input für Eingaben oder data_access für Datenzugriffe."], ["Control", "Die benannte Eigenschaft, die innerhalb einer Surface gesteuert wird, zum Beispiel response_minimization."], ["allowed_fields", "Eine Positivliste: Nur die genannten Felder dürfen in der betreffenden Response ausgegeben werden."]]
  },
  "resolution": {
    title: "Warum Requirements vor dem Coding zusammengeführt werden",
    text: `<p>Eine einzelne API-Operation wird meistens von mehreren Anforderungen gleichzeitig beeinflusst. <code>read_event</code> kann Authentifizierung, Eigentümerprüfung, Datenminimierung, Audit Logging und Rate Limiting benötigen. Würde der Agent dafür fünf getrennte Aufträge erhalten, könnten die Lösungen einander widersprechen oder dieselbe Stelle mehrfach umbauen.</p><p>Die <strong>Resolution</strong> ermittelt zunächst, welche Requirement Instances gelten. Die anschließende <strong>Konsolidierung</strong> führt ihre technischen Folgen zusammen. Dazu gruppiert SpecForge Obligations nach <strong>Surfaces</strong>. Eine Surface ist kein UI-Bildschirm, sondern ein technischer Wirkungsbereich wie Identität, Datenzugriff, Response oder Observability.</p><p>Zusammenführen bedeutet nicht einfach „alles sammeln“. Für jeden Control-Typ gibt es eine feste Merge-Regel. Bei erlaubten Response-Feldern ist häufig die Schnittmenge sicher: Ein Feld bleibt nur erlaubt, wenn alle relevanten Regeln es erlauben. Bei Obergrenzen gewinnt der strengere kleinere Wert. Widersprechen sich Regeln unauflösbar, entsteht ein Conflict. Der Agent wird dann gar nicht gestartet, weil er keine Governance-Entscheidung improvisieren soll.</p>`,
    analogy: "Mehrere Filter liegen übereinander. Nur was durch alle Filter passt, bleibt übrig. Sind zwei Vorgaben logisch unvereinbar, wird nicht geraten – der Prozess stoppt mit einer Diagnose.",
    terms: [["Resolution", "Deterministischer Schritt, der ermittelt, welche Requirements für welche Targets gelten."], ["Konsolidierung", "Zusammenführen aller gleichzeitig wirkenden Obligations zu einem konfliktfreien Gesamtauftrag."], ["Surface", "Technischer Wirkungsbereich einer Obligation, beispielsweise response, data_access oder traffic."], ["Control", "Die konkret zu steuernde Eigenschaft innerhalb einer Surface, etwa authorization oder allowed_fields."], ["Merge-Semantik", "Explizite Regel, nach der mehrere Werte kombiniert oder als Konflikt erkannt werden."], ["Provenance", "Nachvollziehbare Herkunft: Welche Regel, Paketversion und Eingabe führte zu diesem Ergebnis?"]]
  },
  "work-order": {
    title: "Wie aus Anforderungen ein sicherer Arbeitsauftrag wird",
    text: `<p>Bevor Codex gestartet wird, erzeugt SpecForge drei zusammenhängende Artefakte. Der <strong>Implementation Plan</strong> beschreibt den beabsichtigten technischen Zielzustand: betroffene Targets, Obligations, Patterns und Prüfungen. Der <strong>Impact Scope</strong> schätzt konservativ, welche Dateien, Komponenten und Tests von der Änderung berührt werden können. Der <strong>Work Order</strong> ist schließlich der unveränderliche Auftrag für genau einen Agent Run.</p><p>„Konservativ“ heißt beim Impact Scope: Lieber eine möglicherweise betroffene Datei zu viel aufnehmen als eine relevante Datei zu übersehen. Trotzdem ist der Scope eine echte Grenze. <code>MAY_MODIFY</code> erlaubt Änderungen, <code>READ_ONLY</code> liefert nur Kontext, und <code>MUST_NOT_MODIFY</code> markiert verbotene Bereiche. Ändert der Agent beispielsweise ein Knowledge Package, obwohl es schreibgeschützt ist, wird der Run unabhängig von der Codequalität abgelehnt.</p><p>Ein <strong>Pattern</strong> hilft dem Agenten bei der Umsetzung. Es kann empfehlen, Ownership direkt in einer Datenbankabfrage zu erzwingen, und unsichere Alternativen verbieten. Es ist aber weder ein Template noch eine Entscheidung darüber, ob die Regel gilt. Mit <code>--dry-run</code> kannst du den vollständigen Auftrag untersuchen, ohne den Agenten aufzurufen oder Anwendungscode zu verändern.</p>`,
    analogy: "Plan ist die technische Bauplanung, Impact Scope ist der abgesperrte Arbeitsbereich, Work Order ist der unterschriebene Auftrag für einen konkreten Einsatz.",
    terms: [["Implementation Plan", "Deterministisch erzeugte Übersicht des Zielzustands, der Obligations, Guidance und Prüfungen."], ["Impact Scope", "Konservative Berechnung der möglicherweise betroffenen Code- und Testbereiche."], ["Work Order", "Versionierter, gehashter und unveränderlicher Auftrag für genau einen Agent Run."], ["Pattern", "Technische Guidance mit Voraussetzungen, Empfehlungen, Verboten und Verifikationsbezügen."], ["Agent Run", "Eine konkrete Ausführung eines Agent Adapters mit einem bestimmten Work Order."], ["Dry Run", "Vorschau des Auftrags ohne Agent-Aufruf und ohne Änderungen am Anwendungscode."]]
  },
  "gates": {
    title: "Warum ein grüner Build noch keine erfolgreiche Änderung ist",
    text: `<p>Ein Build beantwortet nur die Frage, ob sich die Anwendung technisch bauen lässt. Er beweist nicht, dass der Agent nur erlaubte Dateien geändert, eine Eigentümerprüfung korrekt umgesetzt oder bestehende Funktionen erhalten hat. Deshalb durchläuft jedes Agent-Ergebnis mehrere unabhängige <strong>Gates</strong>.</p><p>Das Permission Gate prüft den erlaubten Scope. Schema, Build und Static Gates prüfen strukturierte Artefakte und technische Qualität. Das Requirement Gate führt die obligatorischen Verification Instances aus. Das Regression Gate schützt bereits verifizierte, weiterhin relevante Eigenschaften. Erst das Evidence Gate stellt sicher, dass alle Resultate exakt zum aktuellen Work Order, Agent Run, Diff und Softwarestand gehören.</p><p><strong>Evidence</strong> ist also mehr als ein Testbericht. Sie bindet erwarteten Wert, beobachteten Wert, Prüfungs-ID und Hashes aneinander. Trotzdem ist sie bewusst begrenzt: Erfolgreiche Evidence sagt, dass die formalisierten Requirements in diesem konkreten Stand und Prüfungsumfang bestanden wurden. Sie sagt nicht, dass das gesamte Produkt allgemein sicher, rechtskonform oder fehlerfrei ist.</p>`,
    analogy: "Ein Auto besteht nicht nur die Prüfung ‚Motor startet‘. Bremsen, Licht, Identität des Fahrzeugs und Prüfbericht gehören zu getrennten Kontrollen.",
    terms: [["Gate", "Eine obligatorische Prüfschranke. Scheitert ein verpflichtendes Gate, wird der Run abgelehnt."], ["Verification Instance", "Konkrete maschinelle Prüfung eines Requirements auf einem Target."], ["Regression", "Eine früher funktionierende, weiterhin relevante Eigenschaft wird durch die Änderung beschädigt."], ["Traceability", "Durchgängige Nachverfolgbarkeit von der Policy bis zu Codeänderung, Prüfung und Evidence."], ["ACCEPTED", "Alle obligatorischen Gates für diesen konkreten Run sind erfolgreich."], ["REJECTED", "Mindestens ein obligatorisches Gate ist fehlgeschlagen; die Änderung wird nicht akzeptiert."]]
  },
  "mission": {
    title: "Was bei einer unvollständigen Implementierung passiert",
    text: `<p>Die Abschlussmission simuliert ein typisches Ergebnis agentischer Entwicklung: Der Agent hat einen großen Teil korrekt umgesetzt, aber einen verpflichtenden Teil vergessen. Das ist kein außergewöhnlicher Systemfehler, sondern genau der Fall, für den die Gates existieren.</p><p>Wenn der UI-Test für <code>Event.location</code> fehlschlägt, bleibt der ursprüngliche Agent Run <strong>REJECTED</strong>. Er wird nicht nachträglich schöngeschrieben. SpecForge darf einen begrenzten <strong>Repair Run</strong> vorbereiten. Dessen Auftrag enthält den ursprünglichen Work Order, den aktuellen Diff, die konkrete fehlgeschlagene Verification sowie erwartete und beobachtete Werte.</p><p>Der Repair darf den ursprünglichen Scope nicht eigenständig erweitern. Nach der Korrektur laufen alle Gates erneut, nicht nur der zuvor rote Test. Das ist wichtig, weil eine Reparatur an der UI versehentlich Build, andere Requirements oder Berechtigungsgrenzen verletzen könnte. Erst der neue vollständige Prüfzyklus kann zu ACCEPTED führen.</p>`,
    analogy: "Eine Nachbesserung bei der Bauabnahme hebt den alten Mangelbericht nicht auf. Sie wird separat dokumentiert und das Gesamtwerk anschließend erneut geprüft.",
    terms: [["Repair Run", "Begrenzter Folge-Run, der ausschließlich konkrete Fehler eines abgelehnten Runs adressiert."], ["Repair Work Order", "Arbeitsauftrag mit ursprünglichem Scope, Diff, Fehlerbeobachtung und verbleibender Versuchszahl."], ["Observed", "Der tatsächlich von einer Verification gemessene Wert oder Zustand."], ["Expected", "Der vom Requirement verlangte und in der Verification erwartete Wert oder Zustand."], ["Scope", "Explizite Grenze der Dateien und Aufgaben, die ein Agent bearbeiten darf."], ["begrenzte Schleife", "Es gibt eine feste Maximalzahl von Reparaturversuchen; keine endlose automatische Wiederholung."]]
  }
};

function getVariant() { const v = new URLSearchParams(location.search).get("variant"); return variants.includes(v) ? v : "A"; }
function setVariant(v) { const u = new URL(location.href); u.searchParams.set("variant", v); history.replaceState({}, "", u); render(); }
function cycleVariant(d) { const i = variants.indexOf(getVariant()); setVariant(variants[(i + d + variants.length) % variants.length]); }
function progress() { return Math.round(state.completed.size / courses.length * 100); }
function toast(message) { const el = document.querySelector("#toast"); el.textContent = message; el.classList.add("show"); setTimeout(() => el.classList.remove("show"), 1800); }

function header(dark = false) {
  return `<header class="topbar"><div class="brand"><span class="brand-mark">S</span> SpecForge Academy <span class="pill">PROTOTYP</span></div><div class="pill">⚡ ${state.xp} XP · ${progress()}%</div></header>`;
}
function nav() {
  return courses.map((c, i) => `<button class="nav-course ${i === state.active ? "active" : ""}" data-course="${i}"><span class="mono">${state.completed.has(i) ? "✓" : c.icon}</span> &nbsp;${c.title}<br><small>${c.duration} · ${c.xp} XP</small></button>`).join("");
}
function courseContent(course, index) {
  const lessons = course.lessons.map((l, i) => `<article class="lesson-card"><span class="lesson-num">LEKTION ${i + 1}/${course.lessons.length}</span><h3>${l.title}</h3>${l.body}</article>`).join("");
  const ready = state.answered.has(index) && (!course.mission || state.missionPassed);
  return `<section class="course-content"><div class="course-head"><p class="eyebrow">Kurs ${index + 1} · ${course.duration} · +${course.xp} XP</p><h2>${course.title}</h2><p class="summary">${course.summary}</p><div class="learning-goals"><b>Danach kannst du …</b><ul>${course.goals.map(g => `<li>${g}</li>`).join("")}</ul></div></div>${guideWidget(course)}${lessons}${pipelineWidget(index)}${cliLabWidget(index)}${quizWidget(course, index)}<button class="btn complete" data-complete="${index}" ${state.completed.has(index) || !ready ? "disabled" : ""}>${state.completed.has(index) ? "✓ Kurs abgeschlossen" : ready ? "Kurs abschließen →" : `🔒 Erst ${course.mission && !state.missionPassed ? "Mission und Quiz" : "Knowledge Check"} bestehen`}</button></section>`;
}
function guideWidget(course) {
  const guide = courseGuides[course.id];
  return `<article class="deep-guide"><div class="guide-copy"><span class="lesson-num">LANGSAM ERKLÄRT · START HIER</span><h3>${guide.title}</h3>${guide.text}<div class="analogy"><span>◉</span><div><b>Vergleich aus dem Alltag</b><p>${guide.analogy}</p></div></div></div><aside class="term-guide"><p class="eyebrow">BEGRIFFE IN DIESEM KURS</p>${guide.terms.map(([term, meaning]) => `<details><summary>${term}<span>+</span></summary><p>${meaning}</p></details>`).join("")}</aside></article>`;
}
function pipelineWidget(index) {
  if (index !== 0) return "";
  const steps = [
    {
      title: "Product Spec + Knowledge laden",
      actor: "SpecForge Loader",
      input: "products/calendar/product.yaml + versionierte Knowledge Packages",
      output: "Validierte Produktfakten und gepinnte Wissenspakete",
      explanation: "Zuerst liest SpecForge die Beschreibung des konkreten Produkts und das wiederverwendbare Wissen aus Security, Privacy, Data und Platform. Dabei wird noch kein Code erzeugt und kein Agent gestartet. Paketversionen und Content-Hashes sorgen dafür, dass später eindeutig nachvollziehbar ist, welches Wissen verwendet wurde.",
      why: "Ohne feste, versionierte Eingaben könnte derselbe Auftrag morgen auf anderem Wissen beruhen.",
      action: "Eingaben validieren und laden"
    },
    {
      title: "Requirements deterministisch auflösen",
      actor: "Requirement Resolver – ohne LLM",
      input: "Produktfakten + Regeln aus den Knowledge Packages",
      output: "Konkrete Requirement Instances pro typisiertem Target",
      explanation: "Der Resolver verbindet allgemeine Regeln mit konkreten Elementen des Calendar-Produkts. Aus SEC-001 wird beispielsweise SEC-001@operation:read_event. Dieser Schritt folgt fest programmierten Regeln: Identische Eingaben erzeugen identische Instances.",
      why: "Der Coding Agent darf nicht selbst auswählen, welche Security- oder Privacy-Regeln für ihn gelten.",
      action: "Requirement Instances berechnen"
    },
    {
      title: "Obligations konsolidieren",
      actor: "Obligation Consolidator – ohne LLM",
      input: "Alle Requirement Instances für dieselben Targets",
      output: "Konfliktfreie technische Verpflichtungen nach Surface",
      explanation: "Mehrere Requirements können gleichzeitig read_event beeinflussen. Der Consolidator dedupliziert identische Controls, bildet etwa Schnittmengen erlaubter Felder und erkennt unvereinbare Erwartungen. Jede Quelle bleibt in der Provenance erhalten.",
      why: "Codex soll einen gemeinsamen, widerspruchsfreien Auftrag erhalten – nicht mehrere lose Prompts, die sich gegenseitig übersehen.",
      action: "Obligations zusammenführen"
    },
    {
      title: "Work Order an Codex übergeben",
      actor: "Codex Agent Adapter",
      input: "Work Order, Resolved Spec, Patterns und Schreibgrenzen",
      output: "Geänderter Anwendungscode + Agent Run Result + Dateidiff",
      explanation: "Erst jetzt kommt der Coding Agent ins Spiel. Codex entscheidet, wie die Obligations im bestehenden Backend, Frontend und in Tests umgesetzt werden. Der Work Order legt Ziel, erlaubte Pfade und obligatorische Prüfungen fest; er schreibt aber nicht den vollständigen Code vor.",
      why: "Der Agent erhält technische Freiheit, aber weder Governance-Freiheit noch unbegrenzten Schreibzugriff.",
      action: "Agent Run simulieren"
    },
    {
      title: "Gates ausführen",
      actor: "Deterministischer Verifier",
      input: "Work Order + Diff + geänderter Workspace + Verification Plan",
      output: "Gate Results mit erwarteten und beobachteten Werten",
      explanation: "Permission, Schema, Build, Static, Requirement, Regression und Evidence Gates prüfen das Ergebnis unabhängig vom Agenten. Eine Zusammenfassung von Codex wie ‚alles erledigt‘ zählt nicht. Schon ein fehlgeschlagenes obligatorisches Gate führt zu REJECTED.",
      why: "Wer implementiert, soll nicht zugleich allein entscheiden, ob die eigene Arbeit korrekt ist.",
      action: "Alle sieben Gates prüfen"
    },
    {
      title: "Evidence versionieren",
      actor: "Evidence & Reporting",
      input: "Requirement-, Work-Order-, Run-, Diff- und Gate-Daten",
      output: "Nachvollziehbare Evidence für genau diesen Softwarestand",
      explanation: "SpecForge verbindet die bestandenen Verifications mit ihren Requirements, dem Work Order, dem Agent Run und den Hashes des konkreten Diffs. So lässt sich später rekonstruieren, was geprüft wurde und auf welcher Grundlage ACCEPTED entstand.",
      why: "Ein grünes Ergebnis ohne Bindung an Eingaben und Codezustand wäre später nicht belastbar zuzuordnen.",
      action: "Evidence-Kette schreiben"
    }
  ];
  const complete = state.pipelineStep >= steps.length;
  const current = complete ? null : steps[state.pipelineStep];
  const detail = complete
    ? `<div class="pipeline-detail complete"><p class="eyebrow">RUN-ERGEBNIS</p><h4>ACCEPTED</h4><p>Alle sechs Phasen wurden durchlaufen. Wichtig: Nicht der Klick und nicht Codex haben akzeptiert. Der Status entstand aus den obligatorischen Gate Results und wurde an versionierte Evidence gebunden.</p><div class="artifact-result"><span>Erzeugte Kette</span><code>Inputs → Instances → Obligations → Work Order → Diff → Gates → Evidence</code></div></div>`
    : `<div class="pipeline-detail"><div class="pipeline-detail-head"><span class="pipe-icon">${state.pipelineStep + 1}</span><div><p class="eyebrow">AKTUELLER SCHRITT</p><h4>${current.title}</h4></div></div><p class="pipeline-explanation">${current.explanation}</p><dl><div><dt>Wer handelt?</dt><dd>${current.actor}</dd></div><div><dt>Eingabe</dt><dd>${current.input}</dd></div><div><dt>Ergebnis</dt><dd>${current.output}</dd></div></dl><div class="pipeline-why"><b>Warum ist das nötig?</b><p>${current.why}</p></div></div>`;
  return `<article class="lesson-card pipeline-lab"><span class="lesson-num">INTERAKTIVES LAB</span><h3>Verfolge einen SpecForge Run</h3><p class="muted">Lies zuerst die Erklärung des markierten Schritts. Der Button simuliert anschließend dessen Ergebnis und führt dich zur nächsten Phase.</p><div class="pipeline">${steps.map((s, i) => `<div class="pipe-step ${i < state.pipelineStep ? "done" : i === state.pipelineStep ? "active" : ""}"><span class="pipe-icon">${i < state.pipelineStep ? "✓" : i + 1}</span><span><b>${s.title}</b>${i < state.pipelineStep ? `<small>${s.output}</small>` : ""}</span></div>`).join("")}</div>${detail}<button class="btn" id="pipeline-next" ${complete ? "disabled" : ""}>${complete ? "✓ Run ACCEPTED" : `${current.action} →`}</button></article>`;
}
function cliLabWidget(index) {
  if (index !== 3) return "";
  const rounds = [
    { prompt: "Du willst sehen, welche Requirements gelten – ohne Code zu verändern.", answer: "resolve", options: [["resolve", "specforge resolve products/calendar"], ["implement", "specforge implement products/calendar --agent codex"], ["report", "specforge report products/calendar"]] },
    { prompt: "Du willst Plan, Scope und Work Order prüfen, aber keinen Agenten starten.", answer: "dry", options: [["validate", "specforge validate products/calendar"], ["dry", "specforge implement products/calendar --agent codex --dry-run"], ["repair", "specforge repair run-42"]] },
    { prompt: "SEC-001 wirkt auf read_event. Du willst die Herleitung genau dort untersuchen.", answer: "explain", options: [["runs", "specforge runs products/calendar"], ["explain", "specforge explain SEC-001 --product products/calendar --target operation:read_event"], ["evidence", "specforge evidence products/calendar"]] }
  ];
  if (state.cliStep >= rounds.length) return `<article class="lesson-card cli-lab"><span class="lesson-num">CLI LAB · BESTANDEN</span><h3>Du hast drei sichere Inspektionspfade gewählt.</h3><div class="terminal"><span class="ok">✓ Kein unbeabsichtigter Agent Run. Kein Anwendungscode verändert.</span></div></article>`;
  const round = rounds[state.cliStep];
  return `<article class="lesson-card cli-lab"><span class="lesson-num">CLI ENTSCHEIDUNG ${state.cliStep + 1}/${rounds.length}</span><h3>Welcher Befehl passt?</h3><p>${round.prompt}</p><div class="command-options">${round.options.map(([key, label]) => `<button data-command="${key}" data-answer="${round.answer}"><code>$ ${label}</code></button>`).join("")}</div><p id="command-feedback" class="muted">Wähle den kleinsten Befehl, der die Frage beantwortet.</p></article>`;
}
function quizWidget(course, index) {
  const passed = state.answered.has(index);
  return `<div class="quiz"><p class="eyebrow" style="color:var(--lime)">KNOWLEDGE CHECK · +40 XP</p><b>${course.quiz.q}</b><div class="quiz-options">${course.quiz.options.map((o, i) => `<button class="quiz-option ${passed && i === course.quiz.answer ? "correct" : ""}" data-quiz="${index}" data-option="${i}" ${passed ? "disabled" : ""}>${String.fromCharCode(65+i)}. ${o}</button>`).join("")}</div><p class="quiz-feedback" id="feedback-${index}">${passed ? `✓ Bestanden. ${course.quiz.explain}` : "Beantworte aus dem Gedächtnis – du kannst es erneut versuchen."}</p></div>`;
}
function hero() {
  return `<section class="hero"><div><p class="eyebrow">Für Software Engineers · ca. 3 Stunden</p><h1>Vom Requirement zur <em>beweisbaren</em> Änderung.</h1><p class="lead">Lerne SpecForge ohne Vorwissen. Jeder neue Begriff wird zuerst in Alltagssprache erklärt und danach an technischen Beispielen angewendet. Du brauchst nur grundlegendes Verständnis von Code, APIs und Tests.</p><button class="btn" data-jump>Ersten Kurs starten →</button></div><div class="hero-diagram"><p class="eyebrow">DER KONTROLLKREIS</p><div class="node">01 / PRODUKT + WISSEN</div><div class="node">02 / COMPILER ENTSCHEIDET</div><div class="node agent">03 / CODEX IMPLEMENTIERT</div><div class="node gate">04 / GATES PRÜFEN</div><div class="node">05 / EVIDENCE BELEGT</div><p class="muted">Der Agent sitzt <em>innerhalb</em> der kontrollierten Klammer – nicht darüber. Im ersten Kurs zerlegen wir jeden Teil.</p></div></section>`;
}
function renderGuided() { return `<main class="guided">${header()}${hero()}<div class="course-shell" id="courses"><aside class="course-nav"><p class="eyebrow">DEIN LERNPFAD</p><div class="progress"><i style="width:${progress()}%"></i></div>${nav()}</aside>${courseContent(courses[state.active], state.active)}</div></main>`; }
function renderCommand() { return `<main class="command">${header(true)}<div class="command-grid"><aside class="sidebar"><p class="eyebrow">MISSIONS</p>${nav()}</aside><section class="workspace">${courseContent(courses[state.active], state.active)}</section><aside class="intel"><p class="eyebrow">RUN TELEMETRY</p><div class="intel-stat">Fortschritt<strong>${progress()}%</strong></div><div class="intel-stat">Evidence Points<strong>${state.xp} XP</strong></div><div class="intel-stat">Status<strong>${state.completed.size === courses.length ? "ACCEPTED" : "RUNNING"}</strong></div><p class="muted mono" style="font-size:12px;line-height:1.7">scope: academy/**<br>mode: deterministic<br>agent: learner<br>gates: ${state.completed.size}/${courses.length}</p></aside></div></main>`; }
function renderMap() {
  const nodes = courses.map((c, i) => `<article class="map-node ${i === state.active ? "active" : ""} ${state.completed.has(i) ? "done" : ""}"><div class="orb">${state.completed.has(i) ? "✓" : c.icon}</div><div><p class="eyebrow">${c.duration} · +${c.xp} XP</p><h3>${c.title}</h3><span class="muted">${c.summary}</span></div><button class="btn secondary" data-course="${i}">${i === state.active ? "Geöffnet" : "Öffnen"}</button></article>`).join("");
  return `<main class="map">${header()}<section class="map-hero"><span class="pill">SPEC → CODE → EVIDENCE</span><h1>Baue deine SpecForge Skill-Map.</h1><p>Sechs Etappen vom ersten mentalen Modell bis zur eigenständigen Agent-Run-Entscheidung.</p><div class="progress"><i style="width:${progress()}%;background:var(--yellow)"></i></div></section><div class="map-layout"><div class="map-path">${nodes}</div><aside class="map-detail">${courseContent(courses[state.active], state.active)}</aside></div></main>`;
}
function render() {
  const v = getVariant();
  document.querySelector("#app").innerHTML = v === "A" ? renderGuided() : v === "B" ? renderCommand() : renderMap();
  document.querySelector("#variant-label").textContent = variantNames[v];
  bind();
}

function bind() {
  document.querySelectorAll("[data-course]").forEach(el => el.onclick = () => { state.active = Number(el.dataset.course); render(); if (getVariant() === "A") document.querySelector("#courses")?.scrollIntoView(); });
  document.querySelector("[data-jump]")?.addEventListener("click", () => document.querySelector("#courses")?.scrollIntoView());
  document.querySelector("#pipeline-next")?.addEventListener("click", () => { state.pipelineStep++; render(); toast(state.pipelineStep === 6 ? "Run akzeptiert · Evidence gebunden" : `Schritt ${state.pipelineStep} abgeschlossen · Ergebnis erzeugt`); });
  document.querySelectorAll("[data-command]").forEach(el => el.onclick = () => answerCommand(el));
  document.querySelectorAll("[data-quiz]").forEach(el => el.onclick = () => answerQuiz(el));
  document.querySelector("[data-complete]")?.addEventListener("click", e => completeCourse(Number(e.currentTarget.dataset.complete)));
  setupMission();
}
function answerQuiz(el) {
  const ci = Number(el.dataset.quiz), selected = Number(el.dataset.option), quiz = courses[ci].quiz;
  const container = el.closest(".quiz");
  state.attempts[ci] = (state.attempts[ci] || 0) + 1;
  if (selected !== quiz.answer) {
    el.classList.add("wrong");
    setTimeout(() => el.classList.remove("wrong"), 650);
    container.querySelector(".quiz-feedback").textContent = `Noch nicht. Versuch ${state.attempts[ci]}. Prüfe, wer in SpecForge entscheiden darf – Compiler, Agent oder Gate.`;
    return;
  }
  container.querySelectorAll(".quiz-option").forEach((b, i) => { b.disabled = true; if (i === quiz.answer) b.classList.add("correct"); });
  container.querySelector(".quiz-feedback").textContent = `✓ Richtig. ${quiz.explain}`;
  if (!state.answered.has(ci)) { state.answered.add(ci); state.xp += 40; toast("+40 XP · Knowledge Check bestanden"); setTimeout(render, 700); }
}
function answerCommand(el) {
  const feedback = document.querySelector("#command-feedback");
  if (el.dataset.command !== el.dataset.answer) {
    el.classList.add("wrong-command");
    feedback.textContent = "Der Befehl ist gültig, aber für dieses Ziel zu weit, zu spät oder nicht erklärend genug. Versuch es erneut.";
    setTimeout(() => el.classList.remove("wrong-command"), 650);
    return;
  }
  el.classList.add("right-command");
  feedback.textContent = "✓ Minimaler, sicherer Schritt gewählt.";
  setTimeout(() => {
    state.cliStep++;
    if (state.cliStep === 3 && !state.cliRewarded) { state.cliRewarded = true; state.xp += 60; toast("+60 XP · CLI Lab bestanden"); }
    render();
  }, 550);
}
function completeCourse(i) {
  if (!state.answered.has(i) || (courses[i].mission && !state.missionPassed)) return;
  state.completed.add(i); state.xp += courses[i].xp; toast(`+${courses[i].xp} XP · Kurs abgeschlossen`);
  if (i < courses.length - 1) state.active = i + 1;
  render();
}
function setupMission() {
  const root = document.querySelector("#mission-builder"); if (!root) return;
  if (state.missionPassed) {
    root.innerHTML = `<div class="complete-banner"><b>✓ Mission bestanden</b><p>Der unvollständige Run bleibt REJECTED. Der Repair Work Order bleibt im ursprünglichen Scope; danach laufen alle Gates erneut.</p></div>`;
    return;
  }
  const groups = [
    { key: "status", label: "1. Status des unvollständigen Runs", choices: ["ACCEPTED", "REJECTED", "PAUSED"], answer: "REJECTED" },
    { key: "action", label: "2. Nächste Aktion", choices: ["Scope frei erweitern", "Repair Work Order", "Evidence manuell ändern"], answer: "Repair Work Order" },
    { key: "scope", label: "3. Repair-Scope", choices: ["Nur ursprünglicher Scope", "Ganzes Repository", "Agent entscheidet"], answer: "Nur ursprünglicher Scope" }
  ];
  root.innerHTML = groups.map(g => `<div><b>${g.label}</b><div class="mission-choice">${g.choices.map(c => `<button data-mission="${g.key}" data-value="${c}">${c}</button>`).join("")}</div></div>`).join("") + `<button class="btn" id="check-mission">Entscheidung prüfen</button>`;
  root.querySelectorAll("[data-mission]").forEach(b => b.onclick = () => { state.mission[b.dataset.mission] = b.dataset.value; b.parentElement.querySelectorAll("button").forEach(x => x.classList.toggle("selected", x === b)); });
  root.querySelector("#check-mission").onclick = () => {
    const ok = groups.every(g => state.mission[g.key] === g.answer);
    document.querySelector("#mission-result").innerHTML = ok ? `<div class="complete-banner"><b>✓ Mission bestanden</b><p>TEST-PRODUCT-LOCATION-UI schlägt fehl → Run REJECTED → begrenzter Repair Work Order → danach alle Gates erneut.</p></div>` : `<div class="callout"><b>Pipeline blockiert.</b> Suche nach der Option, bei der Evidence entscheidet, der Scope nicht wächst und der fehlerhafte Run abgelehnt bleibt.</div>`;
    if (ok) { state.missionPassed = true; toast("Mission bestanden · saubere Entscheidungskette"); setTimeout(render, 850); }
  };
}

document.querySelector("#prev-variant").onclick = () => cycleVariant(-1);
document.querySelector("#next-variant").onclick = () => cycleVariant(1);
window.addEventListener("keydown", e => { if (["INPUT", "TEXTAREA"].includes(document.activeElement.tagName) || document.activeElement.isContentEditable) return; if (e.key === "ArrowLeft") cycleVariant(-1); if (e.key === "ArrowRight") cycleVariant(1); });
window.addEventListener("popstate", render);
render();
