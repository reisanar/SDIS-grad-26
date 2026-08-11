"""Step 2 — demographic charts, word clouds, and headline numbers.

Every chart is conditional: if a question wasn't asked, or nobody answered it,
that chart is skipped and never referenced by the site. Nothing renders an empty
axis. What gets built is recorded in docs_data/charts.json so the snippet
renderer only links to figures that actually exist.

Outputs: docs_assets/*.png, docs_data/summary.json, docs_data/charts.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from canonicalize import background_tokens, canonical_background, canonical_location
from common import DATA, DOCS_ASSETS, DOCS_DATA, log, split_multi
from wordcloud_lite import render_wordcloud

CLEAN = DATA / "clean.csv"
ACCENT = "#4B9CD3"
NAVY = "#13294B"
MIN_ANSWERS = 3  # below this a chart is noise, not information

plt.rcParams.update({"figure.dpi": 160, "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})

built: dict[str, str] = {}   # filename -> caption


def series(df: pd.DataFrame, key: str) -> pd.Series | None:
    if key not in df.columns:
        return None
    s = df[key].dropna().astype(str).str.strip()
    s = s[s != ""]
    return s if len(s) >= MIN_ANSWERS else None


def bar(counts: Counter, title: str, fname: str, caption: str,
        horizontal: bool = True, top: int = 15) -> None:
    if not counts or sum(counts.values()) < MIN_ANSWERS:
        log(f"skip {fname} — not enough data")
        return
    items = counts.most_common(top)[::-1]
    labels = [k for k, _ in items]
    values = [v for _, v in items]
    fig, ax = plt.subplots(figsize=(7.5, max(2.5, 0.42 * len(items) + 1)))
    if horizontal:
        ax.barh(labels, values, color=ACCENT)
        ax.set_xlabel("respondents")
        for y, v in enumerate(values):
            ax.text(v + max(values) * 0.015, y, str(v), va="center", fontsize=9)
        ax.set_xlim(0, max(values) * 1.12)
    else:
        ax.bar(labels, values, color=ACCENT)
        ax.set_ylabel("respondents")
        for x, v in enumerate(values):
            ax.text(x, v + max(values) * 0.02, str(v), ha="center", fontsize=9)
    ax.set_title(title, color=NAVY)
    fig.tight_layout()
    fig.savefig(DOCS_ASSETS / fname, bbox_inches="tight")
    plt.close(fig)
    built[fname] = caption
    log(f"chart -> {fname}")


def counts_single(s: pd.Series) -> Counter:
    return Counter(s.tolist())


def counts_multi(s: pd.Series) -> Counter:
    c: Counter = Counter()
    for v in s:
        c.update(x.title() for x in split_multi(v))
    return c


def main() -> int:
    if not CLEAN.exists():
        log("no clean.csv — run 01_preprocess.py first")
        return 1
    df = pd.read_csv(CLEAN)
    summary: dict = {"n_participants": int(len(df))}

    # ---------- program / role ----------
    s = series(df, "program")
    if s is not None:
        bar(counts_single(s), "Program / role", "program.png", "Program / role")
        summary["programs"] = counts_single(s).most_common()

    # ---------- location: word cloud + counted bar ----------
    # Prefer an explicit family-location question; fall back to hometown so the
    # word cloud still works on forms that only ask where someone grew up.
    loc_key = "family_location" if series(df, "family_location") is not None else "hometown"
    s = series(df, loc_key)
    if s is not None:
        cloud_title = ("Where our families are" if loc_key == "family_location"
                       else "Where we grew up")
        bar_title = ("Where our families live" if loc_key == "family_location"
                     else "Where the cohort grew up")
        cloud_caption = ("Where the cohort's families live" if loc_key == "family_location"
                         else "Where the cohort grew up")
        locs = [canonical_location(v) for v in s]
        locs = [l for l in locs if l]
        freqs = Counter(locs)
        if freqs:
            if render_wordcloud(freqs, DOCS_ASSETS / "family_location_cloud.png",
                                title=cloud_title):
                built["family_location_cloud.png"] = cloud_caption
                log(f"chart -> family_location_cloud.png (from {loc_key})")
            bar(freqs, bar_title, "family_location.png",
                f"{bar_title}, counted", top=20)
            summary["top_locations"] = freqs.most_common(8)
            summary["n_locations"] = len(freqs)

    # ---------- undergraduate background: word cloud + collapsed bar ----------
    s = series(df, "background")
    if s is not None:
        tokens: Counter = Counter()
        for v in s:
            tokens.update(background_tokens(v))
        if tokens:
            if render_wordcloud(tokens, DOCS_ASSETS / "background_cloud.png",
                                title="Undergraduate backgrounds, as written"):
                built["background_cloud.png"] = "Undergraduate backgrounds, in respondents' own words"
                log("chart -> background_cloud.png")

        fams = Counter(f for f in (canonical_background(v) for v in s) if f)
        if fams:
            bar(fams, "Undergraduate background (grouped)", "background.png",
                "Undergraduate background, collapsed into families", top=18)
            summary["top_backgrounds"] = fams.most_common(6)
            other = fams.get("Other", 0)
            if other:
                unmatched = sorted({str(v) for v in s if canonical_background(v) == "Other"})
                (DOCS_DATA / "background_unmatched.json").write_text(
                    json.dumps(unmatched, indent=2))
                log(f"{other} background answers fell into 'Other' — see background_unmatched.json")

    # ---------- everything else, only if present ----------
    for key, (title, fname, caption, multi, horiz) in {
        "experience": ("Years of work experience", "experience.png",
                       "Years of work experience", False, False),
        "genres": ("Genres the cohort listens to most", "genres.png",
                   "Genres the cohort listens to most", True, True),
        "artists": ("Most-named artists", "artists.png", "Most-named artists", True, True),
        "mood": ("Mood of the nominated songs", "mood.png",
                 "Mood of the nominated songs", False, True),
        "work_music": ("What's playing while we work", "work_music.png",
                       "What's playing while we work", False, True),
    }.items():
        s = series(df, key)
        if s is None:
            log(f"skip {fname} — question not in this form")
            continue
        counts = counts_multi(s) if multi else counts_single(s)
        bar(counts, title, fname, caption, horizontal=horiz)
        if key == "genres":
            summary["top_genres"] = counts.most_common(5)
        if key == "artists":
            summary["top_artists"] = counts.most_common(5)

    # ---------- comfort scales ----------
    scales = [k for k in ("python_comfort", "stats_comfort") if k in df.columns
              and pd.to_numeric(df[k], errors="coerce").notna().sum() >= MIN_ANSWERS]
    if scales:
        fig, axes = plt.subplots(1, len(scales), figsize=(4.2 * len(scales), 3), squeeze=False)
        for ax, k in zip(axes[0], scales):
            vals = pd.to_numeric(df[k], errors="coerce").dropna()
            ax.hist(vals, bins=range(1, 7), color=ACCENT, align="left", rwidth=0.8)
            ax.set_title(k.replace("_", " ").title(), color=NAVY)
            ax.set_xticks(range(1, 6))
            ax.set_xlabel("1 = new, 5 = very comfortable")
        fig.tight_layout()
        fig.savefig(DOCS_ASSETS / "comfort.png", bbox_inches="tight")
        plt.close(fig)
        built["comfort.png"] = "Self-reported comfort with Python and statistics"
        log("chart -> comfort.png")
        summary["median_python_comfort"] = float(
            pd.to_numeric(df["python_comfort"], errors="coerce").median()) if "python_comfort" in df else None

    if "song_title" in df.columns:
        summary["n_unique_songs"] = int(df["song_title"].astype(str).str.lower().nunique())

    (DOCS_DATA / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    (DOCS_DATA / "charts.json").write_text(json.dumps(built, indent=2))
    log(f"built {len(built)} figures for {len(df)} participants")
    return 0


if __name__ == "__main__":
    sys.exit(main())
