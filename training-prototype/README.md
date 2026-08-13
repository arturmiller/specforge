# SpecForge Academy – Throwaway-Prototyp

Fragestellung: Drei radikal unterschiedliche Varianten einer interaktiven SpecForge-Schulung, um Lernstruktur und Informationsdichte zu vergleichen. Umschaltbar über `?variant=A|B|C` und die schwebende Leiste.

Start im Repository-Root:

```powershell
uv run python -m http.server 4173 --directory training-prototype
```

Dann `http://localhost:4173/?variant=A` öffnen.

- A: Geführte, redaktionelle Lernreise
- B: Dichte Mission-Control für erfahrene Engineers
- C: Gamifizierte Skill-Map

Der Zustand lebt nur im Speicher und verschwindet beim Reload. Nach Auswahl einer Variante sollte der Prototyp gelöscht oder die Gewinner-Idee sauber in eine echte Anwendung überführt werden.

## Review-Stand

Die zweite Iteration ergänzt sichtbare Lernziele, wiederholbare Knowledge Checks ohne vorzeitige Lösungsanzeige, Abschluss-Gates, ein dreistufiges CLI-Entscheidungslab und eine fachlich präzisierte Darstellung der sieben Verification Gates. Ein Kurs zählt erst nach bestandenem Check als abgeschlossen.

Die dritte Iteration richtet sich ausdrücklich an Lernende ohne SpecForge-Vorwissen: Jeder Kurs beginnt mit einer ausführlichen Herleitung in Alltagssprache, einem anschaulichen Vergleich und einem aufklappbaren Begriffslexikon. Erst danach folgen technische Artefakte und Übungen.

Das Pipeline-Lab erklärt für jede Phase den verantwortlichen Akteur, Eingaben, erzeugte Artefakte und den Zweck des Schritts. Abgeschlossene Schritte zeigen ihr konkretes Ergebnis, statt lediglich einen Fortschrittszähler zu erhöhen.

Kurs 2 führt `surface`, `control` und `allowed_fields` nun vor ihrer ersten Verwendung ein. Das Obligation-Beispiel ist zeilenweise kommentiert und enthält eine explizite Lesereihenfolge von Requirement Definition bis überprüfbarem Zielzustand.

Kurs 5 erklärt alle sieben Gates einzeln mit konkretem Prüfmechanismus, PASS/FAIL-Regel, Beispiel und Aussagegrenze. Er unterscheidet deterministische Entscheidungen von möglicher Flakiness und kennzeichnet Abweichungen zwischen V2-Zielbild und aktueller Demo-Implementierung.
