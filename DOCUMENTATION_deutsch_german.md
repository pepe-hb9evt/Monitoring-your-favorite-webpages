# Überwache deine Lieblingswebseiten

Dokumentation zum Projekt "**[Monitoring-your-favorite-webpages](https://github.com/pepe-hb9evt/Monitoring-your-favorite-webpages)**" auf GitHub.

( **English version** of this document available: [DOCUMENTATION.md](DOCUMENTATION.md) )

Dies ist eine ausführliche Dokumentation des zugehörigen Python-Skripts. Für einen kurzen Überblick konsultiere das deutschsprachige [README](README_deutsch_german.md).

## Inhalt

- [So funktioniert es](#so-funktioniert-es)
- [Webseiten-Liste (`webpages.json`)](#webseiten-liste-webpagesjson)
- [Einstellungen (`settings.json`)](#einstellungen-settingsjson)
- [Zeitplan: stündlicher Start und Prüfintervall](#zeitplan-stündlicher-start-und-prüfintervall)
- [Mail-Versand durch das Skript](#mail-versand-durch-das-skript)
- [Dev-Modus: sichtbares Terminal-Fenster](#dev-modus-sichtbares-terminal-fenster)
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
"bravo-dt": { "url": "https://example-bravo.com/dt/" }
```

Für was die Langform benötigt wird,  zeigen die folgenden Varianten.

### Webseiten mit Logins

Unterstützt wird das Login mit HTTP Basic sowie das WordPress-Anmeldeformular.

**Nicht unterstützt** werden andere Anmeldeformulare (z. B. MediaWiki, DokuWiki).

#### Login HTTP Basic mit Passwort als Umgebungsvariable gespeichert (empfohlen)

```json
"internal": {
  "url": "https://example-echo.com/internal/",
  "username": "my-user",
  "password_env": "MONITOR_PW_INTERNAL"
}
```

Variable einmalig setzen (danach ist ein neues Terminal oder eine neue Anmeldung nötig):

```
setx MONITOR_PW_INTERNAL "secret-password"
```

Ist die Umgebungsvariable beim Lauf nicht gesetzt, wird die Webseite übersprungen; im Report steht dann `Entry '…' skipped: environment variable '…' is not set`. Das gilt für alle Login-Arten mit `password_env`.

#### Login HTTP Basic mit Passwort im Klartext (nicht empfohlen)

```json
"private": {
  "url": "https://example-echo.com/private/",
  "username": "my-user",
  "password": "my-password"
}
```

#### Login mit Anmeldeformular (WordPress)

Viele Vereins- und Verbandsseiten nutzen statt HTTP Basic das normale WordPress-Anmeldeformular. Mit `"login": "wordpress"` meldet sich das Skript vor dem Abruf über dieses Formular an:

```json
"members-reports": {
  "url": "https://example-golf.com/de/members/reports/",
  "login": "wordpress",
  "username": "my-user",
  "password_env": "MONITOR_PW_MEMBERS"
}
```

- Als Adresse des Anmeldeformulars wird `<Webseite>/wp-login.php` verwendet. Verwendet die Webseite eine andere Adresse, `"login_url": "https://example-golf.com/wp-login.php"` ergänzen.
- Jede Anmeldung (gleiche `login_url` und gleicher `username`) erfolgt einmal pro Lauf; weitere Seiten derselben Webseite verwenden sie mit. Auch die Bilder der Seite werden angemeldet abgerufen.
- Schlägt die Anmeldung fehl, wird sie im selben Lauf nicht wiederholt: Alle Seiten mit derselben Anmeldung zählen dann als Fehler und erhalten dieselbe Meldung.
- Ist die Anmeldeseite nicht erreichbar (z. B. Zeitüberschreitung, Verbindungs- oder HTTP-Fehler), steht im Report `Login failed: URL not reachable: …` mit der genauen Ursache.
- Wird die Anmeldung abgelehnt, steht im Report `Login failed: username or password not accepted`, und die Webseite zählt als Fehler. Wird eine Seite stattdessen auf eine Anmeldeseite umgeleitet (z. B. fehlende Berechtigung), steht `Login failed: redirected to the login page`. In beiden Fällen bleibt die letzte Kopie erhalten.
- Dieselbe Prüfung gilt auch für Webseiten ohne `login`: Leitet eine Seite plötzlich auf eine Anmeldeseite um, wird das als Fehler gemeldet, statt die Anmeldeseite zu speichern.
- Anmeldeformulare mit Captcha oder Zwei-Faktor-Anmeldung können nicht verwendet werden.

### Testläufe mit `STOP`

Für einen Test mit nur ein oder zwei Webseiten diese zuoberst in die Liste setzen und darunter einen Eintrag `STOP` einfügen. Alle Einträge nach `STOP` werden übersprungen:

```json
{
  "alpha-news": "https://example-alpha.com/de/news/",
  "STOP": "everything below is ignored",
  "bravo-dt": "https://example-bravo.com/dt/"
}
```

- Der Schlüssel `STOP` darf beliebig geschrieben werden (`stop`, `Stop`); der Wert ist freier Text.
- Übersprungene Webseiten werden weder abgerufen noch geprüft; ihre gespeicherten Erfassungen bleiben unverändert.
- Das Terminal zeigt z. B. `… – 2 webpages (STOP in webpages.json: 28 webpages skipped)`, und beide Reports beginnen mit `Note: STOP in webpages.json – … webpages after STOP skipped`; ein vergessenes `STOP` fällt so auf.
- Um wieder die ganze Liste zu überwachen, die Zeile löschen oder in `_STOP` umbenennen.

### Kommentare

JSON kennt keine Kommentare. Schlüssel, die mit `_` beginnen, werden deshalb ignoriert:

```json
"_comment": "Eine Notiz"
```

Das gilt für alle JSON-Dateien des Projekts (`webpages.json`, `settings.json`, `secrets.json`) und auf jeder Ebene, z. B. auch innerhalb eines Webseiten-Eintrags, innerhalb von `ignore` oder innerhalb von `smtp`. Ein Kommentar-Schlüssel darf mehrfach vorkommen.

Jeder andere nicht erwartete Schlüssel (z. B. ein vertipptes `"pasword"`) wird ebenfalls ignoriert, aber immer im Report als `ERROR: … unknown key …` vermerkt. Der Lauf wird nicht abgebrochen, und die Webseite wird weiter überwacht.

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
| `ignore` | nein | Zeilen, die beim Vergleich ausgelassen werden, oder zu entfernende HTML-Elemente (`elements`), siehe unten. |

Ein fehlerhafter Eintrag wird übersprungen und im Report vermerkt. Unbekannte Schlüssel in einem Eintrag werden nur vermerkt; der Eintrag wird trotzdem verwendet. Fehlt die Datei, ist sie kein gültiges JSON oder enthält sie keine einzige gültige Webseite, endet der Lauf kontrolliert mit einem Protokolleintrag.

### `accept_status`

Optional pro Webseite: `"accept_status": [500]` verwendet den Inhalt auch dann, wenn der Server mit einem dieser HTTP-Fehlercodes antwortet (für Server, die eine normale Seite mit falschem Statuscode ausliefern). Im Report erscheint dann ein Hinweis. Nur für Webseiten verwenden, bei denen das bekannt ist; sonst würden echte Fehlerseiten als Inhalt gespeichert.

### `ignore`

Optional pro Webseite: Zeilen, die sich ständig ändern (Solar-Banner, Zähler, „Letzte Aktualisierung“), lassen sich vom Vergleich ausnehmen, getrennt nach Abschnitt der Erfassungsdatei:

```json
"foxtrot-home": {
  "url": "https://example-foxtrot.com/",
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

#### `ignore.elements`: ganze HTML-Bereiche entfernen

Seitenbereiche, die sich ständig ändern (z. B. ein Kasten „Ähnliche Beiträge“ oder eine Fusszeile mit Zählern), lassen sich als Ganzes entfernen, mit einer Liste von CSS-Selektoren:

```json
"hotel-blog": {
  "url": "https://example-hotel.com/blog/",
  "ignore": {
    "elements": ["div.source-footer", "div.prop-list"]
  }
}
```

- Jedes passende Element wird **mitsamt Inhalt** (bis zum zugehörigen schliessenden Tag, inklusive verschachtelter Elemente) entfernt, bevor Text, Bilder und Links extrahiert werden.
- Selektoren: CSS-Syntax wie im Browser, z. B. `div.klassenname`, `#id`, `footer .widget`, `div[data-x="y"]`. `div.prop-list` trifft jedes `<div>`, dessen `class` `prop-list` enthält.
- Anders als `text`/`images`/`links` wirkt diese Regel **bei der Extraktion**: Die entfernten Bereiche stehen nicht mehr in den Erfassungsdateien. Nach dem Hinzufügen (oder Entfernen) einer solchen Regel meldet der erste Lauf deshalb einmalig eine Änderung. Wer das vermeiden will, löscht vorher die alten Erfassungen der Webseite in `monitored-webpages\<Kurzname>`; der nächste Lauf ist dann ein Erstlauf.
- Ungültige Selektoren werden übersprungen und im Report vermerkt; die Webseite selbst wird weiter überwacht.

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
| `check_interval_hours` | `1` | Prüfung alle N Stunden: `1`, `2`, `3`, `4`, `6`, `8`, `12` oder `24` (siehe [Zeitplan](#zeitplan-stündlicher-start-und-prüfintervall)) |
| `check_anchor_hour` | `0` | Stunde (0–23), ab der das Prüfraster beginnt |
| `intensive_check_interval_hours` | `0` | `0` = aus; N = geänderte Webseite nach N Stunden erneut prüfen (siehe [Intensive Prüfung](#intensive-prüfung-geänderter-webseiten)) |
| `mail_mode` | `none` | `none` = das Skript versendet keine Mail, `script` = das Skript versendet den Daily Report per SMTP (siehe [Mail](#mail-versand-durch-das-skript)) |
| `mail_condition` | `always` | `always` = Mail nach jeder Prüfung, `on_change` = nur wenn eine Änderung oder ein Fehler festgestellt wurde |
| `smtp` | Gmail, Port 587, STARTTLS | SMTP-Server: `host`, `port`, `use_starttls`, `use_ssl`, `username` |
| `mail` | – | `sender`, `recipients` (Liste), `subject_prefix` (Standard `[Webpage Monitoring]`) |
| `dev_mode` | `enabled: false` | `enabled`, `keep_open_after_run_seconds` (Standard `60`, gilt auch für manuelle Starts, `0` = keine Pause), siehe [Dev-Modus](#dev-modus-sichtbares-terminal-fenster) |

Ungültige Werte oder unbekannte Schlüssel brechen einen Lauf nie ab: Es gilt der Standardwert, und im Report erscheint ein Hinweis. Schlüssel, die mit `_` beginnen, sind Kommentare (siehe [Kommentare](#kommentare)). Unbekannte Schlüssel in `secrets.json` werden vermerkt, wenn die Datei für eine Mail gelesen wird.

## Zeitplan: stündlicher Start und Prüfintervall

Das Skript wird **jede Stunde gestartet**. Es entscheidet selbst, ob eine Prüfung aller Webseiten fällig ist:

- **Auf dem Prüfraster:** Geprüft wird zu den Stunden `check_anchor_hour + n × check_interval_hours`. Beispiel: `"check_interval_hours": 6` und `"check_anchor_hour": 5` ergeben Prüfungen um 05:00, 11:00, 17:00 und 23:00 Uhr.
- **Nachholen:** War der Computer zu einer Rasterstunde ausgeschaltet, wird beim nächsten stündlichen Start geprüft, sobald die letzte reguläre Prüfung älter als das Intervall ist. Der Zeitpunkt der letzten regulären Prüfung wird aus `state.json` gelesen (fehlt die Datei: aus `REPORT-of-every-run-last-3-days.txt`).
- **Keine Prüfung fällig:** Das Skript endet sofort mit Exit-Code 0. Es wird nichts in die Reports geschrieben, keine Mail versendet und kein Fenster geöffnet.
- Mit `"check_interval_hours": 1` (Standard) ist jeder Start eine Prüfung, wie in früheren Versionen.
- `python webpages_monitor.py --force` prüft sofort, unabhängig vom Zeitplan.

### Intensive Prüfung geänderter Webseiten

Mit `"intensive_check_interval_hours": N` (N > 0, kleiner als `check_interval_hours`; `0` = aus, Standard) wird eine Webseite mit festgestellter Änderung **N Stunden später** erneut geprüft – nur diese Webseite, nicht die ganze Liste:

| Zeit | Beispiel: regulär alle 6 Stunden ab 04:00, intensiv alle 2 Stunden |
|---|---|
| 04:00 | Reguläre Prüfung aller Webseiten; Webseite A hat sich geändert → A ist im Intensiv-Modus |
| 06:00 | Intensive Prüfung nur von A: erneut geändert → bleibt intensiv; unverändert oder Fehler → verlässt den Intensiv-Modus |
| 08:00 | Nur wenn A um 06:00 erneut geändert war: wieder A |
| 10:00 | Reguläre Prüfung aller Webseiten |

- Fällt eine intensive Prüfung auf eine reguläre Stunde, übernimmt die reguläre Prüfung.
- Nach einer intensiven Prüfung wird **nur bei einer erneuten Änderung** eine Mail versendet (unabhängig von `mail_condition`). Der Betreff beginnt mit `Intensive check:`, der Mail-Text nennt die Anzahl abgerufener Webseiten, z. B. `1 of 32 webpages`.
- Im Run-Report steht `Intensive check: 1 webpage (webpages changed recently)`; nicht abgerufene Webseiten erscheinen dort nicht. Der Daily Report wird nach jeder Prüfung für alle Webseiten neu geschrieben.
- Der Zustand (letzte reguläre Prüfung, Webseiten im Intensiv-Modus) steht in `state.json` im Projektordner (nicht in Git; vom Skript geschrieben, nicht bearbeiten). Fehlt die Datei, wird der Zeitpunkt der letzten Prüfung aus dem Report gelesen.
- `--force` prüft immer alle Webseiten.

### Kommandozeilen-Optionen

| Option | Bedeutung |
|---|---|
| *(keine)* | Prüfen, falls laut Zeitplan fällig |
| `--force` | Sofort prüfen, auch wenn keine Prüfung fällig ist |
| `--test-mail` | Testmail senden (Inhalt: aktueller Daily Report) und beenden; funktioniert auch mit `"mail_mode": "none"` |

## Mail-Versand durch das Skript

Als Alternative zum Versand der Reports auf anderem Weg (z. B. [mit Claude](#optional-benachrichtigung-mit-claude)) kann das Skript den Daily Report selbst per Mail versenden.

1. In `settings.json`: `"mail_mode": "script"` setzen und `smtp` sowie `mail` ausfüllen:

   ```json
   "mail_mode": "script",
   "mail_condition": "always",
   "smtp": { "host": "smtp.gmail.com", "port": 587, "use_starttls": true, "use_ssl": false, "username": "sender@example-alpha.com" },
   "mail": { "sender": "sender@example-alpha.com", "recipients": ["recipient@example-bravo.com"], "subject_prefix": "[Webpage Monitoring]" }
   ```

2. `secrets.example.json` nach `secrets.json` kopieren und das SMTP-Passwort eintragen. Bei Gmail ist das ein *App-Passwort* (Google-Konto → Sicherheit → Bestätigung in zwei Schritten → App-Passwörter), nicht das normale Kontopasswort.
3. Testen: `python webpages_monitor.py --test-mail`

Verhalten:

- Die Mail wird nach jeder Prüfung versendet. Sie beginnt mit dem Ergebnis dieser Prüfung (Zeitpunkt der vorherigen Prüfung, seither geänderte Webseiten und Fehler), danach folgt der Inhalt von `REPORT-daily-summary.txt` (Vergleich mit der Erfassung von vor rund einem Tag):

  ```
  === Check 2026-10-22 13:00 (26 webpages) ===

  Previous check: 2 hours ago (2026-10-22 11:00)
  Since the previous check: 0 changed, 0 errors


  Below: daily report
  Compared with the capture from 25 hours ago: 1 changed, 0 without comparison

  === Daily report 2026-10-22 13:00 ===
  ...
  ```

- Der Betreff nennt beide Ergebnisse, z. B. `[Webpage Monitoring] This check: 0 changed, 0 errors | 25 hours: 1 changed (26 webpages, run 2026-10-22 13:00)`.
- `"mail_condition": "on_change"` versendet nur dann eine Mail, wenn eine Änderung oder ein Fehler festgestellt wurde (Exit-Code 1 oder 2). Erstläufe allein zählen nicht als Änderung.
- Das Ergebnis wird am Ende des Laufs in `REPORT-of-every-run-last-3-days.txt` vermerkt (`Mail: daily report sent to …` oder `ERROR: Mail could not be sent: …`). Ein fehlgeschlagener Versand bricht den Lauf nie ab.
- Mit `use_ssl: true` wird eine SMTPS-Verbindung verwendet (meist Port 465), sonst eine normale Verbindung mit STARTTLS (Port 587).
- Es wird nur die Python-Standardbibliothek verwendet; ein zusätzliches Paket ist nicht nötig.

## Dev-Modus: sichtbares Terminal-Fenster

`install_task.ps1` registriert die Aufgabe mit `pythonw.exe`, das **ohne** Fenster läuft. Um die geplanten Läufe zu beobachten, wird in `settings.json` der Dev-Modus eingeschaltet:

```json
"dev_mode": { "enabled": true, "keep_open_after_run_seconds": 60 }
```

- Bei jeder fälligen Prüfung startet sich das Skript in einem sichtbaren Terminal-Fenster neu und zeigt den Fortschritt.
- Nach dem Lauf bleibt das Fenster `keep_open_after_run_seconds` Sekunden offen; *Enter* schliesst es sofort.
- Stündliche Starts ohne fällige Prüfung öffnen kein Fenster.
- Die Aufgabe muss nicht neu registriert werden; zurückschalten mit `"enabled": false`.

## Geplante Läufe unter Windows (Aufgabenplanung)

### Empfohlen: stündliche Aufgabe mit `install_task.ps1`

In PowerShell im Projektordner:

```
.\install_task.ps1              # Aufgabe "Webpages-Monitor" registrieren / aktualisieren (jede Stunde, zur vollen Stunde)
.\install_task.ps1 -Remove      # Aufgabe entfernen
.\install_task.ps1 -TaskName "My-Monitor"   # anderer Aufgabenname
```

Die Aufgabe startet das Skript jede Stunde mit `pythonw.exe` (ohne Fenster); welche Stunden geprüft werden, wird mit `check_interval_hours` und `check_anchor_hour` festgelegt. Blockiert PowerShell das Skript, einmalig mit `powershell -ExecutionPolicy Bypass -File .\install_task.ps1` starten.

### Alternative: feste Uhrzeiten

Das Skript kann auch zu festen Uhrzeiten gestartet werden. Dann `"check_interval_hours": 1` (Standard) setzen, damit jeder Start eine Prüfung ist.

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
- `secrets.json`
  SMTP-Passwort für den Mail-Versand (nicht in Git).
- `state.json`
  Zustand des Zeitplans: letzte reguläre Prüfung, Webseiten im Intensiv-Modus (vom Skript geschrieben, nicht in Git).
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

https://example-charlie.com/doku.php
Changed
 [Text]
  removed: old text
  added:   new text


The following webpages are unchanged:
-  https://example-alpha.com/de/news/
-  https://example-bravo.com/dt/

Run finished (06:01:23): 4 webpages processed, 1 changed, 1 errors, 0 first runs, 0 list/settings errors
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
Webpages monitor – run 2026-10-22 11:00 – 26 webpages

[ 1/26] https://example-alpha.com/de/news/ ... no change (2.1 s)
[ 2/26] https://example-bravo.com/dt/ ... CHANGED (4.8 s)
[ 3/26] https://example-delta.com/offline/ ... ERROR: timeout (45 s) (45.0 s)
[ 4/26] https://example-golf.com/de/members/reports/ ... login... no change (3.3 s)

Writing reports ... done

Window closes in 60 s - press Enter to close now.
```

- `login...` erscheint bei der Webseite, bei der sich das Skript über ein Anmeldeformular anmeldet.
- Nach „done“ folgt die Meldung `Window closes in 60 s - press Enter to close now.`, damit die letzten Zeilen noch lesbar sind, bevor sich das Fenster schliesst; *Enter* schliesst es sofort. Die Wartezeit ist `keep_open_after_run_seconds` in `dev_mode` (gilt auch für manuelle Starts; `0` = keine Pause).
- Sonst erscheint nichts im Terminal; alle Details stehen in den Report-Dateien. Mit `console_progress` auf `false` werden Anzeige und Pause abgeschaltet.
- Mit `"mail_mode": "script"` folgt nach den Reports die Zeile `Sending mail ... done`.
- Ist keine Prüfung fällig, erscheint nur eine Zeile, z. B. `Webpages monitor – 2026-10-22 12:00 – no check due (last check 2026-10-22 11:00, next 2026-10-22 17:00). Use --force to check now.`

### Exit-Codes

| Code | Bedeutung |
|---|---|
| 0 | Keine Änderung und keine Fehler (auch bei Erstläufen) oder keine Prüfung fällig |
| 1 | Änderung, Fehler bei einer Webseite, Fehler in einem Listen- oder Einstellungseintrag oder Mail konnte nicht versendet werden |
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

- **Nur Mail:** Das Skript kann den Daily Report per SMTP versenden (siehe [Mail](#mail-versand-durch-das-skript)); andere Benachrichtigungen (Push, Messenger) werden nicht unterstützt. Die Mail ist reiner Text ohne Anhang.
- **Stündlicher Start nötig:** Das Skript entscheidet selbst, zu welchen Stunden geprüft wird, muss aber gestartet werden (z. B. stündlich über die Aufgabenplanung mit `install_task.ps1`). Der Computer muss dafür eingeschaltet und mit dem Internet verbunden sein.
- **Keine Bedienoberfläche:** Webseiten-Liste und Einstellungen werden direkt in den JSON-Dateien bearbeitet.
- **Begrenzter Verlauf:** Der Report umfasst die letzten drei Tage, der Daily Report nur den letzten Tagesvergleich. Ältere Stände liegen nur im Archiv und müssen bei Bedarf von Hand verglichen werden.
- **Archiv ohne Bereinigung:** Das Archiv (`archive/`) wächst dauerhaft um eine Datei pro Webseite und Tag; es wird nicht automatisch aufgeräumt.
- **Plattform:** Entwickelt und getestet unter Windows (Aufgabenplanung, Umgebungsvariablen mit `setx`). Das Skript selbst läuft auf jedem System mit Python 3.9 oder neuer; für andere Systeme gibt es aber keine Anleitung zur zeitgesteuerten Ausführung.

Aktuell ist vom Autor keine Weiterentwicklung dieses Projekts geplant, um gewisse Einschränkungen zu beseitigen. Aber vielleicht willst du ja forken und es weiterentwickeln.

## Optional: Benachrichtigung mit Claude

Alternative zum [Mail-Versand durch das Skript](#mail-versand-durch-das-skript) (dann `"mail_mode": "none"` belassen, damit keine Mail doppelt versendet wird). Bei Bedarf lässt sich in der Claude-Desktop-App eine geplante Aufgabe einrichten, die `REPORT-daily-summary.txt` nach den Läufen liest (z. B. 10 Minuten später) und per Mail versendet.
