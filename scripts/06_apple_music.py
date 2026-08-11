"""Step 6 (OPTIONAL) — create a real Apple Music playlist in your library.

Step 4 already produced Apple Music links for every track with no credentials.
This step only matters if you want an actual shareable Apple playlist, which
Apple ties to a signed-in subscriber account:

* APPLE_TEAM_ID + APPLE_KEY_ID + APPLE_PRIVATE_KEY (.p8) -> developer token,
  used to resolve catalog IDs
* plus APPLE_MUSIC_USER_TOKEN (minted once in a browser via MusicKit JS)
  -> creates the playlist

Skipped silently when unconfigured.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

from common import DOCS_DATA, env, log

TRACKS = DOCS_DATA / "playlist_tracks.csv"
API = "https://api.music.apple.com/v1"


def developer_token() -> str | None:
    team, kid, key = env("APPLE_TEAM_ID"), env("APPLE_KEY_ID"), env("APPLE_PRIVATE_KEY")
    if not (team and kid and key):
        return None
    import jwt  # PyJWT[crypto]

    secret = Path(key).read_text() if Path(key).exists() else key
    now = int(time.time())
    return jwt.encode({"iss": team, "iat": now, "exp": now + 43200}, secret,
                      algorithm="ES256", headers={"kid": kid, "alg": "ES256"})


def catalog_id(tok: str, title: str, artist: str, storefront: str) -> str:
    r = requests.get(f"{API}/catalog/{storefront}/search",
                     params={"term": f"{title} {artist}", "types": "songs", "limit": 1},
                     headers={"Authorization": f"Bearer {tok}"}, timeout=30)
    if r.status_code == 429:
        time.sleep(3)
        return catalog_id(tok, title, artist, storefront)
    if not r.ok:
        return ""
    data = r.json().get("results", {}).get("songs", {}).get("data", [])
    return data[0]["id"] if data else ""


def main() -> int:
    if not TRACKS.exists():
        log("no playlist_tracks.csv — run 04_match_tracks.py first")
        return 0
    dev_tok = None
    try:
        dev_tok = developer_token()
    except Exception as exc:
        log(f"developer token failed: {exc}")
    user_tok = env("APPLE_MUSIC_USER_TOKEN")
    if not (dev_tok and user_tok):
        log("no Apple playlist credentials — keeping the per-track Apple links from step 4")
        return 0

    storefront = (env("APPLE_STOREFRONT", "us") or "us").lower()
    tracks = pd.read_csv(TRACKS)
    ids = []
    for r in tracks.itertuples():
        ids.append(catalog_id(dev_tok, r.requested_title, r.requested_artist, storefront))
        time.sleep(0.1)
    tracks["apple_catalog_id"] = ids
    tracks.to_csv(TRACKS, index=False)

    clean = list(dict.fromkeys([i for i in ids if i]))
    body = {"attributes": {"name": env("PLAYLIST_NAME", "Cohort Playlist"),
                           "description": env("PLAYLIST_DESCRIPTION", "One song per person.")},
            "relationships": {"tracks": {"data": [{"id": i, "type": "songs"} for i in clean]}}}
    info = {"matched": len(clean), "total": len(tracks), "storefront": storefront,
            "generated": dt.datetime.now().isoformat(timespec="seconds")}
    try:
        r = requests.post(f"{API}/me/library/playlists",
                          headers={"Authorization": f"Bearer {dev_tok}", "Music-User-Token": user_tok,
                                   "Content-Type": "application/json"},
                          data=json.dumps(body), timeout=45)
        r.raise_for_status()
        d = r.json()["data"][0]
        info.update({"id": d["id"], "url": (d.get("attributes") or {}).get("url", "")})
        log(f"created Apple Music playlist with {len(clean)} tracks")
    except Exception as exc:
        log(f"Apple playlist creation failed: {exc}")
    (DOCS_DATA / "apple_playlist.json").write_text(json.dumps(info, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
