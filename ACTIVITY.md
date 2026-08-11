# Running the activity

A 60–75 minute session for a cohort of roughly 20–60. The engine is that
students are simultaneously the analysts and the dataset, and the site updates
in front of them.

## Before the day

| When | Do this |
|---|---|
| 1 week out | Deploy the site (`DEPLOY.md`), rehearse the pipeline on synthetic data |
| 1 week out | Send the form link with the subject "3 minutes, and you'll be on the map" |
| 2 days out | Reminder to non-responders. Aim for >70% before the session |
| Morning of | Run the workflow once. Confirm the site is live and the playlist plays |
| Morning of | Open these tabs: the live site, the Actions tab, the response sheet, this repo |

Rehearsal command, no credentials and no real data needed:

```bash
pip install -r requirements.txt
python scripts/make_sample_data.py --n 42
python scripts/run_all.py --no-fetch
quarto preview
```

## Run of show

### 0:00 — Open with the room, not with slides (5 min)

Put the live site on the screen. Play two or three preview clips from the
playlist page and let people react to whose song is whose. You now have the
room's attention and you haven't explained anything yet.

Ask: *"How would you turn 40 sentences about music into a picture of this
room?"* Take two answers. Don't correct them.

### 0:05 — The problem with counting words (10 min)

Live in the browser or a notebook, using the published anonymized data:

```python
import pandas as pd
df = pd.read_csv("https://YOURNAME.github.io/immersion27/docs_data/responses_anon.csv")
df["taste_text"].str.split().explode().str.lower().value_counts().head(10)
```

The top words will be junk — "music", "love", "the", "listen". That's the
lesson: **raw frequency measures ubiquity, not distinctiveness.** Let it land
before you offer the fix.

### 0:15 — tf-idf (15 min)

Walk the `workshop.qmd` page. The one sentence students should leave with:

> A term earns weight when it's frequent *in this document* and rare *across
> all the others*.

Run the vectorizer live. Show the top-weighted terms and compare them to the
junk list from the previous step. Ask what the ngram_range change does.

### 0:30 — PCA and the map (15 min)

Project to two dimensions and plot. Then do the three things that make it stick:

1. **Read the axes out loud** from the loadings chart. "PC1 has Radiohead and
   Björk on one end, Bad Bunny and Taylor Swift on the other — what is that
   axis actually measuring?" Let them argue. There's no right answer, which is
   the point.
2. **Name the variance number.** PC1 will explain something like 8–12%. Ask
   whether a picture that captures a tenth of the signal is useful. Defend both
   positions.
3. **Break it.** Add three fake responses to the sheet, re-run the workflow from
   the Actions tab, and reload. The axes rotate. Small-*n* instability stops
   being an abstraction the moment they watch it happen.

### 0:45 — Taste twins (10 min)

Open `docs_data/neighbors.csv` and let people look up their own hashed ID. Ask
the pairs with the highest similarity to say hello. This is the part people
remember, and it's also a clean way to raise the real question:

> This map was built from things you volunteered. What would change — technically
> and ethically — if it were built from your actual listening history, collected
> without asking?

Let that run. Don't resolve it.

### 0:55 — Hand them the deliverable (5 min)

Show the import file on the playlist page and walk one person through getting
the cohort playlist into their own library. Point at the repo and tell them it's
theirs to fork.

## Variations

- **Short version (30 min):** open with the playlist, do tf-idf, show the map,
  skip the live rebuild.
- **Lab version (2 hours):** run the discussion prompts at the bottom of
  `workshop.qmd` in pairs — CountVectorizer vs tf-idf, `min_df` sweeps,
  TruncatedSVD, cosine vs Euclidean.
- **Ongoing:** leave the form open all semester. The map on the wall display
  changes as people's taste drifts.

## Facilitator notes

- **The instability is the lesson, not a flaw.** If a student says "so the map
  isn't real," you're winning. The honest answer is that it's one low-dimensional
  view of a high-dimensional space, and reruns disagree because the data is thin.
- **Neighborhood labels are mechanical.** Some will be sharp, some nonsense.
  Say so before someone points it out.
- **Have a fallback.** If the network dies, `quarto preview` on the last build
  works offline, and the preview clips are the only thing that need connectivity.
- **Don't skip the ethics beat.** Twenty minutes on method and zero on consent
  teaches something you didn't intend.
- **Watch the room during taste twins.** That's the moment the cohort actually
  becomes a cohort, which is the real deliverable of an immersion.
