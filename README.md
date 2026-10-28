# Monitoring your favorite webpages

README for the project "**[Monitoring-your-favorite-webpages](https://github.com/pepe-hb9evt/Monitoring-your-favorite-webpages)**" on Github.

( German: ***Deutsche Version** dieses README verfügbar:* [README_deutsch_german.md](README_deutsch_german.md) )

## Description

A small Python script that monitors your favorite webpages and logs changes to the **visible** content (text, images, links).

The script works through your list of webpages; on every run it saves the current visible content of each webpage and compares it with the previously saved version. It then writes two report files that list for each webpage whether changes were detected and, if so, exactly what has changed.

### Limitations

The main limitations are:

- **Fetching:** Only the HTML delivered by the server is captured – without content loaded by JavaScript, without `<iframe>` content and without the content of PDF or Word files. Pages with a captcha or browser check cannot be monitored reliably.
- **Login:** Only HTTP Basic login and the WordPress login form; no other login forms, no "Sign in with Google/Microsoft", no two-factor authentication, no captcha.
- **Comparison:** The script reports *what* has changed (whole lines), not *where* on the webpage. Images are only compared by their hash value: it detects *that* an image has changed, but there is no before/after view. Changes to layout, colors or fonts are not detected.
- **Operation:** The script has to be started every hour (e.g. with the Windows Task Scheduler, `install_task.ps1`); it then decides itself which hours are checked. Notifications by e-mail only. The report covers three days; the archive is not cleaned up automatically.
- **Platform:** Developed for Windows, but runs on any system with Python 3.9 or newer.

All limitations in detail: [DOCUMENTATION.md → What the current version cannot do](DOCUMENTATION.md#what-the-current-version-cannot-do).

There are currently no plans by the author to develop this project further to remove some of these limitations. But maybe you would like to fork it and develop it further.

### User manual

This README gives a concise overview. For the complete reference, see **[DOCUMENTATION.md](DOCUMENTATION.md)**.

## Features

- Compares visible **text**, **images** and **links** separately. Scripts, hidden elements and volatile URL parts, on the other hand, are ignored.
- Detects replaced images, even if the image URL is unchanged.
- The webpages to check are listed in a JSON file, optionally with the credentials for an HTTP Basic login or the WordPress login form.
- If a webpage redirects to a login page that cannot be passed, this is reported as an error instead of storing the login page.
- While running, the terminal window shows which webpage is being fetched and the result.
- For test runs, an entry `STOP` in the webpage list ends the list; all following entries are skipped.
- Faulty entries or unreachable webpages never stop the run.
- Started every hour, the script checks only every N hours (`check_interval_hours`, e.g. 05:00, 11:00, 17:00, 23:00) and catches up on missed checks.
- Optional: sends the daily report by e-mail itself (SMTP, e.g. Gmail), after every check or only on changes.
- Dev mode: shows a terminal window also for the windowless scheduled runs.
- Two text files are written on every run:

  - `REPORT-of-every-run-last-3-days.txt`: all runs of the last three days, newest first.

  - `REPORT-daily-summary.txt`: daily comparison (newest capture compared with the one that is at least 23 hours old).

Various parameters can be changed in `settings.json` (file names, retention, timeout, user agent, check interval, e-mail, dev mode, …).

## Requirements

- Python 3.9 or newer (Windows: [python.org](https://www.python.org/downloads/), option *Add python.exe to PATH*).
- `pip install -r requirements.txt`

## Installation

1. Copy the files into a project folder, e.g. `C:\Tools\webpages-monitor\`. All data is stored in this folder.
2. Copy `webpages.example.json` to `webpages.json` and enter your own webpages.
3. Optional: copy `settings.example.json` to `settings.json` and adjust values.
4. Optional for e-mail: copy `secrets.example.json` to `secrets.json` and enter the SMTP password; test with `python webpages_monitor.py --test-mail`.
5. Test once: `python webpages_monitor.py --force`
6. Register the hourly task: `.\install_task.ps1` (PowerShell; if script execution is disabled, see below).

The first run only saves a baseline; comparison starts with the second run.

## Webpage list (`webpages.json`)

The webpages to monitor are entered in `webpages.json`:

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

All formats, rules and options are described in:
[DOCUMENTATION.md → Webpage list](DOCUMENTATION.md#webpage-list-webpagesjson).

## Scheduled runs (Windows)

`install_task.ps1` registers a task in the Windows Task Scheduler that starts the script every hour without a window:

```
.\install_task.ps1            # install / update
.\install_task.ps1 -Remove    # uninstall
```

If PowerShell reports that running scripts is disabled on this system, start it this way (the setting of the system remains unchanged):

```
powershell -ExecutionPolicy Bypass -File .\install_task.ps1
powershell -ExecutionPolicy Bypass -File .\install_task.ps1 -Remove
```

Which hours are actually checked is set in `settings.json`:

```json
"check_interval_hours": 6,
"check_anchor_hour": 5
```

This gives checks at 05:00, 11:00, 17:00 and 23:00; missed checks are caught up. With `"intensive_check_interval_hours": 2`, a webpage with a change is checked again 2 hours later (only this webpage), until no new change is found. `--force` checks at once. With `"dev_mode": {"enabled": true}` each check is shown in a visible terminal window.

E-mail by the script (`"mail_mode": "script"`), fixed times instead of hourly starts and further notes:
[DOCUMENTATION.md → Schedule](DOCUMENTATION.md#schedule-hourly-start-and-check-interval), [E-mail](DOCUMENTATION.md#e-mail-sent-by-the-script), [Scheduled runs](DOCUMENTATION.md#scheduled-runs-on-windows-task-scheduler).

## Output

The following text files are created on every run:

- `REPORT-of-every-run-last-3-days.txt`
  Log of every run of the last three days.
- `REPORT-daily-summary.txt`
  Report with a daily comparison. Can be sent by e-mail by the script itself (`"mail_mode": "script"`).
- `monitored-webpages/<shortname>/captured_*.txt`
  All captures are kept for 48 hours.
- `monitored-webpages/<shortname>/archive/*.txt`
  One capture per day is kept permanently in the archive.

Report layouts and exit codes: [DOCUMENTATION.md → Output](DOCUMENTATION.md#output).

## Security

- `webpages.json` reveals which webpages you monitor and can contain passwords. Therefore this file is excluded in `.gitignore`. Never commit this file.
- `secrets.json` contains the SMTP password and is also excluded in `.gitignore`. Never commit this file.
- `password_env` is preferable to `password`, because then no passwords are stored in plain text in the file.
- The reports list the URLs of the webpages, but passwords are never shown.

## License

[MIT](LICENSE)

## Authors

- Pepe HB9EVT
  https://github.com/pepe-hb9evt
- Claude (Anthropic)
  (AI in *Large Language Model* mode)
