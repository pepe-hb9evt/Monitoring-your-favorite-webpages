# Monitoring your favorite webpages

README for the project "**[Monitoring-your-favorite-webpages](https://github.com/pepe-hb9evt/Monitoring-your-favorite-webpages)**" on GitHub.

( German: ***Deutsche Version** dieses README verfügbar:* [README_deutsch_german.md](README_deutsch_german.md) )

<br>

## Description

This Python script monitors your favorite webpages and informs you when changes to the **visible** content (text, images, links) have been detected.

The script works through your list of webpages; on every run it saves the current visible content of each webpage and compares it with the previously saved version. It then writes two report files that list for each webpage whether changes were detected and, if so, exactly what has changed. Optionally, you are then informed by e-mail.

This requires a PC/notebook that runs around the clock, or at least all day, and is connected to the internet.

As of today, this project is implemented in a very basic way. In particular, the layout of the e-mails is not exactly polished. In addition, this project has various limitations (see the chapter of the same name below).

<br>

### User manual

This README gives a concise overview. For the complete reference, see **[DOCUMENTATION.md](DOCUMENTATION.md)**.

<br>

## Features

- Compares visible text, images and links separately. Scripts, hidden elements and volatile URL parts, on the other hand, are ignored.
- Detects replaced images, even if the image URL is unchanged.
- The webpages to check are listed in a JSON file, optionally with the credentials for an HTTP Basic login or the WordPress login form.
- If a webpage redirects to a login page that cannot be passed, this is reported as an error instead of storing the login page.
- While running, the terminal window shows which webpage is being fetched and the result.
- For test runs, an entry `STOP` in the webpage list ends the list; all following entries are skipped.
- Faulty entries or unreachable webpages never stop the run.
- Started every hour, the script checks only every N hours (`check_interval_hours`, e.g. 05:00, 11:00, 17:00, 23:00) and catches up on missed checks.
- Dev mode: shows a terminal window also for the windowless scheduled runs.
- Two text files are written on every run:

  - `REPORT-of-every-run-last-3-days.txt`: all runs of the last three days, newest first.

  - `REPORT-daily-summary.txt`: daily comparison (newest capture compared with the one that is at least 23 hours old).
- Optionally, you can be informed by e-mail about changes to the webpages you monitor. The configurable check interval also defines how often you receive such an e-mail.

Various parameters can be changed in `settings.json` (file names, retention, timeout, user agent, check interval, e-mail, dev mode, …).

<br>

## Limitations

As already mentioned in the introduction, this tool is very basic in its functionality (but it serves the purpose the author had in mind). The main limitations are:

- **Fetching:** Only the HTML delivered by the server is captured – without content loaded by JavaScript, without `<iframe>` content and without the content of PDF or Word files. Pages with a captcha or browser check cannot be monitored reliably.
- **Login:** Only HTTP Basic login and the WordPress login form; no other login forms, no "Sign in with Google/Microsoft", no two-factor authentication, no captcha.
- **Comparison:** The script reports *what* has changed (whole lines), not *where* on the webpage. Images are only compared by their hash value: it detects *that* an image has changed, but there is no before/after view. Changes to layout, colors or fonts are not detected.
- **Operation:** The script has to be started every hour (e.g. with the Windows Task Scheduler, `install_task.ps1`); it then decides itself which hours are checked. Notifications by e-mail only. The report covers three days; the archive is not cleaned up automatically.
- **E-mail:** The e-mail clearly shows that something has changed and what has changed. Apart from that, its layout leaves a lot to be desired.
- **Platform:** Developed for Windows, but runs on any system with Python 3.9 or newer.

All limitations in detail: [DOCUMENTATION.md → What the current version cannot do](DOCUMENTATION.md#what-the-current-version-cannot-do).

There are currently no plans by the author to develop this project further to remove some of these limitations. But maybe you would like to fork it and develop this project further.

<br>

## Requirements

- Python 3.9 or newer (Windows: [python.org](https://www.python.org/downloads/), option *Add python.exe to PATH*).
- `pip install -r requirements.txt`

<br>

## Installation

1. Copy the files into a project folder, e.g. `C:\Tools\webpages-monitor\`. All data is stored in this folder.
2. Copy `webpages.example.json` to `webpages.json` and enter your own webpages.
3. Optional: copy `settings.example.json` to `settings.json` and adjust values.
4. Optional for e-mail: switch on sending in `settings.json` and create `secrets.json` with the SMTP password (see chapter [Setting up e-mail](#setting-up-e-mail)). Sending can be tested with `python webpages_monitor.py --test-mail`.
5. Test the chosen parameters, see the instructions in chapter [Testing the chosen settings](#testing-the-chosen-settings).
6. Register the hourly task, see the instructions in chapter [Scheduled runs (Windows)](#scheduled-runs-windows).

The first run only saves a baseline; comparison starts with the second run.

<br>

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

If a webpage contains parts that change on every fetch (e.g. counters, dates, "related posts"), the script reports a change on every check and sends correspondingly many e-mails. Such parts can be hidden per webpage with the option `ignore`: [DOCUMENTATION.md → `ignore`](DOCUMENTATION.md#ignore).

<br>

## Setting up e-mail

By default, the script sends no e-mails. This is how sending is set up:

1. In `settings.json`, switch on sending and enter the server, sender and recipients:

   ```json
   "mail_mode": "script",
   "mail_condition": "always",
   "smtp": { "host": "smtp.gmail.com", "port": 587, "use_starttls": true, "use_ssl": false, "username": "sender@example-alpha.com" },
   "mail": { "sender": "sender@example-alpha.com", "recipients": ["recipient@example-bravo.com"], "subject_prefix": "[Webpage Monitoring]" }
   ```

   `"mail_condition": "always"` sends an e-mail after every check, `"on_change"` only on a change or an error.
2. Copy `secrets.example.json` to `secrets.json` and enter the SMTP password. For Gmail, this is an *app password* (Google account → Security → 2-step verification → App passwords), not the normal account password.
3. Test: `python webpages_monitor.py --test-mail`, or choose *Send test mail* in the menu `Menu for webpages-monitor-py.bat`.

This is how an e-mail starts:

```
Subject: [Webpage Monitoring] 1 changed, 0 errors since 4 hours

This run:      1 changed, 0 errors since last run 4 hours ago
Daily report:  2 changed, 0 without comparison
```

It is followed by the webpages with new information or with errors in this run, and then by the daily report.

All details: [DOCUMENTATION.md → E-mail sent by the script](DOCUMENTATION.md#e-mail-sent-by-the-script).

<br>

## Scheduled runs (Windows)

#### Windows Task Scheduler

To run the script automatically, it has to be registered in the Windows Task Scheduler. The task is set up so that the script is started once every hour (this is only the periodic start; whether a check and an e-mail actually take place depends, among other things, on the configurable check interval). The terminal window is not visible for these starts (unless dev mode is switched on, see below).

#### Registering / removing

To register the task in the Windows Task Scheduler, go to the project folder in a terminal (PowerShell) and enter this command:

```
.\install_task.ps1
```

If an error message says that running scripts is disabled on this system, use this command instead:

```
powershell -ExecutionPolicy Bypass -File .\install_task.ps1
```

If needed, the task can be removed again directly in the Windows Task Scheduler or with this command:

```
.\install_task.ps1 -Remove
```

or (see above):

```
powershell -ExecutionPolicy Bypass -File .\install_task.ps1 -Remove
```

#### Check interval

Which hours are actually checked is set in `settings.json`:

```json
"check_interval_hours": 6,
"check_anchor_hour": 5
```

This example sets the check interval (`check_interval_hours`) to **6 hours** and the first check of the day (`check_anchor_hour`) to **05:00**, which gives the check times of the rest of the day: checks at 05:00, 11:00, 17:00 and 23:00.

Missed checks, e.g. because the PC was switched off, are caught up by the script itself: if the last check is older than the check interval at the next hourly start, it checks at once.

#### Additional check

With `"intensive_check_interval_hours": 2`, webpages that changed or were not reachable are checked again 2 hours later (only these webpages); only if new content is found, an e-mail is sent and another such check follows, otherwise the additional check ends until the next regular check. The value must be smaller than `check_interval_hours`; `0` switches the additional check off.

#### All further information

Everything else is described in [DOCUMENTATION.md](DOCUMENTATION.md).

<br>

## Testing the chosen settings

Excerpt from `settings.json`:

```JSON
  "dev_mode": {
    "enabled": false,
    "keep_open_after_run_seconds": 20
  }
```

If "enabled" is set to true, the terminal becomes visible on every run and shows what the script is currently doing.

A manual check can be started

- with the batch file `Menu for webpages-monitor-py.bat` or
- in a terminal window with `python webpages_monitor.py --force`.

<br>

## Output

The following text files are created on every run:

- `REPORT-of-every-run-last-3-days.txt`
  Log of every run of the last three days.
- `REPORT-daily-summary.txt`
  Report with a daily comparison. Can be sent by e-mail by the script itself (`"mail_mode": "script"`).
- `monitored-webpages/<shortname>/captured_*.txt`
  All captures are kept for 48 hours. They are used to detect what has changed since the last run and within the last 24 hours (see the two reports above).
- `monitored-webpages/<shortname>/archive/*.txt`
  One capture per day is kept permanently in the archive.

Report layouts and exit codes: [DOCUMENTATION.md → Output](DOCUMENTATION.md#output).

<br>

## Security

- `webpages.json` reveals which webpages you monitor and can contain passwords. Therefore this file is excluded in `.gitignore`. Never commit this file.
- `secrets.json` contains the SMTP password and is also excluded in `.gitignore`. Never commit this file.
- `password_env` is preferable to `password`, because then no passwords are stored in plain text in the file.
- The reports list the URLs of the webpages, but passwords are never shown.

<br>

## License

[MIT](LICENSE)

<br>

## Authors

- Pepe HB9EVT
  https://github.com/pepe-hb9evt
- Claude (Anthropic)
  (AI in *Large Language Model* mode)
