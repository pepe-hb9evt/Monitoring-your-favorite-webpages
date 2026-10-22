# Monitoring your favorite webpages

**Überwache deine Lieblingswebseiten**

## Beschreibung

Ein kleines Python-Skript, das deine Lieblingswebseiten überwacht und Änderungen beim **sichtbaren** Inhalt (Text, Bilder, Links) protokolliert. Das Skript arbeitet deine Liste von Webseiten ab undspeichert bei jedem Aufruf für jede Webseite den aktuellen sichtbaren Inhalt und vergleicht ihn mit der letzten Speicherung. Danach wird eine Protokolldatei beschrieben, in der für jede Webseite deiner Liste, ob Änderungen festgestellt worden sind und wenn ja, was sich konkret geändert hat.

### Einschränkungen

Die aktuelle Version meldet nur, was sich geändert hat, aber meldet dir nicht, wo in der Webseite sich diese Änderung befindet. Webseiten mit Login werden mit HTTP Basic und mit dem WordPress-Anmeldeformular unterstützt.


Das Skript ist ausgerichtet auf Vergleich von Texten. Bilder und Grafiken werden nicht bildlich verglichen sondern lediglich deren Hash-Wert wird verglichen. Somit wird nur erkannt, dass ein Bild oder Grafik geändert wurde, jedoch nicht was sich bildlich geändert hat.

Entwickelt für Windows, läuft aber auf jedem System mit Python 3.

### Benutzungsanleitung

Dieses README gibt einen kompakten Überblick. Für die vollständige Referenz konsultiere  **[DOCUMENTATION_deutsch_german.md](DOCUMENTATION_deutsch_german.md)**

English version: [README.md](README.md)

## Funktionen

- Vergleicht sichtbaren **Text**, **Bilder** und **Links** getrennt; Skripte, versteckte Elemente und wechselnde URL-Bestandteile werden ignoriert.
- Erkennt ausgetauschte Bilder auch unter derselben URL (Inhalts-Hash).
- Webseiten-Liste in einer JSON-Datei, optional mit HTTP-Basic-Login oder WordPress-Anmeldeformular.
- Fehlerhafte Einträge oder nicht erreichbare Webseiten brechen den Lauf nie ab.
- `report-last-3-days.txt`: alle Läufe der letzten drei Tage, neuester zuoberst.
- `daily-report.txt`: 24-Stunden-Vergleich, wird nach jedem Lauf neu geschrieben.
- Optionale `settings.json` für Dateinamen, Aufbewahrung, Timeout, User-Agent, …

## Voraussetzungen

- Python 3.9 oder neuer (Windows: [python.org](https://www.python.org/downloads/), Option *Add python.exe to PATH*).
- `pip install -r requirements.txt`

## Installation

1. Die Dateien in einen Projektordner kopieren, z. B. `C:\Tools\webpages-monitor\`. Alle Daten werden in diesem Ordner gespeichert.
2. `webpages.example.json` nach `webpages.json` kopieren und die eigenen Webseiten eintragen.
3. Optional: `settings.example.json` nach `settings.json` kopieren und Werte anpassen.
4. Einmal testen: `python webpages_monitor.py`

Der erste Lauf speichert nur einen Ausgangsstand; verglichen wird ab dem zweiten Lauf.

## Webseiten-Liste (`webpages.json`)

```json
{
  "alpha-news": "https://example-alpha.com/de/news/",
  "internal": {
    "url": "https://example-epsilon.com/internal/",
    "username": "my-user",
    "password_env": "MONITOR_PW_INTERNAL"
  }
}
```

Alle Formate, Regeln und Optionen: [DOCUMENTATION_deutsch_german.md → Webseiten-Liste](DOCUMENTATION_deutsch_german.md#webseiten-liste-webpagesjson).

## Geplante Läufe (Windows)

```
schtasks /create /tn "Webpages Monitor 0600" /sc daily /st 06:00 /tr "cmd /c cd /d C:\Tools\webpages-monitor && python webpages_monitor.py"
```

Für weitere Uhrzeiten wiederholen. Einrichtung über die Oberfläche und Hinweise: [DOCUMENTATION_deutsch_german.md → Geplante Läufe](DOCUMENTATION_deutsch_german.md#geplante-läufe-unter-windows-aufgabenplanung).

## Ausgabe

```
report-last-3-days.txt                         Report der letzten drei Tage
daily-report.txt                               24-Stunden-Vergleich
monitored-webpages/<shortname>/captured_*.txt  Erfassungen, 48 Stunden aufbewahrt
monitored-webpages/<shortname>/archive/*.txt   eine Erfassung pro Tag, dauerhaft
```

Aufbau der Reports und Exit-Codes: [DOCUMENTATION_deutsch_german.md → Ausgabe](DOCUMENTATION_deutsch_german.md#ausgabe).

## Sicherheit

- `webpages.json` kann Passwörter enthalten und ist in `.gitignore` ausgeschlossen – nie committen.
- `password_env` gegenüber `password` bevorzugen. Passwörter erscheinen nie in den Reports.

## Lizenz

[MIT](LICENSE)

## Autoren

- Pepe HB9EVT
  https://github.com/pepe-hb9evt
- Claude (Anthropic)
