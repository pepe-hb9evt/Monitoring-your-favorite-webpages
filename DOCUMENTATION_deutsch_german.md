# Monitoring your favorite webpages

**Überwache deine Lieblingswebseiten**



# Dokumentation



← Zurück zum [README](README_deutsch_german.md) · English version: [DOCUMENTATION.md](DOCUMENTATION.md)

## Inhalt

- [So funktioniert es](#so-funktioniert-es)
- [Webseiten-Liste (`webpages.json`)](#webseiten-liste-webpagesjson)
- [Einstellungen (`settings.json`)](#einstellungen-settingsjson)
- [Geplante Läufe unter Windows (Aufgabenplanung)](#geplante-läufe-unter-windows-aufgabenplanung)
- [Ausgabe](#ausgabe)
- [Optional: Benachrichtigung mit Claude](#optional-benachrichtigung-mit-claude)

## So funktioniert es

- Ruft die Seiten mit `requests` ab (mit User-Agent, Weiterleitungen werden gefolgt).
- Extrahiert den sichtbaren Inhalt mit BeautifulSoup/lxml: Skripte, Styles, versteckte Elemente (`hidden`, `aria-hidden="true"`, `display:none`) und Kommentare werden ignoriert.
- Vergleicht **Text**, **Bilder** (inklusive Alt-Text und Hash von Inline-SVG) und **Links** getrennt.
- Bildinhalt: Jedes `<img>` wird pro Lauf einmal heruntergeladen und mit einem Inhalts-Hash gespeichert (`URL | alt=… | sha1=…`). So wird auch ein Bild erkannt, das unter **derselben URL** ausgetauscht wurde. Siehe [Bilderkennung](#bilderkennung).
- Wechselnde Bestandteile wie `?ver=`, Session-IDs, CSRF-Tokens und Cache-Buster werden aus URLs entfernt.
- `javascript:`-Links werden ohne ihren Code gespeichert (er enthält oft zufällige Namen, z. B. zur Verschleierung von E-Mail-Adressen); verglichen wird nur der Link-Text.
- Webseiten-Liste in einer JSON-Datei, optional mit Benutzername und Passwort (HTTP Basic).
- Fehlerhafte Einträge und nicht erreichbare Webseiten brechen den Lauf nicht ab; sie werden protokolliert, und die übrigen Webseiten werden trotzdem geprüft.
- Report der letzten drei Tage, neuester Lauf zuoberst; ältere Läufe werden automatisch entfernt.
- Jeder Lauf speichert eine Erfassungsdatei mit Datum und Uhrzeit im Namen; Erfassungen werden 48 Stunden aufbewahrt.
- Daily Report `daily-report.txt`: wird nach jedem Lauf neu geschrieben; vergleicht die neueste Erfassung mit der neuesten Erfassung, die mindestens 24 Stunden alt ist.
- Benutzerabhängige Werte (Dateinamen, Aufbewahrung, Timeout, User-Agent, …) stehen in einer optionalen `settings.json`.

### Bilderkennung

Jedes Bild ist eine Zeile im Abschnitt `=== IMAGES ===` einer Erfassungsdatei:

```
https://example-delta.com/logo.jpg | alt=Logo | sha1=3f9a1c0e7b2d4a51
https://example-delta.com/team.jpg | alt=Team | sha1=?
inline-svg | sha1=8c02e4f1a9b37d60
```

- `<img>`: URL aus `src`, `data-src` oder dem ersten Eintrag von `srcset`; `sha1` = die ersten 16 Hex-Ziffern des SHA1 der Bilddaten (es werden höchstens `image_max_bytes` gelesen).
- Inline-`<svg>`: Hash über den SVG-Code.
- `sha1=?`: Das Bild konnte nicht heruntergeladen werden (Fehler, Timeout, kein Bild-Content-Type, mehr als `image_max_count` Bilder auf der Seite).
- Ignoriert: `data:`-Bilder, Tracking-Pixel (1×1, `pixel`, `spacer`, `blank.gif`), versteckte Elemente.
- Ein Bild, das auf mehreren Seiten vorkommt, wird pro Lauf nur einmal heruntergeladen. Login-Daten werden nur an Bilder auf demselben Host wie die Seite gesendet.

Vergleich: Die Zeilen werden wie Text verglichen. Fehlt auf einer Seite der Hash eines Bildes (gleiche URL und gleicher Alt-Text), etwa bei Erfassungen aus der Zeit vor dieser Funktion, oder ist er `?`, wird der Hash ignoriert. So erzeugt weder die Umstellung noch ein vorübergehend nicht erreichbares Bild eine falsche Änderung. Gleiche URL mit zwei verschiedenen Hashes bedeutet, dass der Bildinhalt ausgetauscht wurde:

```
 [Images]
  removed: https://example-delta.com/logo.jpg | alt=Logo | sha1=3f9a1c0e7b2d4a51
  added:   https://example-delta.com/logo.jpg | alt=Logo | sha1=8c02e4f1a9b37d60
```

Nicht erkannt werden: CSS-Hintergrundbilder, `<picture><source>`, `<canvas>` und per JavaScript geladene Bilder. Bilder, die sich bei jedem Abruf ändern (Webcams, Captchas, zufällige Banner), werden bei jedem Lauf gemeldet; in diesem Fall `"image_hash": false` setzen.

## Webseiten-Liste (`webpages.json`)

Die Datei liegt im Projektordner und wird bei **jedem Lauf** neu eingelesen. Sie ist ein JSON-Objekt, das Kurznamen den Webseiten zuordnet. Eine kommentierte Vorlage mit allen Formaten ist [`webpages.example.json`](webpages.example.json).

### Kurzform

```json
"alpha-news": "https://example-alpha.com/de/news/"
```

### Langform

```json
"beta-dt": { "url": "https://example-beta.com/dt/" }
```

### Mit Login (HTTP Basic), Passwort aus einer Umgebungsvariablen (empfohlen)

```json
"internal": {
  "url": "https://example-epsilon.com/internal/",
  "username": "my-user",
  "password_env": "MONITOR_PW_INTERNAL"
}
```

Variable einmalig setzen (danach ist ein neues Terminal oder eine neue Anmeldung nötig):

```
setx MONITOR_PW_INTERNAL "secret-password"
```

### Mit Login, Passwort im Klartext

```json
"private": {
  "url": "https://example-epsilon.com/private/",
  "username": "my-user",
  "password": "my-password"
}
```

### Kommentare

JSON kennt keine Kommentare. Schlüssel, die mit `_` beginnen, werden deshalb ignoriert:

```json
"_comment": "Eine Notiz"
```

### Regeln

| Feld | Pflicht | Beschreibung |
|---|---|---|
| Kurzname (Schlüssel) | ja | Buchstaben, Ziffern, `.` `_` `-`. Gleichzeitig der Name des Datenordners in `monitored-webpages/`. Ein neuer Name beginnt eine neue Historie. |
| `url` | ja | Muss mit `http://` oder `https://` beginnen. |
| `username` | nein | Nur zusammen mit `password` oder `password_env`. |
| `password` | nein | Passwort im Klartext. |
| `password_env` | nein | Name einer Umgebungsvariablen mit dem Passwort; hat Vorrang vor `password`. |
| `accept_status` | nein | Liste von HTTP-Fehlercodes, deren Inhalt trotzdem verwendet wird, siehe unten. |
| `ignore` | nein | Zeilen, die beim Vergleich ausgelassen werden, siehe unten. |

Ein fehlerhafter Eintrag wird übersprungen und im Report vermerkt. Fehlt die Datei, ist sie kein gültiges JSON oder enthält sie keine einzige gültige Webseite, endet der Lauf kontrolliert mit einem Protokolleintrag.

### `accept_status`

Optional pro Webseite: `"accept_status": [500]` verwendet den Inhalt auch dann, wenn der Server mit einem dieser HTTP-Fehlercodes antwortet (für Server, die eine normale Seite mit falschem Statuscode ausliefern). Im Report erscheint dann ein Hinweis. Nur für Webseiten verwenden, bei denen das bekannt ist; sonst würden echte Fehlerseiten als Inhalt gespeichert.

### `ignore`

Optional pro Webseite: Zeilen, die sich ständig ändern (Solar-Banner, Zähler, „Letzte Aktualisierung“), lassen sich vom Vergleich ausnehmen, getrennt nach Abschnitt der Erfassungsdatei:

```json
"zeta-home": {
  "url": "https://example-zeta.com/",
  "ignore": {
    "images": ["hamqsl.com/solarbc.php"],
    "text": ["re:^Letzte Aktualisierung:"],
    "links": ["/kalender?"]
  }
}
```

- `text`, `images`, `links` sind optional; jeder ist eine Liste von Mustern.
- Ein Muster ist eine Teilzeichenkette (Gross-/Kleinschreibung egal). Mit dem Präfix `re:` ist es ein regulärer Ausdruck (Python-Syntax, Gross-/Kleinschreibung egal, trifft irgendwo in der Zeile; mit `^`/`$` verankern).
- Eine passende Zeile wird vor dem Vergleich aus **beiden** Erfassungen entfernt; sie erscheint also weder als „removed“ noch als „added“. Hat sich sonst nichts geändert, gilt die Webseite als unverändert (auch im Daily Report).
- Die Erfassungsdateien bleiben vollständig; die Regeln wirken nur beim Vergleich. Eine neue Regel wirkt deshalb auch auf bestehende Erfassungen, und wird sie entfernt, gilt wieder der volle Vergleich.
- Fehlerhafte Regeln (falscher Typ, ungültiger regulärer Ausdruck, unbekannter Schlüssel) werden übersprungen und im Report vermerkt; die Webseite selbst wird weiter überwacht.

### Einschränkung: kein Session-Login

Anmeldeformulare auf der Seite selbst (Session-Login, z. B. DokuWiki oder WordPress) werden nicht unterstützt, nur HTTP Basic.

## Einstellungen (`settings.json`)

Optional. Liegt neben dem Skript; siehe [`settings.example.json`](settings.example.json). Alle Schlüssel sind optional.

| Schlüssel | Standard | Bedeutung |
|---|---|---|
| `webpages_file` | `webpages.json` | Name der Webseiten-Liste im Projektordner |
| `report_file` | `report-last-3-days.txt` | Name der Report-Datei im Projektordner |
| `daily_report_file` | `daily-report.txt` | Name des Daily Reports (24-Stunden-Vergleich) |
| `daily_compare_hours` | `24` | Mindestalter der Vergleichserfassung für den Daily Report |
| `capture_keep_hours` | `48` | Wie lange Erfassungsdateien aufbewahrt werden (Stunden) |
| `report_days` | `3` | Wie viele Tage Läufe im Report bleiben |
| `max_change_lines` | `15` | Änderungszeilen pro Webseite im Report |
| `timeout_seconds` | `45` | Zeitlimit pro Abruf |
| `user_agent` | Chrome-ähnliche Zeichenkette | Browser-Kennung, die bei jedem Abruf gesendet wird |
| `ignored_url_params` | `ver`, `sid`, … | URL-Parameter, die beim Vergleich ignoriert werden |
| `image_hash` | `true` | Bilder herunterladen und ihren Inhalt vergleichen (`false`: nur URL und Alt-Text) |
| `image_max_count` | `50` | Max. heruntergeladene Bilder pro Seite |
| `image_max_bytes` | `5000000` | Max. gelesene Bytes pro Bild |
| `image_timeout_seconds` | `15` | Zeitlimit pro Bild |
| `console_progress` | `true` | Fortschritt pro Webseite im Terminal-Fenster anzeigen |

Ungültige Werte oder unbekannte Schlüssel brechen einen Lauf nie ab: Es gilt der Standardwert, und im Report erscheint ein Hinweis.

## Geplante Läufe unter Windows (Aufgabenplanung)

Beispiel: täglich um 05:00, 11:00, 17:00 und 23:00 Uhr. Pfade anpassen; `where python` zeigt den vollständigen Pfad zu `python.exe`.

Auf englischsprachigen Windows-Systemen heisst die Aufgabenplanung „Task Scheduler“.

### Kommandozeile (`schtasks`)

In einer Eingabeaufforderung:

```
schtasks /create /tn "Webpages Monitor 0600" /sc daily /st 06:00 /tr "cmd /c cd /d C:\Tools\webpages-monitor && python webpages_monitor.py"
schtasks /create /tn "Webpages Monitor 1100" /sc daily /st 11:00 /tr "cmd /c cd /d C:\Tools\webpages-monitor && python webpages_monitor.py"
schtasks /create /tn "Webpages Monitor 1700" /sc daily /st 17:00 /tr "cmd /c cd /d C:\Tools\webpages-monitor && python webpages_monitor.py"
schtasks /create /tn "Webpages Monitor 2300" /sc daily /st 23:00 /tr "cmd /c cd /d C:\Tools\webpages-monitor && python webpages_monitor.py"
```

Testen: `schtasks /run /tn "Webpages Monitor 0600"`. Löschen: `schtasks /delete /tn "Webpages Monitor 0600" /f`.

### Grafische Oberfläche

1. *Aufgabenplanung* öffnen → *Einfache Aufgabe erstellen* (oder *Aufgabe erstellen*).
2. *Trigger*: täglich; mit *Aufgabe erstellen* lassen sich mehrere Trigger für die vier Uhrzeiten anlegen.
3. *Aktion*: *Programm starten*
   - Programm/Skript: vollständiger Pfad zu `python.exe`
   - Argumente: `webpages_monitor.py`
   - Starten in: der Projektordner
4. Unter *Einstellungen*: *Aufgabe so schnell wie möglich nach einem verpassten Start ausführen* aktivieren.

### Hinweise

- „Nur ausführen, wenn der Benutzer angemeldet ist“ genügt, wenn der Computer läuft. Damit die Aufgabe auch ohne Anmeldung läuft, braucht sie ein gespeichertes Passwort; Umgebungsvariablen für `password_env` stehen dann nur zur Verfügung, wenn sie als Benutzer- oder Systemvariablen des Kontos gesetzt sind, das die Aufgabe ausführt.
- Der Computer braucht während des Laufs eine Internetverbindung.

## Ausgabe

### Dateien

Alles liegt im Projektordner (der Ordner `monitored-webpages` wird bei Bedarf automatisch angelegt):

```
webpages_monitor.py
webpages.json                 (eigene Webseiten-Liste, nicht in Git)
settings.json                 (optional, nicht in Git)
report-last-3-days.txt        Report der letzten drei Tage
daily-report.txt              24-Stunden-Vergleich (bei jedem Lauf neu geschrieben)
monitored-webpages/<shortname>/captured_<YYYY-MM-DD_HHHMM>.txt  Inhalt eines Laufs (Text, IMAGES, LINKS), 48 Stunden aufbewahrt
monitored-webpages/<shortname>/archive/<date>.txt               letzte Erfassung dieses Tages, dauerhaft aufbewahrt
```

### Aufbau von `report-last-3-days.txt`

Der Report selbst ist auf Englisch:

```
=== Run 2026-10-21 06:00 ===

Previous run: 7 hours ago

No comparison possible for:

https://example-delta.com/offline/
ERROR: URL not reachable: HTTP error 404 Not Found


Changes were detected on the following webpages:

https://example-gamma.com/doku.php
Changed
 [Text]
  removed: old text
  added:   new text


The following webpages are unchanged:
-  https://example-alpha.com/de/news/
-  https://example-beta.com/dt/

Run finished: 4 sites processed, 1 changed, 1 errors, 0 first runs, 0 list/settings errors
```

Neuester Lauf zuoberst; Läufe, die älter als drei Tage sind, werden beim nächsten Lauf entfernt. Der Report zeigt höchstens 15 Änderungszeilen pro Webseite.

Jeder Lauf vergleicht die neueste mit der zweitneuesten Erfassung einer Webseite. Jeder Lauf beginnt mit dem Abstand zum vorherigen Lauf (`Previous run: 47 minutes ago`; bis 99 Minuten in Minuten, ab 100 Minuten in Stunden, gerundet).

### Erfassungsdateien

Jeder erfolgreiche Abruf schreibt `captured_YYYY-MM-DD_HHHMM.txt` (z. B. `captured_2026-10-21_11H00.txt`). Erfassungen, die älter als 48 Stunden sind, werden beim nächsten Lauf gelöscht; die beiden neuesten Erfassungen einer Webseite bleiben immer erhalten. Das Archiv bewahrt dauerhaft eine Kopie pro Tag auf. Beim ersten Lauf nach dem Update wird eine vorhandene `current.txt` zur Erfassungsdatei (Uhrzeit aus dem Dateidatum), und `previous.txt` wird gelöscht.

### Aufbau von `daily-report.txt`

Wird nach jedem Lauf neu geschrieben, im gleichen Aufbau wie ein Lauf des Reports, mit der Kopfzeile `=== Daily report YYYY-MM-DD HH:MM ===`. Für jede Webseite wird die neueste Erfassung mit der neuesten Erfassung verglichen, die mindestens 24 Stunden alt ist; gibt es keine solche, mit der ältesten vorhandenen. Die erste Zeile nennt das Alter der Vergleichserfassung, z. B. `Newest capture compared with the capture from 24 hours ago.`; unter 23 Stunden wird `(oldest capture available)` ergänzt. Webseiten, die im aktuellen Lauf fehlgeschlagen sind, stehen unter „No comparison possible“.

### Terminal-Fenster

Während des Laufs zeigt das Skript, welche Webseite gerade abgerufen wird, und das Ergebnis:

```
Webpages monitor – run 2026-10-22 11:00 – 26 sites

[ 1/26] https://example-alpha.com/de/news/ ... no change (2.1 s)
[ 2/26] https://example-beta.com/dt/ ... CHANGED (4.8 s)
[ 3/26] https://example-delta.com/offline/ ... ERROR: timeout (45 s) (45.0 s)

Writing reports ... done
```

Sonst erscheint nichts im Terminal; alle Details stehen in den Report-Dateien. Mit `console_progress` auf `false` wird die Anzeige abgeschaltet.

### Exit-Codes

| Code | Bedeutung |
|---|---|
| 0 | Alles unverändert |
| 1 | Änderung, Fehler bei einer Webseite oder Fehler in einem Listen- oder Einstellungseintrag |
| 2 | Webseiten-Liste unbrauchbar oder Programmfehler |

## Optional: Benachrichtigung mit Claude

Das Skript selbst versendet nichts. Bei Bedarf lässt sich in der Claude-Desktop-App eine geplante Aufgabe einrichten, die `report-last-3-days.txt` nach den Läufen liest (z. B. 10 Minuten später) und Änderungen meldet.
