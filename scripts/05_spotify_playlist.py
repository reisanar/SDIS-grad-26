"""Step 5 (OPTIONAL) — upgrade the playlist to a real hosted Spotify playlist.

Step 4 already produced a complete, playable playlist with no credentials.
This step is a pure enhancement and is skipped silently when unconfigured:

* SPOTIFY_CLIENT_ID + SPOTIFY_CLIENT_SECRET  -> adds real Spotify track links
  and album/popularity metadata to docs_data/playlist_tracks.csv
* plus SPOTIFY_REFRESH_TOKEN                 -> creates the playlist on your
  account and saves its URL + embed code for the site

Track order is inherited from step 4, so the taste-map sequencing is preserved.
"""
from __future__ import annotations

import base64
import json
import sys
import time

import pandas as pd
import requests

from common import DOCS_DATA, env, log

TRACKS = DOCS_DATA / "playlist_tracks.csv"
API = "https://api.spotify.com/v1"


def _token(payload: dict) -> str | None:
    cid, secret = env("SPOTIFY_CLIENT_ID"), env("SPOTIFY_CLIENT_SECRET")
    if not (cid and secret):
        return None
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    r = requests.post("https://accounts.spotify.com/api/token", data=payload,
                      headers={"Authorization": f"Basic {auth}"}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def token_client_credentials() -> str | None:
    return _token({"grant_type": "client_credentials"})


def token_user() -> str | None:
    refresh = env("SPOTIFY_REFRESH_TOKEN")
    if not refresh:
        return None
    return _token({"grant_type": "refresh_token", "refresh_token": refresh})


def search_track(tok: str, title: str, artist: str) -> dict | None:
    for q in (f'track:"{title}" artist:"{artist}"', f"{title} {artist}"):
        r = requests.get(f"{API}/search", params={"q": q, "type": "track", "limit": 1},
                         headers={"Authorization": f"Bearer {tok}"}, timeout=30)
        if r.status_code == 429:
            time.sleep(int(r.headers.get("Retry-After", 2)) + 1)
            continue
        if not r.ok:
            break
        items = r.json().get("tracks", {}).get("items", [])
        if items:
            t = items[0]
            return {"spotify_id": t["id"], "spotify_uri": t["uri"],
                    "spotify_url": t["external_urls"]["spotify"],
                    "spotify_popularity": t["popularity"]}
    return None


def create_playlist(tok: str, uris: list[str]) -> dict:
    me = requests.get(f"{API}/me", headers={"Authorization": f"Bearer {tok}"}, timeout=30)
    me.raise_for_status()
    uid = me.json()["id"]
    body = {"name": env("PLAYLIST_NAME", "Cohort Playlist"),
            "description": env("PLAYLIST_DESCRIPTION", "One song from every person in the cohort."),
            "public": True}
    r = requests.post(f"{API}/users/{uid}/playlists",
                      headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
                      data=json.dumps(body), timeout=30)
    r.raise_for_status()
    pl = r.json()
    for i in range(0, len(uris), 100):
        requests.post(f"{API}/playlists/{pl['id']}/tracks",
                      headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
                      data=json.dumps({"uris": uris[i:i + 100]}), timeout=30).raise_for_status()
    log(f"created Spotify playlist with {len(uris)} tracks")
    return {"name": pl["name"], "url": pl["external_urls"]["spotify"], "id": pl["id"],
            "embed": f"https://open.spotify.com/embed/playlist/{pl['id']}"}


def main() -> int:
    if not TRACKS.exists():
        log("no playlist_tracks.csv — run 04_match_tracks.py first")
        return 0
    user_tok = None
    try:
        user_tok = token_user()
    except Exception as exc:
        log(f"user token failed ({exc}); trying client credentials")
    try:
        tok = user_tok or token_client_credentials()
    except Exception as exc:
        log(f"Spotify auth failed: {exc}")
        return 0
    if not tok:
        log("no Spotify credentials — keeping the credential-free playlist from step 4")
        return 0

    tracks = pd.read_csv(TRACKS)
    found = []
    for r in tracks.itertuples():
        hit = search_track(tok, r.requested_title, r.requested_artist) or {}
        found.append(hit)
        time.sleep(0.12)
    for col in ("spotify_id", "spotify_uri", "spotify_url", "spotify_popularity"):
        tracks[col] = [f.get(col, "") for f in found]
    tracks.to_csv(TRACKS, index=False)
    n = int((tracks["spotify_id"].astype(str) != "").sum())
    log(f"resolved {n}/{len(tracks)} tracks on Spotify")

    info = {"matched": n, "total": len(tracks)}
    uris = [u for u in tracks["spotify_uri"].astype(str).tolist() if u and u != "nan"]
    if user_tok and uris:
        try:
            info.update(create_playlist(user_tok, list(dict.fromkeys(uris))))
        except Exception as exc:
            log(f"playlist creation failed: {exc}")
    else:
        log("no SPOTIFY_REFRESH_TOKEN — links added, hosted playlist not created")
    (DOCS_DATA / "spotify_playlist.json").write_text(json.dumps(info, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
