"""Utility to receive token from OAuth2 provider."""

import http.server
import json
import socketserver
import urllib.parse
import urllib.request
import webbrowser


def oauth_login_token(
    tp: str, client_id: str, authorize_url: str, token_url: str, scopes: list[str]
) -> str:
    """Use OAuth2 to get login token.

    This is blocking call and thus :func:`asyncio.run_in_executor` should be
    used if called from asyncio.
    """
    redirect_uri = "http://localhost:37719/"

    auth_code = None

    class _HTTPHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            nonlocal auth_code
            parsed_path = urllib.parse.urlparse(self.path)
            if parsed_path.path == "/":
                params = urllib.parse.parse_qs(parsed_path.query)
                auth_code = params.get("code", [None])[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"""
                    <html><body>
                      <p>Authorization complete. You may close this window.</p>
                      <script>window.close();</script>
                    </body></html>
                """)
            else:
                self.send_error(404)

        def log_message(self, fmt: str, *args: str) -> None:
            pass  # suppress default logging

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", 37719), _HTTPHandler) as httpd:
        webbrowser.open(
            authorize_url
            + "?"
            + urllib.parse.urlencode({
                "client_id": client_id,
                "response_type": "code",
                "redirect_uri": redirect_uri,
                "scope": " ".join(scopes),
            })
        )
        print("Waiting for authorization...")
        while auth_code is None:
            httpd.handle_request()

    data = {
        "client_id": client_id,
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
    }
    req = urllib.request.Request(  # noqa: S310
        token_url, data=urllib.parse.urlencode(data).encode("UTF-8"), method="POST"
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req) as resp:  # noqa: S310
        res = json.loads(resp.read())["access_token"]
    assert isinstance(res, str)
    return f"{tp}:{res}"
