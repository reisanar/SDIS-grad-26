"""Step 4 — resolve every song pick WITHOUT any credentials.

Uses the public iTunes Search API (no key, no account, no registration) to turn
"one song per person" into canonical metadata: real title, artist, album, year,
cover art, a 30-second preview clip, and a direct Apple Music link.

From that it writes everything needed to have a playlist on both services:

  docs_data/playlist_tracks.csv    canonical metadata + Apple link + Spotify search link
  docs_data/playlist_import.csv    Title,Artist,Album -- the format Soundiiz /
                                   TuneMyMusic / Spotlistr accept for a one-click import
  docs_data/playlist.txt           "Title - Artist" per line, paste-ready
  docs_data/playlist.m3u           local player / archival copy
  docs_data/playlist_unmatched.csv anything the API couldn't find

The site can play all 30-second previews with zero credentials. 
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse

import pandas as pd
import requests

from common import DATA, DOCS_DATA, env, log

CLEAN = DATA / "clean.csv"
COORDS = DOCS_DATA / "taste_coords.csv"
TRACKS = DOCS_DATA / "playlist_tracks.csv"
ITUNES = "https://itunes.apple.com/search"
UA = {"User-Agent": "cohort-snapshot/1.0 (course project)"}


def spotify_search_url(title: str, artist: str) -> str:
    """A deep link that opens this song in Spotify. No auth, works for everyone."""
    return "https://open.spotify.com/search/" + urllib.parse.quote(f"{title} {artist}")


def youtube_search_url(title: str, artist: str) -> str:
    return "https://www.youtube.com/results?search_query=" + urllib.parse.quote(f"{title} {artist}")


class CatalogUnreachable(Exception):
    """Raised when the network is clearly down, so we stop retrying every song."""


def itunes_lookup(title: str, artist: str, country: str = "US", retries: int = 2) -> dict | None:
    """Public catalog search. Strict artist+title first, then title-only."""
    attempts = [
        {"term": f"{title} {artist}", "entity": "song", "limit": 3, "country": country},
        {"term": title, "entity": "song", "limit": 5, "country": country},
    ]
    for params in attempts:
        for attempt in range(retries):
            try:
                r = requests.get(ITUNES, params=params, headers=UA, timeout=15)
            except requests.RequestException as exc:
                if attempt == retries - 1:
                    raise CatalogUnreachable(str(exc)) from exc
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code == 403:  # rate limited
                time.sleep(5 * (attempt + 1))
                continue
            if not r.ok:
                break
            results = r.json().get("results", [])
            if not results:
                break
            # prefer a result whose artist actually resembles what was typed
            want = artist.lower().strip()
            best = next((x for x in results if want and want.split()[0] in x.get("artistName", "").lower()),
                        results[0])
            return {
                "matched_title": best.get("trackName", ""),
                "matched_artist": best.get("artistName", ""),
                "album": best.get("collectionName", ""),
                "release_year": str(best.get("releaseDate", ""))[:4],
                "duration_ms": best.get("trackTimeMillis", ""),
                "genre": best.get("primaryGenreName", ""),
                "apple_url": best.get("trackViewUrl", ""),
                "preview_url": best.get("previewUrl", ""),
                "artwork": (best.get("artworkUrl100") or "").replace("100x100", "300x300"),
            }
    return None


def ordered_picks() -> pd.DataFrame:
    df = pd.read_csv(CLEAN)
    if df.empty or not {"song_title", "song_artist"} <= set(df.columns):
        return pd.DataFrame()
    if COORDS.exists():  # sequence the playlist along the taste map
        coords = pd.read_csv(COORDS)[["participant_id", "pc1", "neighborhood"]]
        df = df.merge(coords, on="participant_id", how="left").sort_values(
            ["neighborhood", "pc1"], na_position="last")
    cols = [c for c in ("participant_id", "song_title", "song_artist", "mood", "neighborhood") if c in df]
    return df[cols].dropna(subset=["song_title", "song_artist"])


def main() -> int:
    if not CLEAN.exists():
        log("no clean.csv — run 01_preprocess.py first")
        return 1
    picks = ordered_picks()
    if picks.empty:
        log("no song picks yet — nothing to match")
        return 0
    country = (env("ITUNES_COUNTRY", "US") or "US").upper()
    delay = float(env("ITUNES_DELAY", "1.2") or 1.2)  # be polite: ~20 req/min

    rows, misses = [], []
    offline = False
    for i, p in enumerate(picks.itertuples(), start=1):
        base = {
            "position": i,
            "participant_id": p.participant_id,
            "requested_title": p.song_title,
            "requested_artist": p.song_artist,
            "mood": getattr(p, "mood", ""),
            "neighborhood": getattr(p, "neighborhood", ""),
            "spotify_search_url": spotify_search_url(p.song_title, p.song_artist),
            "youtube_search_url": youtube_search_url(p.song_title, p.song_artist),
        }
        hit = None
        if not offline:
            try:
                hit = itunes_lookup(p.song_title, p.song_artist, country)
            except CatalogUnreachable as exc:
                offline = True
                log(f"catalog unreachable ({exc}) — falling back to search links for all remaining tracks")
        if hit:
            rows.append({**base, **hit})
        else:
            if not offline:
                log(f"no catalog match: {p.song_title} — {p.song_artist}")
                misses.append(base)
            rows.append({**base, "matched_title": p.song_title, "matched_artist": p.song_artist,
                         "album": "", "release_year": "", "apple_url": "", "preview_url": "",
                         "artwork": "", "genre": "", "duration_ms": ""})
        if not offline:
            time.sleep(delay)

    tracks = pd.DataFrame(rows)
    tracks.to_csv(TRACKS, index=False)

    # --- exports that make a real playlist a 60-second manual step ------------
    imp = tracks[["matched_title", "matched_artist", "album"]].copy()
    imp.columns = ["Title", "Artist", "Album"]
    imp.to_csv(DOCS_DATA / "playlist_import.csv", index=False)

    (DOCS_DATA / "playlist.txt").write_text(
        "\n".join(f"{r.matched_title} - {r.matched_artist}" for r in tracks.itertuples()))

    m3u = ["#EXTM3U"]
    for r in tracks.itertuples():
        if r.preview_url:
            m3u.append(f"#EXTINF:30,{r.matched_artist} - {r.matched_title}")
            m3u.append(r.preview_url)
    (DOCS_DATA / "playlist.m3u").write_text("\n".join(m3u))

    if misses:
        pd.DataFrame(misses).to_csv(DOCS_DATA / "playlist_unmatched.csv", index=False)

    matched = int((tracks["apple_url"].astype(str) != "").sum())
    previews = int((tracks["preview_url"].astype(str) != "").sum())
    info = {"total": len(tracks), "matched": matched, "unmatched": len(misses),
            "previews": previews, "offline": offline,
            "source": "iTunes Search API (no credentials)"}
    (DOCS_DATA / "match_summary.json").write_text(json.dumps(info, indent=2))
    if offline:
        log(f"no network — wrote {len(tracks)} tracks with search links only; re-run when online")
    else:
        log(f"matched {matched}/{len(tracks)} picks, {previews} playable previews — no credentials used")
    return 0


if __name__ == "__main__":
    sys.exit(main())
