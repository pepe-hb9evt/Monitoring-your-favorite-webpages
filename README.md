# Monitoring your favorite webpages

## Description

A small Python script that monitors your favorite webpages and logs changes to the **visible** content (text, images, links). The script cycles through your list of webpages and, each time it runs, saves the current visible content for each webpage and compares it to the last saved version. It then writes to a log file that indicates, for each webpage on your list, whether changes were detected and, if so, exactly what has changed.

The current version only reports what has changed, but does not tell you where on the webpage the change is located. Likewise, the script cannot yet process webpages that require a login.

### Limitations

The script is designed to compare text. Images and graphics are not compared visually; instead, only their hash values are compared. As a result, the script only detects that an image or graphic has been modified, but not what specific visual changes have been made.

The current version only reports what has changed, but does not tell you where on the webpage the change is located. Likewise, the script cannot yet process webpages that require a login.

Developesd for Windows, but runs on any system with Python 3.

### User Manual

This README provides a concise overview. For the complete reference, consult **[DOCUMENTATION.md](DOCUMENTATION.md)**

## Features

- Compares visible **text**, **images** and **links** separately; scripts, hidden elements and volatile URL noise are ignored.
- Detects replaced images even under the same URL (content hash).
- Site list in a JSON file, optionally with HTTP Basic login.
- Faulty entries or unreachable sites never stop the run.
- `report-last-3-days.txt`: all runs of the last three days, newest first.
- `daily-report.txt`: 24-hour comparison, rewritten after every run.
- Optional `settings.json` for file names, retention, timeout, user agent, …

## Requirements

- Python 3.9 or newer (Windows: [python.org](https://www.python.org/downloads/), option *Add python.exe to PATH*).
- `pip install -r requirements.txt`

## Installation

1. Copy the files into a project folder, e.g. `C:\Tools\webpages-monitor\`. All data is stored in this folder.
2. Copy `webpages.example.json` to `webpages.json` and enter your sites.
3. Optional: copy `settings.example.json` to `settings.json` and adjust values.
4. Test once: `python webpages_monitor.py`

The first run only saves a baseline; comparison starts with the second run.

## Site list (`webpages.json`)

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

All formats, rules and options: [DOCUMENTATION.md → Site list](DOCUMENTATION.md#site-list-webpagesjson).

## Scheduled runs (Windows)

```
schtasks /create /tn "Webpages Monitor 0600" /sc daily /st 06:00 /tr "cmd /c cd /d C:\Tools\webpages-monitor && python webpages_monitor.py"
```

Repeat for further times. GUI setup and notes: [DOCUMENTATION.md → Scheduled runs](DOCUMENTATION.md#scheduled-runs-on-windows-task-scheduler).

## Output

```
report-last-3-days.txt                         report of the last three days
daily-report.txt                               24-hour comparison
monitored-webpages/<shortname>/captured_*.txt  captures, kept 48 hours
monitored-webpages/<shortname>/archive/*.txt   one capture per day, permanent
```

Report layouts and exit codes: [DOCUMENTATION.md → Output](DOCUMENTATION.md#output).

## Security

- `webpages.json` can contain passwords and is listed in `.gitignore` – never commit it.
- Prefer `password_env` over `password`. Passwords never appear in reports.

## License

[MIT](LICENSE)

## Authors

- Pepe HB9EVT
  https://github.com/pepe-hb9evt
- Claude (Anthropic)
