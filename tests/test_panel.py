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


def main():
    fd, cfg_path = tempfile.mkstemp(suffix=".json")
    cfg = {"username": "12345", "password": "secret123",
           "check_interval_seconds": 20, "proactive_renew_minutes": 110,
           "language": "fa"}
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(cfg, f)

    # 3 = switch language, 5 = change interval, 30 = new value, 0 = exit
    proc = subprocess.run(
        [sys.executable, SCRIPT, "--panel", "--config", cfg_path],
        input="3\n5\n30\n0\n", capture_output=True, text=True, timeout=60)
    out = proc.stdout + proc.stderr
    saved = json.load(open(cfg_path))
    os.unlink(cfg_path)

    checks = [
        ("exit code 0", proc.returncode == 0),
        ("language switched to en", saved.get("language") == "en"),
        ("interval changed to 30", saved.get("check_interval_seconds") == 30),
        ("menu shown in English after switch", "Choose an option:" in out),
        ("goodbye in English", "Goodbye!" in out),
        ("startup shown as unsupported here", "not supported on this system" in out),
        ("version shown in header", "1.3.0" in out),
    ]
    failed = 0
    for name, ok in checks:
        print(("PASS " if ok else "FAIL ") + name)
        failed += 0 if ok else 1
    if failed:
        print(out[-2000:])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
