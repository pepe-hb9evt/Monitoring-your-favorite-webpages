# Überwache deine Lieblingswebseiten

README zum Projekt "**[Monitoring-your-favorite-webpages](https://github.com/pepe-hb9evt/Monitoring-your-favorite-webpages)**" auf Github.

( English version of this document available: [README.md](README.md) )

## Beschreibung

Ein kleines Python-Skript, das deine Lieblingswebseiten überwacht und Änderungen am **sichtbaren** Inhalt (Text, Bilder, Links) protokolliert.

Das Skript arbeitet deine Liste von Webseiten ab und speichert bei jedem Lauf den aktuellen sichtbaren Inhalt jeder Webseite und vergleicht ihn mit der letzten Speicherung. Danach werden zwei Report-Dateien geschrieben, in denen für jede Webseite aufgelistet wird, ob Änderungen festgestellt worden sind und wenn ja, was sich konkret geändert hat.

### Einschränkungen

Die wesentlichen Einschränkungen sind:

- **Abruf:** Erfasst wird nur das vom Server gelieferte HTML – ohne JavaScript-Inhalte, `<iframe>`-Inhalte und ohne den Inhalt von PDF- oder Word-Dateien. Seiten mit Captcha oder Browser-Prüfung lassen sich nicht zuverlässig überwachen.
- **Login:** Nur HTTP-Basic-Login und das WordPress-Anmeldeformular; keine anderen Anmeldeformulare, kein „Mit Google/Microsoft anmelden“, keine Zwei-Faktor-Anmeldung, kein Captcha.
- **Vergleich:** Gemeldet wird, *was* sich geändert hat (ganze Zeilen), nicht *wo* auf der Webseite. Bilder werden nur über ihren Hash-Wert verglichen: Erkannt wird, *dass* sich ein Bild geändert hat, aber es gibt keine Anzeige vorher/nachher. Änderungen an Layout, Farben oder Schriften werden nicht erkannt.
- **Betrieb:** Das Skript versendet selbst keine Mails und hat keinen eigenen Zeitplan (Start z. B. über die Windows-Aufgabenplanung). Der Report reicht drei Tage zurück; das Archiv wird nicht automatisch aufgeräumt.
- **Plattform:** Entwickelt für Windows, läuft aber auf jedem System mit Python 3.9 oder neuer.

Alle Einschränkungen im Detail: [DOCUMENTATION_deutsch_german.md → Was die aktuelle Version nicht kann](DOCUMENTATION_deutsch_german.md#was-die-aktuelle-version-nicht-kann).

Aktuell ist vom Autor keine Weiterentwicklung dieses Projekts geplant, um gewisse Einschränkungen zu beseitigen. Aber vielleicht willst du ja forken und es weiterentwickeln.

### Benutzungsanleitung

Dieses README gibt einen kompakten Überblick. Für die vollständige Referenz konsultiere **[DOCUMENTATION_deutsch_german.md](DOCUMENTATION_deutsch_german.md)**.

## Funktionen

- Vergleicht sichtbaren **Text**, **Bilder** und **Links** getrennt. Skripte, versteckte Elemente und wechselnde URL-Bestandteile werden hingegen ignoriert.
- Erkennt ausgetauschte Bilder, auch bei unveränderter Bild-URL.
- Die zu prüfenden Webseiten werden in einer JSON-Datei erfasst, optional auch mit den Zugangsdaten für ein HTTP-Basic-Login oder das WordPress-Anmeldeformular.
- Leitet eine Webseite auf eine Anmeldeseite um, die nicht passiert werden kann, wird das als Fehler gemeldet, statt die Anmeldeseite zu speichern.
- Das Terminal-Fenster zeigt während des Laufs, welche Webseite gerade abgerufen wird, und das Ergebnis.
- Für Testläufe beendet ein Eintrag `STOP` in der Webseiten-Liste die Liste; alle nachfolgenden Einträge werden übersprungen.
- Fehlerhafte Einträge oder nicht erreichbare Webseiten brechen den Lauf nie ab.
- Es werden bei jedem Lauf zwei Textdateien geschrieben:

  - `REPORT-of-every-run-last-3-days.txt`: alle Läufe der letzten drei Tage, neuester zuoberst.

  - `REPORT-daily-summary.txt`: Tagesvergleich (neueste Erfassung mit jener, die mindestens 23 Stunden alt ist).

In `settings.json` können diverse Parameter verändert werden (Dateinamen, Aufbewahrung, Timeout, User-Agent, …).

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

Die zu überwachenden Webseiten werden in `webpages.json` eingetragen:

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

Alle Formate, Regeln und Optionen sind nachzulesen in:
[DOCUMENTATION_deutsch_german.md → Webseiten-Liste](DOCUMENTATION_deutsch_german.md#webseiten-liste-webpagesjson).

## Geplante Läufe (Windows)

In Windows kann ein Job in der System-App „Aufgabenplanung“ zur täglichen Durchführung eingetragen werden. Am einfachsten erfolgt ein neuer Eintrag mit folgendem Befehl in der Eingabeaufforderung:

```
schtasks /create /tn "Webpages Monitor 0600" /sc daily /st 06:00 /tr "cmd /c cd /d C:\Tools\webpages-monitor && python webpages_monitor.py"
```

Angaben zur Einrichtung über die Oberfläche und weitere Hinweise findest du in:
[DOCUMENTATION_deutsch_german.md → Geplante Läufe](DOCUMENTATION_deutsch_german.md#geplante-läufe-unter-windows-aufgabenplanung).

## Ausgabe

Folgende Textdateien werden bei jedem Lauf erzeugt:

- `REPORT-of-every-run-last-3-days.txt`
  Protokollierung von jedem Lauf der letzten drei Tage.
- `REPORT-daily-summary.txt`
  Report mit einem Tagesvergleich. Geeignet, um sich diesen automatisiert per Mail zustellen zu lassen (siehe DOKUMENTATION).
- `monitored-webpages/<shortname>/captured_*.txt` 
  Alle Erfassungen werden für 48 Stunden aufbewahrt.
- `monitored-webpages/<shortname>/archive/*.txt`  
  Eine Erfassung pro Tag wird dauerhaft im Archiv abgelegt.

Aufbau der Reports und Exit-Codes: [DOCUMENTATION_deutsch_german.md → Ausgabe](DOCUMENTATION_deutsch_german.md#ausgabe).

## Sicherheit

- `webpages.json` kann Passwörter enthalten und ist in `.gitignore` ausgeschlossen – nie committen.
- `password_env` gegenüber `password` bevorzugen; so steht das Passwort nicht im Klartext in der Datei. Passwörter erscheinen nie in den Reports.

## Lizenz

[MIT](LICENSE)

## Autoren

- Pepe HB9EVT
  https://github.com/pepe-hb9evt
- Claude (Anthropic)
  (A.I. im *Large Language Model* Modus)
