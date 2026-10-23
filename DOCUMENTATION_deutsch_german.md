# Überwache deine Lieblingswebseiten

Dokumentation zum Projekt "**[Monitoring-your-favorite-webpages](https://github.com/pepe-hb9evt/Monitoring-your-favorite-webpages)**" auf GitHub.

( **English version** of this document available: [DOCUMENTATION.md](DOCUMENTATION.md) )

Dies ist eine ausführliche Dokumentation des zugehörigen Python-Skripts. Für einen kurzen Überblick konsultiere das deutschsprachige [README](README_deutsch_german.md).

## Inhalt

- [So funktioniert es](#so-funktioniert-es)
- [Webseiten-Liste (`webpages.json`)](#webseiten-liste-webpagesjson)
- [Einstellungen (`settings.json`)](#einstellungen-settingsjson)
- [Geplante Läufe unter Windows (Aufgabenplanung)](#geplante-läufe-unter-windows-aufgabenplanung)
- [Ausgabe](#ausgabe)
- [Was die aktuelle Version nicht kann](#was-die-aktuelle-version-nicht-kann)
- [Optional: Benachrichtigung mit Claude](#optional-benachrichtigung-mit-claude)

## So funktioniert es

Das Skript (`webpages_monitor.py`)

- ruft die Seiten mit `requests` ab (mit User-Agent; Weiterleitungen wird gefolgt).
- extrahiert den sichtbaren Inhalt mit BeautifulSoup/lxml: Skripte, Styles, versteckte Elemente (`hidden`, `aria-hidden="true"`, `display:none`) und Kommentare werden ignoriert.
- vergleicht **Text**, **Bilder** (inklusive Alt-Text und Hash von Inline-SVG) und **Links** getrennt.
- lädt jedes `<img>` pro Lauf einmal herunter, erzeugt einen Inhalts-Hash und speichert nur die Kenndaten (`URL | alt=… | sha1=…`). So wird auch ein Bild erkannt, das unter derselben URL ausgetauscht wurde. Siehe [Bilderkennung](#bilderkennung).
- entfernt wechselnde Bestandteile aus URLs wie `?ver=`, Session-IDs, CSRF-Tokens, Cache-Buster und den Parameter `refresh` von Download-Links (WordPress Download Manager).
- speichert `javascript:`-Links ohne ihren Code (dieser enthält oft zufällige Namen, z. B. zur Verschleierung von E-Mail-Adressen); verglichen wird nur der Link-Text.
- holt sich die Liste der zu beobachtenden Webseiten aus einer JSON-Datei, optional mit Benutzername und Passwort (HTTP Basic oder WordPress-Anmeldeformular).
- kann mit fehlerhaften Einträgen in der Webseiten-Liste und nicht erreichbaren Webseiten umgehen, sodass der Lauf nicht abbricht (Fehler werden protokolliert und die übrigen Webseiten werden trotzdem geprüft).
- speichert bei jedem erfolgreichen Abruf den sichtbaren Webseiteninhalt in eine Erfassungsdatei mit Datum und Uhrzeit im Dateinamen. Erfassungen werden 48 Stunden aufbewahrt.
- prüft für jede Webseite anhand der Erfassungsdateien, ob es Unterschiede zwischen dem jetzigen und dem vorherigen Lauf gibt, und protokolliert das Ergebnis in `REPORT-of-every-run-last-3-days.txt` (neuester Lauf stets zuoberst; Läufe, die älter als drei Tage sind, werden automatisch entfernt).
- vergleicht zudem für jede Webseite die jetzige Erfassung mit der neuesten, die mindestens 23 Stunden alt ist, und protokolliert das Ergebnis in `REPORT-daily-summary.txt` (gibt es keine Erfassung, die mindestens 23 Stunden alt ist, wird stattdessen die älteste vorhandene herangezogen).
- ist parametrierbar: Benutzerabhängige Werte (Dateinamen, Aufbewahrung, Timeout, User-Agent, …) stehen in einer optionalen `settings.json`.

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
- Ein Bild, das auf mehreren Seiten vorkommt, wird pro Lauf nur einmal heruntergeladen. HTTP-Basic-Login-Daten werden nur an Bilder auf demselben Host wie die Seite gesendet.

Vergleich: Die Zeilen werden wie Text verglichen. Fehlt auf einer Seite der Hash eines Bildes (gleiche URL und gleicher Alt-Text), etwa weil `image_hash` zwischenzeitlich ausgeschaltet war, oder ist er `?`, wird der Hash ignoriert. So erzeugt weder das Umschalten von `image_hash` noch ein vorübergehend nicht erreichbares Bild eine falsche Änderung. Gleiche URL mit zwei verschiedenen Hashes bedeutet, dass der Bildinhalt ausgetauscht wurde:

```
 [Images]
  removed: https://example-delta.com/logo.jpg | alt=Logo | sha1=3f9a1c0e7b2d4a51
  added:   https://example-delta.com/logo.jpg | alt=Logo | sha1=8c02e4f1a9b37d60
```

Nicht erkannt werden: CSS-Hintergrundbilder, `<picture><source>`, `<canvas>` und per JavaScript geladene Bilder. Bilder, die sich bei jedem Abruf ändern (Webcams, Captchas, zufällige Banner), werden bei jedem Lauf gemeldet; in diesem Fall `"image_hash": false` setzen.

## Webseiten-Liste (`webpages.json`)

Die Datei liegt im Projektordner und wird bei jedem Lauf neu eingelesen. Sie ist ein JSON-Objekt, das Kurznamen den Webseiten zuordnet. Eine kommentierte Vorlage mit allen Formaten ist [`webpages.example.json`](webpages.example.json).

### Kurzform

```json
"alpha-news": "https://example-alpha.com/de/news/"
```

### Langform

```json
"beta-dt": { "url": "https://example-beta.com/dt/" }
```

### Mit Logindaten (HTTP Basic)

#### Passwort als Umgebungsvariable gespeichert (empfohlen)

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

#### Passwort im Klartext (nicht empfohlen)

```json
"private": {
  "url": "https://example-epsilon.com/private/",
  "username": "my-user",
  "password": "my-password"
}
```

### Mit Anmeldeformular (WordPress)

Viele Vereins- und Verbandsseiten nutzen statt HTTP Basic das normale WordPress-Anmeldeformular. Mit `"login": "wordpress"` meldet sich das Skript vor dem Abruf über dieses Formular an:

```json
"members-reports": {
  "url": "https://example-eta.com/de/members/reports/",
  "login": "wordpress",
  "username": "my-user",
  "password_env": "MONITOR_PW_ETA"
}
```

- Als Adresse des Anmeldeformulars wird `<Webseite>/wp-login.php` verwendet. Verwendet die Webseite eine andere Adresse, `"login_url": "https://example-eta.com/wp-login.php"` ergänzen.
- Jede Anmeldung (gleiche `login_url` und gleicher `username`) erfolgt einmal pro Lauf; weitere Seiten derselben Webseite verwenden sie mit. Auch die Bilder der Seite werden angemeldet abgerufen.
- Wird die Anmeldung abgelehnt, steht im Report `Login failed: username or password not accepted`, und die Webseite zählt als Fehler. Wird eine Seite stattdessen auf eine Anmeldeseite umgeleitet (z. B. fehlende Berechtigung), steht `Login failed: redirected to the login page`. In beiden Fällen bleibt die letzte Kopie erhalten.
- Dieselbe Prüfung gilt auch für Webseiten ohne `login`: Leitet eine Seite plötzlich auf eine Anmeldeseite um, wird das als Fehler gemeldet, statt die Anmeldeseite zu speichern.
- Anmeldeformulare mit Captcha oder Zwei-Faktor-Anmeldung können nicht verwendet werden.

### Testläufe mit `STOP`

Für einen Test mit nur ein oder zwei Webseiten diese zuoberst in die Liste setzen und darunter einen Eintrag `STOP` einfügen. Alle Einträge nach `STOP` werden übersprungen:

```json
{
  "alpha-news": "https://example-alpha.com/de/news/",
  "STOP": "everything below is ignored",
  "beta-dt": "https://example-beta.com/dt/"
}
```

- Der Schlüssel `STOP` darf beliebig geschrieben werden (`stop`, `Stop`); der Wert ist freier Text.
- Übersprungene Webseiten werden weder abgerufen noch geprüft; ihre gespeicherten Erfassungen bleiben unverändert.
- Das Terminal zeigt z. B. `… – 2 sites (STOP in webpages.json: 28 sites skipped)`, und beide Reports beginnen mit `Note: STOP in webpages.json – … sites after STOP skipped`; ein vergessenes `STOP` fällt so auf.
- Um wieder die ganze Liste zu überwachen, die Zeile löschen oder in `_STOP` umbenennen.

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
| `login` | nein | `basic` (Standard, HTTP Basic) oder `wordpress` (WordPress-Anmeldeformular), siehe oben. |
| `login_url` | nein | Adresse des Anmeldeformulars bei `wordpress`; Standard `<Webseite>/wp-login.php`. |
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

### Einschränkung: andere Anmeldeformulare

Neben HTTP Basic wird nur das WordPress-Anmeldeformular unterstützt.

**Nicht unterstützt** werden andere Anmeldeformulare (z. B. MediaWiki, DokuWiki).

## Einstellungen (`settings.json`)

Optional. Liegt neben dem Skript; siehe [`settings.example.json`](settings.example.json). Alle Schlüssel sind optional.

| Schlüssel | Standard | Bedeutung |
|---|---|---|
| `webpages_file` | `webpages.json` | Name der Webseiten-Liste im Projektordner |
| `report_file` | `REPORT-of-every-run-last-3-days.txt` | Name der Report-Datei im Projektordner |
| `daily_report_file` | `REPORT-daily-summary.txt` | Name des Daily Reports (Tagesvergleich) |
| `daily_compare_hours` | `23` | Mindestalter der Vergleichserfassung für den Daily Report |
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

Beispiel: täglich um 06:00 Uhr. Für weitere Uhrzeiten den Befehl mit anderem Namen (`/tn`) und anderer Uhrzeit (`/st`) wiederholen. Pfade anpassen; `where python` zeigt den vollständigen Pfad zu `python.exe`.

Auf englischsprachigen Windows-Systemen heisst die Aufgabenplanung „Task Scheduler“.

### Kommandozeile (`schtasks`)

In einer Eingabeaufforderung:

```
schtasks /create /tn "Webpages Monitor 0600" /sc daily /st 06:00 /tr "cmd /c cd /d C:\Tools\webpages-monitor && python webpages_monitor.py"
```

Testen: `schtasks /run /tn "Webpages Monitor 0600"`. Löschen: `schtasks /delete /tn "Webpages Monitor 0600" /f`.

### Grafische Oberfläche

1. *Aufgabenplanung* öffnen → *Einfache Aufgabe erstellen* (oder *Aufgabe erstellen*).
2. *Trigger*: täglich; mit *Aufgabe erstellen* lassen sich mehrere Trigger für verschiedene Uhrzeiten anlegen.
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

- `webpages_monitor.py`
  Das Skript.
- `webpages.json`
  Eigene Webseiten-Liste (nicht in Git).
- `settings.json`
  Optionale Einstellungen (nicht in Git).
- `REPORT-of-every-run-last-3-days.txt`
  Protokollierung von jedem Lauf der letzten drei Tage.
- `REPORT-daily-summary.txt`
  Report mit einem Tagesvergleich, wird bei jedem Lauf neu geschrieben. Geeignet, um sich diesen automatisiert per Mail zustellen zu lassen (siehe [Optional: Benachrichtigung mit Claude](#optional-benachrichtigung-mit-claude)).
- `monitored-webpages/<shortname>/captured_<YYYY-MM-DD_HHHMM>.txt`
  Inhalt eines Abrufs (Text, IMAGES, LINKS); alle Erfassungen werden 48 Stunden aufbewahrt.
- `monitored-webpages/<shortname>/archive/<YYYY-MM-DD>.txt`
  Letzte Erfassung dieses Tages, dauerhaft im Archiv abgelegt.

### Aufbau von `REPORT-of-every-run-last-3-days.txt`

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

Neuester Lauf zuoberst; Läufe, die älter als drei Tage sind, werden beim nächsten Lauf entfernt. Der Report zeigt höchstens 15 Änderungszeilen pro Webseite (Standard, siehe `max_change_lines`).

Jeder Lauf vergleicht die neueste mit der zweitneuesten Erfassung einer Webseite. Jeder Lauf beginnt mit dem Abstand zum vorherigen Lauf (`Previous run: 47 minutes ago`; bis 99 Minuten in Minuten, ab 100 Minuten in Stunden, gerundet).

### Erfassungsdateien

Jeder erfolgreiche Abruf schreibt `captured_YYYY-MM-DD_HHHMM.txt` (z. B. `captured_2026-10-21_11H00.txt`). Erfassungen, die älter als 48 Stunden sind, werden beim nächsten Lauf gelöscht; die beiden neuesten Erfassungen einer Webseite bleiben immer erhalten. Das Archiv bewahrt dauerhaft eine Kopie pro Tag auf (die letzte des Tages).

### Aufbau von `REPORT-daily-summary.txt`

Wird nach jedem Lauf neu geschrieben, im gleichen Aufbau wie ein Lauf des Reports, mit der Kopfzeile `=== Daily report YYYY-MM-DD HH:MM ===`. Für jede Webseite wird die neueste Erfassung mit der neuesten aller Erfassungen verglichen, die mindestens 23 Stunden alt sind; gibt es keine solche, mit der ältesten vorhandenen. Die erste Zeile nennt das Alter der Vergleichserfassung, z. B. `Newest capture compared with the capture from 24 hours ago.`; war keine Erfassung alt genug, wird `(oldest capture available)` ergänzt. Webseiten, die im aktuellen Lauf fehlgeschlagen sind, stehen unter „No comparison possible“.

### Terminal-Fenster

Während des Laufs zeigt das Skript, welche Webseite gerade abgerufen wird, und das Ergebnis:

```
Webpages monitor – run 2026-10-22 11:00 – 26 sites

[ 1/26] https://example-alpha.com/de/news/ ... no change (2.1 s)
[ 2/26] https://example-beta.com/dt/ ... CHANGED (4.8 s)
[ 3/26] https://example-delta.com/offline/ ... ERROR: timeout (45 s) (45.0 s)
[ 4/26] https://example-eta.com/de/members/reports/ ... login... no change (3.3 s)

Writing reports ... done
.....
```

- `login...` erscheint bei der Webseite, bei der sich das Skript über ein Anmeldeformular anmeldet.
- Nach „done“ folgen fünf Punkte, einer pro Sekunde, damit die letzten Zeilen noch lesbar sind, bevor sich das Fenster schliesst.
- Sonst erscheint nichts im Terminal; alle Details stehen in den Report-Dateien. Mit `console_progress` auf `false` werden Anzeige und Pause abgeschaltet.

### Exit-Codes

| Code | Bedeutung |
|---|---|
| 0 | Keine Änderung und keine Fehler (auch bei Erstläufen) |
| 1 | Änderung, Fehler bei einer Webseite oder Fehler in einem Listen- oder Einstellungseintrag |
| 2 | Webseiten-Liste unbrauchbar oder Programmfehler |

## Was die aktuelle Version nicht kann

Die folgenden Punkte unterstützt das Skript bewusst oder vorläufig nicht:

### Abruf der Webseiten

- **Kein JavaScript:** Erfasst wird nur das HTML, das der Server ausliefert. Inhalte, die erst im Browser per JavaScript nachgeladen werden (z. B. dynamische Listen, Kalender-Widgets, Single-Page-Apps), fehlen in den Erfassungen.
- **Keine eingebetteten Inhalte:** Inhalte in `<iframe>`-Elementen (z. B. eingebettete Karten, Videos, fremde Seiten) werden nicht geladen.
- **Nur HTML-Seiten:** PDF-, Word- oder andere Dateien werden nicht inhaltlich überwacht; erfasst wird nur der Link darauf. Liefert eine URL keinen HTML-Inhalt, wird das als Fehler gemeldet.
- **Kein Bot-Schutz:** Seiten mit Captcha oder Browser-Prüfung (z. B. „Checking your browser…“) können nicht zuverlässig abgerufen werden; gespeichert wird dann allenfalls die Prüfseite statt des eigentlichen Inhalts.
- **Nacheinander, nicht parallel:** Die Webseiten werden einzeln abgerufen. Nicht erreichbare Seiten verlängern den Lauf jeweils bis zum Timeout (Standard 45 Sekunden).
- **Keine Prüfung von `robots.txt`:** Die Abrufhäufigkeit sollte deshalb massvoll gewählt werden.

### Anmeldung (Login)

- Unterstützt werden nur **HTTP Basic** und das **WordPress-Anmeldeformular**.
- **Nicht unterstützt** werden andere Anmeldeformulare (z. B. MediaWiki, DokuWiki, Joomla), Anmeldungen über Drittanbieter („Mit Google/Microsoft anmelden“, SSO), Zwei-Faktor-Anmeldung und Anmeldeformulare mit Captcha.
- Anmeldungen aus dem eigenen Browser (Cookies) können nicht übernommen werden.

### Vergleich und Darstellung der Änderungen

- **Keine Ortsangabe:** Gemeldet wird, *was* sich geändert hat (Zeile entfernt/hinzugefügt), nicht *wo* auf der Webseite.
- **Zeilen statt Wörter:** Verglichen werden ganze Zeilen. Ändert sich ein Wort, erscheint die ganze Zeile als „removed“ und „added“. Verschobene Abschnitte erscheinen ebenfalls als entfernt und neu hinzugefügt.
- **Bilder nur per Hash:** Erkannt wird nur, *dass* sich ein Bild geändert hat. Es gibt keine Anzeige des Bildes vorher/nachher und keinen bildlichen Vergleich.
- **Nicht erkannte Bilder:** CSS-Hintergrundbilder, `<picture><source>`, `<canvas>` und per JavaScript geladene Bilder (siehe [Bilderkennung](#bilderkennung)).
- **Wechselnde Bilder:** Bilder, die sich bei jedem Abruf ändern (Webcams, Zufallsbanner), werden bei jedem Lauf als Änderung gemeldet. Abhilfe: `ignore` für dieses Bild oder `"image_hash": false`.
- **Keine Gestaltung:** Änderungen an Layout, Farben, Schriften oder Reihenfolge per CSS werden nicht erkannt; es gibt keine Screenshots.
- **Versteckte Inhalte:** Erkannt werden nur Elemente, die direkt im HTML versteckt sind (`hidden`, `aria-hidden="true"`, `display:none` im `style`-Attribut). Inhalte, die über CSS-Klassen versteckt sind (z. B. zugeklappte Menüs), werden trotzdem erfasst und verglichen.
- **Gekürzte Meldungen:** Pro Webseite zeigt der Report höchstens `max_change_lines` Änderungszeilen (Standard 15); der Rest wird nur gezählt.

### Benachrichtigung und Betrieb

- **Kein eigener Versand:** Das Skript schreibt nur Dateien. Mails oder andere Benachrichtigungen müssen separat eingerichtet werden (siehe [Optional: Benachrichtigung mit Claude](#optional-benachrichtigung-mit-claude)).
- **Kein eigener Zeitplan:** Das Skript läuft nur, wenn es gestartet wird (z. B. über die Aufgabenplanung). Der Computer muss dafür eingeschaltet und mit dem Internet verbunden sein.
- **Keine Bedienoberfläche:** Webseiten-Liste und Einstellungen werden direkt in den JSON-Dateien bearbeitet.
- **Begrenzter Verlauf:** Der Report umfasst die letzten drei Tage, der Daily Report nur den letzten Tagesvergleich. Ältere Stände liegen nur im Archiv und müssen bei Bedarf von Hand verglichen werden.
- **Archiv ohne Bereinigung:** Das Archiv (`archive/`) wächst dauerhaft um eine Datei pro Webseite und Tag; es wird nicht automatisch aufgeräumt.
- **Plattform:** Entwickelt und getestet unter Windows (Aufgabenplanung, Umgebungsvariablen mit `setx`). Das Skript selbst läuft auf jedem System mit Python 3.9 oder neuer; für andere Systeme gibt es aber keine Anleitung zur zeitgesteuerten Ausführung.

Aktuell ist vom Autor keine Weiterentwicklung dieses Projekts geplant, um gewisse Einschränkungen zu beseitigen. Aber vielleicht willst du ja forken und es weiterentwickeln.

## Optional: Benachrichtigung mit Claude

Das Skript selbst versendet nichts. Bei Bedarf lässt sich in der Claude-Desktop-App eine geplante Aufgabe einrichten, die `REPORT-daily-summary.txt` nach den Läufen liest (z. B. 10 Minuten später) und per Mail versendet.
