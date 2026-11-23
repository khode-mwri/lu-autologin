#!/usr/bin/env python3
"""
Lorestan University Internet Auto-Login & Session Keep-Alive
Portal: https://internet.lu.ac.ir/login
Author: khode-mwri
"""

import sys
import os
import json
import time
import ssl
import re
import socket
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import hashlib
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
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
LOG_FILE = os.path.join(SCRIPT_DIR, "autologin.log")

# Single-instance lock port to prevent duplicate processes
LOCK_PORT = 47829
_instance_lock_socket = None

def ensure_single_instance():
    """Ensure only one instance of the auto-login service runs at a time."""
    global _instance_lock_socket
    try:
        _instance_lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _instance_lock_socket.bind(("127.0.0.1", LOCK_PORT))
    except socket.error:
        print("[INFO] Another instance of LU Auto-Login is already running. Exiting.", flush=True)
        sys.exit(0)


def load_or_create_config():
    """Load configuration from config.json, or prompt interactively if missing."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if cfg.get("username") and cfg.get("password") and cfg["username"] != "YOUR_STUDENT_ID":
                    return cfg
        except Exception as e:
            print(f"[ERROR] Failed to read config.json: {e}")

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

    cfg = {
        "username": username,
        "password": password,
        "check_interval_seconds": 20,
        "proactive_renew_minutes": 110
    }

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        print("[OK] Configuration saved successfully to config.json.")
    except Exception as e:
        print(f"[ERROR] Could not save config.json: {e}")

    return cfg


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
    """Create SSL context that permits internal/self-signed university certificates."""
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


def test_university_portal_reachability(opener, urls):
    """Check if the university portal can be reached."""
    for url in urls:
        try:
            req = urllib.request.Request(url)
            with opener.open(req, timeout=5) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                return resp.geturl(), html
        except Exception:
            continue
    return None, None


def extract_form_params(html):
    """Extract hidden inputs and MikroTik CHAP challenge if present."""
    params = {}
    hidden_inputs = re.findall(r'<input[^>]+type=["\']hidden["\'][^>]*>', html, re.IGNORECASE)
    for inp in hidden_inputs:
        name_m = re.search(r'name=["\']([^"\']+)["\']', inp, re.IGNORECASE)
        val_m = re.search(r'value=["\']([^"\']*)["\']', inp, re.IGNORECASE)
        if name_m and val_m:
            params[name_m.group(1)] = val_m.group(1)

    chap_id = None
    chap_challenge = None
    js_chap = re.search(r"hexMD5\s*\(\s*(['\"])(.*?)\1\s*\+\s*.*?\+\s*(['\"])(.*?)\3\s*\)", html)
    if js_chap:
        chap_id = js_chap.group(2)
        chap_challenge = js_chap.group(4)

    return params, chap_id, chap_challenge


def perform_login(opener, username, password, portal_urls):
    """Execute login to internet.lu.ac.ir portal."""
    log("Connecting to university portal...", "INFO")
    
    portal_url, html = test_university_portal_reachability(opener, portal_urls)
    if not portal_url:
        log("Cannot reach internet.lu.ac.ir. Ensure you are on University Wi-Fi.", "WARNING")
        return False

    if "logout" in html.lower() or "status" in portal_url.lower():
        log("Session is currently active (Already logged in).", "INFO")
        return True

    params, chap_id, chap_challenge = extract_form_params(html)
    
    payload = {
        "username": username,
        "password": password,
    }

    if chap_id and chap_challenge:
        log("MikroTik CHAP authentication detected. Computing MD5 hash...", "DEBUG")
        try:
            if chap_id.startswith("\\"):
                val = int(chap_id[1:], 8)
                cid_bytes = bytes([val])
            else:
                cid_bytes = chap_id.encode('latin1')
            pwd_bytes = password.encode('utf-8')
            chal_bytes = chap_challenge.encode('latin1')
            payload["password"] = hashlib.md5(cid_bytes + pwd_bytes + chal_bytes).hexdigest()
        except Exception as e:
            log(f"CHAP calculation fallback: {e}", "WARNING")

    for k, v in params.items():
        if k not in payload:
            payload[k] = v

    data = urllib.parse.urlencode(payload).encode('utf-8')
    post_req = urllib.request.Request(
        portal_url,
        data=data,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': portal_url
        }
    )

    try:
        with opener.open(post_req, timeout=8) as resp:
            resp_body = resp.read().decode('utf-8', errors='ignore')
            final_url = resp.geturl()

            if "status" in final_url or "logout" in resp_body.lower() or "connected" in resp_body.lower():
                log("Login SUCCESSFUL! Connected to university internet.", "SUCCESS")
                return True
            elif "invalid" in resp_body.lower() or "incorrect" in resp_body.lower() or "wrong" in resp_body.lower():
                log("Login FAILED: Incorrect username or password.", "ERROR")
                return False
            else:
                time.sleep(1)
                if check_internet(["http://clients3.google.com/generate_204"]):
                    log("Login confirmed! Internet access is verified.", "SUCCESS")
                    return True
                log("Login request sent, awaiting network confirmation...", "INFO")
                return True
    except Exception as e:
        log(f"Network error during login request: {e}", "ERROR")
        return False


def run_monitor():
    ensure_single_instance()

    cfg = load_or_create_config()
    username = cfg["username"]
    password = cfg["password"]
    check_interval = int(cfg.get("check_interval_seconds", 20))
    proactive_seconds = int(cfg.get("proactive_renew_minutes", 110)) * 60

    portal_urls = ["https://internet.lu.ac.ir/login", "http://internet.lu.ac.ir/login"]
    connectivity_urls = [
        "http://clients3.google.com/generate_204",
        "http://detectportal.firefox.com/success.txt",
        "http://www.msftconnecttest.com/connecttest.txt"
    ]

    print("=" * 65)
    print("  LORESTAN UNIVERSITY (LU) INTERNET AUTO-LOGIN SERVICE")
    print("=" * 65)
    log(f"Configured User     : {username}", "INFO")
    log(f"Target Portal       : {portal_urls[0]}", "INFO")
    log(f"Check Frequency     : Every {check_interval} seconds", "INFO")
    log(f"Proactive Renewal   : Every {proactive_seconds // 60} minutes", "INFO")
    print("=" * 65)

    opener = create_session()
    last_login_time = 0

    if check_internet(connectivity_urls):
        log("Internet is currently ACTIVE.", "INFO")
        last_login_time = time.time()
    else:
        log("Internet is DOWN. Attempting initial login...", "WARNING")
        if perform_login(opener, username, password, portal_urls):
            last_login_time = time.time()

    while True:
        try:
            time.sleep(check_interval)
            now = time.time()

            if last_login_time > 0 and (now - last_login_time) >= proactive_seconds:
                log("Proactive session renewal window reached. Refreshing session...", "INFO")
                if perform_login(opener, username, password, portal_urls):
                    last_login_time = now
                continue

            if not check_internet(connectivity_urls):
                log("Internet disconnected! Reconnecting...", "WARNING")
                if perform_login(opener, username, password, portal_urls):
                    last_login_time = now
                    log("Connection restored successfully.", "SUCCESS")
                else:
                    log("Retry scheduled in next cycle...", "INFO")

        except KeyboardInterrupt:
            log("Service stopped by user.", "INFO")
            break
        except Exception as ex:
            log(f"Unexpected error: {ex}", "ERROR")
            time.sleep(5)


if __name__ == "__main__":
    run_monitor()
