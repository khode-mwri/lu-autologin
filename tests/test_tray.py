#!/usr/bin/env python3
"""Tests for the tray icon helpers.

Covers what can be checked without a display or Windows:
- tray icon image generation (Pillow),
- graceful fallback when pystray is unavailable (no tray, notify -> log),
- tray menu construction when pystray IS importable (skipped otherwise),
- set_tray_status with no icon is a no-op that still records state.

Usage:
    python3 tests/test_tray.py
    /tmp/traytest/bin/python tests/test_tray.py   # with pystray installed
"""

import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import lu_autologin as lu


def main():
    checks = []

    def check(name, ok):
        print(("PASS " if ok else "FAIL ") + name)
        checks.append(ok)

    cfg = {"language": "fa", "username": "12345", "password": "secret123"}
    control = {"cfg": cfg, "status": "starting", "status_text": "",
               "icon": None, "restart_requested": False}

    # --- icon image -------------------------------------------------------
    if lu._PIL_AVAILABLE:
        for status, rgb in lu.TRAY_COLORS.items():
            img = lu._tray_image(status)
            check(f"icon {status} is 64x64 RGBA",
                  img is not None and img.size == (64, 64) and img.mode == "RGBA")
            px = img.load()
            most_common = collections.Counter(
                px[x, y] for y in range(64) for x in range(64)
            ).most_common(1)[0][0]
            check(f"icon {status} dominant color matches",
                  most_common == rgb + (255,))
        check("unknown status falls back to gray",
              lu._tray_image("bogus") is not None)
    else:
        print("SKIP icon image tests (Pillow not installed)")
        check("icon returns None without Pillow", lu._tray_image("online") is None)

    # --- fallback when pystray is missing ---------------------------------
    tray = lu.create_tray(cfg, control)
    if not lu._PYSTRAY_AVAILABLE or os.name != "nt":
        check("create_tray returns None without pystray/Windows", tray is None)
    else:
        print("SKIP fallback test (pystray available on Windows)")

    # notify with no icon falls back to the log and returns False.
    check("notify without icon returns False",
          lu.notify(control, "test message", "test title") is False)

    # set_tray_status with no icon records state and does not raise.
    lu.set_tray_status(control, "online", "Connected")
    check("set_tray_status records state without icon",
          control["status"] == "online" and control["status_text"] == "Connected")

    # --- menu construction (only when pystray imports) --------------------
    if lu._PYSTRAY_AVAILABLE:
        menu = lu.build_tray_menu(cfg, control)
        items = list(menu)
        check("menu has 7 entries", len(items) == 7)
        check("first menu item is the disabled status line",
              items[0].enabled is False)
        check("menu has a quit item",
              any(getattr(i, "text", "") in ("خروج", "Quit") for i in items))
    else:
        print("SKIP menu tests (pystray not installed)")

    failed = checks.count(False)
    print(f"{len(checks) - failed}/{len(checks)} checks passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
