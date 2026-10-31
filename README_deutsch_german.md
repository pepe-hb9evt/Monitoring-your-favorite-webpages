# Überwache deine Lieblingswebseiten

README zum Projekt "**[Monitoring-your-favorite-webpages](https://github.com/pepe-hb9evt/Monitoring-your-favorite-webpages)**" auf GitHub.

( English version of this document available: [README.md](README.md) )

<br>

## Beschreibung

Dieses Python-Skript überwacht deine Lieblingswebseiten und informiert, wenn Änderungen am **sichtbaren** Inhalt (Text, Bilder, Links) detektiert worden sind.

Das Skript arbeitet deine Liste von Webseiten ab und speichert bei jedem Lauf den aktuellen sichtbaren Inhalt jeder Webseite und vergleicht ihn mit der letzten Speicherung. Danach werden zwei Report-Dateien geschrieben, in denen für jede Webseite aufgelistet wird, ob Änderungen festgestellt worden sind und wenn ja, was sich konkret geändert hat. Optional wirst du danach per Mail informiert.

Dazu wird ein PC/Notebook benötigt, der rund um die Uhr oder zumindest tagsüber ständig läuft und mit dem Internet verbunden ist.

Dieses Projekt ist - per heutigem Stand - sehr spartanisch umgesetzt. Insbesondere die Mails sind von der Darstellung her nicht das Gelbe vom Ei. Zudem hat dieses Projekt diverse Einschränkungen (siehe nachfolgend im gleichnamigen Kapitel).

<br>

### Benutzungsanleitung

Dieses README gibt einen kompakten Überblick. Für die vollständige Referenz konsultiere **[DOCUMENTATION_deutsch_german.md](DOCUMENTATION_deutsch_german.md)**.

<br>

## Funktionen

- Vergleicht sichtbaren Text, Bilder und Links getrennt. Skripte, versteckte Elemente und wechselnde URL-Bestandteile werden hingegen ignoriert.
- Erkennt ausgetauschte Bilder, auch bei unveränderter Bild-URL.
- Die zu prüfenden Webseiten werden in einer JSON-Datei erfasst, optional auch mit den Zugangsdaten für ein HTTP-Basic-Login oder das WordPress-Anmeldeformular.
- Leitet eine Webseite auf eine Anmeldeseite um, die nicht passiert werden kann, wird das als Fehler gemeldet, statt die Anmeldeseite zu speichern.
- Das Terminal-Fenster zeigt während des Laufs, welche Webseite gerade abgerufen wird, und das Ergebnis.
- Für Testläufe beendet ein Eintrag `STOP` in der Webseiten-Liste die Liste; alle nachfolgenden Einträge werden übersprungen.
- Fehlerhafte Einträge oder nicht erreichbare Webseiten brechen den Lauf nie ab.
- Stündlich gestartet, prüft das Skript nur alle N Stunden (`check_interval_hours`, z. B. 05:00, 11:00, 17:00, 23:00 Uhr) und holt verpasste Prüfungen nach.
- Dev-Modus: zeigt auch bei den fensterlosen geplanten Läufen ein Terminal-Fenster.
- Es werden bei jedem Lauf zwei Textdateien geschrieben:

  - `REPORT-of-every-run-last-3-days.txt`: alle Läufe der letzten drei Tage, neuester zuoberst.

  - `REPORT-daily-summary.txt`: Tagesvergleich (neueste Erfassung mit jener, die mindestens 23 Stunden alt ist).
- Optional kannst du dich per Mail über erfolgte Änderungen an den von dir überwachten Webseiten informieren lassen. Über das parametrierbare Prüfungsintervall definiert sich auch, in welchem Rhythmus du ein solches Mail bekommst.

In `settings.json` können diverse Parameter verändert werden (Dateinamen, Aufbewahrung, Timeout, User-Agent, Prüfintervall, Mail, Dev-Modus, …).

<br>

## Einschränkungen

Wie bereits in der Einleitung darauf hingewiesen, ist dieses Tool sehr spartanisch in seiner Funktionalität (aber erfüllt jenen Zweck, den sich der Autor als Ziel gesetzt hat). Die wesentlichen Einschränkungen sind:

- **Abruf:** Erfasst wird nur das vom Server gelieferte HTML – ohne JavaScript-Inhalte, `<iframe>`-Inhalte und ohne den Inhalt von PDF- oder Word-Dateien. Seiten mit Captcha oder Browser-Prüfung lassen sich nicht zuverlässig überwachen.
- **Login:** Nur HTTP-Basic-Login und das WordPress-Anmeldeformular; keine anderen Anmeldeformulare, kein „Mit Google/Microsoft anmelden“, keine Zwei-Faktor-Anmeldung, kein Captcha.
- **Vergleich:** Gemeldet wird, *was* sich geändert hat (ganze Zeilen), nicht *wo* auf der Webseite. Bilder werden nur über ihren Hash-Wert verglichen: Erkannt wird, *dass* sich ein Bild geändert hat, aber es gibt keine Anzeige vorher/nachher. Änderungen an Layout, Farben oder Schriften werden nicht erkannt.
- **Betrieb:** Das Skript muss jede Stunde gestartet werden (z. B. über die Windows-Aufgabenplanung, `install_task.ps1`); es entscheidet dann selbst, zu welchen Stunden geprüft wird. Benachrichtigung nur per Mail. Der Report reicht drei Tage zurück; das Archiv wird nicht automatisch aufgeräumt.
- **Mail:** Dass sich was geändert hat und was sich geändert hat, geht aus dem Mail klar hervor. Abgesehen davon lässt die Darstellung sehr zu wünschen übrig.
- **Plattform:** Entwickelt für Windows, läuft aber auf jedem System mit Python 3.9 oder neuer.

Alle Einschränkungen im Detail: [DOCUMENTATION_deutsch_german.md → Was die aktuelle Version nicht kann](DOCUMENTATION_deutsch_german.md#was-die-aktuelle-version-nicht-kann).

Aktuell ist vom Autor keine Weiterentwicklung dieses Projekts geplant, um gewisse Einschränkungen zu beseitigen. Aber vielleicht willst du ja forken und dieses Projekt weiterentwickeln.

<br>

## Voraussetzungen

- Python 3.9 oder neuer (Windows: [python.org](https://www.python.org/downloads/), Option *Add python.exe to PATH*).
- `pip install -r requirements.txt`

<br>

## Installation

1. Die Dateien in einen Projektordner kopieren, z. B. `C:\Tools\webpages-monitor\`. Alle Daten werden in diesem Ordner gespeichert.
2. `webpages.example.json` nach `webpages.json` kopieren und die eigenen Webseiten eintragen.
3. Optional: `settings.example.json` nach `settings.json` kopieren und Werte anpassen.
4. Optional für Mail: in `settings.json` den Mail-Versand einschalten und `secrets.json` mit dem SMTP-Passwort anlegen (siehe Kapitel [Mail einrichten](#mail-einrichten)). Das Funktionieren des Mailversands kann mit `python webpages_monitor.py --test-mail` getestet werden.
5. Die gewählten Parameter testen, siehe Anleitung in Kapitel [Testen der gewählten Einstellungen](#testen-der-gewählten-einstellungen).
6. Stündliche Aufgabe registrieren, siehe Anleitung in Kapitel [Geplante Läufe (Windows)](#geplante-läufe-windows).

Der erste Lauf speichert nur einen Ausgangsstand; verglichen wird ab dem zweiten Lauf.

<br>

## Webseiten-Liste (`webpages.json`)

Die zu überwachenden Webseiten werden in `webpages.json` eingetragen:

```json
{
  "alpha-news": "https://example-alpha.com/de/news/",
  "internal": {
    "url": "https://example-echo.com/internal/",
    "username": "my-user",
    "password_env": "MONITOR_PW_INTERNAL"
  }
}
```

Alle Formate, Regeln und Optionen sind nachzulesen in:
[DOCUMENTATION_deutsch_german.md → Webseiten-Liste](DOCUMENTATION_deutsch_german.md#webseiten-liste-webpagesjson).

Enthält eine Webseite Teile, die sich bei jedem Abruf ändern (z. B. Zähler, Datum, „Ähnliche Beiträge“), meldet das Skript bei jeder Prüfung eine Änderung und verschickt entsprechend viele Mails. Solche Teile lassen sich mit der Option `ignore` pro Webseite ausblenden: [DOCUMENTATION_deutsch_german.md → `ignore`](DOCUMENTATION_deutsch_german.md#ignore).

<br>

## Mail einrichten

Ab Werk versendet das Skript keine Mails. So wird der Mail-Versand eingerichtet:

1. In `settings.json` den Versand einschalten und Server, Absender und Empfänger eintragen:

   ```json
   "mail_mode": "script",
   "mail_condition": "always",
   "smtp": { "host": "smtp.gmail.com", "port": 587, "use_starttls": true, "use_ssl": false, "username": "sender@example-alpha.com" },
   "mail": { "sender": "sender@example-alpha.com", "recipients": ["recipient@example-bravo.com"], "subject_prefix": "[Webpage Monitoring]" }
   ```

   `"mail_condition": "always"` versendet nach jeder Prüfung eine Mail, `"on_change"` nur bei einer Änderung oder einem Fehler.
2. `secrets.example.json` nach `secrets.json` kopieren und das SMTP-Passwort eintragen. Bei Gmail ist das ein *App-Passwort* (Google-Konto → Sicherheit → Bestätigung in zwei Schritten → App-Passwörter), nicht das normale Kontopasswort.
3. Testen: `python webpages_monitor.py --test-mail` oder im Menü `Menu for webpages-monitor-py.bat` den Punkt *Send test mail* wählen.

So sieht der Anfang einer Mail aus:

```
Betreff: [Webpage Monitoring] 1 changed, 0 errors since 4 hours

This run:      1 changed, 0 errors since last run 4 hours ago
Daily report:  2 changed, 0 without comparison
```

Danach folgen die Webseiten mit neuen Infos bzw. mit Fehlern in diesem Lauf und anschliessend der Daily Report.

Alle Details: [DOCUMENTATION_deutsch_german.md → Mail-Versand durch das Skript](DOCUMENTATION_deutsch_german.md#mail-versand-durch-das-skript).

<br>

## Geplante Läufe (Windows)

#### Windows-Aufgabenplanung

Soll das Skript automatisiert aufgerufen werden, muss man hierzu das Python-Skript in der Windows-Aufgabenplanung registrieren. Der Auftrag ist so formuliert, dass dann das Skript ein Mal pro Stunde aufgerufen wird (Dies ist nur der periodische Aufruf. Ob tatsächlich eine Prüfung und Mail-Versand stattfindet, hängt unter anderem vom parametrierbaren Prüfrhythmus ab). Das Terminal-Fenster wird bei diesem Aufruf nicht sichtbar (ausser der dev-Modus ist aktiviert, vgl. unten).

#### Initiierung / Stoppen

Zur Registrierung in der Windows-Aufgabenplanung wechselt man im Terminal (PowerShell) in den Projektordner und erteilt dann folgenden Befehl:

```
.\install_task.ps1
```

Erscheint eine Fehlermeldung, wonach die Ausführung von Skripts auf diesem System deaktiviert ist, so ist stattdessen dieser Befehl zu verwenden:

```
powershell -ExecutionPolicy Bypass -File .\install_task.ps1
```

Der erteilte Auftrag kann bei Bedarf direkt in der Windows-Aufgabenplanung oder mit diesem Befehl wieder gelöscht werden:

```
.\install_task.ps1 -Remove
```

beziehungsweise (vgl. oben):

```
powershell -ExecutionPolicy Bypass -File .\install_task.ps1 -Remove
```

#### Prüfrhythmus

Zu welchen Stunden tatsächlich geprüft wird, legt `settings.json` fest:

```json
"check_interval_hours": 6,
"check_anchor_hour": 5
```

Dieses Beispiel legt den Prüfrhythmus (`check_interval_hours`) auf **6 Stunden** fest und zeitlich soll die erste Prüfung (`check_anchor_hour`) um **05 Uhr** sein, wodurch sich die Prüfzeiten des restlichen Tages ergeben, also Prüfungen um 05:00, 11:00, 17:00 und 23:00 Uhr.

Verpasste Prüfungstermine, z. B. weil der PC ausgeschaltet war, holt das Skript selbst nach: Ist die letzte Prüfung beim nächsten stündlichen Start älter als der Prüfrhythmus, prüft es sofort.

#### Zusatzprüfung

Mit `"intensive_check_interval_hours": 2` werden geänderte oder nicht erreichbare Webseiten 2 Stunden später erneut geprüft (nur diese Webseiten); nur wenn dabei neue Inhalte gefunden werden, wird eine Mail versendet und es folgt eine weitere solche Prüfung, sonst endet die Zusatzprüfung bis zur nächsten regulären Prüfung. Der Wert muss kleiner sein als `check_interval_hours`; `0` schaltet die Zusatzprüfung aus.

#### Alle weiteren Infos

Alles Weitere steht in der [DOCUMENTATION_deutsch_german.md](DOCUMENTATION_deutsch_german.md).

<br>

## Testen der gewählten Einstellungen

Auszug aus `settings.json` :

```JSON
  "dev_mode": {
    "enabled": false,
    "keep_open_after_run_seconds": 20
  }
```

Setzt man "enabled" auf true, wird bei jedem Lauf das Terminal sichtbar und angezeigt, was das Skript aktuell macht.

Eine manuelle Prüfung kann ausgelöst werden

- in der Batch-Datei `Menu for webpages-monitor-py.bat` oder
- in einem Terminal-Fenster mit `python webpages_monitor.py --force`.

<br>

## Ausgabe

Folgende Textdateien werden bei jedem Lauf erzeugt:

- `REPORT-of-every-run-last-3-days.txt`
  Protokollierung von jedem Lauf der letzten drei Tage.
- `REPORT-daily-summary.txt`
  Report mit einem Tagesvergleich. Kann vom Skript selbst per Mail versendet werden (`"mail_mode": "script"`).
- `monitored-webpages/<shortname>/captured_*.txt` 
  Alle Erfassungen werden für 48 Stunden aufbewahrt. Anhand diesen wird detektiert, was sich seit letztem Lauf und innert den letzten 24 Stunden geändert hat (vgl. oben die zwei "Reports").
- `monitored-webpages/<shortname>/archive/*.txt`  
  Eine Erfassung pro Tag wird dauerhaft im Archiv abgelegt.

Aufbau der Reports und Exit-Codes: [DOCUMENTATION_deutsch_german.md → Ausgabe](DOCUMENTATION_deutsch_german.md#ausgabe).

<br>

## Sicherheit

- `webpages.json` gibt Auskunft, welche Webseiten du beobachtest, und kann Passwörter enthalten. Deshalb ist diese Datei in `.gitignore` ausgeschlossen. Niemals diese Datei committen.
- `secrets.json` enthält das SMTP-Passwort und ist ebenfalls in `.gitignore` ausgeschlossen. Niemals diese Datei committen.
- `password_env` ist gegenüber `password` zu bevorzugen, da so keine Passwörter im Klartext in der Datei stehen.
- In den Reports sind die URL der Webseiten aufgelistet, doch niemals werden Passwörter genannt.

<br>

## Lizenz

[MIT](LICENSE)

<br>

## Autoren

- Pepe HB9EVT <br>https://github.com/pepe-hb9evt
- Claude (Anthropic) <br>(A.I. im *Large Language Model* Modus)
