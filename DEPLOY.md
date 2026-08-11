# Deploying this as a GitHub Page

Two paths. **Path A needs no credentials of any kind** and gets you a live site
with a playable playlist. Path B is the optional upgrade to hosted Spotify /
Apple playlists. Do A first — it works on its own.

Total time for Path A: about 25 minutes, most of it waiting on builds.

---

## Path A — zero-credential deployment

### 1. Create the repository

1. Unzip this project into a folder, e.g. `cohort-snapshot`.
2. On GitHub, click **New repository**. Name it (say `immersion27`), make it
   **Public** (required for free GitHub Pages), and do **not** add a README —
   this project already has one.
3. In a terminal, from inside the project folder:

```bash
git init
git add .
git commit -m "Cohort snapshot site"
git branch -M main
git remote add origin https://github.com/YOURNAME/immersion27.git
git push -u origin main
```

### 2. Build the Google Form

1. Open [forms.google.com](https://forms.google.com) and create a blank form.
2. Add the questions exactly as listed in `schemas/google_form_schema.md`.
   Copy the titles verbatim — the pipeline matches on them.
3. **Settings ▸ Responses ▸ Collect email addresses = Responder input.**
4. **Responses tab ▸ Link to Sheets ▸ Create new spreadsheet.**
5. Copy the form's share link (**Send ▸ link icon**). You'll need it in step 4.

### 3. Publish the response sheet as CSV

In the response spreadsheet:

1. **File ▸ Share ▸ Publish to web.**
2. In the first dropdown pick the **responses sheet** (not "Entire document").
3. In the second dropdown pick **Comma-separated values (.csv)**.
4. Click **Publish**, confirm, and copy the URL it gives you.

> **Privacy check.** A published sheet is readable by anyone with the URL, and
> your sheet contains email addresses. Two ways to handle this properly:
> **(a)** turn *off* email collection in the form and let the pipeline hash the
> timestamp instead, or **(b)** use the service-account route in `README.md`,
> which keeps the sheet fully private. Option (b) is the right call if you
> collect emails. Don't publish a sheet with student emails in it.

### 4. Point the project at your form

Edit three placeholders and push:

| File | Find | Replace with |
|---|---|---|
| `_quarto.yml` | `USERNAME/REPO` (2 places) | your GitHub user and repo |
| `index.qmd` | `FORM_LINK_HERE` | your Google Form share link |
| — | — | — |

```bash
git add . && git commit -m "Point at my form" && git push
```

### 5. Add the CSV URL as a repository secret

**Repo ▸ Settings ▸ Secrets and variables ▸ Actions ▸ New repository secret**

| Name | Value |
|---|---|
| `GOOGLE_SHEET_ID` | the sheet ID (or `FORM_CSV_URL` if you published a CSV) |
| `GOOGLE_SHEET_GID` | the responses tab id, if it isn't the first tab |
| `ANON_SALT` | any random string, e.g. `immersion-2027-x7f2` |

That's the entire credential list for Path A. Two secrets, neither of which is
a music service account.

### 6. Turn on GitHub Pages

**Repo ▸ Settings ▸ Pages ▸ Build and deployment**

- Source: **Deploy from a branch**
- Branch: **main**, folder: **/docs**
- Save.

### 7. Run the build

**Repo ▸ Actions ▸ "Refresh snapshot and publish" ▸ Run workflow.**

First run takes 3–5 minutes (installing Quarto and Python packages). When it
goes green, your site is at:

```
https://YOURNAME.github.io/immersion27/
```

If Actions shows a permissions error on the commit step, go to
**Settings ▸ Actions ▸ General ▸ Workflow permissions** and select
**Read and write permissions**.

### 8. Confirm it works

Submit one test response through the form, re-run the workflow, and check that
your answer moved the numbers. Then delete the test row from the sheet.

**You are done.** The site rebuilds itself daily at 7:00 AM Eastern, and you can
force a rebuild any time from the Actions tab.

---

## Path B — optional hosted playlists

Only needed if you want a real Spotify or Apple playlist URL rather than the
built-in preview player plus one-click import file.

### Spotify

1. [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) ▸
   **Create app**. Any name. Redirect URI: `http://127.0.0.1:8080/callback`.
2. Copy the Client ID and Client Secret.
3. Locally:

```bash
pip install -r requirements.txt
export SPOTIFY_CLIENT_ID=xxx SPOTIFY_CLIENT_SECRET=yyy
python scripts/get_spotify_refresh_token.py
```

A browser opens, you approve, and the terminal prints a refresh token.

4. Add three secrets to the repo: `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`,
   `SPOTIFY_REFRESH_TOKEN`.

### Apple Music

1. In your paid Apple Developer account: **Certificates, IDs & Profiles ▸ Keys ▸
   +**, enable **MusicKit**, download the `.p8` (one download only, keep it).
2. Note your Team ID and the Key ID.
3. Secrets: `APPLE_TEAM_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY_P8` (paste the
   whole file contents including the BEGIN/END lines).
4. For playlist *creation* you also need `APPLE_MUSIC_USER_TOKEN`, minted in a
   browser with MusicKit JS by a signed-in Apple Music subscriber. It expires
   roughly every six months. Without it you still get every Apple track link.

Re-run the workflow. The playlist page will now show the embedded Spotify
player and direct links.

---

## Troubleshooting

**Start here for any render error:**

```bash
python scripts/doctor.py --fix
```

It finds stale files, a `_quarto.yml` pointing at the wrong stylesheet, missing
SCSS layer boundaries, missing include targets, and stale build caches — and
repairs what it safely can.

| Symptom | Fix |
|---|---|
| Action fails at "Run pipeline" with *no response source configured* | `FORM_CSV_URL` secret is missing or misspelled |
| Site builds but shows 0 participants | The consent question wording in the form doesn't match `schemas/columns.yml` |
| Charts missing, no taste map | Fewer than 4 responses — PCA needs at least 4 |
| Page loads without styling | Pages is pointed at `/root` instead of `/docs` |
| `styles.css doesn't contain at least one layer boundary` | A stale `styles.css` is still in the folder. Run `python scripts/doctor.py --fix`, then `rm -rf .quarto _freeze` |
| `quarto preview` fails on a fresh clone with a missing include | Run `python scripts/bootstrap_placeholders.py` first (or just `python scripts/run_all.py`) |
| 404 on the site | Wait 2 minutes after the first green build; Pages is slow the first time |
| Unmatched songs | Check `docs_data/playlist_unmatched.csv`, fix the spelling in the sheet, re-run |
| Everything works locally but not in Actions | Check the *Secrets* tab — secrets don't transfer from your `.env` |
