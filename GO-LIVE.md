# Go live with the SDIS form

Everything below is filled in for your actual form and sheet. Total time: about
ten minutes, and only the first step touches Google.

**Your form:** `https://docs.google.com/forms/d/e/1FAIpQLSffnSoDFPcI8As6cheWlBfTLeVxLnasJ-hv0qt-5BleGPT4eQ/viewform`
**Your sheet ID:** `1ZVwPOVBZlzhgCc85GAGK_zJc83jfcN3xX2MbzIrDRRk`
**Responses tab (gid):** `1695451547`

---

## Step 1 — Share the response sheet

The pipeline reads the sheet over plain HTTPS with no credentials, which only
works if the sheet is link-readable.

1. Open the sheet:
   `https://docs.google.com/spreadsheets/d/1ZVwPOVBZlzhgCc85GAGK_zJc83jfcN3xX2MbzIrDRRk/edit`
2. Click **Share** (top right).
3. Under **General access**, change *Restricted* to **Anyone with the link**.
4. Leave the role as **Viewer**.
5. Click **Done**.

> **Is this safe?** Your form collects no email addresses and no names, so the
> responses are already effectively anonymous. The only fields are program,
> background, hometown, a song, and a sentence about how it feels — all of which
> you are publishing on the site anyway. If you later add an email or name
> question, switch to the service-account method in `README.md` instead, which
> keeps the sheet private.

**Verify it worked:** open an incognito window and paste this. If you get a CSV
download instead of a sign-in page, you're set:

```
https://docs.google.com/spreadsheets/d/1ZVwPOVBZlzhgCc85GAGK_zJc83jfcN3xX2MbzIrDRRk/export?format=csv&gid=1695451547
```

---

## Step 2 — Create your `.env`

From inside the project folder:

```bash
cd cohort-snapshot
cp .env.example .env
```

`.env.example` already contains your sheet ID and gid, so the copy is nearly
ready. Open `.env` and confirm these three lines:

```bash
GOOGLE_SHEET_ID=1ZVwPOVBZlzhgCc85GAGK_zJc83jfcN3xX2MbzIrDRRk
GOOGLE_SHEET_GID=1695451547
ANON_SALT=sdis-2026-change-this-to-anything
```

`ANON_SALT` is any random string. It seasons the hash that turns a response into
an anonymous ID, so IDs can't be compared across cohorts. Change it each year.

`.env` is git-ignored and never committed.

> **Shortcut:** you can paste the entire sheet URL into `GOOGLE_SHEET_ID` —
> including `?resourcekey=&gid=...` — and both the ID and gid are extracted.

---

## Step 3 — Confirm the pipeline sees your questions

```bash
pip install -r requirements.txt
python scripts/inspect_sheet.py
```

Expected output:

```
N rows, 8 columns
==============================================================================
INTERNAL KEY       FORM QUESTION
------------------------------------------------------------------------------
background         What is your undergraduate background?
genres             Which genres to you listen to the most?
hometown           Where did you grow up? (city, state/country)
program            What is your program (or role) at SDIS?
song_artist        Who performs it?
song_title         What is the title of one song that has been on your mind r
taste_text         In a sentence, describe how this song makes you feel
timestamp          Timestamp

FYI — handled automatically, no action needed:
  - family_location: the location word cloud uses `hometown` instead
  - consent: no consent question — ALL responses will be included
  - artists: no artists question — the taste map leans on genres and free text
  - email: no email collected — IDs are hashed from the timestamp instead
```

**Read the row count.** `0 rows` means the connection works but nobody has
answered yet — not an error. Everything downstream stays empty until responses
arrive, and the site still builds.

### If this step fails

| Message | Fix |
|---|---|
| `Could not read the sheet without credentials` | Step 1 didn't take. Re-check **General access = Anyone with the link** |
| `parsed only 1 column` | Wrong tab. Confirm `GOOGLE_SHEET_GID=1695451547` |
| A question listed as missing | Paste its exact wording into `schemas/columns.yml` under that key's `exact:` list |
| `ModuleNotFoundError` | `pip install -r requirements.txt` |

---

## Step 4 — Do a dry run before the cohort responds

Don't wait for real data to find problems. Submit **one test response through
the form yourself**, then:

```bash
python scripts/inspect_sheet.py
```

You should now see `1 rows`, and the sample-value column should show your own
answers in the right places. That confirms the whole chain end to end: form →
sheet → pipeline.

Delete that test row from the sheet afterward, or leave it — one row won't build
a taste map anyway (PCA needs at least 4).

---

## Step 5 — Run the full pipeline

```bash
python scripts/run_all.py
```

This fetches from your sheet and runs everything. Expected output with real
responses:

```
[immersion] fetched 37 rows from the link-shared sheet
[immersion] mapped 8 columns: [...]
[immersion] wrote .../clean.csv and .../responses_anon.csv (37 participants)
[immersion] chart -> program.png
[immersion] chart -> family_location_cloud.png (from hometown)
[immersion] chart -> background_cloud.png
[immersion] chart -> background.png
[immersion] chart -> genres.png
[immersion] taste map source: free-text answers to 'how this song makes you feel'
[immersion] tf-idf matrix: 37 participants x 214 terms (min_df=2)
[immersion] PC1 9.4% / PC2 7.8% of variance
[immersion] matched 36/37 picks, 36 playable previews — no credentials used
[immersion] wrote _generated.md, _tastemap.md, _playlist.md
```

Then look at it:

```bash
quarto preview
```

### If `quarto preview` errors

```bash
python scripts/doctor.py --fix
```

It now also executes every page's Python cells, which is where small-cohort
failures show up (too few responses for PCA, empty vocabulary). With 5 responses
the pages render — they just say "not enough responses yet" where a chart will
eventually go.

### Checks worth doing on the first real run

1. **`docs_data/playlist_unmatched.csv`** — songs the catalog couldn't find,
   usually a typo. Fix the spelling directly in the sheet and re-run.
2. **`docs_data/background_unmatched.json`** — backgrounds that fell into
   `Other`. Add a keyword to `BACKGROUND_RULES` in `scripts/canonicalize.py`.
3. **The location word cloud** — confirm hometowns collapsed sensibly
   (`Raleigh, NC` → `NC`, `Mumbai, India` → `India`).
4. **The taste map** — with fewer than ~15 responses it will look like one blob.
   That's expected; it separates as answers arrive.

---

## Step 6 — Publish to GitHub Pages

Once locally it looks right:

```bash
quarto render
git add -A
git commit -m "First real snapshot"
git push
```

If you haven't set up the repo and Pages yet, do that once — `DEPLOY.md` has the
walkthrough (create repo → push → Settings ▸ Pages ▸ branch `main`, folder
`/docs`).

### Automate the refresh

In your repo: **Settings ▸ Secrets and variables ▸ Actions ▸ New repository
secret**, add:

| Secret name | Value |
|---|---|
| `GOOGLE_SHEET_ID` | `1ZVwPOVBZlzhgCc85GAGK_zJc83jfcN3xX2MbzIrDRRk` |
| `GOOGLE_SHEET_GID` | `1695451547` |
| `ANON_SALT` | the same random string from your `.env` |

The workflow then refreshes daily at 7:00 AM Eastern, and you can trigger it any
time from **Actions ▸ Refresh snapshot and publish ▸ Run workflow** — which is
the button to press live during the session.

---

## Day-of checklist

| When | Do |
|---|---|
| 1 week out | Send the form link; aim for >70% before the session |
| 2 days out | Reminder to non-responders |
| Morning of | **Actions ▸ Run workflow**, confirm the site looks right |
| Morning of | Open tabs: live site, Actions, the response sheet |
| During | Re-run the workflow live after a few new responses — the map visibly shifts |

Your form link to share:

```
https://docs.google.com/forms/d/e/1FAIpQLSffnSoDFPcI8As6cheWlBfTLeVxLnasJ-hv0qt-5BleGPT4eQ/viewform
```

Put that same link in `index.qmd` where it says `FORM_LINK_HERE`, so the site
itself recruits stragglers.

---

## Quick reference

```bash
python scripts/inspect_sheet.py      # what does the pipeline see?
python scripts/run_all.py            # fetch + full rebuild
python scripts/run_all.py --no-fetch # rebuild from the last download
python scripts/run_all.py --only 03  # just the taste map
python scripts/doctor.py --fix       # fix any render error
quarto preview                       # look at it
quarto render && git push            # publish
```
