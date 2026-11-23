#!/usr/bin/env python3
"""
Lorestan University Internet Auto-Login & Session Keep-Alive
Portal: https://internet.lu.ac.ir/login
Author: khode-mwri

Multi-strategy login
--------------------
The portal is a MikroTik hotspot page, but its exact shape can vary:
CHAP on or off, chap-id written as a raw byte / octal / hex escape,
the login form posting to the page URL or to a different action URL,
plain HTTP or HTTPS. Instead of assuming one shape, this script
detects what the page actually contains and tries every plausible
login method until one is *verified* by a real internet check.
The winning method is remembered in config.json ("strategy") and
tried first on the next run; if it stops working, the others are
tried again automatically.

Strategies (tried in this order, remembered winner first):
  chap-form   - MikroTik CHAP (MD5 of chap-id + password + challenge),
                POSTed to the login form's action URL.
  plain-form  - Plain username/password POSTed to the form's action URL.
  plain-page  - Plain username/password POSTed to the page URL itself.
  chap-page   - CHAP hash POSTed to the page URL itself.
  get-login   - Username/password sent as a GET query to the form action.

Usage:
  python lu_autologin.py               # monitor loop (default; on Windows
                                       # shows a tray icon next to the clock)
  python lu_autologin.py --once        # try to log in once, then exit
  python lu_autologin.py --diagnose    # fetch the portal, print what was
                                       # found (forms, CHAP data) and save
                                       # the HTML to portal_debug.html
  python lu_autologin.py --panel       # interactive settings panel
                                       # (also available as the `autologin`
                                       # command after install)
  python lu_autologin.py --no-tray     # monitor loop without the tray icon
  python lu_autologin.py --strategy chap-form --once   # force one method
"""

import sys
import os
import json
import time
import ssl
import re
import socket
import argparse
import getpass
import shutil
import subprocess
import threading
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import hashlib
import py_compile
from datetime import datetime

# Configure standard streams for safety on Windows
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
LOG_FILE = os.path.join(SCRIPT_DIR, "autologin.log")
DEBUG_HTML_FILE = os.path.join(SCRIPT_DIR, "portal_debug.html")

# Single-instance lock port to prevent duplicate processes
LOCK_PORT = 47829
_instance_lock_socket = None

DEFAULT_PORTAL_URLS = [
    "https://internet.lu.ac.ir/login",
    "http://internet.lu.ac.ir/login",
]
DEFAULT_CONNECTIVITY_URLS = [
    "http://clients3.google.com/generate_204",
    "http://detectportal.firefox.com/success.txt",
    "http://www.msftconnecttest.com/connecttest.txt",
]

STRATEGY_NAMES = ["chap-form", "plain-form", "plain-page", "chap-page", "get-login"]

# Release version. Bump together with version.txt on every release push;
# the self-update check compares this against version.txt on GitHub.
__version__ = "1.3.0"

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/khode-mwri/lu-autologin/main"
VERSION_URL = GITHUB_RAW_BASE + "/version.txt"

# Files the self-updater refreshes from GitHub (never config.json).
UPDATE_FILES = [
    "lu_autologin.py", "autologin.bat", "run.bat", "run_background.bat",
    "stop_background.bat", "enable_startup.bat", "disable_startup.bat",
    "view_logs.bat", "setup.bat", "launch_silent.vbs",
]
UPDATE_CHECK_INTERVAL_SECONDS = 6 * 3600
NOTIFY_AFTER_FAILURES = 3


def ensure_single_instance():
    """Ensure only one instance of the auto-login service runs at a time."""
    global _instance_lock_socket
    try:
        _instance_lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _instance_lock_socket.bind(("127.0.0.1", LOCK_PORT))
    except socket.error:
        print("[INFO] Another instance of LU Auto-Login is already running. Exiting.", flush=True)
        sys.exit(0)


def load_config(config_file, interactive=True):
    """Load configuration, filling in defaults; prompt for credentials if missing."""
    cfg = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to read {config_file}: {e}")

    cfg.setdefault("check_interval_seconds", 20)
    cfg.setdefault("proactive_renew_minutes", 110)
    cfg.setdefault("auto_update", True)
    cfg.setdefault("portal_urls", list(DEFAULT_PORTAL_URLS))
    cfg.setdefault("connectivity_urls", list(DEFAULT_CONNECTIVITY_URLS))

    if cfg.get("username") and cfg.get("password") and cfg["username"] != "YOUR_STUDENT_ID":
        return cfg

    if not interactive:
        return cfg

    # If missing or placeholder, prompt user in interactive mode
    print("=" * 65)
    print("  Lorestan University Auto-Login - First Time Setup")
    print("=" * 65)
    print("Please enter your university credentials (stored locally in config.json):")
    try:
        username = input("Student ID (Username): ").strip()
        password = input("Password             : ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nSetup cancelled.")
        sys.exit(1)

    if not username or not password:
        print("[ERROR] Username and password cannot be empty.")
        sys.exit(1)

    cfg["username"] = username
    cfg["password"] = password
    save_config(cfg, config_file)
    print("[OK] Configuration saved successfully to config.json.")
    return cfg


def save_config(cfg, config_file):
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Could not save {config_file}: {e}")


def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [{level}] {message}"
    print(formatted, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8", errors="replace") as f:
            f.write(formatted + "\n")
    except Exception:
        pass


def get_ssl_context():
    """Create SSL context that permits internal/self-signed university certificates.

    NOTE: verification is off on purpose — the university portal uses a
    self-signed certificate. This only ever talks to the portal host(s)
    in portal_urls, so the exposure is limited to the campus network.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def create_session():
    """Build URL opener with cookie jar and browser headers."""
    cj = http.cookiejar.CookieJar()
    ssl_handler = urllib.request.HTTPSHandler(context=get_ssl_context())
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        ssl_handler
    )
    opener.addheaders = [
        ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'),
        ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
        ('Accept-Language', 'en-US,en;q=0.9'),
    ]
    return opener


def check_internet(test_urls):
    """
    Check if global internet is reachable.
    Returns True if reachable, False otherwise.
    """
    for test_url in test_urls:
        try:
            req = urllib.request.Request(test_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                if "generate_204" in test_url and resp.status == 204:
                    return True
                if "firefox" in test_url and resp.status == 200:
                    body = resp.read(20).decode('utf-8', errors='ignore').strip()
                    if body == "success":
                        return True
                if "msftconnecttest" in test_url and resp.status == 200:
                    body = resp.read(50).decode('utf-8', errors='ignore')
                    if "Microsoft" in body:
                        return True
        except Exception:
            continue
    return False


# ---------------------------------------------------------------------------
# Portal parsing
# ---------------------------------------------------------------------------

def decode_js_string(s):
    """Decode a JavaScript string literal body (without surrounding quotes).

    Handles \\xNN (hex), \\NNN (octal), \\n \\r \\t \\\\ \\' \\" and raw
    bytes. Returns a str whose latin-1 code points are the original bytes,
    so ``.encode('latin-1')`` recovers the exact byte sequence.
    """
    out = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch != '\\' or i + 1 >= len(s):
            out.append(ch)
            i += 1
            continue
        nxt = s[i + 1]
        if nxt == 'x':
            hexpart = s[i + 2:i + 4]
            if len(hexpart) == 2 and all(c in '0123456789abcdefABCDEF' for c in hexpart):
                out.append(chr(int(hexpart, 16)))
                i += 4
                continue
            out.append('x')
            i += 2
            continue
        if nxt in '01234567':
            j = i + 1
            oct_digits = ''
            while j < len(s) and len(oct_digits) < 3 and s[j] in '01234567':
                oct_digits += s[j]
                j += 1
            out.append(chr(int(oct_digits, 8) & 0xFF))
            i = j
            continue
        simple = {'n': '\n', 'r': '\r', 't': '\t', 'b': '\b', 'f': '\f', 'v': '\v', '0': '\0'}
        if nxt in simple:
            out.append(simple[nxt])
            i += 2
            continue
        # \\ \' \" \/ and anything else: the character itself.
        out.append(nxt)
        i += 2
    return ''.join(out)


def _scan_hexmd5_args(html):
    """Find hexMD5(...) calls and return [(chap_id_raw, challenge_raw), ...].

    Scans character by character so escaped quotes and nested parens
    cannot break the parse. First literal = chap-id, last literal =
    chap-challenge; whatever sits between them is the password expression.
    """
    results = []
    for m in re.finditer(r'hexMD5\s*\(', html):
        i = m.end()
        depth = 1
        literals = []
        cur = None
        quote = None
        escaped = False
        while i < len(html) and depth > 0:
            ch = html[i]
            if quote is not None:
                if escaped:
                    cur += ch
                    escaped = False
                elif ch == '\\':
                    cur += ch
                    escaped = True
                elif ch == quote:
                    literals.append(cur)
                    cur = None
                    quote = None
                else:
                    cur += ch
            else:
                if ch in ('"', "'"):
                    quote = ch
                    cur = ""
                elif ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
            i += 1
        if len(literals) >= 2:
            results.append((literals[0], literals[-1]))
    return results


def extract_chap(html):
    """Extract MikroTik CHAP (chap-id bytes, chap-challenge string).

    Returns (chap_id_bytes, challenge) or (None, None) when the page
    does not use CHAP. chap-id may be a raw byte, an octal escape
    (\\001) or a hex escape (\\x01) — all three decode to the same byte.
    """
    for chap_raw, chal_raw in _scan_hexmd5_args(html):
        chap_id = decode_js_string(chap_raw).encode('latin-1')
        challenge = decode_js_string(chal_raw)
        if chap_id:
            if len(chap_id) != 1:
                log(f"CHAP chap-id decoded to {len(chap_id)} bytes (expected 1); "
                    "using it as-is, other strategies remain as fallback.", "WARNING")
            return chap_id, challenge

    # Fallbacks: chap data in hidden inputs or JS variables.
    chap_m = re.search(
        r'''chap[-_]?id['"]?\s*[:=]\s*['"]([^'"]+)['"]''', html, re.IGNORECASE)
    chal_m = re.search(
        r'''chap[-_]?challenge['"]?\s*[:=]\s*['"]([^'"]+)['"]''', html, re.IGNORECASE)
    if chap_m and chal_m:
        chap_id = decode_js_string(chap_m.group(1)).encode('latin-1')
        challenge = decode_js_string(chal_m.group(1))
        if chap_id:
            return chap_id, challenge
    return None, None


def _tag_attr(tag, name, default=None):
    m = re.search(
        r'%s\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s>]+))' % re.escape(name),
        tag, re.IGNORECASE)
    if not m:
        return default
    if m.group(2) is not None:
        return m.group(2)
    if m.group(3) is not None:
        return m.group(3)
    return m.group(4)


def parse_forms(html, page_url):
    """Return [{'action': absolute URL, 'name': str, 'hidden': {k: v}}]."""
    forms = []
    for m in re.finditer(r'<form\b([^>]*)>(.*?)</form>', html,
                         re.IGNORECASE | re.DOTALL):
        attrs, body = m.group(1), m.group(2)
        action = _tag_attr(attrs, 'action') or page_url
        name = _tag_attr(attrs, 'name') or _tag_attr(attrs, 'id') or ''
        hidden = {}
        for inp in re.finditer(r'<input\b[^>]*>', body, re.IGNORECASE):
            tag = inp.group(0)
            if (_tag_attr(tag, 'type', '') or '').lower() != 'hidden':
                continue
            n = _tag_attr(tag, 'name')
            v = _tag_attr(tag, 'value')
            if n is not None:
                hidden[n] = v or ''
        forms.append({
            'action': urllib.parse.urljoin(page_url, action),
            'name': name,
            'hidden': hidden,
        })
    return forms


def preferred_form(forms, page_url):
    """Pick the form a login POST should go to.

    MikroTik serves two forms: 'sendin' (the one actually submitted by
    its JS) and 'login' (the visible one). Prefer sendin, then login,
    then any form whose action mentions login, then the first form.
    """
    if not forms:
        return {'action': page_url, 'name': '', 'hidden': {}}
    for want in ('sendin', 'login'):
        for f in forms:
            if f['name'].lower() == want:
                return f
    for f in forms:
        if 'login' in f['action'].lower():
            return f
    return forms[0]


def fetch_portal(opener, portal_urls):
    """GET the portal; follow redirects. Returns (final_url, html) or (None, None).

    The HTML is decoded as latin-1 on purpose: a raw chap-id byte is not
    valid UTF-8, and decoding with errors='ignore' would silently drop
    it and break CHAP detection. latin-1 maps bytes 1:1, so the byte
    survives and .encode('latin-1') recovers it exactly.
    """
    for url in portal_urls:
        try:
            req = urllib.request.Request(url)
            with opener.open(req, timeout=8) as resp:
                raw = resp.read()
                html = raw.decode('latin-1')
                return resp.geturl(), html
        except Exception as e:
            log(f"Portal {url} unreachable: {e}", "DEBUG")
            continue
    return None, None


def is_logged_in_page(html, url):
    low = html.lower()
    return ("logout" in low
            or "status" in url.lower()
            or "you are logged in" in low
            or "successfully logged in" in low)


# ---------------------------------------------------------------------------
# Login attempts
# ---------------------------------------------------------------------------

def _post(opener, url, payload, referer, timeout=10):
    data = urllib.parse.urlencode(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': referer,
    })
    with opener.open(req, timeout=timeout) as resp:
        body = resp.read().decode('utf-8', errors='ignore')
        return resp.geturl(), body


def _get(opener, url, payload, referer, timeout=10):
    query = urllib.parse.urlencode(payload)
    full = url + ('&' if '?' in url else '?') + query
    req = urllib.request.Request(full, headers={'Referer': referer})
    with opener.open(req, timeout=timeout) as resp:
        body = resp.read().decode('utf-8', errors='ignore')
        return resp.geturl(), body


def _verify(final_url, body, connectivity_urls):
    """Classify a login attempt. 'ok' | 'bad-creds' | 'failed'.

    'ok' only when the portal itself reports a session (status/logout
    page) or a real internet check passes. A previous version returned
    success on an ambiguous response; that hid real failures.
    """
    low = body.lower()
    bad_markers = ("invalid username", "invalid password", "incorrect password",
                   "wrong password", "authentication failed", "login failed",
                   "invalid user", "bad username or password")
    if any(m in low for m in bad_markers):
        return 'bad-creds'
    if "status" in final_url.lower() or "logout" in low:
        return 'ok'
    if check_internet(connectivity_urls):
        return 'ok'
    return 'failed'


def _chap_hash(chap_id, password, challenge):
    return hashlib.md5(
        chap_id + password.encode('utf-8') + challenge.encode('latin-1')
    ).hexdigest()


def _attempt(opener, target, payload, method, referer, connectivity_urls):
    try:
        if method == 'POST':
            final_url, body = _post(opener, target, payload, referer)
        else:
            final_url, body = _get(opener, target, payload, referer)
    except Exception as e:
        log(f"Request to {target} failed: {e}", "DEBUG")
        return 'failed'
    return _verify(final_url, body, connectivity_urls)


def _strategy_chap_form(opener, info, cfg):
    chap_id, challenge = info['chap_id'], info['challenge']
    form = info['form']
    payload = dict(form['hidden'])
    payload['username'] = cfg['username']
    payload['password'] = _chap_hash(chap_id, cfg['password'], challenge)
    return _attempt(opener, form['action'], payload, 'POST',
                    info['page_url'], info['connectivity_urls'])


def _strategy_plain_form(opener, info, cfg):
    form = info['form']
    payload = dict(form['hidden'])
    payload['username'] = cfg['username']
    payload['password'] = cfg['password']
    return _attempt(opener, form['action'], payload, 'POST',
                    info['page_url'], info['connectivity_urls'])


def _strategy_plain_page(opener, info, cfg):
    form = info['form']
    payload = dict(form['hidden'])
    payload['username'] = cfg['username']
    payload['password'] = cfg['password']
    return _attempt(opener, info['page_url'], payload, 'POST',
                    info['page_url'], info['connectivity_urls'])


def _strategy_chap_page(opener, info, cfg):
    chap_id, challenge = info['chap_id'], info['challenge']
    form = info['form']
    payload = dict(form['hidden'])
    payload['username'] = cfg['username']
    payload['password'] = _chap_hash(chap_id, cfg['password'], challenge)
    return _attempt(opener, info['page_url'], payload, 'POST',
                    info['page_url'], info['connectivity_urls'])


def _strategy_get_login(opener, info, cfg):
    form = info['form']
    payload = dict(form['hidden'])
    payload['username'] = cfg['username']
    payload['password'] = cfg['password']
    return _attempt(opener, form['action'], payload, 'GET',
                    info['page_url'], info['connectivity_urls'])


STRATEGIES = [
    ("chap-form", _strategy_chap_form),
    ("plain-form", _strategy_plain_form),
    ("plain-page", _strategy_plain_page),
    ("chap-page", _strategy_chap_page),
    ("get-login", _strategy_get_login),
]


def perform_login(opener, cfg, config_file, force_strategy=None):
    """Try login strategies until one is verified. Returns (success, strategy)."""
    portal_urls = cfg.get("portal_urls") or list(DEFAULT_PORTAL_URLS)
    connectivity_urls = cfg.get("connectivity_urls") or list(DEFAULT_CONNECTIVITY_URLS)

    page_url, html = fetch_portal(opener, portal_urls)
    if not page_url:
        log("Cannot reach internet.lu.ac.ir. Ensure you are on University Wi-Fi.", "WARNING")
        return False, None

    if is_logged_in_page(html, page_url):
        log("Session is currently active (Already logged in).", "INFO")
        return True, "already-logged-in"

    forms = parse_forms(html, page_url)
    form = preferred_form(forms, page_url)
    chap_id, challenge = extract_chap(html)
    info = {
        'page_url': page_url,
        'form': form,
        'chap_id': chap_id,
        'challenge': challenge,
        'connectivity_urls': connectivity_urls,
    }
    log(f"Portal page: {page_url} | forms: {len(forms)} | "
        f"form action: {form['action']} | CHAP: {'yes' if chap_id else 'no'}", "DEBUG")

    order = list(STRATEGIES)
    remembered = cfg.get("strategy")
    if remembered in dict(STRATEGIES):
        order.sort(key=lambda s: 0 if s[0] == remembered else 1)
        log(f"Trying remembered strategy first: {remembered}", "DEBUG")

    for name, fn in order:
        if force_strategy and name != force_strategy:
            continue
        if name.startswith("chap") and not chap_id:
            log(f"Skipping {name}: page does not use CHAP.", "DEBUG")
            continue
        log(f"Trying login method: {name} ...", "INFO")
        result = fn(opener, info, cfg)
        if result == 'ok':
            log(f"Login SUCCESSFUL via {name}! Connected to university internet.", "SUCCESS")
            if cfg.get("strategy") != name:
                cfg["strategy"] = name
                save_config(cfg, config_file)
            return True, name
        if result == 'bad-creds':
            log("Login FAILED: Incorrect username or password. "
                "Check your credentials in config.json.", "ERROR")
            return False, None
        log(f"Method {name} did not work, trying the next one...", "INFO")

    log("All login methods failed. Run with --diagnose and check portal_debug.html.", "ERROR")
    return False, None


# ---------------------------------------------------------------------------
# Diagnose mode
# ---------------------------------------------------------------------------

def diagnose(opener, cfg):
    portal_urls = cfg.get("portal_urls") or list(DEFAULT_PORTAL_URLS)
    page_url, html = fetch_portal(opener, portal_urls)
    if not page_url:
        print("[DIAGNOSE] Portal unreachable from here. Are you on University Wi-Fi?")
        print("[DIAGNOSE] Tried: " + ", ".join(portal_urls))
        return 1

    try:
        with open(DEBUG_HTML_FILE, "w", encoding="utf-8", errors="replace") as f:
            f.write(html)
        print(f"[DIAGNOSE] Saved portal HTML to {DEBUG_HTML_FILE}")
    except Exception as e:
        print(f"[DIAGNOSE] Could not save HTML: {e}")

    forms = parse_forms(html, page_url)
    form = preferred_form(forms, page_url)
    chap_id, challenge = extract_chap(html)

    print(f"[DIAGNOSE] Final URL   : {page_url}")
    print(f"[DIAGNOSE] Already in : {'yes' if is_logged_in_page(html, page_url) else 'no'}")
    print(f"[DIAGNOSE] Forms found: {len(forms)}")
    for i, f in enumerate(forms):
        print(f"[DIAGNOSE]   form {i}: name={f['name']!r} action={f['action']!r} hidden={f['hidden']!r}")
    print(f"[DIAGNOSE] Preferred form action: {form['action']}")
    if chap_id:
        print(f"[DIAGNOSE] CHAP detected: chap-id={chap_id!r} challenge={challenge!r}")
    else:
        print("[DIAGNOSE] CHAP not detected: plain username/password login expected.")
    print("[DIAGNOSE] Strategies that would be tried: " +
          ", ".join(n for n, _ in STRATEGIES))
    return 0


# ---------------------------------------------------------------------------
# Self-update
# ---------------------------------------------------------------------------

def parse_version(text):
    """'1.3.0' -> (1, 3, 0). Tolerates whitespace and missing parts."""
    parts = []
    for piece in str(text or "").strip().split("."):
        piece = piece.strip()
        if piece.isdigit():
            parts.append(int(piece))
        else:
            break
    return tuple(parts) if parts else (0,)


def fetch_remote_version(url=VERSION_URL, timeout=10):
    """Return the version string from version.txt on GitHub, or None."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "lu-autologin"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace").strip()
    except Exception as e:
        log(f"Update check failed: {e}", "WARNING")
        return None


def check_for_update(url=VERSION_URL):
    """Return (available, remote_version). available is True when the remote
    version is newer than this script's __version__."""
    remote = fetch_remote_version(url)
    if not remote:
        return False, None
    return parse_version(remote) > parse_version(__version__), remote


def _download_file(url, dest_path, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "lu-autologin"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    with open(dest_path, "wb") as f:
        f.write(data)
    return dest_path


def _version_in_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            m = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', f.read(), re.M)
        return m.group(1) if m else None
    except Exception:
        return None


def download_update_files(remote_version, dest_dir=SCRIPT_DIR, base_url=GITHUB_RAW_BASE):
    """Download the update set into dest_dir/.update, verify it, then move it
    into place (keeping a .bak copy of each replaced file). Returns True on
    success; on any failure the live files are left untouched."""
    tmp_dir = os.path.join(dest_dir, ".update")
    try:
        os.makedirs(tmp_dir, exist_ok=True)
        staged = []
        for name in UPDATE_FILES:
            staged_path = os.path.join(tmp_dir, name)
            _download_file(f"{base_url}/{name}", staged_path)
            staged.append((name, staged_path))
        # Verify the new script before touching anything live.
        script_path = os.path.join(tmp_dir, "lu_autologin.py")
        py_compile.compile(script_path, doraise=True)
        if _version_in_file(script_path) != remote_version:
            log("Downloaded script version does not match version.txt; aborting update.", "ERROR")
            return False
        for name, staged_path in staged:
            target = os.path.join(dest_dir, name)
            if os.path.exists(target):
                shutil.copy2(target, target + ".bak")
            os.replace(staged_path, target)
        return True
    except Exception as e:
        log(f"Update download failed: {e}", "ERROR")
        return False
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def apply_update(remote_version=None, dest_dir=SCRIPT_DIR, base_url=GITHUB_RAW_BASE):
    """Check for an update and apply it if one is available.
    Returns (updated, remote_version)."""
    if remote_version is None:
        available, remote_version = check_for_update()
        if not available:
            return False, remote_version
    log(f"Updating to version {remote_version}...", "INFO")
    if download_update_files(remote_version, dest_dir, base_url):
        log(f"Updated to version {remote_version}.", "SUCCESS")
        return True, remote_version
    return False, remote_version


# ---------------------------------------------------------------------------
# Interactive settings panel (`autologin` command)
# ---------------------------------------------------------------------------

PANEL_STRINGS = {
    "fa": {
        "title": "پنل مدیریت ورود خودکار اینترنت دانشگاه لرستان",
        "service_running": "وضعیت سرویس: در حال اجرا",
        "service_stopped": "وضعیت سرویس: متوقف",
        "startup_on": "اجرای خودکار با ویندوز: فعال",
        "startup_off": "اجرای خودکار با ویندوز: غیرفعال",
        "startup_na": "اجرای خودکار با ویندوز: در این سیستم پشتیبانی نمی‌شود",
        "user": "نام کاربری",
        "strategy": "روش لاگین",
        "strategy_none": "هنوز مشخص نشده",
        "check_interval": "فاصله‌ی بررسی",
        "renew": "تمدید پیشگیرانه",
        "seconds": "ثانیه",
        "minutes": "دقیقه",
        "menu": "انتخاب کنید:",
        "opt_start_service": "شروع سرویس در پس‌زمینه",
        "opt_stop_service": "توقف سرویس",
        "opt_toggle_startup": "فعال/غیرفعال کردن اجرای خودکار با ویندوز",
        "opt_language": "تغییر زبان به English",
        "opt_credentials": "تغییر نام کاربری و پسورد",
        "opt_interval": "تغییر فاصله‌ی بررسی",
        "opt_renew": "تغییر زمان تمدید پیشگیرانه",
        "opt_test": "تست لاگین الان",
        "opt_diagnose": "عیب‌یابی پورتال",
        "opt_logs": "نمایش لاگ",
        "opt_exit": "خروج",
        "prompt_choice": "شماره‌ی گزینه: ",
        "invalid_choice": "گزینه‌ی نامعتبر است.",
        "started": "سرویس در پس‌زمینه شروع شد.",
        "start_failed": "شروع سرویس ممکن نشد.",
        "stopped": "سرویس متوقف شد.",
        "stop_failed": "توقف سرویس ممکن نشد.",
        "startup_enabled": "اجرای خودکار با ویندوز فعال شد.",
        "startup_disabled": "اجرای خودکار با ویندوز غیرفعال شد.",
        "startup_failed": "تغییر اجرای خودکار ممکن نشد.",
        "lang_switched": "زبان به English تغییر کرد.",
        "new_username": "نام کاربری جدید (خالی = بدون تغییر): ",
        "new_password": "پسورد جدید (خالی = بدون تغییر): ",
        "saved": "تنظیمات ذخیره شد.",
        "new_interval": "فاصله‌ی بررسی جدید به ثانیه (الان: {v}): ",
        "new_renew": "تمدید پیشگیرانه‌ی جدید به دقیقه (الان: {v}): ",
        "invalid_number": "عدد معتبر وارد کنید.",
        "not_available": "این گزینه در این سیستم در دسترس نیست.",
        "press_enter": "برای بازگشت Enter بزنید...",
        "goodbye": "خدانگهدار!",
        "test_ok": "لاگین موفق بود.",
        "test_fail": "لاگین ناموفق بود؛ لاگ را ببینید.",
        "version": "نسخه",
        "opt_update": "بررسی به‌روزرسانی",
        "update_available": "نسخه‌ی جدید {v} موجود است.",
        "update_prompt": "به‌روز شود؟ (y/n): ",
        "update_done": "به‌روز شد.",
        "update_failed": "به‌روزرسانی ناموفق بود.",
        "update_check_failed": "بررسی به‌روزرسانی ممکن نشد.",
        "up_to_date": "به‌روز هستید.",
        "notif_title": "ورود خودکار دانشگاه لرستان",
        "notif_failed": "لاگین ناموفق بود؛ اینترنت قطع است.",
        "notif_recovered": "اینترنت وصل شد.",
        "tray_online": "متصل",
        "tray_offline": "قطع",
        "tray_starting": "در حال شروع...",
    },
    "en": {
        "title": "Lorestan University Auto-Login Panel",
        "service_running": "Service status: running",
        "service_stopped": "Service status: stopped",
        "startup_on": "Run on Windows startup: enabled",
        "startup_off": "Run on Windows startup: disabled",
        "startup_na": "Run on Windows startup: not supported on this system",
        "user": "Username",
        "strategy": "Login method",
        "strategy_none": "not detected yet",
        "check_interval": "Check interval",
        "renew": "Proactive renewal",
        "seconds": "seconds",
        "minutes": "minutes",
        "menu": "Choose an option:",
        "opt_start_service": "Start service in background",
        "opt_stop_service": "Stop service",
        "opt_toggle_startup": "Enable/disable run on Windows startup",
        "opt_language": "Switch language to فارسی",
        "opt_credentials": "Change username and password",
        "opt_interval": "Change check interval",
        "opt_renew": "Change proactive renewal time",
        "opt_test": "Test login now",
        "opt_diagnose": "Diagnose portal",
        "opt_logs": "View logs",
        "opt_exit": "Exit",
        "prompt_choice": "Option number: ",
        "invalid_choice": "Invalid option.",
        "started": "Service started in background.",
        "start_failed": "Could not start the service.",
        "stopped": "Service stopped.",
        "stop_failed": "Could not stop the service.",
        "startup_enabled": "Run on Windows startup enabled.",
        "startup_disabled": "Run on Windows startup disabled.",
        "startup_failed": "Could not change the startup setting.",
        "lang_switched": "Language switched to فارسی.",
        "new_username": "New username (empty = no change): ",
        "new_password": "New password (empty = no change): ",
        "saved": "Settings saved.",
        "new_interval": "New check interval in seconds (current: {v}): ",
        "new_renew": "New proactive renewal in minutes (current: {v}): ",
        "invalid_number": "Enter a valid number.",
        "not_available": "This option is not available on this system.",
        "press_enter": "Press Enter to go back...",
        "goodbye": "Goodbye!",
        "test_ok": "Login succeeded.",
        "test_fail": "Login failed; check the log.",
        "version": "Version",
        "opt_update": "Check for updates",
        "update_available": "New version {v} is available.",
        "update_prompt": "Update now? (y/n): ",
        "update_done": "Updated.",
        "update_failed": "Update failed.",
        "update_check_failed": "Could not check for updates.",
        "up_to_date": "You are up to date.",
        "notif_title": "LU Auto-Login",
        "notif_failed": "Login failed; the internet is down.",
        "notif_recovered": "Internet is back.",
        "tray_online": "Connected",
        "tray_offline": "Offline",
        "tray_starting": "Starting...",
    },
}


def _t(cfg, key, **kw):
    lang = cfg.get("language", "fa")
    strings = PANEL_STRINGS.get(lang, PANEL_STRINGS["fa"])
    s = strings.get(key, key)
    return s.format(**kw) if kw else s


def startup_vbs_path():
    """Path of the .vbs file that auto-starts the service on Windows logon."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    return os.path.join(appdata, "Microsoft", "Windows", "Start Menu",
                        "Programs", "Startup", "lu_autologin.vbs")


def is_startup_enabled():
    p = startup_vbs_path()
    return bool(p and os.path.exists(p))


def set_startup(enabled):
    """Enable/disable auto-start on Windows logon. Returns True on success."""
    p = startup_vbs_path()
    if not p:
        return False
    try:
        if enabled:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            script = os.path.join(SCRIPT_DIR, "lu_autologin.py")
            vbs = ('Set WshShell = CreateObject("WScript.Shell")\r\n'
                   f'WshShell.Run "pythonw.exe ""{script}""", 0, False\r\n')
            with open(p, "w", encoding="ascii") as f:
                f.write(vbs)
        else:
            if os.path.exists(p):
                os.remove(p)
        return True
    except Exception:
        return False


def is_service_running():
    """True when another instance holds the single-instance lock port."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind(("127.0.0.1", LOCK_PORT))
        return False
    except socket.error:
        return True
    finally:
        probe.close()


def _pythonw_exe():
    exe = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if os.path.exists(exe):
        return exe
    return shutil.which("pythonw") or "pythonw"


def start_service():
    """Start the monitor in the background (Windows only)."""
    if os.name != "nt":
        return False
    try:
        script = os.path.join(SCRIPT_DIR, "lu_autologin.py")
        subprocess.Popen([_pythonw_exe(), script],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         stdin=subprocess.DEVNULL, close_fds=True)
        return True
    except Exception:
        return False


def stop_service():
    """Stop a running background monitor (Windows only)."""
    if os.name != "nt":
        return False
    try:
        cmd = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'pythonw.exe' "
               "-and $_.CommandLine -like '*lu_autologin.py*' } | "
               "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }")
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                       capture_output=True, timeout=30)
        time.sleep(1)
        return not is_service_running()
    except Exception:
        return False


def open_logs():
    """Open the log file in Notepad (Windows) or print its path."""
    if os.name == "nt" and os.path.exists(LOG_FILE):
        try:
            subprocess.Popen(["notepad.exe", LOG_FILE])
            return True
        except Exception:
            return False
    print(LOG_FILE)
    return False


def _pause(cfg):
    try:
        input(_t(cfg, "press_enter"))
    except (EOFError, KeyboardInterrupt):
        print()


def run_panel(cfg, config_file):
    """Interactive settings panel. Returns an exit code."""
    if os.name == "nt":
        # UTF-8 code page so Persian text displays correctly in the console.
        os.system("chcp 65001 >nul")
    while True:
        print("=" * 65)
        print("  " + _t(cfg, "title"))
        print("=" * 65)
        running = is_service_running()
        print(_t(cfg, "service_running" if running else "service_stopped"))
        if startup_vbs_path() is None:
            print(_t(cfg, "startup_na"))
        else:
            print(_t(cfg, "startup_on" if is_startup_enabled() else "startup_off"))
        print(f"{_t(cfg, 'user')}: {cfg.get('username', '-')}")
        print(f"{_t(cfg, 'strategy')}: {cfg.get('strategy') or _t(cfg, 'strategy_none')}")
        print(f"{_t(cfg, 'check_interval')}: {cfg.get('check_interval_seconds', 20)} {_t(cfg, 'seconds')}")
        print(f"{_t(cfg, 'renew')}: {cfg.get('proactive_renew_minutes', 110)} {_t(cfg, 'minutes')}")
        print(f"{_t(cfg, 'version')}: {__version__}")
        print("-" * 65)
        print(_t(cfg, "menu"))
        print(f"  1. {_t(cfg, 'opt_stop_service' if running else 'opt_start_service')}")
        print(f"  2. {_t(cfg, 'opt_toggle_startup')}")
        print(f"  3. {_t(cfg, 'opt_language')}")
        print(f"  4. {_t(cfg, 'opt_credentials')}")
        print(f"  5. {_t(cfg, 'opt_interval')}")
        print(f"  6. {_t(cfg, 'opt_renew')}")
        print(f"  7. {_t(cfg, 'opt_test')}")
        print(f"  8. {_t(cfg, 'opt_diagnose')}")
        print(f"  9. {_t(cfg, 'opt_logs')}")
        print(f" 10. {_t(cfg, 'opt_update')}")
        print(f"  0. {_t(cfg, 'opt_exit')}")
        try:
            choice = input(_t(cfg, "prompt_choice")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print(_t(cfg, "goodbye"))
            return 0

        if choice == "0":
            print(_t(cfg, "goodbye"))
            return 0
        elif choice == "1":
            if running:
                print(_t(cfg, "stopped" if stop_service() else "stop_failed"))
            else:
                print(_t(cfg, "started" if start_service() else "start_failed"))
        elif choice == "2":
            target = not is_startup_enabled()
            ok = set_startup(target)
            if ok:
                print(_t(cfg, "startup_enabled" if target else "startup_disabled"))
            else:
                print(_t(cfg, "startup_failed"))
        elif choice == "3":
            cfg["language"] = "en" if cfg.get("language", "fa") == "fa" else "fa"
            save_config(cfg, config_file)
            print(_t(cfg, "lang_switched"))
        elif choice == "4":
            try:
                new_user = input(_t(cfg, "new_username")).strip()
                new_pass = getpass.getpass(_t(cfg, "new_password")).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                continue
            if new_user:
                cfg["username"] = new_user
            if new_pass:
                cfg["password"] = new_pass
            save_config(cfg, config_file)
            print(_t(cfg, "saved"))
        elif choice == "5":
            try:
                v = input(_t(cfg, "new_interval",
                             v=cfg.get("check_interval_seconds", 20))).strip()
                n = int(v)
                if not 5 <= n <= 3600:
                    raise ValueError
                cfg["check_interval_seconds"] = n
                save_config(cfg, config_file)
                print(_t(cfg, "saved"))
            except (ValueError, EOFError, KeyboardInterrupt):
                print()
                print(_t(cfg, "invalid_number"))
        elif choice == "6":
            try:
                v = input(_t(cfg, "new_renew",
                             v=cfg.get("proactive_renew_minutes", 110))).strip()
                n = int(v)
                if not 1 <= n <= 600:
                    raise ValueError
                cfg["proactive_renew_minutes"] = n
                save_config(cfg, config_file)
                print(_t(cfg, "saved"))
            except (ValueError, EOFError, KeyboardInterrupt):
                print()
                print(_t(cfg, "invalid_number"))
        elif choice == "7":
            opener = create_session()
            ok, _ = perform_login(opener, cfg, config_file)
            print(_t(cfg, "test_ok" if ok else "test_fail"))
            _pause(cfg)
        elif choice == "8":
            opener = create_session()
            diagnose(opener, cfg)
            _pause(cfg)
        elif choice == "9":
            if not open_logs():
                print(_t(cfg, "not_available"))
            _pause(cfg)
        elif choice == "10":
            available, remote = check_for_update()
            if remote is None:
                print(_t(cfg, "update_check_failed"))
            elif not available:
                print(_t(cfg, "up_to_date"))
            else:
                print(_t(cfg, "update_available", v=remote))
                try:
                    ans = input(_t(cfg, "update_prompt")).strip().lower()
                except (EOFError, KeyboardInterrupt):
                    print()
                    continue
                if ans in ("y", "yes", "بله"):
                    ok, _ = apply_update(remote)
                    if ok:
                        print(_t(cfg, "update_done"))
                        if is_service_running():
                            stop_service()
                            time.sleep(1)
                            start_service()
                    else:
                        print(_t(cfg, "update_failed"))
            _pause(cfg)
        else:
            print(_t(cfg, "invalid_choice"))
        print()
    return 0


# ---------------------------------------------------------------------------
# System tray icon + notifications (Windows, pystray is optional)
# ---------------------------------------------------------------------------

try:
    import pystray
    _PYSTRAY_AVAILABLE = True
except Exception:
    pystray = None
    _PYSTRAY_AVAILABLE = False

try:
    from PIL import Image, ImageDraw
    _PIL_AVAILABLE = True
except Exception:
    Image = None
    ImageDraw = None
    _PIL_AVAILABLE = False

TRAY_COLORS = {
    "starting": (156, 163, 175),   # gray
    "online": (34, 197, 94),       # green
    "offline": (239, 68, 68),      # red
}


def _tray_image(status):
    """64x64 tray icon: a Wi-Fi-like symbol in the status color."""
    if not _PIL_AVAILABLE:
        return None
    color = TRAY_COLORS.get(status, TRAY_COLORS["starting"])
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([2, 2, 62, 62], radius=14, fill=color + (255,))
    d.arc([16, 22, 48, 54], 200, 340, fill="white", width=4)
    d.arc([22, 30, 42, 50], 200, 340, fill="white", width=4)
    d.ellipse([29, 42, 35, 48], fill="white")
    return img


def notify(control, message, title=None):
    """Show a tray notification (toast). Falls back to the log when no
    tray icon is running."""
    icon = control.get("icon") if control else None
    if icon is not None:
        try:
            icon.notify(message, title or "LU Auto-Login")
            return True
        except Exception:
            pass
    log(f"{title + ': ' if title else ''}{message}", "INFO")
    return False


def build_tray_menu(cfg, control):
    """Fresh tray menu (rebuilt whenever the status text changes)."""
    lang = cfg.get("language", "fa")
    if lang == "fa":
        status_label = control.get("status_text") or "در حال شروع..."
        login_now = "لاگین الان"
        open_panel = "باز کردن پنل"
        check_update = "بررسی به‌روزرسانی"
        quit_label = "خروج"
    else:
        status_label = control.get("status_text") or "Starting..."
        login_now = "Login now"
        open_panel = "Open panel"
        check_update = "Check for updates"
        quit_label = "Quit"

    def _login_now(icon, item):
        control["wake_event"].set()

    def _open_panel(icon, item):
        try:
            bat = os.path.join(SCRIPT_DIR, "autologin.bat")
            if hasattr(os, "startfile"):
                os.startfile(bat)
            else:
                subprocess.Popen(["cmd", "/c", "start", "", bat])
        except Exception as e:
            log(f"Could not open panel from tray: {e}", "ERROR")

    def _check_update(icon, item):
        def _run():
            cfg = control["cfg"]
            available, remote = check_for_update()
            if remote is None:
                notify(control, _t(cfg, "update_check_failed"), _t(cfg, "notif_title"))
            elif available:
                ok, _ = apply_update(remote)
                if ok:
                    notify(control, _t(cfg, "update_done"), _t(cfg, "notif_title"))
                    request_restart(control)
                else:
                    notify(control, _t(cfg, "update_failed"), _t(cfg, "notif_title"))
            else:
                notify(control, _t(cfg, "up_to_date"), _t(cfg, "notif_title"))
        threading.Thread(target=_run, daemon=True).start()

    def _quit(icon, item):
        control["stop_event"].set()
        icon.stop()

    return pystray.Menu(
        pystray.MenuItem(status_label, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(login_now, _login_now),
        pystray.MenuItem(open_panel, _open_panel),
        pystray.MenuItem(check_update, _check_update),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(quit_label, _quit),
    )


def set_tray_status(control, status, status_text):
    control["status"] = status
    control["status_text"] = status_text
    icon = control.get("icon")
    if icon is None:
        return
    try:
        img = _tray_image(status)
        if img is not None:
            icon.icon = img
        icon.title = f"LU Auto-Login — {status_text}"
        icon.menu = build_tray_menu(control["cfg"], control)
        icon.update_menu()
    except Exception:
        pass


def create_tray(cfg, control):
    """Build the tray icon (Windows only, pystray optional). Returns the
    pystray Icon, or None when the tray is unavailable."""
    if os.name != "nt" or not _PYSTRAY_AVAILABLE:
        if os.name == "nt":
            log("pystray is not installed; tray icon and notifications are "
                "unavailable. Run: python -m pip install pystray pillow",
                "WARNING")
        return None
    try:
        menu = build_tray_menu(cfg, control)
        icon = pystray.Icon("lu-autologin", _tray_image("starting"),
                            "LU Auto-Login", menu)
        control["icon"] = icon
        return icon
    except Exception as e:
        log(f"Could not start tray icon: {e}", "WARNING")
        return None


def spawn_new_process():
    script = os.path.join(SCRIPT_DIR, "lu_autologin.py")
    subprocess.Popen([sys.executable, script] + sys.argv[1:])


def request_restart(control):
    """Restart the process with the same arguments (used after an update).
    With a tray running, stop the tray first so the main thread can restart
    cleanly; without a tray, spawn the new process and exit immediately."""
    if control is None:
        spawn_new_process()
        os._exit(0)
    control["restart_requested"] = True
    icon = control.get("icon")
    if icon is not None:
        try:
            icon.stop()
        except Exception:
            pass
    else:
        spawn_new_process()
        os._exit(0)


# ---------------------------------------------------------------------------
# Monitor loop
# ---------------------------------------------------------------------------

def run_monitor(cfg, config_file, once=False, force_strategy=None,
                stop_event=None, wake_event=None, control=None):
    username = cfg["username"]
    password = cfg["password"]
    check_interval = int(cfg.get("check_interval_seconds", 20))
    proactive_seconds = int(cfg.get("proactive_renew_minutes", 110)) * 60

    portal_urls = cfg.get("portal_urls") or list(DEFAULT_PORTAL_URLS)

    print("=" * 65)
    print("  LORESTAN UNIVERSITY (LU) INTERNET AUTO-LOGIN SERVICE")
    print("=" * 65)
    log(f"Configured User     : {username}", "INFO")
    log(f"Target Portal       : {portal_urls[0]}", "INFO")
    log(f"Check Frequency     : Every {check_interval} seconds", "INFO")
    log(f"Proactive Renewal   : Every {proactive_seconds // 60} minutes", "INFO")
    log(f"Version             : {__version__}", "INFO")
    if cfg.get("strategy"):
        log(f"Preferred Method    : {cfg['strategy']} (remembered)", "INFO")
    print("=" * 65)

    opener = create_session()
    connectivity_urls = cfg.get("connectivity_urls") or list(DEFAULT_CONNECTIVITY_URLS)
    last_login_time = 0
    fail_streak = 0
    last_update_check = 0

    def _online():
        if control is not None:
            set_tray_status(control, "online", _t(cfg, "tray_online"))

    def _offline():
        if control is not None:
            set_tray_status(control, "offline", _t(cfg, "tray_offline"))

    def _note_failed():
        if fail_streak == NOTIFY_AFTER_FAILURES and control is not None:
            notify(control, _t(cfg, "notif_failed"), _t(cfg, "notif_title"))

    if check_internet(connectivity_urls):
        log("Internet is currently ACTIVE.", "INFO")
        last_login_time = time.time()
        _online()
    else:
        log("Internet is DOWN. Attempting initial login...", "WARNING")
        _offline()
        ok, _ = perform_login(opener, cfg, config_file, force_strategy)
        if ok:
            last_login_time = time.time()
            _online()
        else:
            fail_streak = 1

    if once:
        return 0 if last_login_time > 0 else 1

    if stop_event is None:
        stop_event = threading.Event()
    if wake_event is None:
        wake_event = threading.Event()

    while not stop_event.is_set():
        try:
            # Wake early for "Login now" from the tray, or wait the interval.
            wake_event.wait(check_interval)
            wake_event.clear()
            if stop_event.is_set():
                break
            now = time.time()

            # Periodic self-update check.
            if cfg.get("auto_update", True) and (now - last_update_check) >= UPDATE_CHECK_INTERVAL_SECONDS:
                last_update_check = now
                available, remote = check_for_update()
                if available:
                    ok, _ = apply_update(remote)
                    if ok:
                        request_restart(control)
                        break

            if last_login_time > 0 and (now - last_login_time) >= proactive_seconds:
                log("Proactive session renewal window reached. Refreshing session...", "INFO")
                if perform_login(opener, cfg, config_file, force_strategy)[0]:
                    last_login_time = now
                    fail_streak = 0
                    _online()
                else:
                    fail_streak += 1
                    _offline()
                    _note_failed()
                continue

            if not check_internet(connectivity_urls):
                log("Internet disconnected! Reconnecting...", "WARNING")
                _offline()
                if perform_login(opener, cfg, config_file, force_strategy)[0]:
                    last_login_time = now
                    if fail_streak >= 1 and control is not None:
                        notify(control, _t(cfg, "notif_recovered"), _t(cfg, "notif_title"))
                    fail_streak = 0
                    _online()
                    log("Connection restored successfully.", "SUCCESS")
                else:
                    fail_streak += 1
                    _note_failed()
                    log("Retry scheduled in next cycle...", "INFO")
            else:
                fail_streak = 0
                _online()

        except KeyboardInterrupt:
            log("Service stopped by user.", "INFO")
            break
        except Exception as ex:
            log(f"Unexpected error: {ex}", "ERROR")
            stop_event.wait(5)
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Lorestan University internet auto-login (multi-strategy).")
    parser.add_argument("--once", action="store_true",
                        help="Try to log in once, then exit (exit 0 on success).")
    parser.add_argument("--diagnose", action="store_true",
                        help="Fetch the portal, print detected forms/CHAP data, "
                             "save the HTML to portal_debug.html, then exit.")
    parser.add_argument("--panel", action="store_true",
                        help="Open the interactive settings panel "
                             "(also available as the `autologin` command).")
    parser.add_argument("--no-tray", action="store_true",
                        help="Disable the system tray icon (Windows).")
    parser.add_argument("--strategy", choices=[n for n, _ in STRATEGIES],
                        help="Force a single login method (for testing).")
    parser.add_argument("--config", default=DEFAULT_CONFIG_FILE,
                        help="Path to config.json (default: next to the script).")
    args = parser.parse_args()

    cfg = load_config(args.config, interactive=not args.diagnose)
    opener = create_session()

    if args.diagnose:
        return diagnose(opener, cfg)

    if args.panel:
        return run_panel(cfg, args.config)

    if not cfg.get("username") or not cfg.get("password"):
        print("[ERROR] No credentials configured. Run once without --diagnose "
              "to enter them, or fill in config.json.")
        return 1

    if args.once:
        return run_monitor(cfg, args.config, once=True,
                           force_strategy=args.strategy)

    ensure_single_instance()

    stop_event = threading.Event()
    wake_event = threading.Event()
    control = {
        "cfg": cfg,
        "status": "starting",
        "status_text": _t(cfg, "tray_starting"),
        "icon": None,
        "restart_requested": False,
        "stop_event": stop_event,
        "wake_event": wake_event,
    }

    tray = None if args.no_tray else create_tray(cfg, control)

    monitor_thread = threading.Thread(
        target=run_monitor,
        args=(cfg, args.config),
        kwargs={"force_strategy": args.strategy,
                "stop_event": stop_event,
                "wake_event": wake_event,
                "control": control},
        daemon=True)
    monitor_thread.start()

    if tray is not None:
        tray.run()  # blocks until the icon is stopped (Quit or restart)
        if control.get("restart_requested"):
            spawn_new_process()
        return 0

    # No tray: wait for the monitor thread (it restarts itself after updates).
    try:
        while monitor_thread.is_alive():
            monitor_thread.join(timeout=1)
    except KeyboardInterrupt:
        stop_event.set()
        monitor_thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
