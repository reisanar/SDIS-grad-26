# Testing and deploying

Two workflows: **synthetic data** (test everything offline, right now) and
**live Google Form responses**. Do the synthetic run first — it exercises every
code path in about a minute.

---

## Part 1 — Test with synthetic data

```bash
cd cohort-snapshot
pip install -r requirements.txt

python scripts/make_sample_data.py --n 40     # fake responses in your form's format
python scripts/run_all.py --no-fetch          # whole pipeline
quarto preview                                # open the site
```

`--no-fetch` skips the Google Sheet and uses the local file.

### What the synthetic data looks like

It reproduces your live export **exactly** — same eight columns, same order,
including the trailing space in the "makes you feel" header. A generated file
and a real export are interchangeable.

It is also deliberately messy, because real responses are:

- **Backgrounds** arrive in ~28 spellings (`CS`, `comp sci`, `B.S. Computer
  Science`) so you can watch them collapse into families.
- **Hometowns** mix `Raleigh, NC` with `Mumbai, India` so you can watch the
  location parser produce `NC` and `India`.
- **Feeling sentences are composed, not sampled** — all 40 are unique, drawn
  from six emotional families (nostalgia, energy, calm, melancholy, joy,
  connection). That shared-within-family, distinct-across-family structure is
  what gives PCA something real to find.
- **Anchor songs always appear**: `DtMf` (odd capitalization),
  `Tití Me Preguntó` (accents), `Texas Hold 'Em` (apostrophe), `Not Like Us`.

### What you should see

```
[immersion] mapped 8 columns: [...]
[immersion] built 6 figures for 40 participants
[immersion] taste map source: free-text answers to 'how this song makes you feel'
[immersion] tf-idf matrix: 40 participants x 135 terms (min_df=2)
[immersion] matched 40/40 picks, 40 playable previews
```

Charts for questions your form doesn't ask are **skipped, not blank**.

### Verify the cleanup worked

```bash
python -c "
import json; d=json.load(open('docs_data/summary.json'))
print('locations :', d['top_locations'][:5])
print('backgrounds:', d['top_backgrounds'][:5])"
```

Every `Raleigh, NC` / `Durham, NC` / `Chapel Hill, NC` should be a single `NC`.

### Useful variations

```bash
python scripts/check_pages.py                   # run every page's code, no Quarto needed
python scripts/make_sample_data.py --n 5        # tiny cohort, like a first test batch
python scripts/make_sample_data.py --n 8        # still small (PCA needs 4+)
python scripts/make_sample_data.py --n 120      # large cohort
python scripts/make_sample_data.py --schema classic   # fuller question set
python scripts/run_all.py --only 03             # re-run just the taste map
python scripts/doctor.py --fix                  # fix any render problem
```

---

## Part 2 — Run with live Google Form responses

> **For the current SDIS form, use `GO-LIVE.md` instead** — it has your sheet ID,
> tab gid, and form link already filled in. The generic version follows.

### 1. Share the response sheet

Open the sheet → **Share** → **General access** → **Anyone with the link**
(Viewer). No service account, no credentials.

### 2. Point the pipeline at it

Copy `.env.example` to `.env` and set the sheet ID — the long string in the
sheet URL between `/d/` and `/edit`:

```bash
GOOGLE_SHEET_ID=1ZVwPOVBZlzhgCc85GAGK_zJc83jfcN3xX2MbzIrDRRk
ANON_SALT=immersion-2027-pick-something-random
```

### 3. Confirm your questions are recognized

```bash
python scripts/inspect_sheet.py
```

Expected output for your form:

```
INTERNAL KEY       FORM QUESTION
background         What is your undergraduate background?
genres             Which genres to you listen to the most?
hometown           Where did you grow up? (city, state/country)
program            What is your program (or role) at SDIS?
song_artist        Who performs it?
song_title         What is the title of one song that has been on your mind...
taste_text         In a sentence, describe how this song makes you feel
```

`0 rows` simply means nobody has responded yet — the connection is fine.

If a question ever shows up as missing, paste its exact wording into
`schemas/columns.yml` under that key's `exact:` list. That is the only file to
edit when you reword a question.

### 4. Run it

```bash
python scripts/run_all.py     # fetches from the sheet, then everything else
quarto preview
```

### 5. Publish

```bash
quarto render
git add -A && git commit -m "Refresh snapshot" && git push
```

Or let the GitHub Action do it — add `GOOGLE_SHEET_ID` and `ANON_SALT` as
repository secrets and it refreshes daily. Full setup in `DEPLOY.md`.

---

## Small cohorts

The site is built to render at **any** size, including zero responses:

| Responses | What happens |
|---|---|
| 0 | Everything renders with placeholders. No crash |
| 1–3 | Charts skipped ("not enough data"), taste map skipped |
| 4–14 | Map builds but will look like a blob; vocabulary auto-relaxes to `min_df=1` |
| 15+ | Neighborhoods start separating meaningfully |
| 30+ | What you want for the session |

Verify your copy handles this before a session:

```bash
python scripts/check_pages.py
```

That executes every page's Python exactly as Quarto would, and fails loudly if
any cell breaks — which is faster than a full render and catches the
small-cohort bugs a 40-response test would miss.

## How the taste map is built

**The map comes from one question:** *"In a sentence, describe how this song
makes you feel."* Not the genre checkboxes, not the program — the writing. This
matches the 2026 immersion site, and it is the reason the map is worth showing:
it separates people by *how they describe feeling*, which no bar chart can.

- Each person's sentence becomes a tf-idf vector (unigrams + bigrams).
- PCA projects to two dimensions; k-means labels neighborhoods, named
  automatically from each cluster's most distinctive terms.
- **Color = taste neighborhood** (learned from the writing).
  **Marker shape = program/role** (what they told you). Nine shapes, one per
  program option.

Because sentences are short documents, the vectorizer starts at `min_df=2` and
automatically relaxes to `min_df=1` if the vocabulary comes out too thin.

To blend genre checkboxes in as a weaker secondary signal:

```bash
TASTE_MAP_INCLUDE_GENRES=1 python scripts/run_all.py --only 03
```

Off by default — checkboxes pull the map toward a few category blobs and drown
out the writing.

---

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `0 rows, 8 columns` | Connected fine, no responses yet. Submit one and re-run |
| `Could not read the sheet without credentials` | Sharing isn't "Anyone with the link" |
| A question shows as missing | Add its exact wording to `schemas/columns.yml` |
| `only N participants — need at least 4` | PCA needs 4+ responses with a song |
| A chart is missing | That question wasn't asked, or fewer than 3 answered |
| Many backgrounds land in `Other` | Add patterns to `BACKGROUND_RULES` in `canonicalize.py`; see `docs_data/background_unmatched.json` |
| Taste map looks like one blob | Usually too few responses; it separates around 15–20 |
| Any Quarto render error | `python scripts/doctor.py --fix` |
| `n_components=N must be between 0 and min(n_samples, n_features)` | Too few responses for PCA on that page. Fixed in the current version — run `python scripts/check_pages.py` to confirm your copy is current |
| Songs unmatched | See `docs_data/playlist_unmatched.csv`, fix spelling in the sheet, re-run |
