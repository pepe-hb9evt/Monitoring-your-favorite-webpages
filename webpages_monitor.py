
#!/usr/bin/env python3

"""
Project:
    Monitoring your favorite webpages

Source code and documentation on GitHub:
    https://github.com/pepe-hb9evt/Monitoring-your-favorite-webpages

License:
    MIT

Authors
    Pepe HB9EVT, https://github.com/pepe-hb9evt
    Claude (Anthropic) (AI in 'Large Language Model' mode)
"""

import argparse
import difflib
import hashlib
import json
import os
import re
import smtplib
import ssl
import subprocess
import sys
import time
from email.message import EmailMessage
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
import soupsieve
from bs4 import BeautifulSoup, Comment

# --- Settings ------------------------------------------------------------------------------
# User-dependent values live in "settings.json" in the folder of this script.
# If the file or a key is missing, the defaults below apply.
PROJECT_DIR = Path(__file__).resolve().parent  # all files live in the folder of the script
SETTINGS_FILE = PROJECT_DIR / "settings.json"
SECRETS_FILE = PROJECT_DIR / "secrets.json"  # SMTP password, never part of the repository
STATE_FILE = PROJECT_DIR / "state.json"  # last regular check and webpages in intensive mode
STATE_TIME_FORMAT = "%Y-%m-%d %H:%M"
PASSWORD_PLACEHOLDER = "PUT-YOUR-GMAIL-APP-PASSWORD-HERE"
SITES_DIR = PROJECT_DIR / "monitored-webpages"  # one sub-folder per monitored webpage
DEFAULTS = {
    "webpages_file": "webpages.json",                 # webpage list (file name inside the project folder)
    "report_file": "REPORT-of-every-run-last-3-days.txt",  # report file (file name inside the project folder)
    "report_days": 3,                           # how long runs stay in the report (days)
    "daily_report_file": "REPORT-daily-summary.txt",       # daily comparison (file name inside the project folder)
    "daily_compare_hours": 23,                  # minimum age of the reference capture for the daily report
    "capture_keep_hours": 48,                   # how long capture files are kept (hours)
    "max_change_lines": 15,                     # change lines per webpage in the report
    "timeout_seconds": 45,                      # time limit per request
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    # URL parameters that may change on every request and are ignored when comparing
    "ignored_url_params": ["ver", "v", "_", "t", "ts", "time", "timestamp", "cb", "cachebust",
                           "sid", "phpsessid", "csrf", "csrf_token", "token", "nonce", "sectok",
                           "refresh"],  # refresh: changes on every request (WordPress Download Manager links)
    "image_hash": True,                         # download images and compare their content
    "image_max_count": 50,                      # max. downloaded images per page
    "image_max_bytes": 5000000,                 # max. bytes read per image (hash over this part)
    "image_timeout_seconds": 15,                # time limit per image
    "console_progress": True,                   # show progress per webpage in the terminal window
    # Schedule: the script is started every hour; a check is done every N hours
    "check_interval_hours": 1,                  # 1, 2, 3, 4, 6, 8, 12 or 24 (1 = check on every start)
    "check_anchor_hour": 0,                     # hour of day (0-23) the check grid starts from
    "intensive_check_interval_hours": 0,        # 0 = off; N = check changed/unreachable webpages again after N hours
    # Mail sent by this script (alternative to sending the reports by other means)
    "mail_mode": "none",                        # "none" = the script sends no mail, "script" = send by SMTP
    "mail_condition": "always",                 # "always" = after every check, "on_change" = only on change/error
    "smtp": {"host": "smtp.gmail.com", "port": 587, "use_starttls": True, "use_ssl": False, "username": ""},
    "mail": {"sender": "", "recipients": [], "subject_prefix": "[Webpage Monitoring]"},
    # Dev mode: show a terminal window also for windowless scheduled runs (pythonw.exe)
    "dev_mode": {"enabled": False, "keep_open_after_run_seconds": 60},  # seconds also used for manual starts
}
ALLOWED_INTERVALS = (1, 2, 3, 4, 6, 8, 12, 24)  # divisors of 24, so the grid repeats every day
CHOICES = {"mail_mode": ("none", "script"), "mail_condition": ("always", "on_change")}
# expected types of the keys inside the object settings
NESTED_TYPES = {
    "smtp": {"host": str, "port": int, "use_starttls": bool, "use_ssl": bool, "username": str},
    "mail": {"sender": str, "recipients": list, "subject_prefix": str},
    "dev_mode": {"enabled": bool, "keep_open_after_run_seconds": int},
}
SETTING_TYPES = {"webpages_file": str, "report_file": str, "daily_report_file": str, "daily_compare_hours": int,
                 "capture_keep_hours": int, "report_days": int, "max_change_lines": int,
                 "timeout_seconds": int, "user_agent": str, "ignored_url_params": list,
                 "image_hash": bool, "image_max_count": int, "image_max_bytes": int,
                 "image_timeout_seconds": int, "console_progress": bool,
                 "check_interval_hours": int, "check_anchor_hour": int,
                 "intensive_check_interval_hours": int, "mail_mode": str,
                 "mail_condition": str, "smtp": dict, "mail": dict, "dev_mode": dict}


def check_nested(key, value, problems):
    """Return the object setting merged with its defaults; invalid inner values keep the default."""
    merged = dict(DEFAULTS[key])
    for inner, inner_value in value.items():
        if inner.startswith("_"):
            continue
        expected = NESTED_TYPES[key].get(inner)
        if expected is None:
            problems.append(f"{SETTINGS_FILE.name}: unknown key '{key}.{inner}' ignored")
        elif isinstance(inner_value, bool) != (expected is bool) or not isinstance(inner_value, expected) \
                or (expected is int and inner_value < 0) \
                or (expected is list and not all(isinstance(x, str) and x.strip() for x in inner_value)):
            problems.append(f"{SETTINGS_FILE.name}: invalid value for '{key}.{inner}', default used")
        else:
            merged[inner] = inner_value
    return merged


def load_settings():
    """Return (settings, problems). Invalid values are replaced by the defaults."""
    cfg, problems = dict(DEFAULTS), []
    if not SETTINGS_FILE.exists():
        return cfg, problems
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError("a JSON object is expected")
    except Exception as e:
        return cfg, [f"{SETTINGS_FILE.name} not readable ({e}), defaults used"]
    for key, value in data.items():
        if key.startswith("_"):
            continue
        if key not in DEFAULTS:
            problems.append(f"{SETTINGS_FILE.name}: unknown key '{key}' ignored")
        elif SETTING_TYPES[key] is dict:
            if isinstance(value, dict):
                cfg[key] = check_nested(key, value, problems)
            else:
                problems.append(f"{SETTINGS_FILE.name}: invalid value for '{key}' (object expected), default used")
        elif key == "check_anchor_hour":
            if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 23:
                cfg[key] = value
            else:
                problems.append(f"{SETTINGS_FILE.name}: invalid value for '{key}' (0-23), default used")
        elif key == "intensive_check_interval_hours":
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                cfg[key] = value  # upper limit is checked below (depends on check_interval_hours)
            else:
                problems.append(f"{SETTINGS_FILE.name}: invalid value for '{key}' (0 = off, or hours), default used")
        elif key == "check_interval_hours" and value not in ALLOWED_INTERVALS:
            problems.append(f"{SETTINGS_FILE.name}: invalid value for '{key}' "
                            f"(allowed: {', '.join(map(str, ALLOWED_INTERVALS))}), default used")
        elif key in CHOICES and value not in CHOICES[key]:
            problems.append(f"{SETTINGS_FILE.name}: invalid value for '{key}' "
                            f"(allowed: {', '.join(CHOICES[key])}), default used")
        elif isinstance(value, bool) != (SETTING_TYPES[key] is bool) or not isinstance(value, SETTING_TYPES[key]) \
                or (SETTING_TYPES[key] is str and not value.strip()) \
                or (SETTING_TYPES[key] is int and value < 1) \
                or (SETTING_TYPES[key] is list and not all(isinstance(x, str) for x in value)):
            problems.append(f"{SETTINGS_FILE.name}: invalid value for '{key}', default used")
        else:
            cfg[key] = value
    intensive = cfg["intensive_check_interval_hours"]
    if intensive and intensive >= cfg["check_interval_hours"]:
        problems.append(f"{SETTINGS_FILE.name}: 'intensive_check_interval_hours' ({intensive}) must be smaller than "
                        f"'check_interval_hours' ({cfg['check_interval_hours']}), intensive check switched off")
        cfg["intensive_check_interval_hours"] = 0
    return cfg, problems


SETTINGS, SETTINGS_PROBLEMS = load_settings()
WEBPAGES_FILE = PROJECT_DIR / SETTINGS["webpages_file"]
REPORT_FILE = SETTINGS["report_file"]
DAILY_REPORT_FILE = SETTINGS["daily_report_file"]
REPORT_DAYS = SETTINGS["report_days"]
DAILY_COMPARE_HOURS = SETTINGS["daily_compare_hours"]
CAPTURE_KEEP_HOURS = SETTINGS["capture_keep_hours"]
CAPTURE_PREFIX = "captured_"
CAPTURE_FORMAT = "%Y-%m-%d_%HH%M"  # e.g. captured_2026-10-21_11H00.txt
CAPTURE_NAME = re.compile(r"^captured_(\d{4}-\d{2}-\d{2}_\d{2}H\d{2})\.txt$")
MAX_CHANGE_LINES = SETTINGS["max_change_lines"]
TIMEOUT = SETTINGS["timeout_seconds"]
UA = SETTINGS["user_agent"]
NOISE_PARAMS = {x.lower() for x in SETTINGS["ignored_url_params"]}
IMAGE_HASH = SETTINGS["image_hash"]
IMAGE_MAX_COUNT = SETTINGS["image_max_count"]
IMAGE_MAX_BYTES = SETTINGS["image_max_bytes"]
IMAGE_TIMEOUT = SETTINGS["image_timeout_seconds"]
CONSOLE_PROGRESS = SETTINGS["console_progress"]
CHECK_INTERVAL_HOURS = SETTINGS["check_interval_hours"]
CHECK_ANCHOR_HOUR = SETTINGS["check_anchor_hour"]
INTENSIVE_HOURS = SETTINGS["intensive_check_interval_hours"]
CATCH_UP_TOLERANCE = timedelta(minutes=10)  # a delayed start of the previous check still counts as on time
MAIL_MODE = SETTINGS["mail_mode"]
MAIL_CONDITION = SETTINGS["mail_condition"]
DEV_MODE = SETTINGS["dev_mode"]
PROGRESS_URL_WIDTH = 60  # longer URLs are shortened in the terminal window
PROGRESS_ERROR_WIDTH = 80  # longer error texts are shortened in the terminal window
IMAGE_CACHE = {}  # image URL -> hash, so an image used on several pages is downloaded once per run
LOGIN_SESSIONS = {}  # (login URL, username) -> logged-in requests.Session or error text, one login per run
LOGIN_TYPES = ("basic", "wordpress")
SITE_KEYS = ("url", "username", "password", "password_env", "login", "login_url", "accept_status",
             "ignore")  # allowed keys of a webpage entry in long form; keys starting with _ are comments
SECRETS_KEYS = ("smtp_password",)  # allowed keys in secrets.json; keys starting with _ are comments
STOP_KEY = "stop"  # key (any case) in webpages.json that ends the list; entries below it are skipped
STOP_SKIPPED = None  # number of entries skipped because of STOP in the current run, None = no STOP
WP_LOGGED_IN_COOKIE = "wordpress_logged_in_"  # prefix of the cookie WordPress sets after a successful login
UNKNOWN_HASH = "?"  # image could not be downloaded; ignored when comparing
IMAGE_LINE = re.compile(r"^(.*) \| sha1=([0-9a-f]{16}|\?)$")
HIDDEN_STYLE = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.I)
PIXEL = re.compile(r"(pixel|tracking|spacer|blank\.gif|1x1)", re.I)
HEADER = re.compile(r"^=== Run (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) ===$")


# --- Terminal progress ---------------------------------------------------------------------
def progress(text="", end="\n"):
    """Write a progress message to the terminal window immediately (no buffering)."""
    if not CONSOLE_PROGRESS:
        return
    try:
        print(text, end=end, flush=True)
    except Exception:
        pass  # the terminal output must never stop the run


def short_url(url):
    return url if len(url) <= PROGRESS_URL_WIDTH else url[:PROGRESS_URL_WIDTH - 3] + "..."


def progress_status(lines, status):
    """Short result text of one webpage for the terminal window."""
    if status == "error":
        text = "ERROR: " + lines[0].removeprefix("URL not reachable: ")
        return text if len(text) <= PROGRESS_ERROR_WIDTH else text[:PROGRESS_ERROR_WIDTH - 3] + "..."
    return {"ok": "no change", "first": "first run", "changed": "CHANGED"}.get(status, status)


# --- Content extraction --------------------------------------------------------------------
def clean_url(url, base):
    """Make a URL absolute and drop fragments and volatile parameters."""
    if not url or url.strip() in ("", "<>", "#"):
        return None
    if url.strip().lower().startswith("javascript:"):
        return "javascript:"  # code often contains random names (e.g. e-mail obfuscation)
    url = urljoin(base, url.strip())
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        return url  # mailto:, tel: etc. unchanged
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
         if k.lower() not in NOISE_PARAMS and not (k.isdigit() and v == "")]
    # timestamp-like bare numeric parameters (e.g. taskrunner.php?...&1699999999)
    q = [(k, v) for k, v in q if not (v == "" and re.fullmatch(r"\d{8,}", k))]
    return urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(q), ""))


def is_hidden(tag):
    if tag.name is None or not hasattr(tag, "attrs") or tag.attrs is None:
        return False
    if tag.has_attr("hidden"):
        return True
    if tag.get("aria-hidden", "").lower() == "true":
        return True
    return bool(HIDDEN_STYLE.search(tag.get("style", "") or ""))


def extract(html, base_url, remove_selectors=None):
    """Return (text_lines, images, links) of the visible content.
    remove_selectors: CSS selectors of elements removed with all their content (ignore.elements)."""
    soup = BeautifulSoup(html, "lxml")
    for t in soup.find_all(string=lambda s: isinstance(s, Comment)):
        t.extract()
    for t in soup(["script", "style", "noscript", "template", "head"]):
        t.decompose()
    for t in [t for t in soup.find_all(True) if is_hidden(t)]:
        t.decompose()
    for selector in remove_selectors or []:  # volatile page areas, e.g. "div.prop-list"
        for t in soup.select(selector):
            if not t.decomposed:  # already removed together with a matching parent
                t.decompose()

    images, links = [], []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if not src and img.get("srcset"):
            src = img["srcset"].split(",")[0].strip().split(" ")[0]
        u = clean_url(src, base_url)
        if not u or u.startswith("data:") or PIXEL.search(u):
            continue
        if img.get("width") == "1" and img.get("height") == "1":
            continue
        images.append(f"{u} | alt={' '.join((img.get('alt') or '').split())}")
    for svg in soup.find_all("svg"):
        h = hashlib.sha1(re.sub(r"\s+", " ", str(svg)).encode()).hexdigest()[:16]
        images.append(f"inline-svg | sha1={h}")
    for a in soup.find_all("a", href=True):
        u = clean_url(a["href"], base_url)
        if not u:
            continue
        txt = " ".join(a.get_text(" ", strip=True).split())
        links.append(f"{txt} -> {u}")

    # full text, line by line in document order
    block = ("p div li ul ol tr td th table h1 h2 h3 h4 h5 h6 section article header footer "
             "nav main aside form pre blockquote dd dt dl br hr fieldset legend").split()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for t in soup.find_all(block):
        t.insert_before("\n")
        t.insert_after("\n")
    lines = [" ".join(z.split()) for z in soup.get_text().splitlines()]
    return [z for z in lines if z], images, links


# --- Image content -------------------------------------------------------------------------
def image_hash(url, auth, session=None):
    """Return the first 16 hex digits of the SHA1 of the image bytes, or UNKNOWN_HASH on any problem.
    session: logged-in session of a login-form webpage (its cookies only go to their own domain)."""
    if url in IMAGE_CACHE:
        return IMAGE_CACHE[url]
    result = UNKNOWN_HASH
    try:
        getter = session.get if session is not None else requests.get
        with getter(url, headers={"User-Agent": UA}, timeout=IMAGE_TIMEOUT,
                    auth=auth, stream=True, allow_redirects=True) as r:
            r.raise_for_status()
            ct = r.headers.get("Content-Type", "").lower()
            if not ct or ct.startswith("image/") or "octet-stream" in ct:
                h, size = hashlib.sha1(), 0
                for chunk in r.iter_content(65536):
                    chunk = chunk[:IMAGE_MAX_BYTES - size]
                    h.update(chunk)
                    size += len(chunk)
                    if size >= IMAGE_MAX_BYTES:
                        break
                if size:
                    result = h.hexdigest()[:16]
    except Exception:
        pass  # unreachable image: hash stays unknown, no false change
    IMAGE_CACHE[url] = result
    return result


def add_image_hashes(images, page_url, auth, session=None):
    """Append ' | sha1=...' to each <img> line. Credentials are only sent to the host of the page."""
    host, out, fetched = urlparse(page_url).netloc.lower(), [], 0
    for line in images:
        if line.startswith("inline-svg"):
            out.append(line)
            continue
        url = line.split(" | alt=", 1)[0]
        h = UNKNOWN_HASH
        if urlparse(url).scheme in ("http", "https") and (fetched < IMAGE_MAX_COUNT or url in IMAGE_CACHE):
            fetched += url not in IMAGE_CACHE
            h = image_hash(url, auth if urlparse(url).netloc.lower() == host else None, session)
        out.append(f"{line} | sha1={h}")
    return out


def split_image_line(line):
    """Return (base, hash) of an <img> line; hash is None for lines without hash (image_hash off)."""
    m = IMAGE_LINE.match(line)
    return (m.group(1), m.group(2)) if m else (line, None)


def align_image_hashes(old, new):
    """Ignore the image hash where it is missing or unknown on one side, so that switching image_hash
    and temporarily unreachable images do not show up as changes."""
    old_by_base = {}
    for line in old:
        if not line.startswith("inline-svg"):
            base, h = split_image_line(line)
            old_by_base.setdefault(base, (line, h))
    aligned = []
    for line in new:
        base, h = split_image_line(line)
        if not line.startswith("inline-svg") and base in old_by_base:
            old_line, old_h = old_by_base[base]
            if h in (None, UNKNOWN_HASH) or old_h in (None, UNKNOWN_HASH):
                line = old_line
        aligned.append(line)
    return aligned


def build_file(text, images, links):
    return "\n".join(text + ["", "=== IMAGES ==="] + images + ["", "=== LINKS ==="] + links) + "\n"


def split_sections(content):
    sections, cur = {"TEXT": [], "IMAGES": [], "LINKS": []}, "TEXT"
    for line in content.splitlines():
        if line == "=== IMAGES ===":
            cur = "IMAGES"
        elif line == "=== LINKS ===":
            cur = "LINKS"
        elif line:
            sections[cur].append(line)
    return sections


def diff_lines(old, new, title):
    out = []
    for z in difflib.unified_diff(old, new, lineterm="", n=0):
        if z.startswith(("---", "+++", "@@")):
            continue
        out.append(("  removed: " if z[0] == "-" else "  added:   ") + z[1:])
    return [f" [{title}]"] + out if out else []


def apply_ignore(sections, rules):
    """Remove lines matching the ignore rules of a webpage ({section: [compiled regex, ...]})."""
    if not rules:
        return sections
    # rules["ELEMENTS"] (CSS selectors) is applied during extraction, not here
    return {sec: [z for z in lines if not any(p.search(z) for p in rules.get(sec, []))]
            for sec, lines in sections.items()}


def compare(old_content, new_content, ignore=None):
    """Return (diff_lines, notes) for two capture contents.
    ignore: per-webpage rules; matching lines are removed on both sides before comparing."""
    a = apply_ignore(split_sections(old_content), ignore)
    n = apply_ignore(split_sections(new_content), ignore)
    notes = []
    if len(a["TEXT"]) >= 10 and len(n["TEXT"]) < 0.3 * len(a["TEXT"]):
        notes.append(f"Note: text shrank a lot ({len(a['TEXT'])} -> {len(n['TEXT'])} lines), page may be broken")
    n["IMAGES"] = align_image_hashes(a["IMAGES"], n["IMAGES"])
    d = diff_lines(a["TEXT"], n["TEXT"], "Text") + diff_lines(a["IMAGES"], n["IMAGES"], "Images") \
        + diff_lines(a["LINKS"], n["LINKS"], "Links")
    return d, notes


def age_hours(now, reference):
    """Age in whole hours; 30 minutes and more are rounded up."""
    return (int((now - reference).total_seconds() // 60) + 30) // 60


# --- Capture files -------------------------------------------------------------------------
def capture_path(folder, when):
    return folder / f"{CAPTURE_PREFIX}{when.strftime(CAPTURE_FORMAT)}.txt"


def list_captures(folder):
    """Return [(timestamp, path), ...] of all capture files, oldest first."""
    found = []
    if folder.is_dir():
        for p in folder.iterdir():
            m = CAPTURE_NAME.match(p.name)
            if m and p.is_file():
                found.append((datetime.strptime(m.group(1), CAPTURE_FORMAT), p))
    return sorted(found)


def prune_captures(folder, now):
    """Delete captures older than CAPTURE_KEEP_HOURS; the two newest are always kept."""
    limit = now - timedelta(hours=CAPTURE_KEEP_HOURS)
    for when, path in list_captures(folder)[:-2]:
        if when < limit:
            path.unlink()


# --- Report --------------------------------------------------------------------------------
def shorten(lines):
    if len(lines) <= MAX_CHANGE_LINES:
        return lines
    return lines[:MAX_CHANGE_LINES] + [f"  ... and {len(lines) - MAX_CHANGE_LINES} more lines"]


def interval_text(delta):
    """Up to 99 minutes in minutes, from 100 minutes on in hours (rounded, half up)."""
    minutes = int((delta.total_seconds() + 30) // 60)
    if minutes < 100:
        return f"{minutes} {'minute' if minutes == 1 else 'minutes'}"
    hours = (minutes + 30) // 60
    return f"{hours} hours"


def write_report(now, short):
    """Newest run first; runs older than REPORT_DAYS days are removed."""
    path = PROJECT_DIR / REPORT_FILE
    blocks, head, cur = [], None, []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = HEADER.match(line)
            if m:
                if head:
                    blocks.append((head, cur))
                head, cur = m.group(1), [line]
            elif head:
                cur.append(line)
        if head:
            blocks.append((head, cur))
    earlier = [datetime.strptime(b[0], "%Y-%m-%d %H:%M") for b in blocks]
    earlier = [t for t in earlier if t < now]
    gap = f"Previous run: {interval_text(now - max(earlier))} ago" if earlier else "Previous run: none"
    new = (f"{now:%Y-%m-%d %H:%M}", [f"=== Run {now:%Y-%m-%d %H:%M} ===", "", gap, ""] + short)
    limit = now - timedelta(days=REPORT_DAYS)
    allb = [new] + [b for b in blocks if datetime.strptime(b[0], "%Y-%m-%d %H:%M") >= limit]
    allb.sort(key=lambda b: b[0], reverse=True)
    path.write_text("\n".join("\n".join(b[1]).rstrip() + "\n\n\n\n" for b in allb), encoding="utf-8")


def finished_time():
    """Clock time (hh:mm:ss) at which the run finished, for the line "Run finished" in the report."""
    return datetime.now().strftime("%H:%M:%S")


def group_entries(title, entries):
    out = [title, ""]
    for e in entries:
        out += e + [""]
    return out if entries else [title, "(none)", ""]


def build_daily_report(now, sites, failed):
    """Compare per webpage the newest capture with the newest capture at least DAILY_COMPARE_HOURS old
    (or with the oldest capture if none is old enough). failed: {name: error text of this run}.
    Return (lines, stats); stats = {"hours": reference age, "changed": n, "no_comparison": n}."""
    limit = now - timedelta(hours=DAILY_COMPARE_HOURS)
    no_comparison, changed, unchanged, ages, fallback_ages = [], [], [], [], set()
    for name, entry in sites.items():
        url = entry["url"]
        if name in failed:
            no_comparison.append([url, "ERROR: " + failed[name]])
            continue
        captures = list_captures(SITES_DIR / name)
        if len(captures) < 2:
            no_comparison.append([url, "Only one capture available, no comparison possible"])
            continue
        newest = captures[-1]
        old_enough = [c for c in captures[:-1] if c[0] <= limit]  # oldest first
        reference = old_enough[-1] if old_enough else captures[0]  # newest old enough, else oldest available
        try:
            d, notes = compare(reference[1].read_text(encoding="utf-8"), newest[1].read_text(encoding="utf-8"),
                               entry.get("ignore"))
        except Exception as e:
            no_comparison.append([url, f"ERROR: capture file not readable: {type(e).__name__}: {e}"])
            continue
        ages.append(age_hours(now, reference[0]))
        if not old_enough:
            fallback_ages.add(ages[-1])
        if d:
            changed.append([url, "Changed"] + shorten(d) + notes)
        else:
            unchanged.append(f"-  {url}")
    # most frequent reference age (webpages usually share the same run times)
    hours = max(set(ages), key=ages.count) if ages else DAILY_COMPARE_HOURS
    title = f"Newest capture compared with the capture from {hours} {'hour' if hours == 1 else 'hours'} ago."
    if ages and hours in fallback_ages:  # no capture old enough yet: the oldest one was used
        title += " (oldest capture available)"
    lines = [title, ""]
    lines += group_entries("No comparison possible for:", no_comparison) + [""]
    lines += group_entries("Changes were detected on the following webpages:", changed) + [""]
    lines += ["The following webpages are unchanged:"] + (unchanged or ["(none)"]) + [""]
    lines.append(f"Daily report finished: {len(sites)} webpages, {len(changed)} changed, "
                 f"{len(no_comparison)} without comparison")
    return lines, {"hours": hours, "changed": len(changed), "no_comparison": len(no_comparison)}


def since_text(delta):
    """Time since the previous run for the mail: below one hour in minutes, otherwise in whole hours."""
    minutes = int((delta.total_seconds() + 30) // 60)
    if minutes < 60:
        return f"{minutes} {'minute' if minutes == 1 else 'minutes'}"
    hours = (minutes + 30) // 60
    return f"{hours} {'hour' if hours == 1 else 'hours'}"


def mail_subject_text(now, previous, count):
    """Short subject: result of this run, e.g. '0 changed, 0 errors since 1 hour'."""
    since = f"since {since_text(now - previous)}" if previous else "(first run)"
    return f"{count['changed']} changed, {count['error']} errors {since}"


def mail_intro(now, previous, count, sites_text, changed_urls, error_urls, daily_stats, intensive=False):
    """Lines at the top of the mail: summary, then this run (changed webpages, errors), then the daily report."""
    since = f"since last run {since_text(now - previous)} ago" if previous else "(first run)"
    lines = [f"This run:      {count['changed']} changed, {count['error']} errors {since}",
             f"Daily report:  {daily_stats['changed']} changed, {daily_stats['no_comparison']} without comparison",
             "", "",
             f"=== {'Intensive run' if intensive else 'Run'} {now:%Y-%m-%d %H:%M} ({sites_text}) ===", ""]
    if intensive:
        lines += ["Only webpages with a recent change were fetched.", ""]
    lines += ["New information on:"] + ([f"-  {u}" for u in changed_urls] or ["(none)"]) + [""]
    lines += ["Errors:"] + ([f"-  {u}" for u in error_urls] or ["(none)"]) + ["", "", ""]
    return lines


def write_daily_report(now, lines):
    """Replace the daily report file and return its content (also used as mail text)."""
    content = "\n".join([f"=== Daily report {now:%Y-%m-%d %H:%M} ===", ""] + lines).rstrip() + "\n"
    (PROJECT_DIR / DAILY_REPORT_FILE).write_text(content, encoding="utf-8")
    return content


# --- Webpage list --------------------------------------------------------------------------
IGNORE_SECTIONS = {"text": "TEXT", "images": "IMAGES", "links": "LINKS"}
IGNORE_ELEMENTS = "elements"  # key in "ignore" for CSS selectors of HTML elements to remove


def parse_ignore(key, raw):
    """Parse the optional 'ignore' object of a webpage: {"text"|"images"|"links": [pattern, ...],
    "elements": [CSS selector, ...]}.
    A pattern is a case-insensitive substring, or a regular expression with the prefix 're:'.
    Return ({section: [compiled regex, ...], "ELEMENTS": [selector, ...]}, problems);
    faulty rules are dropped."""
    rules, problems = {}, []
    if raw is None:
        return rules, problems
    if not isinstance(raw, dict):
        return rules, [f"Entry '{key}': 'ignore' must be an object with 'text', 'images', 'links', "
                       "'elements' (rules ignored, webpage still monitored)"]
    for sub, patterns in raw.items():
        if sub.startswith("_"):
            continue
        if sub not in IGNORE_SECTIONS and sub != IGNORE_ELEMENTS:
            problems.append(f"Entry '{key}': unknown key 'ignore.{sub}' ignored "
                            "(allowed: text, images, links, elements)")
            continue
        if not isinstance(patterns, list):
            what = "CSS selectors" if sub == IGNORE_ELEMENTS else "patterns"
            problems.append(f"Entry '{key}': 'ignore.{sub}' must be a list of {what} (rules ignored)")
            continue
        if sub == IGNORE_ELEMENTS:
            selectors = []
            for sel in patterns:
                if not isinstance(sel, str) or not sel.strip():
                    problems.append(f"Entry '{key}': empty or invalid selector in 'ignore.elements' ignored: {sel!r}")
                    continue
                try:
                    soupsieve.compile(sel.strip())  # check the syntax once while loading
                    selectors.append(sel.strip())
                except Exception as e:
                    problems.append(f"Entry '{key}': invalid CSS selector in 'ignore.elements' ignored: "
                                    f"{sel!r} ({str(e).splitlines()[0]})")  # first line only
            if selectors:
                rules["ELEMENTS"] = selectors
            continue
        compiled = []
        for p in patterns:
            if not isinstance(p, str) or not p.strip() or p.strip() == "re:":
                problems.append(f"Entry '{key}': empty or invalid pattern in 'ignore.{sub}' ignored: {p!r}")
                continue
            try:
                compiled.append(re.compile(p[3:], re.I) if p.startswith("re:") else re.compile(re.escape(p), re.I))
            except re.error as e:
                problems.append(f"Entry '{key}': invalid regular expression in 'ignore.{sub}' ignored: "
                                f"{p!r} ({e})")
        if compiled:
            rules[IGNORE_SECTIONS[sub]] = compiled
    return rules, problems


def load_sites():
    """Read webpages.json (short form "name": "URL" or long form with username/password).
    Return (valid_sites, fatal_problems, entry_problems).
    Fatal problems (file missing/broken/empty) prevent the run; invalid single entries
    are skipped and only logged. A key "STOP" ends the list (sets STOP_SKIPPED)."""
    global STOP_SKIPPED
    STOP_SKIPPED = None
    if not WEBPAGES_FILE.exists():
        return None, [f"File missing: {WEBPAGES_FILE}"], []
    duplicates = []
    try:
        def pairs(items):
            d = {}
            for k, v in items:
                if k in d and not k.startswith("_"):  # comment keys may appear several times
                    duplicates.append((k, d))  # d identifies the object that holds the duplicate
                d.setdefault(k, v)  # the first entry wins
            return d
        data = json.loads(WEBPAGES_FILE.read_text(encoding="utf-8-sig"), object_pairs_hook=pairs)
    except Exception as e:
        return None, [f"File not readable or not valid JSON: {e}"], []
    if not isinstance(data, dict) or not data:
        return None, ['Wrong content: a non-empty object {"shortname": "URL", ...} is expected'], []
    good = {}
    problems = []
    for k, holder in duplicates:
        if holder is data:
            problems.append(f"Short name '{k}' appears more than once, only the first entry is used")
        else:
            entry = next((name for name, value in data.items() if value is holder
                          or (isinstance(value, dict) and any(v is holder for v in value.values()))), "?")
            problems.append(f"Entry '{entry}': key '{k}' appears more than once, only the first value is used "
                            "(put several values into one list, e.g. \"accept_status\": [500, 502])")
    keys = list(data)
    for index, (key, value) in enumerate(data.items()):
        if key.startswith("_"):  # comment key, e.g. "_comment"
            continue
        if key.lower() == STOP_KEY:  # test runs: ignore everything below
            STOP_SKIPPED = sum(1 for k in keys[index + 1:] if not k.startswith("_"))
            break
        if isinstance(value, str):  # short form: "shortname": "URL"
            value = {"url": value}
        if not re.fullmatch(r"[A-Za-z0-9._-]+", key):
            problems.append(f"Entry '{key}' skipped: invalid short name (allowed: letters, digits, . _ -)")
        elif not isinstance(value, dict) or not isinstance(value.get("url"), str) \
                or not re.match(r"https?://[^\s/]+", value["url"]):
            problems.append(f"URL of '{key}' invalid: {(value.get('url') if isinstance(value, dict) else value)!r} "
                            "(entry skipped; http:// or https:// expected)")
        else:
            unknown = [k for k in value if not k.startswith("_") and k not in SITE_KEYS]
            if unknown:  # e.g. a misspelt "pasword"; the webpage is still processed
                problems.append(f"Entry '{key}': unknown {'key' if len(unknown) == 1 else 'keys'} "
                                f"{', '.join(repr(k) for k in unknown)} ignored (allowed: {', '.join(SITE_KEYS)}; "
                                "keys starting with _ are comments)")
            username = value.get("username")
            password = value.get("password")
            if value.get("password_env"):
                password = os.environ.get(value["password_env"])
                if password is None:
                    problems.append(f"Entry '{key}' skipped: environment variable "
                                    f"'{value['password_env']}' is not set")
                    continue
            if bool(username) != bool(password):
                problems.append(f"Entry '{key}' skipped: 'username' and 'password' must be given together")
                continue
            login = value.get("login", "basic")
            if login not in LOGIN_TYPES:
                problems.append(f"Entry '{key}' skipped: 'login' must be one of {', '.join(LOGIN_TYPES)}")
                continue
            if login == "wordpress" and not username:
                problems.append(f"Entry '{key}' skipped: login 'wordpress' needs 'username' and 'password' "
                                "or 'password_env'")
                continue
            login_url = value.get("login_url")
            if login_url is None and login == "wordpress":
                p = urlparse(value["url"])
                login_url = f"{p.scheme}://{p.netloc}/wp-login.php"
            if login == "wordpress" and (not isinstance(login_url, str)
                                         or not re.match(r"https?://[^\s/]+", login_url)):
                problems.append(f"Entry '{key}' skipped: 'login_url' invalid (http:// or https:// expected)")
                continue
            accept = value.get("accept_status", [])
            if not isinstance(accept, list) or not all(
                    isinstance(c, int) and not isinstance(c, bool) and 400 <= c <= 599 for c in accept):
                problems.append(f"Entry '{key}' skipped: 'accept_status' must be a list of HTTP codes 400-599")
                continue
            ignore, ignore_problems = parse_ignore(key, value.get("ignore"))
            problems += ignore_problems  # faulty rules are dropped, the webpage is still monitored
            credentials = (username, password) if username else None
            good[key] = {"url": value["url"], "auth": credentials if login == "basic" else None,
                         "form_login": (login, login_url, credentials) if login != "basic" else None,
                         "accept_status": set(accept), "ignore": ignore}
    if not good:
        first = " (STOP is the first entry)" if STOP_SKIPPED is not None else ""
        return None, ["No valid URL in the webpage list" + first] + problems, []
    return good, [], problems


def error_text(e):
    if isinstance(e, requests.exceptions.Timeout):
        return f"URL not reachable: timeout ({TIMEOUT} s)"
    if isinstance(e, requests.exceptions.SSLError):
        return f"URL not reachable: SSL/certificate error ({e})"
    if isinstance(e, requests.exceptions.ConnectionError):
        return f"URL not reachable: connection failed ({e})"
    if isinstance(e, requests.exceptions.HTTPError):
        return f"URL not reachable: HTTP error {e.response.status_code} {e.response.reason or ''}".strip()
    return f"Request failed: {type(e).__name__}: {e}"


def wordpress_login(login_url, credentials, target_url):
    """Log in through the WordPress login form. Return (session, None) or (None, error text).
    The password is only sent to login_url and never appears in error texts."""
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "de,en;q=0.7"})
    login = urlparse(login_url)
    # Open the target page first, like a browser: it usually redirects to the webpage's login page and sets
    # its cookies. A direct GET of wp-login.php is avoided, because some webpages drop such requests.
    referer = target_url
    try:
        referer = session.get(target_url, timeout=TIMEOUT, allow_redirects=True).url
    except Exception:
        pass  # not needed for the login itself
    try:
        session.cookies.set("wordpress_test_cookie", "WP Cookie check", domain=login.hostname, path="/")
        r = session.post(login_url, timeout=TIMEOUT, allow_redirects=True,
                         headers={"Referer": referer, "Origin": f"{login.scheme}://{login.netloc}"},
                         data={"log": credentials[0], "pwd": credentials[1], "rememberme": "forever",
                               "wp-submit": "Log In", "redirect_to": target_url, "testcookie": "1"})
        r.raise_for_status()
    except Exception as e:
        return None, "Login failed: " + error_text(e)
    if not any(c.name.startswith(WP_LOGGED_IN_COOKIE) for c in session.cookies):
        return None, "Login failed: username or password not accepted (no login cookie received)"
    return session, None


def get_login_session(form_login, target_url):
    """Return (session, error text) for a login-form webpage; one login per login URL and user per run."""
    login, login_url, credentials = form_login
    key = (login_url, credentials[0])
    if key not in LOGIN_SESSIONS:
        progress("login... ", end="")  # shown in the progress line of the page that triggers the login
        session, error = wordpress_login(login_url, credentials, target_url)
        LOGIN_SESSIONS[key] = session if session is not None else error
    cached = LOGIN_SESSIONS[key]
    return (None, cached) if isinstance(cached, str) else (cached, None)


def looks_like_login_page(requested_url, response):
    """True if the request was redirected to a login page instead of the requested page."""
    if not response.history:
        return False
    final = urlparse(response.url)
    return final.path != urlparse(requested_url).path and ("login" in final.path.lower()
                                                            or "login" in final.query.lower())


def process_site(name, url, auth, now, accept_status=frozenset(), ignore=None, form_login=None):
    """Return (lines, status); status: 'ok' | 'first' | 'changed' | 'error'.
    accept_status: HTTP error codes whose response content is used anyway (server misconfiguration).
    ignore: per-webpage rules; "ELEMENTS" selectors are removed before extraction (not in the capture),
            line rules are only applied when comparing (captures stay complete).
    form_login: (type, login URL, (username, password)) for webpages behind a login form, else None."""
    folder = SITES_DIR / name
    notes = []
    session = None
    if form_login:
        session, error = get_login_session(form_login, url)
        if error:
            return [error], "error"
    try:
        getter = session.get if session is not None else requests.get
        r = getter(url, headers={"User-Agent": UA, "Accept-Language": "de,en;q=0.7"},
                   timeout=TIMEOUT, allow_redirects=True, auth=auth)
        if r.status_code in accept_status:
            notes.append(f"Note: server answered HTTP {r.status_code} {r.reason or ''}".rstrip()
                         + ", content used anyway")
        else:
            r.raise_for_status()
    except Exception as e:
        return [error_text(e)], "error"

    # content checks
    if looks_like_login_page(url, r):
        return ["Login failed: redirected to the login page (login missing, not accepted or no access); "
                "copy not overwritten"], "error"
    ct = r.headers.get("Content-Type", "")
    if ct and "html" not in ct.lower() and "xml" not in ct.lower():
        return [f"Content faulty: unexpected content type '{ct}' (not HTML)"], "error"
    try:
        r.encoding = r.encoding if r.encoding and r.encoding.lower() != "iso-8859-1" else r.apparent_encoding
        text, images, links = extract(r.text, r.url, (ignore or {}).get("ELEMENTS"))
    except Exception as e:
        return [f"Content faulty: HTML could not be parsed ({type(e).__name__}: {e})"], "error"
    if not text or sum(len(z) for z in text) < 30:
        return ["Content faulty: no or almost no visible text (page empty or error page?); "
                "copy not overwritten"], "error"
    if not links:
        notes.append("Note: no links found")
    if IMAGE_HASH:
        images = add_image_hashes(images, url, auth, session)

    content = build_file(text, images, links)
    try:
        (folder / "archive").mkdir(parents=True, exist_ok=True)
        older = [c for c in list_captures(folder) if c[0] < now]
        old_content = older[-1][1].read_text(encoding="utf-8") if older else None
        capture_path(folder, now).write_text(content, encoding="utf-8")
        (folder / "archive" / f"{now:%Y-%m-%d}.txt").write_text(content, encoding="utf-8")
        prune_captures(folder, now)
    except Exception as e:
        return [f"Saving failed in {folder}: {type(e).__name__}: {e}"], "error"

    if old_content is None:
        return ["First run, baseline saved, no comparison possible"] + notes, "first"
    d, more_notes = compare(old_content, content, ignore)
    notes += more_notes
    if d:
        return ["Changed"] + shorten(d) + notes, "changed"
    return ["No change"] + notes, "ok"


# --- Schedule ------------------------------------------------------------------------------
def last_check_time():
    """Time of the newest run in the report file, None if there is none (or the file is not readable)."""
    path = PROJECT_DIR / REPORT_FILE
    newest = None
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            m = HEADER.match(line)
            if m:
                when = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M")
                newest = when if newest is None or when > newest else newest
    except Exception:
        return None
    return newest


def next_grid_time(now):
    """Next full hour on the check grid after now."""
    candidate = now.replace(minute=0) + timedelta(hours=1)
    while (candidate.hour - CHECK_ANCHOR_HOUR) % CHECK_INTERVAL_HOURS:
        candidate += timedelta(hours=1)
    return candidate


def parse_state_time(value):
    try:
        return datetime.strptime(value, STATE_TIME_FORMAT)
    except (TypeError, ValueError):
        return None


def load_state():
    """state.json: {"last_regular_check": time, "intensive": {shortname: time of its last check}}.
    A missing or broken file gives an empty state (the report is then used for the last check)."""
    state = {"last_regular_check": None, "intensive": {}}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return state
    if isinstance(data, dict):
        state["last_regular_check"] = parse_state_time(data.get("last_regular_check"))
        intensive = data.get("intensive")
        if isinstance(intensive, dict):
            state["intensive"] = {k: t for k, v in intensive.items() if (t := parse_state_time(v))}
    return state


def save_state(state):
    """Write state.json (via a temporary file, so a broken file cannot remain)."""
    data = {"_comment": "Written by webpages_monitor.py - do not edit",
            "last_regular_check": (state["last_regular_check"].strftime(STATE_TIME_FORMAT)
                                   if state["last_regular_check"] else None),
            "intensive": {k: v.strftime(STATE_TIME_FORMAT) for k, v in sorted(state["intensive"].items())}}
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, STATE_FILE)


def intensive_due(now, state):
    """Short names on the intensive list whose last check is at least INTENSIVE_HOURS old."""
    if not INTENSIVE_HOURS:
        return []
    limit = timedelta(hours=INTENSIVE_HOURS) - CATCH_UP_TOLERANCE
    return [name for name, last in state["intensive"].items() if now - last >= limit]


def check_due(now, state):
    """Return (mode, reason): mode "regular", "intensive" or None (nothing due).
    Regular: on the grid hour (anchor + n * interval) or as catch-up when the last regular check is
    older than the interval (e.g. the computer was switched off at the grid hour).
    Intensive: webpages on the intensive list (changed or not reachable at the previous check)
    whose last check is INTENSIVE_HOURS old."""
    if (now.hour - CHECK_ANCHOR_HOUR) % CHECK_INTERVAL_HOURS == 0:
        return "regular", "scheduled check"
    last = state["last_regular_check"] or last_check_time()
    if last is None:
        return "regular", "catch-up check (no previous check found)"
    if now - last >= timedelta(hours=CHECK_INTERVAL_HOURS) - CATCH_UP_TOLERANCE:
        return "regular", f"catch-up check (last regular check {interval_text(now - last)} ago)"
    names = intensive_due(now, state)
    if names:
        return "intensive", f"intensive check of {len(names)} {'webpage' if len(names) == 1 else 'webpages'}"
    pending = ""
    if state["intensive"]:
        upcoming = min(state["intensive"].values()) + timedelta(hours=INTENSIVE_HOURS)
        pending = f", next intensive check {upcoming:%Y-%m-%d %H:%M}"
    return None, (f"no check due (last regular check {last:%Y-%m-%d %H:%M}, "
                  f"next {next_grid_time(now):%Y-%m-%d %H:%M}{pending})")


# --- Mail ----------------------------------------------------------------------------------
# appended to every mail sent by the script (not to the report files)
MAIL_FOOTER = ("- - - - -\n"
               "Sent by: Monitoring your favorite webpages (Python Tool)\n"
               "Source:  https://github.com/pepe-hb9evt/Monitoring-your-favorite-webpages\n"
               "Author:  Pepe HB9EVT, with Claude (Anthropic)\n")
SECRETS_PROBLEMS = []  # notes about secrets.json (unknown keys), filled when the file is read


def load_password():
    """SMTP password from secrets.json; raises RuntimeError with a readable text if it is missing.
    Unknown keys (not starting with _) are noted in SECRETS_PROBLEMS."""
    SECRETS_PROBLEMS.clear()
    try:
        data = json.loads(SECRETS_FILE.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise RuntimeError(f"{SECRETS_FILE.name} missing - copy secrets.example.json and fill in the password")
    except Exception as e:
        raise RuntimeError(f"{SECRETS_FILE.name} not readable: {e}")
    if not isinstance(data, dict):
        raise RuntimeError(f"{SECRETS_FILE.name}: a JSON object is expected")
    for key in data:
        if not key.startswith("_") and key not in SECRETS_KEYS:
            SECRETS_PROBLEMS.append(f"{SECRETS_FILE.name}: unknown key '{key}' ignored "
                                    f"(allowed: {', '.join(SECRETS_KEYS)})")
    password = data.get("smtp_password", "")
    if not isinstance(password, str) or not password.strip() or password == PASSWORD_PLACEHOLDER:
        raise RuntimeError(f"SMTP password missing - fill in {SECRETS_FILE.name}")
    return password


def send_mail(subject, body):
    """Send a plain text mail with the SMTP settings. Raises an exception on failure.
    Returns the recipient list as text (for the report)."""
    smtp_cfg, mail_cfg = SETTINGS["smtp"], SETTINGS["mail"]
    if not mail_cfg["sender"].strip():
        raise RuntimeError(f"{SETTINGS_FILE.name}: 'mail.sender' missing")
    if not mail_cfg["recipients"]:
        raise RuntimeError(f"{SETTINGS_FILE.name}: 'mail.recipients' missing")
    if not smtp_cfg["host"].strip() or not smtp_cfg["port"]:
        raise RuntimeError(f"{SETTINGS_FILE.name}: 'smtp.host' or 'smtp.port' missing")
    password = load_password()
    msg = EmailMessage()
    msg["From"] = mail_cfg["sender"]
    msg["To"] = ", ".join(mail_cfg["recipients"])
    msg["Subject"] = f"{mail_cfg['subject_prefix'].strip()} {subject}".strip()
    body = body.rstrip() + "\n\n\n" + MAIL_FOOTER
    msg.set_content(body)
    username = smtp_cfg["username"].strip() or mail_cfg["sender"]
    context = ssl.create_default_context()
    if smtp_cfg["use_ssl"]:
        with smtplib.SMTP_SSL(smtp_cfg["host"], smtp_cfg["port"], context=context, timeout=30) as server:
            server.login(username, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(smtp_cfg["host"], smtp_cfg["port"], timeout=30) as server:
            if smtp_cfg["use_starttls"]:
                server.starttls(context=context)
            server.login(username, password)
            server.send_message(msg)
    return msg["To"]


def mail_after_check(subject, body, has_news, intensive=False):
    """Send the daily report after a check according to mail_mode/mail_condition.
    After an intensive check a mail is sent only if a new change was found (has_news).
    Return the lines for the run report (empty if no mail is configured)."""
    if MAIL_MODE != "script":
        return []
    if intensive and not has_news:
        return ["Mail: not sent (intensive check without a new change)"]
    if MAIL_CONDITION == "on_change" and not has_news:
        return ["Mail: not sent (no change and no error, mail_condition = on_change)"]
    progress("Sending mail ... ", end="")
    try:
        recipients = send_mail(subject, body)
    except Exception as e:
        progress("failed")
        return [f"ERROR: Mail could not be sent: {type(e).__name__}: {e}"] + [f"ERROR: {m}" for m in SECRETS_PROBLEMS]
    progress("done")
    return [f"Mail: daily report sent to {recipients}"] + [f"ERROR: {m}" for m in SECRETS_PROBLEMS]


def send_test_mail(now):
    """--test-mail: send the current daily report (or a short text) and report the result."""
    path = PROJECT_DIR / DAILY_REPORT_FILE
    try:
        report = path.read_text(encoding="utf-8")
    except Exception:
        report = f"({path.name} not available yet)\n"
    body = (f"Test mail of the webpages monitor, sent {now:%Y-%m-%d %H:%M}.\n"
            f"mail_mode = {MAIL_MODE}, mail_condition = {MAIL_CONDITION}\n\n"
            f"Current content of {path.name}:\n\n{report}")
    try:
        recipients = send_mail("Test mail", body)
    except Exception as e:
        print(f"ERROR: test mail could not be sent: {type(e).__name__}: {e}")
        for message in SECRETS_PROBLEMS + SETTINGS_PROBLEMS:
            print(f"ERROR: {message}")
        return 2
    print(f"Test mail sent to {recipients}")
    for message in SECRETS_PROBLEMS + SETTINGS_PROBLEMS:
        print(f"ERROR: {message}")
    return 1 if SECRETS_PROBLEMS or SETTINGS_PROBLEMS else 0


# --- Dev mode ------------------------------------------------------------------------------
def has_console():
    """False for windowless runs (pythonw.exe has no stdout)."""
    return sys.stdout is not None


RUN_MODE = "regular"  # mode of the current run, handed over to the dev mode window


def relaunch_in_console():
    """Start this script again in a new terminal window (Windows only). True if it was started."""
    if os.name != "nt":
        return False
    python = Path(sys.executable).with_name("python.exe")  # pythonw.exe has no window
    if not python.exists():
        return False
    try:
        subprocess.Popen([str(python), str(Path(__file__).resolve()), *sys.argv[1:], "--dev-window",
                          "--run-mode", RUN_MODE],
                         cwd=str(PROJECT_DIR), creationflags=subprocess.CREATE_NEW_CONSOLE, close_fds=True)
        return True
    except OSError:
        return False


def wait_before_closing(seconds):
    """Keep the dev mode window open for some seconds; Enter closes it at once."""
    print(f"\nWindow closes in {seconds} s - press Enter to close now.", flush=True)
    deadline = time.monotonic() + seconds
    if os.name == "nt":
        import msvcrt
        while time.monotonic() < deadline:
            if msvcrt.kbhit() and msvcrt.getwch() in ("\r", "\n"):
                return
            time.sleep(0.1)
    else:
        time.sleep(max(0, deadline - time.monotonic()))


def closing_pause(dev_window):
    """Pause before the terminal window closes, so the final lines can still be read.
    Same for the dev mode window and manual starts: dev_mode.keep_open_after_run_seconds (0 = no pause)."""
    seconds = DEV_MODE["keep_open_after_run_seconds"]
    if seconds and (dev_window or (CONSOLE_PROGRESS and has_console())):
        wait_before_closing(seconds)


def parse_args():
    parser = argparse.ArgumentParser(description="Webpages monitor")
    parser.add_argument("--force", action="store_true", help="check now, even if no check is due")
    parser.add_argument("--test-mail", action="store_true", help="send a test mail and exit")
    parser.add_argument("--dev-window", action="store_true", help=argparse.SUPPRESS)  # set by dev mode
    parser.add_argument("--run-mode", choices=("regular", "intensive"), help=argparse.SUPPRESS)  # set by dev mode
    return parser.parse_args()


def main():
    args = parse_args()
    now = datetime.now().replace(second=0, microsecond=0)  # capture files have minute resolution
    try:
        sys.stdout.reconfigure(errors="replace")  # special characters must not break the console output
    except Exception:
        pass
    global RUN_MODE
    if args.test_mail:
        return send_test_mail(now)
    state = load_state()
    if args.force:
        mode = "regular"
    elif args.run_mode:  # the dev mode window was started for this mode
        mode = args.run_mode
    else:
        mode, reason = check_due(now, state)
        if mode is None:
            progress(f"Webpages monitor – {now:%Y-%m-%d %H:%M} – {reason}. Use --force to check now.")
            return 0
    RUN_MODE = mode
    if DEV_MODE["enabled"] and not has_console() and not args.dev_window:
        # scheduled run without a console (pythonw): hand over to a visible window
        if relaunch_in_console():
            return 0
    code = run_check(now, state, mode)
    closing_pause(args.dev_window)
    return code


def run_check(now, state, mode="regular"):
    """One check: fetch and compare all webpages ("regular") or only the webpages in intensive mode
    ("intensive"), write the reports, update state.json, send the mail."""
    intensive = mode == "intensive"
    try:
        PROJECT_DIR.mkdir(parents=True, exist_ok=True)
        SITES_DIR.mkdir(exist_ok=True)  # create "monitored-webpages" if it does not exist yet
    except Exception as e:  # logging is not possible
        print(f"ERROR: folder {SITES_DIR} not available: {e}", file=sys.stderr)
        return 2
    short, daily, code = [], None, 0
    mail_subject, intro, news = "Run failed", [], True
    previous = last_check_time()  # before this run is added to the report
    try:
        sites, fatal, entry_problems = load_sites()
        stop_note = []
        if STOP_SKIPPED is not None:
            stop_note = [f"Note: STOP in {WEBPAGES_FILE.name} – {STOP_SKIPPED} "
                         f"{'webpage' if STOP_SKIPPED == 1 else 'webpages'} after STOP skipped", ""]
            short += stop_note
        if fatal:
            progress(f"Webpages monitor – run {now:%Y-%m-%d %H:%M} – ERROR: webpage list faulty, no webpage fetched")
            short += ["No comparison possible for:", "", str(WEBPAGES_FILE)] + [f"ERROR: {m}" for m in fatal] + [""]
            if SETTINGS_PROBLEMS:
                short += [str(SETTINGS_FILE)] + [f"ERROR: {m}" for m in SETTINGS_PROBLEMS] + [""]
            short.append(f"Run finished ({finished_time()}) in a controlled way: webpage list faulty, no webpage fetched")
            code = 2
            mail_subject = "ERROR: webpage list faulty, no webpage fetched"
        else:
            all_sites = sites
            if intensive:
                for name in [n for n in state["intensive"] if n not in all_sites]:
                    del state["intensive"][name]  # webpage was removed from the list
                due_names = set(intensive_due(now, state))
                sites = {n: e for n, e in all_sites.items() if n in due_names}
                short += [f"Intensive check: {len(sites)} {'webpage' if len(sites) == 1 else 'webpages'} "
                          "(changed or not reachable at the previous check)", ""]
            no_comparison, changed, unchanged = [], [], []
            if SETTINGS_PROBLEMS:
                no_comparison += [[str(SETTINGS_FILE)] + [f"ERROR: {m}" for m in SETTINGS_PROBLEMS]]
                code = 1
            if entry_problems:
                no_comparison += [[str(WEBPAGES_FILE)] + [f"ERROR: {m}" for m in entry_problems]]
                code = 1
            failed, follow_up = {}, []
            count = {"ok": 0, "first": 0, "changed": 0, "error": 0}
            stop_text = (f" (STOP in {WEBPAGES_FILE.name}: {STOP_SKIPPED} "
                         f"{'webpage' if STOP_SKIPPED == 1 else 'webpages'} skipped)" if STOP_SKIPPED is not None else "")
            kind = "intensive check" if intensive else "run"
            progress(f"Webpages monitor – {kind} {now:%Y-%m-%d %H:%M} – {len(sites)} webpages{stop_text}\n")
            width = len(str(len(sites)))
            for index, (name, entry) in enumerate(sites.items(), start=1):
                url = entry["url"]
                progress(f"[{index:>{width}}/{len(sites)}] {short_url(url)} ... ", end="")
                started = time.monotonic()
                try:
                    lines, status = process_site(name, url, entry["auth"], now, entry["accept_status"],
                                                 entry["ignore"], entry["form_login"])
                except Exception as e:  # one webpage must not abort the run
                    lines, status = [f"Unexpected error: {type(e).__name__}: {e}"], "error"
                progress(f"{progress_status(lines, status)} ({time.monotonic() - started:.1f} s)")
                count[status] += 1
                if status in ("changed", "error"):
                    follow_up.append(name)  # candidate for the next intensive check
                if status == "error":
                    failed[name] = lines[0]
                    no_comparison.append([url, "ERROR: " + lines[0]] + lines[1:])
                elif status == "first":
                    no_comparison.append([url] + lines)
                elif status == "changed":
                    changed.append([url] + lines)
                else:
                    unchanged.append(url)

            short += group_entries("No comparison possible for:", no_comparison) + [""]
            short += group_entries("Changes were detected on the following webpages:", changed) + [""]
            short += ["The following webpages are unchanged:"] + ([f"-  {u}" for u in unchanged] or ["(none)"]) + [""]
            short.append(f"Run finished ({finished_time()}): {len(sites)} webpages processed, {count['changed']} changed, "
                         f"{count['error']} errors, {count['first']} first runs, "
                         f"{len(entry_problems) + len(SETTINGS_PROBLEMS)} list/settings errors")
            code = 1 if (count["changed"] or count["error"] or entry_problems or SETTINGS_PROBLEMS) else 0
            if not intensive:
                state["last_regular_check"] = now
            # intensive list for the next check after INTENSIVE_HOURS hours (only the checked webpages):
            # regular check -> webpages changed or not reachable; intensive check -> the same, but only
            # if at least one webpage has new content, otherwise the chain ends (even if errors remain)
            if INTENSIVE_HOURS and (not intensive or count["changed"]):
                state["intensive"] = {name: now for name in follow_up}
            else:
                state["intensive"] = {}
            daily_lines, daily_stats = build_daily_report(now, all_sites, failed)  # always all webpages
            daily = stop_note + daily_lines
            sites_text = f"{len(sites)} of {len(all_sites)} webpages" if intensive else f"{len(sites)} webpages"
            # subject: result of this run only (short); the daily report is summarized in the mail text
            mail_subject = mail_subject_text(now, previous, count)
            error_urls = [sites[name]["url"] for name in failed]
            intro = mail_intro(now, previous, count, sites_text, [c[0] for c in changed], error_urls,
                               daily_stats, intensive)
            news = count["changed"] > 0 if intensive else code != 0
    except Exception as e:
        short += ["ERROR: Unexpected error during the run: " + f"{type(e).__name__}: {e}", "",
                  f"Run finished ({finished_time()}) in a controlled way after an unexpected error"]
        code = 2
    progress("\nWriting reports ... ", end="")
    report_errors, daily_text = [], None
    try:
        # on fatal errors: same text as the run
        daily_text = write_daily_report(now, daily if daily is not None else short)
    except Exception as e:
        report_errors.append(f"ERROR: daily report could not be written: {e}")
    progress("failed" if report_errors else "done")
    if daily_text is None:  # the mail carries the same text as the daily report file
        daily_text = "\n".join([f"=== Daily report {now:%Y-%m-%d %H:%M} ===", ""]
                                + (daily if daily is not None else short)).rstrip() + "\n"
    mail_body = "\n".join(intro) + daily_text if intro else daily_text
    mail_lines = mail_after_check(mail_subject, mail_body, news, intensive)
    if mail_lines:
        short += [""] + mail_lines
    try:
        save_state(state)
    except Exception as e:
        short += ["", f"ERROR: {STATE_FILE.name} could not be written: {e}"]
        code = max(code, 1)
    try:
        write_report(now, short)
    except Exception as e:
        report_errors.append(f"ERROR: report could not be written: {e}")
    for message in report_errors:
        print(message, file=sys.stderr)
        code = 2
    if any(line.startswith("ERROR:") for line in mail_lines):
        code = max(code, 1)
    return code


if __name__ == "__main__":
    sys.exit(main())
