#!/usr/bin/env python3
"""Tests for the self-update code (no Windows, no GitHub needed).

Serves a fake update set from a local HTTP server and checks:
- version parsing and comparison,
- fetching version.txt (newer / same / missing),
- downloading + verifying + installing the update set into a temp dir,
- rejection of a broken script (live files left untouched).

Usage:
    python3 tests/test_update.py
"""

import functools
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import lu_autologin as lu


def _serve(directory):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=directory)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def _write_update_set(directory, version, broken=False):
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, "version.txt"), "w", encoding="utf-8") as f:
        f.write(version + "\n")
    for name in lu.UPDATE_FILES:
        path = os.path.join(directory, name)
        if name == "lu_autologin.py":
            body = (f'__version__ = "{version}"\n' if not broken
                    else "def broken(:\n")
        else:
            body = f"# fake {name} for version {version}\n"
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)


def main():
    checks = []

    def check(name, ok):
        print(("PASS " if ok else "FAIL ") + name)
        checks.append(ok)

    # --- version parsing -------------------------------------------------
    check("parse 1.3.0", lu.parse_version("1.3.0") == (1, 3, 0))
    check("parse with spaces", lu.parse_version(" 2.0 ") == (2, 0))
    check("parse empty", lu.parse_version("") == (0,))
    check("parse single", lu.parse_version("1") == (1,))
    check("newer compares greater",
          lu.parse_version("1.3.0") > lu.parse_version("1.2.9"))
    check("same compares equal",
          lu.parse_version("1.3.0") == lu.parse_version("1.3.0"))

    # --- fetch / check against a local server -----------------------------
    with tempfile.TemporaryDirectory() as serve_dir:
        _write_update_set(serve_dir, "9.9.9")
        server, base = _serve(serve_dir)
        try:
            available, remote = lu.check_for_update(url=base + "/version.txt")
            check("remote newer detected",
                  available is True and remote == "9.9.9")

            # Same version as the script -> not available.
            with open(os.path.join(serve_dir, "version.txt"), "w") as f:
                f.write(lu.__version__ + "\n")
            available, remote = lu.check_for_update(url=base + "/version.txt")
            check("same version not an update",
                  available is False and remote == lu.__version__)

            # Missing version.txt -> (False, None), no crash.
            available, remote = lu.check_for_update(url=base + "/nope.txt")
            check("missing version.txt handled",
                  available is False and remote is None)
        finally:
            server.shutdown()

    # --- full apply into a temp dir ---------------------------------------
    with tempfile.TemporaryDirectory() as serve_dir, \
            tempfile.TemporaryDirectory() as dest_dir:
        _write_update_set(serve_dir, "9.9.9")
        server, base = _serve(serve_dir)
        try:
            old_script = os.path.join(dest_dir, "lu_autologin.py")
            with open(old_script, "w", encoding="utf-8") as f:
                f.write('__version__ = "1.3.0"\n# old\n')
            updated, remote = lu.apply_update("9.9.9", dest_dir=dest_dir,
                                              base_url=base)
            check("apply_update succeeds", updated is True and remote == "9.9.9")
            check("new script installed",
                  lu._version_in_file(old_script) == "9.9.9")
            check("backup kept",
                  os.path.exists(old_script + ".bak")
                  and lu._version_in_file(old_script + ".bak") == "1.3.0")
            check("other files installed",
                  os.path.exists(os.path.join(dest_dir, "autologin.bat")))
        finally:
            server.shutdown()

    # --- broken script is rejected, live files untouched ------------------
    with tempfile.TemporaryDirectory() as serve_dir, \
            tempfile.TemporaryDirectory() as dest_dir:
        _write_update_set(serve_dir, "9.9.9", broken=True)
        server, base = _serve(serve_dir)
        try:
            old_script = os.path.join(dest_dir, "lu_autologin.py")
            with open(old_script, "w", encoding="utf-8") as f:
                f.write('__version__ = "1.3.0"\n# old\n')
            updated, _ = lu.apply_update("9.9.9", dest_dir=dest_dir,
                                         base_url=base)
            check("broken script rejected", updated is False)
            check("live file untouched",
                  lu._version_in_file(old_script) == "1.3.0")
        finally:
            server.shutdown()

    failed = checks.count(False)
    print(f"{len(checks) - failed}/{len(checks)} checks passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
