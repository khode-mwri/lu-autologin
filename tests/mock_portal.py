#!/usr/bin/env python3
"""Mock MikroTik-style hotspot portal for testing lu_autologin.py.

Serves a login page in several shapes (CHAP with hex / octal / raw chap-id,
plain login, form action on a different path) and verifies credentials
the way a real hotspot would, including the 2-hour-style session flag
used by /generate_204.

Usage:
    python3 tests/mock_portal.py --variant chap-hex --port 8765 --password secret123

Variants:
    chap-hex     CHAP, chap-id written as a hex escape   (\\x9f)
    chap-octal   CHAP, chap-id written as an octal escape (\\237)
    chap-raw     CHAP, chap-id as a raw byte in the page
    plain        No CHAP, plain username/password form
    chap-action  CHAP, but the form posts to /hotspot-login (not /login)
    plain-action Plain login, form posts to /hotspot-login
"""

import argparse
import hashlib
import http.server
import socketserver
import urllib.parse

CHAP_ID_BYTE = 0x9F
CHALLENGE = "a1b2c3d4e5f60718293a4b5c6d7e8f90"


def login_page(variant):
    """Return the login page as bytes."""
    if variant.startswith("chap"):
        if variant == "chap-hex":
            chap_js = "'\\x9f'"
        elif variant == "chap-octal":
            chap_js = "'\\237'"
        elif variant == "chap-raw":
            chap_js = None  # raw byte inserted below
        else:  # chap-action
            chap_js = "'\\x9f'"
        action = "/hotspot-login" if variant == "chap-action" else "/login"
        if chap_js is None:
            js = ("<script>function doLogin(){document.sendin.password.value="
                  "hexMD5('" + chr(CHAP_ID_BYTE) + "' + document.login.password.value + '"
                  + CHALLENGE + "');document.sendin.submit();return false;}</script>")
        else:
            js = ("<script>function doLogin(){document.sendin.password.value="
                  "hexMD5(" + chap_js + " + document.login.password.value + '"
                  + CHALLENGE + "');document.sendin.submit();return false;}</script>")
        page = f"""<html><head><title>Hotspot login</title></head><body>
{js}
<form name="login" action="{action}" method="post" onSubmit="return doLogin()">
<input type="hidden" name="dst" value="http://example.com/" />
<input type="hidden" name="popup" value="true" />
Username: <input type="text" name="username" /><br/>
Password: <input type="password" name="password" /><br/>
<input type="submit" value="Log in" />
</form>
<form name="sendin" action="{action}" method="post">
<input type="hidden" name="username" />
<input type="hidden" name="password" />
<input type="hidden" name="dst" value="http://example.com/" />
<input type="hidden" name="popup" value="true" />
</form>
</body></html>"""
        return page.encode("latin-1")
    # plain variants
    action = "/hotspot-login" if variant == "plain-action" else "/login"
    page = f"""<html><head><title>Hotspot login</title></head><body>
<form name="login" action="{action}" method="post">
<input type="hidden" name="dst" value="http://example.com/" />
<input type="hidden" name="popup" value="true" />
Username: <input type="text" name="username" /><br/>
Password: <input type="password" name="password" /><br/>
<input type="submit" value="Log in" />
</form>
</body></html>"""
    return page.encode("utf-8")


class Handler(http.server.BaseHTTPRequestHandler):
    variant = "chap-hex"
    password = "secret123"
    logged_in = False

    def log_message(self, *args):
        pass

    def _send(self, code, body=b"", ctype="text/html", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        if path in ("/login", "/hotspot-login") and "username" in query:
            # GET-based login attempt (some portals accept credentials
            # as query parameters). Plaintext only; CHAP portals reject it.
            username = query.get("username", [""])[0]
            password = query.get("password", [""])[0]
            ok = (password == self.password)
            print(f"[mock] GET-login {path} user={username!r} ok={ok}", flush=True)
            if ok:
                Handler.logged_in = True
                self._send(302, extra={"Location": "/status"})
            else:
                self._send(200, b"<html><body>Invalid username or password. "
                                 b"Please try again.</body></html>")
            return
        if path == "/login":
            self._send(200, login_page(self.variant))
        elif path == "/status":
            if Handler.logged_in:
                self._send(200, b"<html><body>connected. <a href='/logout'>logout</a></body></html>")
            else:
                self._send(302, extra={"Location": "/login"})
        elif path == "/generate_204":
            if Handler.logged_in:
                self._send(204, b"")
            else:
                self._send(302, extra={"Location": "/login"})
        else:
            self._send(404, b"not found")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8", errors="ignore")
        fields = urllib.parse.parse_qs(raw)
        username = fields.get("username", [""])[0]
        password = fields.get("password", [""])[0]

        if self.variant.startswith("chap"):
            expected = hashlib.md5(
                bytes([CHAP_ID_BYTE]) + self.password.encode("utf-8")
                + CHALLENGE.encode("latin-1")).hexdigest()
            ok = (password == expected)
        else:
            ok = (password == self.password)

        print(f"[mock] POST {self.path} user={username!r} ok={ok}", flush=True)
        if ok:
            # NOTE: class attribute, not instance — each request gets a
            # fresh handler object, so instance state would be lost.
            Handler.logged_in = True
            self._send(302, extra={"Location": "/status"})
        else:
            self._send(200, b"<html><body>Invalid username or password. "
                             b"Please try again.</body></html>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="chap-hex",
                    choices=["chap-hex", "chap-octal", "chap-raw", "plain",
                             "chap-action", "plain-action"])
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--password", default="secret123")
    args = ap.parse_args()

    Handler.variant = args.variant
    Handler.password = args.password
    Handler.logged_in = False

    with socketserver.ThreadingTCPServer(("127.0.0.1", args.port), Handler) as httpd:
        print(f"[mock] variant={args.variant} on 127.0.0.1:{args.port}", flush=True)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
