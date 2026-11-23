#!/usr/bin/env python3
"""Scripted test for the --panel mode (no Windows needed).

Drives the panel through stdin: switch language fa -> en, change the
check interval to 30, then exit. Asserts the config file was updated
and the menu re-rendered in English.

Usage:
    python3 tests/test_panel.py
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPT = os.path.join(ROOT, "lu_autologin.py")


def _run_panel(cfg_dict, stdin_text):
    fd, cfg_path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(cfg_dict, f)
    proc = subprocess.run(
        [sys.executable, SCRIPT, "--panel", "--config", cfg_path],
        input=stdin_text, capture_output=True, text=True, timeout=60)
    out = proc.stdout + proc.stderr
    saved = json.load(open(cfg_path))
    os.unlink(cfg_path)
    return proc, saved, out


def main():
    checks = []

    def check(name, ok):
        print(("PASS " if ok else "FAIL ") + name)
        checks.append(ok)

    base_cfg = {"username": "12345", "password": "secret123",
                "check_interval_seconds": 20, "proactive_renew_minutes": 110,
                "language": "fa"}

    # Scenario 1: switch language fa -> en, change interval, exit.
    proc, saved, out = _run_panel(
        dict(base_cfg), "3\n5\n30\n0\n")
    check("exit code 0", proc.returncode == 0)
    check("language switched to en", saved.get("language") == "en")
    check("interval changed to 30", saved.get("check_interval_seconds") == 30)
    check("menu shown in English after switch", "Choose an option:" in out)
    check("goodbye in English", "Goodbye!" in out)
    check("startup shown as unsupported here", "not supported on this system" in out)
    check("version shown in header", "1.3.1" in out)

    # Scenario 2: config saved as English, but the panel must still OPEN
    # in Persian by default.
    proc, saved, out = _run_panel(
        dict(base_cfg, language="en"), "0\n")
    check("opens in Persian despite saved en (title)",
          "پنل مدیریت ورود خودکار" in out)
    check("opens in Persian despite saved en (menu)",
          "انتخاب کنید:" in out)
    check("opens in Persian despite saved en (no English menu)",
          "Choose an option:" not in out)

    failed = checks.count(False)
    print(f"{len(checks) - failed}/{len(checks)} checks passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
