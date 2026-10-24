# Keep an eye on your favorite webpages

Documentation of the project "**[Monitoring-your-favorite-webpages](https://github.com/pepe-hb9evt/Monitoring-your-favorite-webpages)**" on GitHub.

( German: **Deutsche Version** dieses Dokuments verfügbar unter: [DOCUMENTATION_deutsch_german.md](DOCUMENTATION_deutsch_german.md) )

This is the detailed documentation of the Python script. For a short overview, see the [README](README.md).

## Contents

- [How it works](#how-it-works)
- [Site list (`webpages.json`)](#site-list-webpagesjson)
- [Settings (`settings.json`)](#settings-settingsjson)
- [Scheduled runs on Windows (Task Scheduler)](#scheduled-runs-on-windows-task-scheduler)
- [Output](#output)
- [What the current version cannot do](#what-the-current-version-cannot-do)
- [Optional: notification with Claude](#optional-notification-with-claude)

## How it works

The script (`webpages_monitor.py`)

- fetches the pages with `requests` (with a user agent; redirects are followed).
- extracts the visible content with BeautifulSoup/lxml: scripts, styles, hidden elements (`hidden`, `aria-hidden="true"`, `display:none`) and comments are ignored.
- compares **text**, **images** (including alt text and a hash of inline SVG) and **links** separately.
- downloads each `<img>` once per run, creates a content hash and stores only the key data (`URL | alt=… | sha1=…`). This also detects an image that was replaced under the same URL. See [Image detection](#image-detection).
- removes volatile parts from URLs such as `?ver=`, session IDs, CSRF tokens, cache busters and the `refresh` parameter of download links (WordPress Download Manager).
- stores `javascript:` links without their code (it often contains random names, e.g. to obfuscate e-mail addresses); only the link text is compared.
- reads the list of webpages to monitor from a JSON file, optionally with username and password (HTTP Basic or WordPress login form).
- copes with faulty entries in the site list and unreachable webpages, so the run does not stop (errors are logged and the remaining webpages are still checked).
- on every successful fetch, saves the visible content of the webpage in a capture file with date and time in its name. Captures are kept for 48 hours.
- checks for each webpage, based on the capture files, whether there are differences between the current and the previous run, and logs the result in `REPORT-of-every-run-last-3-days.txt` (newest run always first; runs older than three days are removed automatically).
- additionally compares for each webpage the current capture with the newest one that is at least 23 hours old, and logs the result in `REPORT-daily-summary.txt` (if no capture is at least 23 hours old, the oldest one available is used instead).
- is configurable: user-dependent values (file names, retention, timeout, user agent, …) are kept in an optional `settings.json`.

### Image detection

Each image is one line in the section `=== IMAGES ===` of a capture file:

```
https://example-delta.com/logo.jpg | alt=Logo | sha1=3f9a1c0e7b2d4a51
https://example-delta.com/team.jpg | alt=Team | sha1=?
inline-svg | sha1=8c02e4f1a9b37d60
```

- `<img>`: URL from `src`, `data-src` or the first entry of `srcset`; `sha1` = the first 16 hex digits of the SHA1 of the image data (at most `image_max_bytes` are read).
- Inline `<svg>`: hash over the SVG code.
- `sha1=?`: the image could not be downloaded (error, timeout, no image content type, more than `image_max_count` images on the page).
- Ignored: `data:` images, tracking pixels (1×1, `pixel`, `spacer`, `blank.gif`), hidden elements.
- An image that appears on several pages is downloaded only once per run. HTTP Basic credentials are only sent for images on the same host as the page.

Comparison: the lines are compared like text. If the hash of an image (same URL and same alt text) is missing on one side, e.g. because `image_hash` was switched off in between, or if it is `?`, the hash is ignored. So neither switching `image_hash` nor a temporarily unreachable image causes a false change. The same URL with two different hashes means that the image content was replaced:

```
 [Images]
  removed: https://example-delta.com/logo.jpg | alt=Logo | sha1=3f9a1c0e7b2d4a51
  added:   https://example-delta.com/logo.jpg | alt=Logo | sha1=8c02e4f1a9b37d60
```

Not detected: CSS background images, `<picture><source>`, `<canvas>` and images loaded by JavaScript. Images that change on every request (webcams, captchas, random banners) are reported on every run; in that case set `"image_hash": false`.

## Site list (`webpages.json`)

The file lives in the project folder and is re-read on every run. It is a JSON object that maps short names to webpages. A commented template with all formats is [`webpages.example.json`](webpages.example.json).

### Short form

```json
"alpha-news": "https://example-alpha.com/de/news/"
```

### Long form

```json
"bravo-dt": { "url": "https://example-bravo.com/dt/" }
```

The following variants show what the long form is needed for.

### Webpages with logins

Logins with HTTP Basic and the WordPress login form are supported.

Other login forms (e.g. MediaWiki, DokuWiki) are **not supported**.

#### Login HTTP Basic with the password stored in an environment variable (recommended)

```json
"internal": {
  "url": "https://example-echo.com/internal/",
  "username": "my-user",
  "password_env": "MONITOR_PW_INTERNAL"
}
```

Set the variable once (a new terminal or a new sign-in is required afterwards):

```
setx MONITOR_PW_INTERNAL "secret-password"
```

If the environment variable is not set during the run, the webpage is skipped; the report then shows `Entry '…' skipped: environment variable '…' is not set`. This applies to all login types with `password_env`.

#### Login HTTP Basic with the password in plain text (not recommended)

```json
"private": {
  "url": "https://example-echo.com/private/",
  "username": "my-user",
  "password": "my-password"
}
```

#### Login with a login form (WordPress)

Many club and association websites use the normal WordPress login form instead of HTTP Basic. With `"login": "wordpress"` the script signs in through this form before fetching the page:

```json
"members-reports": {
  "url": "https://example-golf.com/de/members/reports/",
  "login": "wordpress",
  "username": "my-user",
  "password_env": "MONITOR_PW_MEMBERS"
}
```

- `<site>/wp-login.php` is used as the address of the login form. If the website uses another address, add `"login_url": "https://example-golf.com/wp-login.php"`.
- Each login (same `login_url` and same `username`) is done once per run; further pages of the same website reuse it. The images of the page are fetched logged in as well.
- If the login fails, it is not retried in the same run: all pages with the same login then count as errors and get the same message.
- If the login page cannot be reached (e.g. timeout, connection or HTTP error), the report shows `Login failed: URL not reachable: …` with the exact cause.
- If the login is refused, the report shows `Login failed: username or password not accepted`, and the webpage counts as an error. If a page is redirected to a login page instead (e.g. missing access rights), it shows `Login failed: redirected to the login page`. In both cases the last copy is kept.
- The same check also applies to webpages without `login`: if a page suddenly redirects to a login page, this is reported as an error instead of storing the login page.
- Login forms with a captcha or two-factor authentication cannot be used.

### Test runs with `STOP`

To test with only one or two webpages, put them at the top of the list and add an entry `STOP` below them. All entries after `STOP` are skipped:

```json
{
  "alpha-news": "https://example-alpha.com/de/news/",
  "STOP": "everything below is ignored",
  "bravo-dt": "https://example-bravo.com/dt/"
}
```

- The key `STOP` may be written in any case (`stop`, `Stop`); its value is free text.
- Skipped webpages are neither fetched nor checked; their stored captures stay unchanged.
- The terminal shows e.g. `… – 2 sites (STOP in webpages.json: 28 sites skipped)`, and both reports start with `Note: STOP in webpages.json – … sites after STOP skipped`; this way a forgotten `STOP` is noticed.
- To monitor the whole list again, delete the line or rename it to `_STOP`.

### Comments

JSON has no comments. Keys that start with `_` are therefore ignored:

```json
"_comment": "A note"
```

### Rules

| Field | Required | Description |
|---|---|---|
| Short name (key) | yes | Letters, digits, `.` `_` `-`. Also the name of the data folder in `monitored-webpages/`. A new name starts a new history. |
| `url` | yes | Must start with `http://` or `https://`. |
| `username` | no | Only together with `password` or `password_env`. |
| `password` | no | Password in plain text. |
| `password_env` | no | Name of an environment variable holding the password; takes precedence over `password`. |
| `login` | no | `basic` (default, HTTP Basic) or `wordpress` (WordPress login form), see above. |
| `login_url` | no | Address of the login form for `wordpress`; default `<site>/wp-login.php`. |
| `accept_status` | no | List of HTTP error codes whose content is used anyway, see below. |
| `ignore` | no | Lines left out when comparing, or HTML elements removed (`elements`), see below. |

A faulty entry is skipped and noted in the report. If the file is missing, is not valid JSON or contains not a single valid webpage, the run ends in a controlled way with a log entry.

### `accept_status`

Optional per webpage: `"accept_status": [500]` uses the content even if the server answers with one of these HTTP error codes (for servers that deliver a normal page with a wrong status code). The report then shows a note. Use it only for webpages where this is known; otherwise real error pages would be stored as content.

### `ignore`

Optional per webpage: lines that change all the time (solar banners, counters, "Last update") can be excluded from the comparison, separately for each section of the capture file:

```json
"foxtrot-home": {
  "url": "https://example-foxtrot.com/",
  "ignore": {
    "images": ["hamqsl.com/solarbc.php"],
    "text": ["re:^Last update:"],
    "links": ["/calendar?"]
  }
}
```

- `text`, `images`, `links` are optional; each is a list of patterns.
- A pattern is a substring (case-insensitive). With the prefix `re:` it is a regular expression (Python syntax, case-insensitive, matches anywhere in the line; use `^`/`$` to anchor).
- A matching line is removed from **both** captures before comparing, so it shows up neither as "removed" nor as "added". If nothing else changed, the webpage counts as unchanged (also in the daily report).
- The capture files stay complete; the rules apply only when comparing. A new rule therefore also works for existing captures, and if it is removed, the full comparison applies again.
- Faulty rules (wrong type, invalid regular expression, unknown key) are skipped and noted in the report; the webpage itself is still monitored.

#### `ignore.elements`: remove whole HTML areas

Page areas that change all the time (e.g. a "related posts" box or a footer with counters) can be removed as a whole, with a list of CSS selectors:

```json
"hotel-blog": {
  "url": "https://example-hotel.com/blog/",
  "ignore": {
    "elements": ["div.source-footer", "div.prop-list"]
  }
}
```

- Each matching element is removed **with all its content** (up to its own closing tag, nested elements included) before text, images and links are extracted.
- Selectors: CSS syntax as in the browser, e.g. `div.classname`, `#id`, `footer .widget`, `div[data-x="y"]`. `div.prop-list` matches every `<div>` whose `class` contains `prop-list`.
- Unlike `text`/`images`/`links`, this rule works **during extraction**: the removed areas are no longer in the capture files. After adding (or removing) such a rule, the first run therefore reports a change once. To avoid this, delete the old captures of the webpage in `monitored-webpages\<shortname>` beforehand; the next run is then a first run.
- Invalid selectors are skipped and noted in the report; the webpage itself is still monitored.

## Settings (`settings.json`)

Optional. Lives next to the script; see [`settings.example.json`](settings.example.json). All keys are optional.

| Key | Default | Meaning |
|---|---|---|
| `webpages_file` | `webpages.json` | Name of the site list in the project folder |
| `report_file` | `REPORT-of-every-run-last-3-days.txt` | Name of the report file in the project folder |
| `daily_report_file` | `REPORT-daily-summary.txt` | Name of the daily report (daily comparison) |
| `daily_compare_hours` | `23` | Minimum age of the reference capture for the daily report |
| `capture_keep_hours` | `48` | How long capture files are kept (hours) |
| `report_days` | `3` | How many days runs stay in the report |
| `max_change_lines` | `15` | Change lines per webpage in the report |
| `timeout_seconds` | `45` | Time limit per request |
| `user_agent` | Chrome-like string | Browser identification sent with every request |
| `ignored_url_params` | `ver`, `sid`, … | URL parameters ignored when comparing |
| `image_hash` | `true` | Download images and compare their content (`false`: URL and alt text only) |
| `image_max_count` | `50` | Max. downloaded images per page |
| `image_max_bytes` | `5000000` | Max. bytes read per image |
| `image_timeout_seconds` | `15` | Time limit per image |
| `console_progress` | `true` | Show the progress per webpage in the terminal window |

Invalid values or unknown keys never stop a run: the default value applies, and the report shows a note.

## Scheduled runs on Windows (Task Scheduler)

Example: daily at 06:00. For further times, repeat the command with another name (`/tn`) and another time (`/st`). Adjust the paths; `where python` shows the full path to `python.exe`.

On Windows systems in German, the Task Scheduler is called "Aufgabenplanung".

### Command line (`schtasks`)

In a command prompt:

```
schtasks /create /tn "Webpages Monitor 0600" /sc daily /st 06:00 /tr "cmd /c cd /d C:\Tools\webpages-monitor && python webpages_monitor.py"
```

Test: `schtasks /run /tn "Webpages Monitor 0600"`. Delete: `schtasks /delete /tn "Webpages Monitor 0600" /f`.

### Graphical interface

1. Open *Task Scheduler* → *Create Basic Task* (or *Create Task*).
2. *Trigger*: daily; with *Create Task* several triggers can be added for different times.
3. *Action*: *Start a program*
   - Program/script: full path to `python.exe`
   - Add arguments: `webpages_monitor.py`
   - Start in: the project folder
4. Under *Settings*: enable *Run task as soon as possible after a scheduled start is missed*.

### Notes

- "Run only when user is logged on" is enough if the computer is running. For the task to run without being signed in, it needs a stored password; environment variables for `password_env` are then only available if they are set as user or system variables of the account that runs the task.
- The computer needs an internet connection during the run.

## Output

### Files

Everything lives in the project folder (the folder `monitored-webpages` is created automatically when needed):

- `webpages_monitor.py`
  The script.
- `webpages.json`
  Your own site list (not in Git).
- `settings.json`
  Optional settings (not in Git).
- `REPORT-of-every-run-last-3-days.txt`
  Log of every run of the last three days.
- `REPORT-daily-summary.txt`
  Report with a daily comparison, rewritten on every run. Suitable for automatic delivery by e-mail (see [Optional: notification with Claude](#optional-notification-with-claude)).
- `monitored-webpages/<shortname>/captured_<YYYY-MM-DD_HHHMM>.txt`
  Content of one fetch (text, IMAGES, LINKS); all captures are kept for 48 hours.
- `monitored-webpages/<shortname>/archive/<YYYY-MM-DD>.txt`
  Last capture of that day, kept permanently in the archive.

### Layout of `REPORT-of-every-run-last-3-days.txt`

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

Run finished: 4 sites processed, 1 changed, 1 errors, 0 first runs, 0 list/settings errors
```

Newest run first; runs older than three days are removed on the next run. The report shows at most 15 change lines per webpage (default, see `max_change_lines`).

Each run compares the newest with the second newest capture of a webpage. Each run starts with the time since the previous run (`Previous run: 47 minutes ago`; up to 99 minutes in minutes, from 100 minutes on in hours, rounded).

### Capture files

Every successful fetch writes `captured_YYYY-MM-DD_HHHMM.txt` (e.g. `captured_2026-10-21_11H00.txt`). Captures older than 48 hours are deleted on the next run; the two newest captures of a webpage are always kept. The archive keeps one copy per day permanently (the last one of the day).

### Layout of `REPORT-daily-summary.txt`

Rewritten after every run, in the same layout as a run of the report, with the header `=== Daily report YYYY-MM-DD HH:MM ===`. For each webpage, the newest capture is compared with the newest of all captures that are at least 23 hours old; if there is none, with the oldest one available. The first line names the age of the reference capture, e.g. `Newest capture compared with the capture from 24 hours ago.`; if no capture was old enough, `(oldest capture available)` is added. Webpages that failed in the current run are listed under "No comparison possible".

### Terminal window

While running, the script shows which webpage is being fetched and the result:

```
Webpages monitor – run 2026-10-22 11:00 – 26 sites

[ 1/26] https://example-alpha.com/de/news/ ... no change (2.1 s)
[ 2/26] https://example-bravo.com/dt/ ... CHANGED (4.8 s)
[ 3/26] https://example-delta.com/offline/ ... ERROR: timeout (45 s) (45.0 s)
[ 4/26] https://example-golf.com/de/members/reports/ ... login... no change (3.3 s)

Writing reports ... done

Terminal will be closed in 5 seconds.....
```

- `login...` appears for the webpage at which the script signs in through a login form.
- After "done" the message `Terminal will be closed in 5 seconds` follow; then five dots appear, one per second, so the last lines can still be read before the window closes.
- Nothing else is written to the terminal; all details are in the report files. With `console_progress` set to `false`, the display and the pause are switched off.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | No change and no errors (also for first runs) |
| 1 | Change, error at a webpage, or error in a list or settings entry |
| 2 | Site list unusable or program error |

## What the current version cannot do

The script does not support the following points, either intentionally or for the time being:

### Fetching the webpages

- **No JavaScript:** only the HTML delivered by the server is captured. Content that is loaded in the browser by JavaScript (e.g. dynamic lists, calendar widgets, single-page apps) is missing from the captures.
- **No embedded content:** content in `<iframe>` elements (e.g. embedded maps, videos, other websites) is not loaded.
- **HTML pages only:** PDF, Word or other files are not monitored for their content; only the link to them is captured. If a URL does not deliver HTML content, this is reported as an error.
- **No bot protection:** pages with a captcha or a browser check (e.g. "Checking your browser…") cannot be fetched reliably; at best the check page is stored instead of the actual content.
- **One after another, not in parallel:** the webpages are fetched one by one. Unreachable pages extend the run up to the timeout each (default 45 seconds).
- **No `robots.txt` check:** the fetch frequency should therefore be chosen with moderation.

### Login

- Only **HTTP Basic** and the **WordPress login form** are supported.
- **Not supported** are other login forms (e.g. MediaWiki, DokuWiki, Joomla), sign-ins through third parties ("Sign in with Google/Microsoft", SSO), two-factor authentication and login forms with a captcha.
- Logins from your own browser (cookies) cannot be taken over.

### Comparison and display of changes

- **No location:** the script reports *what* has changed (line removed/added), not *where* on the webpage.
- **Lines, not words:** whole lines are compared. If one word changes, the whole line appears as "removed" and "added". Moved sections also appear as removed and newly added.
- **Images by hash only:** the script only detects *that* an image has changed. There is no before/after view of the image and no visual comparison.
- **Undetected images:** CSS background images, `<picture><source>`, `<canvas>` and images loaded by JavaScript (see [Image detection](#image-detection)).
- **Changing images:** images that change on every request (webcams, random banners) are reported as a change on every run. Remedy: `ignore` for this image or `"image_hash": false`.
- **No design:** changes to layout, colors, fonts or order via CSS are not detected; there are no screenshots.
- **Hidden content:** only elements hidden directly in the HTML are recognized (`hidden`, `aria-hidden="true"`, `display:none` in the `style` attribute). Content hidden through CSS classes (e.g. collapsed menus) is still captured and compared.
- **Shortened reports:** per webpage, the report shows at most `max_change_lines` change lines (default 15); the rest is only counted.

### Notification and operation

- **No sending of its own:** the script only writes files. E-mails or other notifications have to be set up separately (see [Optional: notification with Claude](#optional-notification-with-claude)).
- **No schedule of its own:** the script only runs when it is started (e.g. by the Task Scheduler). The computer must be switched on and connected to the internet.
- **No user interface:** the site list and the settings are edited directly in the JSON files.
- **Limited history:** the report covers the last three days, the daily report only the latest daily comparison. Older states are only in the archive and have to be compared by hand if needed.
- **Archive without clean-up:** the archive (`archive/`) grows permanently by one file per webpage and day; it is not cleaned up automatically.
- **Platform:** developed and tested on Windows (Task Scheduler, environment variables with `setx`). The script itself runs on any system with Python 3.9 or newer; however, there are no instructions for scheduled runs on other systems.

There are currently no plans by the author to develop this project further to remove some of these limitations. But maybe you would like to fork it and develop it further.

## Optional: notification with Claude

The script itself sends nothing. If needed, a scheduled task can be set up in the Claude desktop app that reads `REPORT-daily-summary.txt` after the runs (e.g. 10 minutes later) and sends it by e-mail.
