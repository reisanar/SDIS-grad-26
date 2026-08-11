# Cohort Snapshot — Quarto site

Our SDIS cohort snapshot from the 2026 graduate student orientation. Demographics, a
tf-idf + PCA **musical taste map**, and a **cohort playlist** 


## What's in the box

| Path | Purpose |
|---|---|
| `schemas/google_form_schema.md` | The exact form to build — question titles, types, and why each one exists |
| `schemas/columns.yml` | Maps form question titles to internal keys. **The only file you edit when you reword a question.** |
| `scripts/00_fetch_responses.py` | Pulls responses (service account, published CSV, or local file) |
| `scripts/01_preprocess.py` | Consent filter, hashed IDs, de-duplication, tidying |
| `scripts/02_demographics.py` | Charts + `summary.json` |
| `scripts/03_taste_map.py` | tf-idf → PCA → k-means, static + interactive map, loadings, taste twins |
| `scripts/04_match_tracks.py` | **Credential-free** track resolution via the public iTunes Search API: real metadata, cover art, 30-second previews, Apple links, Spotify deep links, and import files |
| `scripts/05_spotify_playlist.py` | *Optional.* Upgrades to real Spotify links + a hosted playlist |
| `scripts/06_apple_music.py` | *Optional.* Creates a real Apple Music playlist |
| `scripts/07_render_snippets.py` | Writes `_generated.md`, `_tastemap.md`, `_playlist.md` |
| `scripts/run_all.py` | Runs the lot |
| `scripts/make_sample_data.py` | 42 synthetic responses so you can rehearse before the form goes live |
| `scripts/bootstrap_placeholders.py` | Writes placeholder partials/images so a fresh clone renders before any data exists |
| `scripts/doctor.py` | Diagnoses and repairs common `quarto preview` failures (`--fix`) |
| `scripts/check_pages.py` | Runs every .qmd's Python without Quarto — catches small-cohort render errors |
| `scripts/inspect_sheet.py` | Shows how YOUR sheet's questions map to internal keys — run this first |
| `scripts/sheet_io.py` | Reads a link-shared Google Sheet with no credentials |
| `scripts/canonicalize.py` | Collapses messy free-text (majors, state names) into groups |
| `scripts/wordcloud_lite.py` | Dependency-free word clouds (no C extension to build) |
| `TESTING.md` | How to test with sample data and how to run against the live form |
| `GO-LIVE.md` | Step-by-step for THIS form and sheet, with the IDs filled in |
| `.github/workflows/build.yml` | Daily refresh + manual "Run workflow" button |
| `DEPLOY.md` | Step-by-step GitHub Pages deployment |
| `ACTIVITY.md` | Run-of-show for the session itself |

## Quick start (10 minutes, no credentials)

```bash
pip install -r requirements.txt
python scripts/make_sample_data.py --n 42   # fake responses
python scripts/run_all.py --no-fetch        # full pipeline, playlist steps skip gracefully
quarto preview
```

Rendering a **fresh clone with no data at all** also works — `run_all.py` starts
by writing placeholder partials and images so Quarto never chokes on a missing
`{{< include >}}`. To do only that step:

```bash
python scripts/bootstrap_placeholders.py && quarto preview
```

> **Styling note.** The stylesheet is `styles.scss`, not `.css`. Quarto compiles
> anything listed under `theme:` as SCSS and *requires* the
> `/*-- scss:defaults --*/` and `/*-- scss:rules --*/` layer markers. A plain
> `.css` file there fails to render.

You'll get the whole site: charts, taste map, and a **complete, playable
playlist** — every step degrades instead of failing, so a missing credential
never breaks the build.

## How the playlist works without credentials

Playlist *creation* on Spotify or Apple is inherently tied to a user account —
no public API will make one for an anonymous caller. So the pipeline delivers
the playlist a different way, and the result is arguably better for a cohort
site:

1. **Public catalog matching.** The iTunes Search API needs no key, no account,
   and no registration. It returns canonical title/artist/album/year, cover art,
   a direct Apple Music link, and a 30-second preview clip for nearly every song.
2. **The site plays the music itself.** Those preview clips are embedded as a
   card grid on the playlist page. Any visitor hears the cohort playlist
   immediately — no login, no subscription, no app.
3. **One-click import for personal libraries.** The pipeline writes
   `playlist_import.csv` and `playlist.txt` in the format free transfer tools
   (Soundiiz, TuneMyMusic, Spotlistr) accept, so anyone can push the full
   playlist into their own Spotify or Apple library in about a minute.
4. **Deep links per track** open any song directly in Spotify search, Apple
   Music, or YouTube.

Steps 05 and 06 are optional upgrades: add credentials and you also get a real
hosted playlist URL and an embedded Spotify player. Nothing else changes.

## Going live

### 1. Build the form
Follow `schemas/google_form_schema.md` verbatim. Link responses to a Sheet.

### 2. Connect the sheet

**Simplest (no credentials):** open the response sheet ▸ Share ▸ General access
▸ **Anyone with the link** (Viewer), then set `GOOGLE_SHEET_ID` in `.env` to the
ID from the URL. Then run `python scripts/inspect_sheet.py` to confirm your
questions are recognized.

**Most private:** create a Google Cloud service account, enable the Sheets API,
share the sheet with the service account's email as Viewer, and set
`GOOGLE_SERVICE_ACCOUNT_JSON` alongside `GOOGLE_SHEET_ID`. Use this if the sheet
collects emails and you don't want it link-readable.

Full walkthrough of both, plus sample-data testing: **`TESTING.md`**.

### 3. Spotify (optional)
Skip this entirely unless you want a hosted playlist URL.
Create an app at developer.spotify.com. Add
`http://127.0.0.1:8080/callback` as a redirect URI. Then:

```bash
python scripts/get_spotify_refresh_token.py
```

Paste the printed `SPOTIFY_REFRESH_TOKEN` into `.env` and into the repo secrets.
Without it you still get matched tracks and per-song links — you just don't get
an auto-created playlist.

### 4. Apple Music (optional)
Skip unless you want a real playlist in a library — track links already work.
In your Apple Developer account, create a **MusicKit** identifier and a private
key (`.p8`). Set `APPLE_TEAM_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY`. That's
enough for catalog matching and per-track Apple links. Creating a playlist in a
library additionally needs a **Music User Token**, which can only be minted in a
browser via MusicKit JS by a signed-in subscriber — do that once, put it in
`APPLE_MUSIC_USER_TOKEN`, and note it expires (roughly every six months), so
re-mint it before each cohort. If it's absent the site still ships an
Apple-friendly page of direct song links.

### 5. GitHub
Required secrets: `FORM_CSV_URL` (or `GOOGLE_SHEET_ID` +
`GOOGLE_SERVICE_ACCOUNT_JSON`) and `ANON_SALT`. That's it.

Optional, only for hosted playlists: `SPOTIFY_CLIENT_ID`,
`SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`, `APPLE_TEAM_ID`,
`APPLE_KEY_ID`, `APPLE_PRIVATE_KEY_P8`, `APPLE_MUSIC_USER_TOKEN`.

Full walkthrough with screenshots-worth-of-detail: **`DEPLOY.md`**.

Settings ▸ Pages ▸ Deploy from branch ▸ `main` ▸ `/docs`.

Replace `USERNAME/REPO` in `_quarto.yml` and the form URL placeholder
`FORM_LINK_HERE` in `index.qmd`.

## Running the session

`ACTIVITY.md` has a 60-75 minute run of show, discussion prompts, and
facilitator notes.

## During the event

Hit **Actions ▸ Refresh snapshot and publish ▸ Run workflow** whenever you want
the room to see itself update — it's a genuinely good live demo. The daily cron
covers everything else. The playlist step creates a *new* playlist each run;
if you'd rather update one in place, set the playlist ID and switch the
`POST /users/{id}/playlists` call to `PUT /playlists/{id}/tracks`.

## Notes on the method

- **Why tf-idf before PCA:** raw counts would put "music", "pop", and "listen"
  in charge of the first component, and everyone would land in a blob. tf-idf
  reweights toward the terms that actually distinguish people.
- **Small-*n* caveat:** with ~40 responses and a few hundred terms, PC1 will
  explain something like 8–12% of the variance and the axes will rotate between
  runs. Say this out loud during the session — watching the map shift when five
  more responses arrive teaches more than a stable map would.
- **Ordering the playlist by PC1** is a small touch that makes the deliverable
  feel designed: the sequence moves through taste neighborhoods instead of
  whiplashing between Chopin and metal.

## Privacy posture

Emails are hashed with a per-cohort salt and never published. Non-consenting
responses are dropped before analysis. `data/` (raw + clean, with emails) is
git-ignored; only `docs_data/` is committed. Set a fresh `ANON_SALT` each year
so IDs can't be joined across cohorts.
