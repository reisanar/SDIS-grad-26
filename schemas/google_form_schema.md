# Google Form blueprint — "Cohort Snapshot"

> **The live SDIS form is already built** and the pipeline is configured for it.
> Its questions and options are recorded in "Live form reference" at the bottom
> of this file. The blueprint below is the fuller superset — use it if you want
> to expand the form in a future year.

Build the form once, reuse every year. Each question below lists the
**exact title** to type into Google Forms, the question type, and the short
key the pipeline uses internally (`schemas/columns.yml` maps title -> key).

Keep the titles stable. If you reword a question, update `columns.yml` —
nothing else in the pipeline needs to change.

## Section 1 — Consent & identity

| # | Question title (exact) | Type | Key | Notes |
|---|---|---|---|---|
| 1 | `Email` | Auto-collected | `email` | Turn on *Collect email addresses = Responder input*. Only ever used to build an anonymous hashed ID; never published. |
| 2 | `May we include your (anonymized) answers in the cohort snapshot?` | Multiple choice: Yes / No | `consent` | Rows with `No` are dropped before any analysis. |
| 3 | `Display name for the credits page (optional)` | Short answer | `display_name` | Blank = the person stays fully anonymous. |

## Section 2 — Demographics (all optional)

| # | Question title (exact) | Type | Key |
|---|---|---|---|
| 4 | `Which program/track are you in?` | Multiple choice + Other | `program` |
| 5 | `What is your undergraduate background?` | Checkboxes + Other | `background` |
| 6 | `Years of work experience` | Multiple choice (`0-1`, `2-4`, `5-9`, `10+`) | `experience` |
| 7 | `Where did you grow up? (city, state/country)` | Short answer | `hometown` |
| 8 | `Which best describes your current comfort with Python?` | Linear scale 1-5 | `python_comfort` |
| 9 | `Which best describes your current comfort with statistics?` | Linear scale 1-5 | `stats_comfort` |
| 10 | `What do you most want to get out of the immersion?` | Paragraph | `goals` |

## Section 3 — Music (this is what powers the taste map + playlist)

| # | Question title (exact) | Type | Key | Notes |
|---|---|---|---|---|
| 11 | `Name up to 3 artists you love` | Short answer | `artists` | Ask for comma-separated. Validation regex optional. |
| 12 | `One song that has to be on the cohort playlist` | Short answer | `song_title` | **Required.** This is the playlist seed. |
| 13 | `Who performs it?` | Short answer | `song_artist` | **Required.** Search accuracy depends on this. |
| 14 | `Which genres do you listen to most?` | Checkboxes + Other | `genres` | Offer ~12 genres so the tf-idf vocabulary has structure. |
| 15 | `Describe your music taste in a sentence` | Paragraph | `taste_text` | Free text — the richest tf-idf signal. |
| 16 | `What are you listening to while you work?` | Multiple choice + Other | `work_music` | Nice demographic-style chart. |
| 17 | `Pick a mood word for your song` | Multiple choice (`energetic`, `chill`, `nostalgic`, `focus`, `dance`, `melancholy`) | `mood` | Used to color the taste map. |

## Wiring it up

1. In the form: **Responses -> Link to Sheets -> Create new spreadsheet.**
2. Either
   - **File -> Share -> Publish to web -> the responses sheet -> CSV**, and put
     that URL in `FORM_CSV_URL` (simplest, no credentials), **or**
   - share the sheet with a Google service-account email (Viewer) and set
     `GOOGLE_SHEET_ID` + `GOOGLE_SERVICE_ACCOUNT_JSON` (private form data stays
     private; this is the recommended option since responses include emails).
3. `python scripts/run_all.py` — or just let the scheduled GitHub Action do it.


---

## Live form reference (current SDIS form)

These are the questions and options the pipeline is tuned for today.

| Question | Type | Internal key |
|---|---|---|
| `What is your program (or role) at SDIS?` | Multiple choice | `program` |
| `What is your undergraduate background?` | Short answer (free text) | `background` |
| `Where did you grow up? (city, state/country)` | Short answer | `hometown` |
| `Which genres to you listen to the most?` | Checkboxes | `genres` |
| `What is the title of one song that has been on your mind recently?` | Short answer | `song_title` |
| `Who performs it?` | Short answer | `song_artist` |
| `In a sentence, describe how this song makes you feel` | Paragraph | `taste_text` |

**Program / role options** (marker shape on the taste map):

`MS in DS` · `PhD in DS` · `CHIP PhD` · `CHIP MS` · `MS in LS` · `MS in IS` ·
`PhD in ILS` · `Faculty` · `Staff`

**Genre options** (checkboxes, multi-select):

`Pop` · `Metal` · `Classical` · `Folk` · `Jazz` · `Electronic` · `Reggaeton` ·
`Indie Rock` · `R&B` · `Country` · `Hip-hop` · `Latin` · `Other`

### Notes on this form

- **No consent question**, so every response is included. Since no email is
  collected either, responses are already effectively anonymous — but free-text
  answers are published verbatim, so consider adding a line to the form
  description saying so.
- **No family-location question.** The location word cloud falls back to
  `hometown`, parsing `Raleigh, NC` to `NC` and `Bogota, Colombia` to `Colombia`.
- **Participant IDs** are hashed from the timestamp since there is no email.
