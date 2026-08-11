"""One-time helper: get a Spotify refresh token so CI can create playlists.

    python scripts/get_spotify_refresh_token.py

Requires SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET and a redirect URI of
http://127.0.0.1:8080/callback registered in your Spotify app settings.
Paste the printed refresh token into your .env and into the repo's Actions
secrets. It does not expire unless you revoke it.
"""
from __future__ import annotations

import base64
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

from common import env

REDIRECT = "http://127.0.0.1:8080/callback"
SCOPES = "playlist-modify-public playlist-modify-private"
code_holder: dict[str, str] = {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        q = urllib.parse.urlparse(self.path).query
        code_holder.update(dict(urllib.parse.parse_qsl(q)))
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write("<h2>Done - you can close this tab and return to the terminal.</h2>".encode())

    def log_message(self, *a):  # silence
        pass


def main() -> None:
    cid, secret = env("SPOTIFY_CLIENT_ID"), env("SPOTIFY_CLIENT_SECRET")
    if not (cid and secret):
        raise SystemExit("Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET first.")
    url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(
        {"client_id": cid, "response_type": "code", "redirect_uri": REDIRECT, "scope": SCOPES})
    print("Opening browser for authorization...\n", url)
    webbrowser.open(url)
    HTTPServer(("127.0.0.1", 8080), Handler).handle_request()

    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    r = requests.post("https://accounts.spotify.com/api/token",
                      data={"grant_type": "authorization_code", "code": code_holder["code"],
                            "redirect_uri": REDIRECT},
                      headers={"Authorization": f"Basic {auth}"}, timeout=30)
    r.raise_for_status()
    print("\nSPOTIFY_REFRESH_TOKEN=" + r.json()["refresh_token"])


if __name__ == "__main__":
    main()
