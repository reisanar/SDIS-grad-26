"""Step 7 — turn results into the markdown partials the .qmd pages include.

Outputs: _generated.md   headline numbers + demographic charts
         _tastemap.md    component interpretation + neighborhoods
         _playlist.md    preview player, service links, full track table
"""
from __future__ import annotations

import datetime as dt
import html
import json
import sys

import pandas as pd

from common import DOCS_ASSETS, DOCS_DATA, ROOT, log


def read_json(name: str) -> dict:
    p = DOCS_DATA / name
    try:
        return json.loads(p.read_text()) if p.exists() else {}
    except Exception:
        return {}


def cell(v) -> str:
    s = "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)
    return s.replace("|", "\\|")


def main() -> int:
    summary = read_json("summary.json")
    match = read_json("match_summary.json")
    spotify = read_json("spotify_playlist.json")
    apple = read_json("apple_playlist.json")
    terms = read_json("taste_terms.json")
    stamp = dt.datetime.now().strftime("%B %d, %Y at %I:%M %p")
    n = summary.get("n_participants", 0)

    # ---------------- _generated.md ----------------
    g = ["::: {.callout-note}",
         f"**{n} people** have filled out the cohort survey. Last refreshed {stamp}.",
         ":::", ""]
    bits = []
    if summary.get("top_locations"):
        top_loc = ", ".join(f"**{name}** ({c})" for name, c in summary["top_locations"][:3])
        bits.append(f"Families are spread across {summary.get('n_locations', 0)} states and "
                    f"countries, most often {top_loc}.")
    if summary.get("top_backgrounds"):
        top_bg = ", ".join(f"**{name}**" for name, _ in summary["top_backgrounds"][:3])
        bits.append(f"The most common undergraduate backgrounds are {top_bg}.")
    if summary.get("top_genres"):
        tops = ", ".join(f"**{name}** ({c})" for name, c in summary["top_genres"][:3])
        bits.append(f"Most-listened genres: {tops}.")
    if summary.get("n_unique_songs"):
        bits.append(f"{summary['n_unique_songs']} distinct songs were nominated for the playlist.")
    if bits:
        g.append(" ".join(bits) + "\n")
    # only reference charts that step 02 actually built, in a sensible order
    manifest = read_json("charts.json")
    preferred = ["family_location_cloud.png", "family_location.png",
                 "background_cloud.png", "background.png", "program.png",
                 "experience.png", "comfort.png", "genres.png", "artists.png",
                 "mood.png", "work_music.png"]
    ordered = [f for f in preferred if f in manifest] + \
              [f for f in manifest if f not in preferred]
    for fname in ordered:
        if (DOCS_ASSETS / fname).exists():
            caption = manifest[fname]
            g.append(f'![{caption}](docs_assets/{fname}){{fig-alt="{caption}"}}\n')
    if not ordered:
        g.append("*Charts appear here once responses come in.*\n")
    (ROOT / "_generated.md").write_text("\n".join(g))

    # ---------------- _tastemap.md ----------------
    t = []
    src = terms.pop("_source", None) if isinstance(terms, dict) else None
    if src:
        t.append(f"*The map is built from {src}.*\n")
    for pc, d in terms.items():
        if not isinstance(d, dict) or "positive" not in d:
            continue
        pos = ", ".join(f"`{x}`" for x in d["positive"][:6])
        neg = ", ".join(f"`{x}`" for x in d["negative"][:6])
        t.append(f"**{pc}** ({d['explained_variance']:.1%} of the variance) separates "
                 f"{pos} on one side from {neg} on the other.\n")
    coords_p = DOCS_DATA / "taste_coords.csv"
    if coords_p.exists():
        c = pd.read_csv(coords_p)
        t.append("\n### Neighborhoods\n")
        for name, grp in c.groupby("neighborhood"):
            t.append(f"- **{name}** — {len(grp)} people")
        t.append("")
    (ROOT / "_tastemap.md").write_text("\n".join(t))

    # ---------------- _playlist.md ----------------
    p = []
    tracks_p = DOCS_DATA / "playlist_tracks.csv"
    if not tracks_p.exists():
        p.append("*The playlist appears here once responses come in and "
                 "`scripts/04_match_tracks.py` has run.*\n")
        (ROOT / "_playlist.md").write_text("\n".join(p))
        log("wrote snippets (no playlist yet)")
        return 0

    try:
        tr = pd.read_csv(tracks_p)
    except Exception:
        tr = pd.DataFrame()
    if tr.empty:
        p.append("*The playlist appears here once responses come in.*\n")
        (ROOT / "_playlist.md").write_text("\n".join(p))
        log("wrote snippets (playlist still empty)")
        return 0

    # hosted playlists, if the optional steps ran
    if spotify.get("embed"):
        p.append(f'''<iframe style="border-radius:12px" src="{spotify['embed']}?utm_source=generator"
width="100%" height="480" frameborder="0" allowfullscreen
allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
loading="lazy"></iframe>\n''')
    links = []
    if spotify.get("url"):
        links.append(f"[▶ Open on Spotify]({spotify['url']}){{.btn .btn-primary}}")
    if apple.get("url"):
        links.append(f"[ Open on Apple Music]({apple['url']}){{.btn .btn-primary}}")
    links.append("[⬇ Import file (CSV)](docs_data/playlist_import.csv){.btn .btn-primary}")
    links.append("[⬇ Plain text list](docs_data/playlist.txt){.btn .btn-primary}")
    p.append(" ".join(links) + "\n")

    # built-in preview player — works with zero credentials
    playable = tr[tr["preview_url"].astype(str).str.startswith("http")] if "preview_url" in tr else pd.DataFrame()
    if len(playable):
        p.append("## Play it right here\n")
        p.append(f"Every one of these {len(playable)} clips streams straight from this page — "
                 "no account, no login, nothing to install.\n")
        p.append('<div class="preview-grid">')
        for r in playable.itertuples():
            art = html.escape(str(getattr(r, "artwork", "") or ""))
            title = html.escape(str(r.matched_title))
            artist = html.escape(str(r.matched_artist))
            p.append(f'''<div class="preview-card">
  {'<img src="' + art + '" alt="Album art for ' + title + '" loading="lazy">' if art else ''}
  <div class="preview-meta"><strong>{title}</strong><br><span>{artist}</span></div>
  <audio controls preload="none" src="{html.escape(str(r.preview_url))}"></audio>
</div>''')
        p.append("</div>\n")

    # the full table
    p.append("## Every track\n")
    p.append("| # | Track | Artist | Year | Neighborhood | Listen on |")
    p.append("|---:|---|---|---:|---|---|")
    for r in tr.itertuples():
        listen = []
        sp_url = getattr(r, "spotify_url", "")
        if isinstance(sp_url, str) and sp_url.startswith("http"):
            listen.append(f"[Spotify]({sp_url})")
        elif isinstance(getattr(r, "spotify_search_url", ""), str):
            listen.append(f"[Spotify]({r.spotify_search_url})")
        if isinstance(getattr(r, "apple_url", ""), str) and str(r.apple_url).startswith("http"):
            listen.append(f"[Apple]({r.apple_url})")
        if isinstance(getattr(r, "youtube_search_url", ""), str):
            listen.append(f"[YouTube]({r.youtube_search_url})")
        p.append(f"| {getattr(r, 'position', '')} | {cell(r.matched_title)} | {cell(r.matched_artist)} "
                 f"| {cell(getattr(r, 'release_year', ''))} | {cell(getattr(r, 'neighborhood', ''))} "
                 f"| {' · '.join(listen)} |")
    p.append("")

    if match:
        note = (f"\n*{match.get('matched', 0)} of {match.get('total', 0)} picks were matched "
                f"automatically against the public music catalog — no API keys involved.")
        if match.get("unmatched"):
            note += (f" {match['unmatched']} needed a manual look; they're listed in "
                     "[`playlist_unmatched.csv`](docs_data/playlist_unmatched.csv).")
        p.append(note + "*\n")

    # how to get it into a personal library, credential-free
    if not spotify.get("url"):
        p.append("""
## Get this into your own Spotify or Apple library

Playlists live inside an account, so this last hop is yours to make — it takes
about a minute:

1. Download the [import file](docs_data/playlist_import.csv) above.
2. Go to a free transfer tool ([Soundiiz](https://soundiiz.com),
   [TuneMyMusic](https://www.tunemymusic.com), or [Spotlistr](https://www.spotlistr.com)).
3. Choose **import from file / text**, upload the CSV (or paste the
   [plain text list](docs_data/playlist.txt)), and pick Spotify or Apple Music
   as the destination.
4. Log in when prompted, name it, done — the whole cohort playlist lands in your library.

You can also click any **Spotify** link in the table above to open that song
directly, and add it with the ⋯ menu.
""")
    (ROOT / "_playlist.md").write_text("\n".join(p))
    log("wrote _generated.md, _tastemap.md, _playlist.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
