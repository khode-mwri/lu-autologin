#!/usr/bin/env python3
"""Run lu_autologin.py against the mock portal in every variant.

For each variant it starts the mock server, runs the script with --once
(correct password -> must succeed, wrong password -> must fail), and
also runs --diagnose once to check portal parsing. Prints a summary
table and exits non-zero if anything fails.

Usage:
    python3 tests/run_strategy_tests.py
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPT = os.path.join(ROOT, "lu_autologin.py")
MOCK = os.path.join(HERE, "mock_portal.py")

VARIANTS = ["chap-hex", "chap-octal", "chap-raw", "plain",
            "chap-action", "plain-action"]
PASSWORD = "secret123"


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def wait_up(port, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/login", timeout=2)
            return True
        except Exception:
            time.sleep(0.2)
    return False


def run_script(config_path, extra_args):
    cmd = [sys.executable, SCRIPT, "--config", config_path] + extra_args
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return proc.returncode, proc.stdout + proc.stderr


def make_config(port, password):
    fd, path = tempfile.mkstemp(suffix=".json")
    cfg = {
        "username": "12345",
        "password": password,
        "check_interval_seconds": 20,
        "proactive_renew_minutes": 110,
        "portal_urls": [f"http://127.0.0.1:{port}/login"],
        "connectivity_urls": [f"http://127.0.0.1:{port}/generate_204"],
    }
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    return path


def run_case(variant, password, extra_args, expect):
    """Start a fresh mock server, run the script once, stop the server.

    A fresh server per case matters: login state is server-side, and a
    previous successful login would make the next case see the internet
    as already active.
    """
    port = free_port()
    mock = subprocess.Popen(
        [sys.executable, MOCK, "--variant", variant,
         "--port", str(port), "--password", PASSWORD],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        if not wait_up(port):
            return f"FAIL (mock did not start)"
        cfg = make_config(port, password)
        try:
            rc, out = run_script(cfg, extra_args)
        finally:
            os.unlink(cfg)
        if expect == "success":
            ok = rc == 0 and "SUCCESSFUL via" in out
        elif expect == "bad-creds":
            ok = rc != 0 and "Incorrect username or password" in out
        elif expect == "chap":
            ok = rc == 0 and "CHAP detected" in out
        else:  # "no-chap"
            ok = rc == 0 and "CHAP not detected" in out
        return "PASS" if ok else f"FAIL (rc={rc})\n{out[-800:]}"
    finally:
        mock.terminate()
        try:
            mock.wait(timeout=5)
        except subprocess.TimeoutExpired:
            mock.kill()


def main():
    results = []
    for variant in VARIANTS:
        results.append((variant, "good-password",
                        run_case(variant, PASSWORD, ["--once"], "success")))
        results.append((variant, "wrong-password",
                        run_case(variant, "wrong-password", ["--once"], "bad-creds")))
        results.append((variant, "diagnose",
                        run_case(variant, PASSWORD, ["--diagnose"],
                                 "chap" if variant.startswith("chap") else "no-chap")))

    print()
    print(f"{'variant':<13} {'case':<14} result")
    print("-" * 50)
    failed = 0
    for variant, case, res in results:
        first = res.split("\n")[0]
        print(f"{variant:<13} {case:<14} {first}")
        if first.startswith("FAIL"):
            failed += 1
            print(res)
    print("-" * 50)
    print(f"{len(results) - failed}/{len(results)} checks passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
