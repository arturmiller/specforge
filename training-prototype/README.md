# SpecForge · Geführte Lernreise

Der statische Prototyp erzählt in acht Stationen den „Fall des zu offenen Kalenders“. Seine fachlichen Daten werden aus dem aktuellen semantischen SpecForge-Dataset erzeugt; `scenario.generated.js` ist deshalb absichtlich nicht versioniert.

Im Repository-Root einmal ausführen:

```powershell
uv run specforge training products/calendar
```

Danach `training-prototype/index.html` direkt im Browser öffnen. Ein Webserver, eine Graphdatenbank und Netzwerkzugriff sind nicht nötig.

Der Browser speichert den Fortschritt ausschließlich unter einem vom Szenario-Hash abhängigen Schlüssel. „Lernreise zurücksetzen“ entfernt nur diesen Eintrag. Nach einer fachlichen Änderung den Build-Befehl erneut ausführen; der neue Hash invalidiert alten Fortschritt automatisch.

Es gibt bewusst nur die „Geführte Lernreise“. Der frühere Variantenrouter, Mission Control und Skill Map wurden entfernt.
