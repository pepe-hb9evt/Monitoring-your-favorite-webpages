# Keep an eye on your favorite webpages

Documentation of the project "**[Monitoring-your-favorite-webpages](https://github.com/pepe-hb9evt/Monitoring-your-favorite-webpages)**" on GitHub.

( German: **Deutsche Version** dieses Dokuments verfügbar unter: [DOCUMENTATION_deutsch_german.md](DOCUMENTATION_deutsch_german.md) )

This is the detailed documentation of the Python script. For a short overview, see the [README](README.md).

<br>

## Contents

- [How it works](#how-it-works)
- [Site list (`webpages.json`)](#site-list-webpagesjson)
- [Settings (`settings.json`)](#settings-settingsjson)
- [Scheduled runs on Windows (Task Scheduler)](#scheduled-runs-on-windows-task-scheduler)
- [Output](#output)
- [What the current version cannot do](#what-the-current-version-cannot-do)
- [Optional: notification with Claude](#optional-notification-with-claude)

<br>

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

<br>

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

<<<<<<< Updated upstream
## Site list (`webpages.json`)
=======
<br>

## Webpage list (`webpages.json`)
>>>>>>> Stashed changes

The file lives in the project folder and is re-read on every run. It is a JSON object that maps short names to webpages. A commented template with all formats is [`webpages.example.json`](webpages.example.json).

<br>

### Short form

```json
"alpha-news": "https://example-alpha.com/de/news/"
```

<br>

### Long form

```json
"beta-dt": { "url": "https://example-beta.com/dt/" }
```

### With credentials (HTTP Basic)

<<<<<<< Updated upstream
#### Password stored in an environment variable (recommended)
=======
<br>

### Webpages with logins

Logins with HTTP Basic and the WordPress login form are supported.

Other login forms (e.g. MediaWiki, DokuWiki) are **not supported**.

<br>

#### Login HTTP Basic with the password stored in an environment variable (recommended)
>>>>>>> Stashed changes

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

<<<<<<< Updated upstream
#### Password in plain text (not recommended)
=======
If the environment variable is not set during the run, the webpage is skipped; the report then shows `Entry '…' skipped: environment variable '…' is not set`. This applies to all login types with `password_env`.

<br>

#### Login HTTP Basic with the password in plain text (not recommended)
>>>>>>> Stashed changes

```json
"private": {
  "url": "https://example-epsilon.com/private/",
  "username": "my-user",
  "password": "my-password"
}
```

<<<<<<< Updated upstream
### With a login form (WordPress)
=======
<br>

#### Login with a login form (WordPress)
>>>>>>> Stashed changes

Many club and association websites use the normal WordPress login form instead of HTTP Basic. With `"login": "wordpress"` the script signs in through this form before fetching the page:

```json
"members-reports": {
  "url": "https://example-eta.com/de/members/reports/",
  "login": "wordpress",
  "username": "my-user",
  "password_env": "MONITOR_PW_ETA"
}
```

- `<site>/wp-login.php` is used as the address of the login form. If the website uses another address, add `"login_url": "https://example-eta.com/wp-login.php"`.
- Each login (same `login_url` and same `username`) is done once per run; further pages of the same website reuse it. The images of the page are fetched logged in as well.
- If the login is refused, the report shows `Login failed: username or password not accepted`, and the webpage counts as an error. If a page is redirected to a login page instead (e.g. missing access rights), it shows `Login failed: redirected to the login page`. In both cases the last copy is kept.
- The same check also applies to webpages without `login`: if a page suddenly redirects to a login page, this is reported as an error instead of storing the login page.
- Login forms with a captcha or two-factor authentication cannot be used.

<br>

### Test runs with `STOP`

To test with only one or two webpages, put them at the top of the list and add an entry `STOP` below them. All entries after `STOP` are skipped:

```json
{
  "alpha-news": "https://example-alpha.com/de/news/",
  "STOP": "everything below is ignored",
  "beta-dt": "https://example-beta.com/dt/"
}
```

- The key `STOP` may be written in any case (`stop`, `Stop`); its value is free text.
- Skipped webpages are neither fetched nor checked; their stored captures stay unchanged.
- The terminal shows e.g. `… – 2 sites (STOP in webpages.json: 28 sites skipped)`, and both reports start with `Note: STOP in webpages.json – … sites after STOP skipped`; this way a forgotten `STOP` is noticed.
- To monitor the whole list again, delete the line or rename it to `_STOP`.

<br>

### Comments

JSON has no comments. Keys that start with `_` are therefore ignored:

```json
"_comment": "A note"
```

<<<<<<< Updated upstream
=======
This applies to all JSON files of the project (`webpages.json`, `settings.json`, `secrets.json`) and on every level, e.g. also inside a webpage entry, inside `ignore` or inside `smtp`. A comment key may appear several times.

Every other key that is not expected (e.g. a misspelt `"pasword"`) is ignored as well, but always noted in the report as `ERROR: … unknown key …`. The run is not stopped, and the webpage is still monitored.

<br>

>>>>>>> Stashed changes
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
| `ignore` | no | Lines left out when comparing, see below. |

A faulty entry is skipped and noted in the report. If the file is missing, is not valid JSON or contains not a single valid webpage, the run ends in a controlled way with a log entry.

<br>

### `accept_status`

Optional per webpage: `"accept_status": [500]` uses the content even if the server answers with one of these HTTP error codes (for servers that deliver a normal page with a wrong status code). The report then shows a note. Use it only for webpages where this is known; otherwise real error pages would be stored as content.

<br>

### `ignore`

Optional per webpage: lines that change all the time (solar banners, counters, "Last update") can be excluded from the comparison, separately for each section of the capture file:

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
- A matching line is removed from **both** captures before comparing, so it shows up neither as "removed" nor as "added". If nothing else changed, the webpage counts as unchanged (also in the daily report).
- The capture files stay complete; the rules apply only when comparing. A new rule therefore also works for existing captures, and if it is removed, the full comparison applies again.
- Faulty rules (wrong type, invalid regular expression, unknown key) are skipped and noted in the report; the webpage itself is still monitored.

<<<<<<< Updated upstream
### Limitation: other login forms
=======
<br>

#### `ignore.elements`: remove whole HTML areas
>>>>>>> Stashed changes

Besides HTTP Basic, only the WordPress login form is supported.

Other login forms (e.g. MediaWiki, DokuWiki) are **not supported**.

<br>

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
<<<<<<< Updated upstream

Invalid values or unknown keys never stop a run: the default value applies, and the report shows a note.
=======
| `check_interval_hours` | `1` | Check every N hours: `1`, `2`, `3`, `4`, `6`, `8`, `12` or `24` (see [Schedule](#schedule-hourly-start-and-check-interval)) |
| `check_anchor_hour` | `0` | Hour of day (0–23) the check grid starts from |
| `intensive_check_interval_hours` | `0` | `0` = off; N = check changed or unreachable webpages again after N hours (see [Intensive check](#intensive-check-of-changed-and-unreachable-webpages)) |
| `mail_mode` | `none` | `none` = the script sends no mail, `script` = the script sends the daily report by SMTP (see [E-mail](#e-mail-sent-by-the-script)) |
| `mail_condition` | `always` | `always` = mail after every check, `on_change` = only if a change or an error was detected |
| `smtp` | Gmail, port 587, STARTTLS | SMTP server: `host`, `port`, `use_starttls`, `use_ssl`, `username` |
| `mail` | – | `sender`, `recipients` (list), `subject_prefix` (default `[Webpage Monitoring]`) |
| `dev_mode` | `enabled: false` | `enabled`, `keep_open_after_run_seconds` (default `60`, also used for manual starts, `0` = no pause), see [Dev mode](#dev-mode-visible-terminal-window) |

Invalid values or unknown keys never stop a run: the default value applies, and the report shows a note. Keys starting with `_` are comments (see [Comments](#comments)). Unknown keys in `secrets.json` are noted when the file is read for a mail.

<br>

## Schedule: hourly start and check interval

The script is meant to be **started every hour**. It decides itself whether a check of all webpages is due:

- **On the check grid:** a check is done at the hours `check_anchor_hour + n × check_interval_hours`. Example: `"check_interval_hours": 6` and `"check_anchor_hour": 5` give checks at 05:00, 11:00, 17:00 and 23:00.
- **Catch-up:** if the computer was switched off at a grid hour, the check is done at the next hourly start as soon as the last regular check is older than the interval. The time of the last regular check is taken from `state.json` (if missing: from `REPORT-of-every-run-last-3-days.txt`).
- **No check due:** the script ends at once with exit code 0. Nothing is written to the reports, no mail is sent and no window is opened.
- With `"check_interval_hours": 1` (default) every start is a check, as in earlier versions.
- `python webpages_monitor.py --force` checks at once, regardless of the schedule.

<br>

### Intensive check of changed and unreachable webpages

With `"intensive_check_interval_hours": N` (N > 0, smaller than `check_interval_hours`; `0` = off, default), webpages that **changed** or were **not reachable** are checked again **N hours later** – only these webpages, not the whole list:

- **Regular check:** All changed and all unreachable webpages are put on the intensive list.
- **Intensive check:** Only the webpages on the intensive list are fetched.
  - If at least one webpage has **new content**, a mail is sent and the list is rebuilt: all webpages that changed or were not reachable in this check. The next intensive check follows N hours later.
  - If no webpage has new content, **no mail** is sent and the list is cleared: no further intensive check, even if webpages are still not reachable.
- The next regular check always replaces the list with its own result.
- First runs (newly added webpages) are not put on the list.

| Time | Example: regular every 4 hours from 03:00, intensive after 1 hour | Mail | Intensive list |
|---|---|---|---|
| 03:00 | Regular check of all webpages: A changed, B not reachable | yes | A, B |
| 04:00 | Intensive check of A and B: A changed again, B not reachable | yes | A, B |
| 05:00 | Intensive check of A and B: A unchanged, B not reachable | no | empty |
| 06:00 | no check | – | empty |
| 07:00 | Regular check of all webpages | according to `mail_condition` | new |

Variant: if B is reachable again at 04:00 and has new content while A is unchanged, a mail is sent and only B is checked at 05:00.

Note: if a webpage changes on every fetch (e.g. a counter or date), a mail is sent every hour until the next regular check. Remedy: an `ignore` entry for this webpage.

- If an intensive check falls on a regular hour, the regular check covers it.
- The run section of the mail is titled `=== Intensive run … ===` and names the number of fetched webpages, e.g. `2 of 32 webpages`.
- The run report notes `Intensive check: 2 webpages (changed or not reachable at the previous check)`; webpages not fetched do not appear there. The daily report is rewritten for all webpages after every check.
- The state (last regular check, webpages in intensive mode) is kept in `state.json` in the project folder (not in Git; written by the script, do not edit). If the file is missing, the time of the last check is taken from the report.
- `--force` always checks all webpages.

<br>

### Command line options

| Option | Meaning |
|---|---|
| *(none)* | Check if due according to the schedule |
| `--force` | Check now, even if no check is due |
| `--test-mail` | Send a test mail (content: current daily report) and exit; works also with `"mail_mode": "none"` |

There is also a batch file that conveniently offers these options in a selection menu:<br>
File `Menu for webpage-monitor-py.bat`

<br>

## E-mail sent by the script

As an alternative to sending the reports by other means (e.g. [with Claude](#optional-notification-with-claude)), the script can send the daily report by e-mail itself.

1. In `settings.json`: set `"mail_mode": "script"` and fill in `smtp` and `mail`:

   ```json
   "mail_mode": "script",
   "mail_condition": "always",
   "smtp": { "host": "smtp.gmail.com", "port": 587, "use_starttls": true, "use_ssl": false, "username": "sender@example-alpha.com" },
   "mail": { "sender": "sender@example-alpha.com", "recipients": ["recipient@example-bravo.com"], "subject_prefix": "[Webpage Monitoring]" }
   ```

2. Copy `secrets.example.json` to `secrets.json` and enter the SMTP password. For Gmail, this is an *app password* (Google account → Security → 2-step verification → App passwords), not the normal account password.
3. Test: `python webpages_monitor.py --test-mail`

Behaviour:

- The mail is sent after each check. It starts with a two-line summary (this run and daily report), then the details of this run (webpages with new information, webpages with errors), followed by the content of `REPORT-daily-summary.txt` (comparison with the capture of about one day ago):

```
This run:      1 changed, 0 errors since last run 1 hour ago
Daily report:  2 changed, 2 without comparison


=== Run 2026-10-22 13:00 (26 webpages) ===

New information on:
-  https://www.example-alpha.com/news/

Errors:
(none)



=== Daily report 2026-10-22 13:00 ===
...
```

<br>

- The subject is short and names only the result of this run, e.g. `[Webpage Monitoring] 0 changed, 0 errors since 1 hour` (below one hour in minutes, otherwise in whole hours).
- `"mail_condition": "on_change"` sends a mail only if a change or an error was detected (exit code 1 or 2). First runs alone do not count as a change.
- The result is noted at the end of the run in `REPORT-of-every-run-last-3-days.txt` (`Mail: daily report sent to …` or `ERROR: Mail could not be sent: …`). A failed mail never stops the run.
- With `use_ssl: true` an SMTPS connection is used (usually port 465), otherwise a normal connection with STARTTLS (port 587).
- Only the Python standard library is used; no additional package is needed.

<br>

## Dev mode: visible terminal window

`install_task.ps1` registers the task with `pythonw.exe`, which runs **without** a window. To watch the scheduled runs, switch on the dev mode in `settings.json`:

```json
"dev_mode": { "enabled": true, "keep_open_after_run_seconds": 60 }
```

- For each due check, the script starts itself again in a visible terminal window and shows the progress.
- After the run, the window stays open for `keep_open_after_run_seconds` seconds; *Enter* closes it at once.
- Hourly starts without a due check open no window.
- The task does not have to be registered again; switch back with `"enabled": false`.
>>>>>>> Stashed changes

<br>

## Scheduled runs on Windows (Task Scheduler)

<<<<<<< Updated upstream
=======
<br>

### Recommended: hourly task with `install_task.ps1`

In PowerShell, in the project folder:

```
.\install_task.ps1              # register / update the task "Webpages-Monitor" (every hour, at the full hour)
.\install_task.ps1 -Remove      # remove the task
.\install_task.ps1 -TaskName "My-Monitor"   # other task name
```

The task starts the script every hour with `pythonw.exe` (no window); which hours are checked is set with `check_interval_hours` and `check_anchor_hour`. If PowerShell blocks the script, start it once with `powershell -ExecutionPolicy Bypass -File .\install_task.ps1`.

<br>

### Alternative: fixed times

The script can also be started at fixed times. In this case set `"check_interval_hours": 1` (default), so that every start is a check.

>>>>>>> Stashed changes
Example: daily at 06:00. For further times, repeat the command with another name (`/tn`) and another time (`/st`). Adjust the paths; `where python` shows the full path to `python.exe`.

On Windows systems in German, the Task Scheduler is called "Aufgabenplanung".

<br>

### Command line (`schtasks`)

In a command prompt:

```
schtasks /create /tn "Webpages Monitor 0600" /sc daily /st 06:00 /tr "cmd /c cd /d C:\Tools\webpages-monitor && python webpages_monitor.py"
```

Test: `schtasks /run /tn "Webpages Monitor 0600"`. Delete: `schtasks /delete /tn "Webpages Monitor 0600" /f`.

<br>

### Graphical interface

1. Open *Task Scheduler* → *Create Basic Task* (or *Create Task*).
2. *Trigger*: daily; with *Create Task* several triggers can be added for different times.
3. *Action*: *Start a program*
   - Program/script: full path to `python.exe`
   - Add arguments: `webpages_monitor.py`
   - Start in: the project folder
4. Under *Settings*: enable *Run task as soon as possible after a scheduled start is missed*.

<br>

### Notes

- "Run only when user is logged on" is enough if the computer is running. For the task to run without being signed in, it needs a stored password; environment variables for `password_env` are then only available if they are set as user or system variables of the account that runs the task.
- The computer needs an internet connection during the run.

<br>

## Output

<br>

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

<br>

### Layout of `REPORT-of-every-run-last-3-days.txt`

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

Newest run first; runs older than three days are removed on the next run. The report shows at most 15 change lines per webpage (default, see `max_change_lines`).

Each run compares the newest with the second newest capture of a webpage. Each run starts with the time since the previous run (`Previous run: 47 minutes ago`; up to 99 minutes in minutes, from 100 minutes on in hours, rounded).

<br>

### Capture files

Every successful fetch writes `captured_YYYY-MM-DD_HHHMM.txt` (e.g. `captured_2026-10-21_11H00.txt`). Captures older than 48 hours are deleted on the next run; the two newest captures of a webpage are always kept. The archive keeps one copy per day permanently (the last one of the day).

<br>

### Layout of `REPORT-daily-summary.txt`

Rewritten after every run, in the same layout as a run of the report, with the header `=== Daily report YYYY-MM-DD HH:MM ===`. For each webpage, the newest capture is compared with the newest of all captures that are at least 23 hours old; if there is none, with the oldest one available. The first line names the age of the reference capture, e.g. `Newest capture compared with the capture from 24 hours ago.`; if no capture was old enough, `(oldest capture available)` is added. Webpages that failed in the current run are listed under "No comparison possible".

<br>

### Terminal window

While running, the script shows which webpage is being fetched and the result:

```
Webpages monitor – run 2026-10-22 11:00 – 26 sites

[ 1/26] https://example-alpha.com/de/news/ ... no change (2.1 s)
[ 2/26] https://example-beta.com/dt/ ... CHANGED (4.8 s)
[ 3/26] https://example-delta.com/offline/ ... ERROR: timeout (45 s) (45.0 s)
[ 4/26] https://example-eta.com/de/members/reports/ ... login... no change (3.3 s)

Writing reports ... done
.....
```

- `login...` appears for the webpage at which the script signs in through a login form.
- After "done", five dots follow, one per second, so the last lines can still be read before the window closes.
- Nothing else is written to the terminal; all details are in the report files. With `console_progress` set to `false`, the display and the pause are switched off.

<br>

### Exit codes

| Code | Meaning |
|---|---|
| 0 | No change and no errors (also for first runs) |
| 1 | Change, error at a webpage, or error in a list or settings entry |
| 2 | Site list unusable or program error |

<br>

## What the current version cannot do

The script does not support the following points, either intentionally or for the time being:

<br>

### Fetching the webpages

- **No JavaScript:** only the HTML delivered by the server is captured. Content that is loaded in the browser by JavaScript (e.g. dynamic lists, calendar widgets, single-page apps) is missing from the captures.
- **No embedded content:** content in `<iframe>` elements (e.g. embedded maps, videos, other websites) is not loaded.
- **HTML pages only:** PDF, Word or other files are not monitored for their content; only the link to them is captured. If a URL does not deliver HTML content, this is reported as an error.
- **No bot protection:** pages with a captcha or a browser check (e.g. "Checking your browser…") cannot be fetched reliably; at best the check page is stored instead of the actual content.
- **One after another, not in parallel:** the webpages are fetched one by one. Unreachable pages extend the run up to the timeout each (default 45 seconds).
- **No `robots.txt` check:** the fetch frequency should therefore be chosen with moderation.

<br>

### Login

- Only **HTTP Basic** and the **WordPress login form** are supported.
- **Not supported** are other login forms (e.g. MediaWiki, DokuWiki, Joomla), sign-ins through third parties ("Sign in with Google/Microsoft", SSO), two-factor authentication and login forms with a captcha.
- Logins from your own browser (cookies) cannot be taken over.

<br>

### Comparison and display of changes

- **No location:** the script reports *what* has changed (line removed/added), not *where* on the webpage.
- **Lines, not words:** whole lines are compared. If one word changes, the whole line appears as "removed" and "added". Moved sections also appear as removed and newly added.
- **Images by hash only:** the script only detects *that* an image has changed. There is no before/after view of the image and no visual comparison.
- **Undetected images:** CSS background images, `<picture><source>`, `<canvas>` and images loaded by JavaScript (see [Image detection](#image-detection)).
- **Changing images:** images that change on every request (webcams, random banners) are reported as a change on every run. Remedy: `ignore` for this image or `"image_hash": false`.
- **No design:** changes to layout, colors, fonts or order via CSS are not detected; there are no screenshots.
- **Hidden content:** only elements hidden directly in the HTML are recognized (`hidden`, `aria-hidden="true"`, `display:none` in the `style` attribute). Content hidden through CSS classes (e.g. collapsed menus) is still captured and compared.
- **Shortened reports:** per webpage, the report shows at most `max_change_lines` change lines (default 15); the rest is only counted.

<br>

### Notification and operation

- **No sending of its own:** the script only writes files. E-mails or other notifications have to be set up separately (see [Optional: notification with Claude](#optional-notification-with-claude)).
- **No schedule of its own:** the script only runs when it is started (e.g. by the Task Scheduler). The computer must be switched on and connected to the internet.
- **No user interface:** the site list and the settings are edited directly in the JSON files.
- **Limited history:** the report covers the last three days, the daily report only the latest daily comparison. Older states are only in the archive and have to be compared by hand if needed.
- **Archive without clean-up:** the archive (`archive/`) grows permanently by one file per webpage and day; it is not cleaned up automatically.
- **Platform:** developed and tested on Windows (Task Scheduler, environment variables with `setx`). The script itself runs on any system with Python 3.9 or newer; however, there are no instructions for scheduled runs on other systems.

There are currently no plans by the author to develop this project further to remove some of these limitations. But maybe you would like to fork it and develop it further.

<br>

## Optional: notification with Claude

The script itself sends nothing. If needed, a scheduled task can be set up in the Claude desktop app that reads `REPORT-daily-summary.txt` after the runs (e.g. 10 minutes later) and sends it by e-mail.
