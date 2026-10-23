#!/usr/bin/env python3
r"""Webpages monitor: fetches pages, extracts the visible content, stores copies and compares them.

Requirements (once):  pip install -r requirements.txt
Run:                  python webpages_monitor.py
Settings:             settings.json next to the script (optional, see settings.example.json)
Site list:            <PROJECT_DIR>\webpages.json (read on every run); keys starting with _ are comments
Storage:              <PROJECT_DIR>\monitored-webpages\<shortname>\captured_<YYYY-MM-DD_HHHMM>.txt (one per run,
                      kept 48 hours) and archive\<YYYY-MM-DD>.txt (last capture of each day, kept)
Report:               <PROJECT_DIR>\report-last-3-days.txt (short reports of the last 3 days,
                      newest first; older runs are removed automatically)
Daily report:         <PROJECT_DIR>\daily-report.txt (rewritten on every run: newest capture compared
                      with the newest capture at least 24 hours old, or the oldest one available)
Login:                HTTP Basic (default) or WordPress login form ("login": "wordpress"); see DOCUMENTATION.md
Images:               each <img> is downloaded once per run and stored with a content hash
                      ("URL | alt=... | sha1=..."), so a new image under the same URL is detected
Console:              progress per webpage is shown while running (setting "console_progress")
Exit code:            0 = no change, 1 = change or site error, 2 = configuration/program error
"""
import difflib
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Comment

# --- Settings ------------------------------------------------------------------------------
# User-dependent values live in "settings.json" in the folder of this script.
# If the file or a key is missing, the defaults below apply.
PROJECT_DIR = Path(__file__).resolve().parent  # all files live in the folder of the script
SETTINGS_FILE = PROJECT_DIR / "settings.json"
SITES_DIR = PROJECT_DIR / "monitored-webpages"  # one sub-folder per monitored webpage
# names of the former version; renamed automatically on the first run (see migrate_legacy_names)
LEGACY_SITES_DIR = PROJECT_DIR / "monitored-websites"
LEGACY_WEBPAGES_FILE = PROJECT_DIR / "websites.json"
LEGACY_SETTING_KEYS = {"websites_file": "webpages_file"}
DEFAULTS = {
    "webpages_file": "webpages.json",                 # site list (file name inside the project folder)
    "report_file": "report-last-3-days.txt",    # report file (file name inside the project folder)
    "report_days": 3,                           # how long runs stay in the report (days)
    "daily_report_file": "daily-report.txt",    # 24-hour comparison (file name inside the project folder)
    "daily_compare_hours": 24,                  # minimum age of the reference capture for the daily report
    "capture_keep_hours": 48,                   # how long capture files are kept (hours)
    "max_change_lines": 15,                     # change lines per site in the report
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
}
SETTING_TYPES = {"webpages_file": str, "report_file": str, "daily_report_file": str, "daily_compare_hours": int,
                 "capture_keep_hours": int, "report_days": int, "max_change_lines": int,
                 "timeout_seconds": int, "user_agent": str, "ignored_url_params": list,
                 "image_hash": bool, "image_max_count": int, "image_max_bytes": int,
                 "image_timeout_seconds": int, "console_progress": bool}


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
        key = LEGACY_SETTING_KEYS.get(key, key)  # former key names keep working
        if key not in DEFAULTS:
            problems.append(f"{SETTINGS_FILE.name}: unknown key '{key}' ignored")
        elif isinstance(value, bool) != (SETTING_TYPES[key] is bool) or not isinstance(value, SETTING_TYPES[key]) \
                or (SETTING_TYPES[key] is str and not value.strip()) \
                or (SETTING_TYPES[key] is int and value < 1) \
                or (SETTING_TYPES[key] is list and not all(isinstance(x, str) for x in value)):
            problems.append(f"{SETTINGS_FILE.name}: invalid value for '{key}', default used")
        else:
            cfg[key] = value
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
PROGRESS_URL_WIDTH = 60  # longer URLs are shortened in the terminal window
PROGRESS_ERROR_WIDTH = 80  # longer error texts are shortened in the terminal window
CLOSING_DOTS = 5  # dots written after the run, one per CLOSING_DOT_SECONDS, before the window closes
CLOSING_DOT_SECONDS = 1
IMAGE_CACHE = {}  # image URL -> hash, so an image used on several pages is downloaded once per run
LOGIN_SESSIONS = {}  # (login URL, username) -> logged-in requests.Session or error text, one login per run
LOGIN_TYPES = ("basic", "wordpress")
WP_LOGGED_IN_COOKIE = "wordpress_logged_in_"  # prefix of the cookie WordPress sets after a successful login
UNKNOWN_HASH = "?"  # image could not be downloaded; ignored when comparing
IMAGE_LINE = re.compile(r"^(.*) \| sha1=([0-9a-f]{16}|\?)$")
HIDDEN_STYLE = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.I)
PIXEL = re.compile(r"(pixel|tracking|spacer|blank\.gif|1x1)", re.I)
JS_LINK = re.compile(r" -> javascript:.*$", re.I)  # normalizes javascript links of older captures
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


def extract(html, base_url):
    """Return (text_lines, images, links) of the visible content."""
    soup = BeautifulSoup(html, "lxml")
    for t in soup.find_all(string=lambda s: isinstance(s, Comment)):
        t.extract()
    for t in soup(["script", "style", "noscript", "template", "head"]):
        t.decompose()
    for t in [t for t in soup.find_all(True) if is_hidden(t)]:
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
    session: logged-in session of a login-form site (its cookies only go to their own domain)."""
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
    """Return (base, hash) of an <img> line; hash is None for lines without hash (older captures)."""
    m = IMAGE_LINE.match(line)
    return (m.group(1), m.group(2)) if m else (line, None)


def align_image_hashes(old, new):
    """Ignore the image hash where it is missing or unknown on one side, so that older captures
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


def normalize_link_line(line):
    """Apply the current URL cleaning to a stored link line, so older captures that still contain
    volatile parameters (e.g. after 'ignored_url_params' was extended) do not show up as changes."""
    line = JS_LINK.sub(" -> javascript:", line)
    text, sep, url = line.rpartition(" -> ")
    if not sep or not url.lower().startswith(("http://", "https://")):
        return line
    return f"{text} -> {clean_url(url, url) or url}"


def split_sections(content):
    sections, cur = {"TEXT": [], "IMAGES": [], "LINKS": []}, "TEXT"
    for line in content.splitlines():
        if line == "=== IMAGES ===":
            cur = "IMAGES"
        elif line == "=== LINKS ===":
            cur = "LINKS"
        elif line:
            sections[cur].append(normalize_link_line(line) if cur == "LINKS" else line)
    return sections


def diff_lines(old, new, title):
    out = []
    for z in difflib.unified_diff(old, new, lineterm="", n=0):
        if z.startswith(("---", "+++", "@@")):
            continue
        out.append(("  removed: " if z[0] == "-" else "  added:   ") + z[1:])
    return [f" [{title}]"] + out if out else []


def apply_ignore(sections, rules):
    """Remove lines matching the ignore rules of a site ({section: [compiled regex, ...]})."""
    if not rules:
        return sections
    return {sec: [z for z in lines if not any(p.search(z) for p in rules.get(sec, []))]
            for sec, lines in sections.items()}


def compare(old_content, new_content, ignore=None):
    """Return (diff_lines, notes) for two capture contents.
    ignore: per-site rules; matching lines are removed on both sides before comparing."""
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


def migrate_legacy(folder):
    """Convert current.txt of the former layout into a capture file (time = file time); drop previous.txt."""
    current, previous = folder / "current.txt", folder / "previous.txt"
    if current.exists():
        when = datetime.fromtimestamp(current.stat().st_mtime).replace(second=0, microsecond=0)
        target = capture_path(folder, when)
        if target.exists():
            current.unlink()
        else:
            current.rename(target)
    if previous.exists():
        previous.unlink()


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


def group_entries(title, entries):
    out = [title, ""]
    for e in entries:
        out += e + [""]
    return out if entries else [title, "(none)", ""]


def build_daily_report(now, sites, failed):
    """Compare per site the newest capture with the newest capture at least DAILY_COMPARE_HOURS old
    (or with the oldest capture if none is old enough). failed: {name: error text of this run}."""
    limit = now - timedelta(hours=DAILY_COMPARE_HOURS)
    no_comparison, changed, unchanged, ages = [], [], [], []
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
        old_enough = [c for c in captures[:-1] if c[0] <= limit]
        reference = old_enough[-1] if old_enough else captures[0]
        try:
            d, notes = compare(reference[1].read_text(encoding="utf-8"), newest[1].read_text(encoding="utf-8"),
                               entry.get("ignore"))
        except Exception as e:
            no_comparison.append([url, f"ERROR: capture file not readable: {type(e).__name__}: {e}"])
            continue
        ages.append(age_hours(now, reference[0]))
        if d:
            changed.append([url, "Changed"] + shorten(d) + notes)
        else:
            unchanged.append(f"-  {url}")
    # most frequent reference age (sites usually share the same run times)
    hours = max(set(ages), key=ages.count) if ages else DAILY_COMPARE_HOURS
    title = f"Newest capture compared with the capture from {hours} {'hour' if hours == 1 else 'hours'} ago."
    if hours < DAILY_COMPARE_HOURS - 1:  # less than 23 hours: no capture old enough yet
        title += " (oldest capture available)"
    lines = [title, ""]
    lines += group_entries("No comparison possible for:", no_comparison) + [""]
    lines += group_entries("Changes were detected on the following webpages:", changed) + [""]
    lines += ["The following webpages are unchanged:"] + (unchanged or ["(none)"]) + [""]
    lines.append(f"Daily report finished: {len(sites)} sites, {len(changed)} changed, "
                 f"{len(no_comparison)} without comparison")
    return lines


def write_daily_report(now, lines):
    """Replace the daily report file."""
    content = "\n".join([f"=== Daily report {now:%Y-%m-%d %H:%M} ===", ""] + lines).rstrip() + "\n"
    (PROJECT_DIR / DAILY_REPORT_FILE).write_text(content, encoding="utf-8")


# --- Site list -----------------------------------------------------------------------------
IGNORE_SECTIONS = {"text": "TEXT", "images": "IMAGES", "links": "LINKS"}


def parse_ignore(key, raw):
    """Parse the optional 'ignore' object of a site: {"text"|"images"|"links": [pattern, ...]}.
    A pattern is a case-insensitive substring, or a regular expression with the prefix 're:'.
    Return ({section: [compiled regex, ...]}, problems); faulty rules are dropped."""
    rules, problems = {}, []
    if raw is None:
        return rules, problems
    if not isinstance(raw, dict):
        return rules, [f"Entry '{key}': 'ignore' must be an object with 'text', 'images', 'links' "
                       "(rules ignored, site still monitored)"]
    for sub, patterns in raw.items():
        if sub.startswith("_"):
            continue
        if sub not in IGNORE_SECTIONS:
            problems.append(f"Entry '{key}': unknown key 'ignore.{sub}' ignored "
                            "(allowed: text, images, links)")
            continue
        if not isinstance(patterns, list):
            problems.append(f"Entry '{key}': 'ignore.{sub}' must be a list of patterns (rules ignored)")
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
    are skipped and only logged."""
    if not WEBPAGES_FILE.exists():
        return None, [f"File missing: {WEBPAGES_FILE}"], []
    duplicates = []
    try:
        def pairs(items):
            d = {}
            for k, v in items:
                if k in d:
                    duplicates.append(k)
                d.setdefault(k, v)  # the first entry wins
            return d
        data = json.loads(WEBPAGES_FILE.read_text(encoding="utf-8-sig"), object_pairs_hook=pairs)
    except Exception as e:
        return None, [f"File not readable or not valid JSON: {e}"], []
    if not isinstance(data, dict) or not data:
        return None, ['Wrong content: a non-empty object {"shortname": "URL", ...} is expected'], []
    good = {}
    problems = [f"Short name '{k}' appears more than once, only the first entry is used" for k in duplicates]
    for key, value in data.items():
        if key.startswith("_"):  # comment key, e.g. "_comment"
            continue
        if isinstance(value, str):  # short form: "shortname": "URL"
            value = {"url": value}
        if not re.fullmatch(r"[A-Za-z0-9._-]+", key):
            problems.append(f"Entry '{key}' skipped: invalid short name (allowed: letters, digits, . _ -)")
        elif not isinstance(value, dict) or not isinstance(value.get("url"), str) \
                or not re.match(r"https?://[^\s/]+", value["url"]):
            problems.append(f"URL of '{key}' invalid: {(value.get('url') if isinstance(value, dict) else value)!r} "
                            "(entry skipped; http:// or https:// expected)")
        else:
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
            problems += ignore_problems  # faulty rules are dropped, the site is still monitored
            credentials = (username, password) if username else None
            good[key] = {"url": value["url"], "auth": credentials if login == "basic" else None,
                         "form_login": (login, login_url, credentials) if login != "basic" else None,
                         "accept_status": set(accept), "ignore": ignore}
    if not good:
        return None, ["No valid URL in the site list"] + problems, []
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
    # Open the target page first, like a browser: it usually redirects to the site's login page and sets
    # its cookies. A direct GET of wp-login.php is avoided, because some sites drop such requests.
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
    """Return (session, error text) for a login-form site; one login per login URL and user per run."""
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
    ignore: per-site rules of lines to leave out when comparing (captures stay complete).
    form_login: (type, login URL, (username, password)) for sites behind a login form, else None."""
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
        text, images, links = extract(r.text, r.url)
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
        migrate_legacy(folder)
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


def migrate_legacy_names():
    """Rename the data folder and the site list of the former version (monitored-websites,
    websites.json) to the new names, so the history is kept. Return notes for the report."""
    pairs = [(LEGACY_SITES_DIR, SITES_DIR)]
    if SETTINGS["webpages_file"] == DEFAULTS["webpages_file"]:  # only for the default list name
        pairs.append((LEGACY_WEBPAGES_FILE, WEBPAGES_FILE))
    notes = []
    for old, new in pairs:
        if not old.exists():
            continue
        if new.exists():
            notes.append(f"Note: '{old.name}' is no longer used ('{new.name}' exists); it can be deleted")
            continue
        try:
            old.rename(new)
            notes.append(f"Note: '{old.name}' renamed to '{new.name}'")
        except Exception as e:
            notes.append(f"ERROR: '{old.name}' could not be renamed to '{new.name}': {type(e).__name__}: {e}")
    return notes


def main():
    now = datetime.now().replace(second=0, microsecond=0)  # capture files have minute resolution
    try:
        sys.stdout.reconfigure(errors="replace")  # special characters must not break the console output
    except Exception:
        pass
    try:
        PROJECT_DIR.mkdir(parents=True, exist_ok=True)
        migration_notes = migrate_legacy_names()
        SITES_DIR.mkdir(exist_ok=True)  # create "monitored-webpages" if it does not exist yet
    except Exception as e:  # logging is not possible
        print(f"ERROR: folder {SITES_DIR} not available: {e}", file=sys.stderr)
        return 2
    short, daily, code = (migration_notes + [""] if migration_notes else []), None, 0
    try:
        sites, fatal, entry_problems = load_sites()
        if fatal:
            progress(f"Webpages monitor – run {now:%Y-%m-%d %H:%M} – ERROR: site list faulty, no site fetched")
            short += ["No comparison possible for:", "", str(WEBPAGES_FILE)] + [f"ERROR: {m}" for m in fatal] + [""]
            if SETTINGS_PROBLEMS:
                short += [str(SETTINGS_FILE)] + [f"ERROR: {m}" for m in SETTINGS_PROBLEMS] + [""]
            short.append("Run finished in a controlled way: site list faulty, no site fetched")
            code = 2
        else:
            no_comparison, changed, unchanged = [], [], []
            if SETTINGS_PROBLEMS:
                no_comparison += [[str(SETTINGS_FILE)] + [f"ERROR: {m}" for m in SETTINGS_PROBLEMS]]
                code = 1
            if entry_problems:
                no_comparison += [[str(WEBPAGES_FILE)] + [f"ERROR: {m}" for m in entry_problems]]
                code = 1
            failed = {}
            count = {"ok": 0, "first": 0, "changed": 0, "error": 0}
            progress(f"Webpages monitor – run {now:%Y-%m-%d %H:%M} – {len(sites)} sites\n")
            width = len(str(len(sites)))
            for index, (name, entry) in enumerate(sites.items(), start=1):
                url = entry["url"]
                progress(f"[{index:>{width}}/{len(sites)}] {short_url(url)} ... ", end="")
                started = time.monotonic()
                try:
                    lines, status = process_site(name, url, entry["auth"], now, entry["accept_status"],
                                                 entry["ignore"], entry["form_login"])
                except Exception as e:  # one site must not abort the run
                    lines, status = [f"Unexpected error: {type(e).__name__}: {e}"], "error"
                progress(f"{progress_status(lines, status)} ({time.monotonic() - started:.1f} s)")
                count[status] += 1
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
            short.append(f"Run finished: {len(sites)} sites processed, {count['changed']} changed, "
                         f"{count['error']} errors, {count['first']} first runs, "
                         f"{len(entry_problems) + len(SETTINGS_PROBLEMS)} list/settings errors")
            code = 1 if (count["changed"] or count["error"] or entry_problems or SETTINGS_PROBLEMS) else 0
            daily = build_daily_report(now, sites, failed)
    except Exception as e:
        short += ["ERROR: Unexpected error during the run: " + f"{type(e).__name__}: {e}", "",
                  "Run finished in a controlled way after an unexpected error"]
        code = 2
    progress("\nWriting reports ... ", end="")
    report_errors = []
    try:
        write_report(now, short)
    except Exception as e:
        report_errors.append(f"ERROR: report could not be written: {e}")
    try:
        write_daily_report(now, daily if daily is not None else short)  # on fatal errors: same text as the run
    except Exception as e:
        report_errors.append(f"ERROR: daily report could not be written: {e}")
    progress("failed" if report_errors else "done")
    for message in report_errors:
        print(message, file=sys.stderr)
        code = 2
    if CONSOLE_PROGRESS:  # short pause with visible dots so the final lines can still be read
        for _ in range(CLOSING_DOTS):
            time.sleep(CLOSING_DOT_SECONDS)
            progress(".", end="")
        progress()
    return code


if __name__ == "__main__":
    sys.exit(main())
