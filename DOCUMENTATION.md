# Monitoring your favorite webpages

# Documentation

← Back to [README](README.md)

## Contents

- [How it works](#how-it-works)
- [Site list (`webpages.json`)](#site-list-webpagesjson)
- [Settings (`settings.json`)](#settings-settingsjson)
- [Scheduled runs on Windows (Task Scheduler)](#scheduled-runs-on-windows-task-scheduler)
- [Output](#output)
- [Optional: notification with Claude](#optional-notification-with-claude)

## How it works

- Fetches pages with `requests` (user agent, redirects are followed).
- Extracts the visible content with BeautifulSoup/lxml: scripts, styles, hidden elements (`hidden`, `aria-hidden="true"`, `display:none`) and comments are ignored.
- Compares **text**, **images** (including alt text and inline-SVG hash) and **links** separately.
- Image content: every `<img>` is downloaded once per run and stored with a content hash (`URL | alt=… | sha1=…`), so an image replaced under the **same URL** is detected. See [Image detection](#image-detection).
- Volatile noise such as `?ver=`, session IDs, CSRF tokens, cache busters and the `refresh` parameter of download links (WordPress Download Manager) is stripped from URLs.
- `javascript:` links are stored without their code (it often contains random names, e.g. for e-mail obfuscation); only the link text is compared.
- Site list in a JSON file, optionally with username and password (HTTP Basic or WordPress login form).
- Faulty entries and unreachable sites do not stop the run; they are logged and the remaining sites are still checked.
- Report of the last three days, newest run first; older runs are removed automatically.
- Every run stores a capture file with date and time in its name; captures are kept for 48 hours.
- Daily report `daily-report.txt`: rewritten after every run; compares the newest capture with the newest capture that is at least 24 hours old.
- User-dependent values (file names, retention, timeout, user agent, …) live in an optional `settings.json`.

### Image detection

Each image is one line in the `=== IMAGES ===` section of a capture file:

```
https://example-delta.com/logo.jpg | alt=Logo | sha1=3f9a1c0e7b2d4a51
https://example-delta.com/team.jpg | alt=Team | sha1=?
inline-svg | sha1=8c02e4f1a9b37d60
```

- `<img>`: URL from `src`, `data-src` or the first `srcset` entry; `sha1` = first 16 hex digits of the SHA1 of the image bytes (at most `image_max_bytes` are read).
- Inline `<svg>`: hash over the SVG code.
- `sha1=?`: image could not be downloaded (error, timeout, no image content type, more than `image_max_count` images on the page).
- Ignored: `data:` images, tracking pixels (1×1, `pixel`, `spacer`, `blank.gif`), hidden elements.
- An image used on several pages is downloaded only once per run. Login data is only sent to images on the same host as the page.

Comparison: lines are compared like text. If the hash of an image (same URL and alt text) is missing (captures from before this feature) or `?` on one side, the hash is ignored, so neither the update nor a temporarily unreachable image produces a false change. Same URL with two different hashes means the image content was replaced:

```
 [Images]
  removed: https://example-delta.com/logo.jpg | alt=Logo | sha1=3f9a1c0e7b2d4a51
  added:   https://example-delta.com/logo.jpg | alt=Logo | sha1=8c02e4f1a9b37d60
```

Not detected: CSS background images, `<picture><source>`, `<canvas>` and images loaded by JavaScript. Images that change on every request (webcams, captchas, random banners) are reported on every run; set `"image_hash": false` if this is a problem.

## Site list (`webpages.json`)

The file lives in the project folder and is re-read on **every run**. It is a JSON object that maps short names to sites. A commented template with all formats is in [`webpages.example.json`](webpages.example.json).

### Short form

```json
"alpha-news": "https://example-alpha.com/de/news/"
```

### Long form

```json
"beta-dt": { "url": "https://example-beta.com/dt/" }
```

### With login (HTTP Basic), password from an environment variable (recommended)

```json
"internal": {
  "url": "https://example-epsilon.com/internal/",
  "username": "my-user",
  "password_env": "MONITOR_PW_INTERNAL"
}
```

Set the variable once (a new terminal or a new sign-in is required afterwards):

```
setx MONITOR_PW_INTERNAL "secret-password"
```

### With login, password in plain text

```json
"private": {
  "url": "https://example-epsilon.com/private/",
  "username": "my-user",
  "password": "my-password"
}
```

### With a login form (WordPress)

Many club and association sites use the normal WordPress login form instead of HTTP Basic. With `"login": "wordpress"` the script signs in through that form before fetching the page:

```json
"members-reports": {
  "url": "https://example-eta.com/de/members/reports/",
  "login": "wordpress",
  "username": "my-user",
  "password_env": "MONITOR_PW_ETA"
}
```

- The login form is found at `<site>/wp-login.php`. If the site uses another address, add `"login_url": "https://example-eta.com/wp-login.php"`.
- Each login (same `login_url` and `username`) is done once per run; further pages of the same site reuse it. Images of the page are fetched logged in as well.
- If the login is refused, the report shows `Login failed: username or password not accepted`, and the site counts as an error. If a page is redirected to a login page instead (e.g. missing access rights), the report shows `Login failed: redirected to the login page`. In both cases the last copy is kept.
- The same check also applies to sites without `login`: a page that suddenly redirects to a login page is reported as an error instead of storing the login page.
- Login forms with a captcha or two-factor authentication cannot be used.

### Comments

JSON has no comments. Keys that start with `_` are therefore ignored:

```json
"_comment": "A note"
```

### Rules

| Field | Required | Description |
|---|---|---|
| Short name (key) | yes | Letters, digits, `.` `_` `-`. Also the name of the data folder inside `monitored-webpages/`. A new name starts a new history. |
| `url` | yes | Must start with `http://` or `https://`. |
| `username` | no | Only together with `password` or `password_env`. |
| `password` | no | Password in plain text. |
| `password_env` | no | Name of an environment variable holding the password; takes precedence over `password`. |
| `login` | no | `basic` (default, HTTP Basic) or `wordpress` (WordPress login form), see above. |
| `login_url` | no | Address of the login form for `wordpress`; default `<site>/wp-login.php`. |
| `accept_status` | no | List of HTTP error codes whose content is used anyway, see below. |
| `ignore` | no | Lines left out when comparing, see below. |

A faulty entry is skipped and noted in the report. If the file is missing, is not valid JSON, or contains not a single valid site, the run ends in a controlled way with a log entry.

### `accept_status`

Optional per site: `"accept_status": [500]` uses the content even if the server answers with one of these HTTP error codes (for servers that deliver a normal page with a wrong status code). The report then shows a note. Use it only for sites where this is known; otherwise real error pages would be stored as content.

### `ignore`

Optional per site: lines that change all the time (solar banners, counters, "last update" lines) can be excluded from the comparison, separately for each section of a capture file:

```json
"zeta-home": {
  "url": "https://example-zeta.com/",
  "ignore": {
    "images": ["hamqsl.com/solarbc.php"],
    "text": ["re:^Last update:"],
    "links": ["/calendar?"]
  }
}
```

- `text`, `images`, `links` are optional; each is a list of patterns.
- A pattern is a substring (case-insensitive). With the prefix `re:` it is a regular expression (Python syntax, case-insensitive, matches anywhere in the line; use `^`/`$` to anchor).
- A matching line is removed from **both** captures before comparing, so it shows up neither as "removed" nor as "added". If nothing else changed, the site is reported as unchanged (also in the daily report).
- The capture files stay complete; the rules apply only when comparing. A new rule therefore also works for existing captures, and removing a rule restores the full comparison.
- Faulty rules (wrong type, invalid regular expression, unknown key) are skipped and noted in the report; the site itself is still monitored.

### Limitation: other login forms

Besides HTTP Basic only the WordPress login form is supported. Other login forms (e.g. DokuWiki) are not.

## Settings (`settings.json`)

Optional. Located next to the script; see [`settings.example.json`](settings.example.json). All keys are optional.

| Key | Default | Meaning |
|---|---|---|
| `webpages_file` | `webpages.json` | Name of the site list in the project folder |
| `report_file` | `report-last-3-days.txt` | Name of the report file in the project folder |
| `daily_report_file` | `daily-report.txt` | Name of the daily report (24-hour comparison) |
| `daily_compare_hours` | `24` | Minimum age of the reference capture for the daily report |
| `capture_keep_hours` | `48` | How long capture files are kept (hours) |
| `report_days` | `3` | How many days runs stay in the report |
| `max_change_lines` | `15` | Change lines per site in the report |
| `timeout_seconds` | `45` | Time limit per request |
| `user_agent` | Chrome-like string | Browser identification sent with each request |
| `ignored_url_params` | `ver`, `sid`, … | URL parameters ignored when comparing |
| `image_hash` | `true` | Download images and compare their content (`false`: only URL and alt text) |
| `image_max_count` | `50` | Max. downloaded images per page |
| `image_max_bytes` | `5000000` | Max. bytes read per image |
| `image_timeout_seconds` | `15` | Time limit per image |
| `console_progress` | `true` | Show the progress per webpage in the terminal window |

Invalid values or unknown keys never abort a run: the default is used and a note appears in the report.

## Scheduled runs on Windows (Task Scheduler)

Example: daily at 06:00, 11:00, 17:00 and 23:00. Adjust the paths; `where python` shows the full path to `python.exe`.

On Windows systems with German language the 'Task Scheduler' is named 'Aufgabenplanung'.

### Command line (`schtasks`)

In a command prompt:

```
schtasks /create /tn "Webpages Monitor 0600" /sc daily /st 06:00 /tr "cmd /c cd /d C:\Tools\webpages-monitor && python webpages_monitor.py"
schtasks /create /tn "Webpages Monitor 1100" /sc daily /st 11:00 /tr "cmd /c cd /d C:\Tools\webpages-monitor && python webpages_monitor.py"
schtasks /create /tn "Webpages Monitor 1700" /sc daily /st 17:00 /tr "cmd /c cd /d C:\Tools\webpages-monitor && python webpages_monitor.py"
schtasks /create /tn "Webpages Monitor 2300" /sc daily /st 23:00 /tr "cmd /c cd /d C:\Tools\webpages-monitor && python webpages_monitor.py"
```

Test: `schtasks /run /tn "Webpages Monitor 0600"`. Delete: `schtasks /delete /tn "Webpages Monitor 0600" /f`.

### Graphical interface

1. Open *Task Scheduler* → *Create Basic Task* (or *Create Task*).
2. *Trigger*: daily; with *Create Task* you can add several triggers for the four times.
3. *Action*: *Start a program*
   - Program/script: full path to `python.exe`
   - Arguments: `webpages_monitor.py`
   - Start in: the project folder
4. Under *Settings*: enable *Run task as soon as possible after a scheduled start is missed*.

### Notes

- "Run only when user is logged on" is enough if the computer is running. To run without being signed in, the task needs a stored password; environment variables for `password_env` are then only available if they are set as user or system variables of the account that runs the task.
- The computer needs an internet connection while the script runs.

## Output

### Files

Everything lives in the project folder (the folder `monitored-webpages` is created automatically if missing):

```
webpages_monitor.py
webpages.json                 (your own site list, not in Git)
settings.json                 (optional, not in Git)
report-last-3-days.txt        report of the last three days
daily-report.txt              24-hour comparison (rewritten on every run)
monitored-webpages/<shortname>/captured_<YYYY-MM-DD_HHHMM>.txt  content of one run (text, IMAGES, LINKS), kept 48 hours
monitored-webpages/<shortname>/archive/<date>.txt               last capture of that day, kept permanently
```

### Layout of `report-last-3-days.txt`

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

Newest run first; runs older than three days are removed on the next run. The report shows at most 15 change lines per site.

Each run compares the newest capture with the second newest capture of a site. Each run starts with the time since the previous run (`Previous run: 47 minutes ago`; up to 99 minutes in minutes, from 100 minutes on in hours, rounded).

### Capture files

Every successful fetch writes `captured_YYYY-MM-DD_HHHMM.txt` (e.g. `captured_2026-10-21_11H00.txt`). Captures older than 48 hours are deleted on the next run; the two newest captures of a site are always kept. The archive keeps one copy per day permanently. On the first run after the update, an existing `current.txt` becomes a capture file (time taken from the file date) and `previous.txt` is deleted.

### Layout of `daily-report.txt`

Rewritten after every run, in the same layout as a run of the report, with the header `=== Daily report YYYY-MM-DD HH:MM ===`. For each site the newest capture is compared with the newest capture that is at least 24 hours old; if there is none, with the oldest capture available. The first line names the age of the compared capture, e.g. `Newest capture compared with the capture from 24 hours ago.`; below 23 hours `(oldest capture available)` is added. Sites that failed in the current run are listed under "No comparison possible".

### Terminal window

While running, the script shows which webpage is being fetched and the result:

```
Webpages monitor – run 2026-10-22 11:00 – 26 sites

[ 1/26] https://example-alpha.com/de/news/ ... no change (2.1 s)
[ 2/26] https://example-beta.com/dt/ ... CHANGED (4.8 s)
[ 3/26] https://example-delta.com/offline/ ... ERROR: timeout (45 s) (45.0 s)

Writing reports ... done
```

Nothing else is written to the terminal; all details are in the report files. Set `console_progress` to `false` to switch the display off.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Everything unchanged |
| 1 | Change, site error, or error in a list/settings entry |
| 2 | Site list unusable or program error |

## Optional: notification with Claude

The script itself sends nothing. If you like, set up a scheduled task in the Claude desktop app that reads `report-last-3-days.txt` after the runs (e.g. 10 minutes later) and reports changes.
