"""Step 3 — the musical taste map: tf-idf -> PCA -> 2D, plus k-means neighborhoods.

The map is built from what people WROTE, not from what they checked. Each
participant's document is their free-text answer to "In a sentence, describe how
this song makes you feel" — the same approach as the 2026 immersion site. That
sentence is the richest, most personal signal in the survey, and it is what makes
the map interesting: two people who both checked "Pop" may write wildly different
sentences, and the map should separate them.

tf-idf down-weights words everyone uses ("song", "makes", "feel") and lifts the
words that actually distinguish people. PCA then finds the two directions of
largest variance, so distance on the map is similarity of expressed feeling.

Set TASTE_MAP_INCLUDE_GENRES=1 to blend the checkbox genres in as a weaker
secondary signal. Off by default — checkboxes flatten the map toward a handful
of category clusters and drown out the writing.

Outputs: docs_assets/taste_map.png
         docs_assets/taste_map.html        (interactive, hover = anonymous id)
         docs_assets/pc_loadings.png
         docs_data/taste_coords.csv
         docs_data/taste_terms.json        (top +/- terms per component)
         docs_data/neighbors.csv           (each person's 3 nearest taste twins)
"""
from __future__ import annotations

import json
import sys
from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from common import DATA, DOCS_ASSETS, DOCS_DATA, env, log

CLEAN = DATA / "clean.csv"
# The free-text sentence is the map. Everything else is optional seasoning.
PRIMARY_FIELD = "taste_text"
# Only used when TASTE_MAP_INCLUDE_GENRES=1, and deliberately down-weighted.
SECONDARY_FIELDS = ["genres"]
# Fallback chain if a form has no free-text question at all.
FALLBACK_FIELDS = ["artists", "genres", "mood", "work_music"]

# marker shape encodes program/role; color still encodes taste neighborhood
MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*", "<", ">"]
# Words that appear across most answers to "how does this song make you feel"
# and therefore carry no distinguishing information.
EXTRA_STOPWORDS = {
    "music", "song", "songs", "listen", "listening", "like", "love", "feel",
    "feels", "feeling", "makes", "make", "making", "really", "kind", "stuff",
    "lot", "bit", "just", "pretty", "im", "makes me", "song makes", "track",
    "sound", "sounds", "always", "every", "time", "way", "thing", "things",
}


def choose_fields(df: pd.DataFrame) -> tuple[list[tuple[str, int]], str]:
    """Return [(field, weight)] and a human description of what the map used."""
    include_genres = str(env("TASTE_MAP_INCLUDE_GENRES", "0")).strip().lower() in {"1", "true", "yes"}

    has_primary = (PRIMARY_FIELD in df.columns
                   and df[PRIMARY_FIELD].fillna("").astype(str).str.strip().ne("").sum() >= 4)
    if has_primary:
        fields = [(PRIMARY_FIELD, 3)]   # the sentence dominates
        note = "free-text answers to 'how this song makes you feel'"
        if include_genres:
            for f in SECONDARY_FIELDS:
                if f in df.columns:
                    fields.append((f, 1))
            note += " blended with genre checkboxes"
        return fields, note

    # No usable free text — fall back so the map still builds
    fields = [(f, 1) for f in FALLBACK_FIELDS if f in df.columns]
    return fields, "artists, genres, and other categorical answers (no free text found)"


def build_documents(df: pd.DataFrame, fields: list[tuple[str, int]]) -> list[str]:
    docs = []
    for _, row in df.iterrows():
        parts = []
        for f, weight in fields:
            val = row.get(f)
            if isinstance(val, str) and val.strip():
                parts.extend([val] * weight)   # repetition = up-weighting
        docs.append(" ".join(parts).lower())
    return docs


def main() -> int:
    if not CLEAN.exists():
        log("no clean.csv — run 01_preprocess.py first")
        return 1
    df = pd.read_csv(CLEAN)
    if len(df) < 4:
        log(f"only {len(df)} participants — need at least 4 for a meaningful map")
        return 1

    fields, source_note = choose_fields(df)
    if not fields:
        log("no usable text columns for the taste map")
        return 1
    log(f"taste map source: {source_note}")

    docs = build_documents(df, fields)
    non_empty = sum(1 for d in docs if d.strip())
    if non_empty < 4:
        log(f"only {non_empty} participants wrote anything — need at least 4")
        return 1

    stop = list(TfidfVectorizer(stop_words="english").get_stop_words() | EXTRA_STOPWORDS)

    # One sentence per person is a SHORT document, so an aggressive min_df can
    # empty the vocabulary. Start strict, relax until enough terms survive.
    X, vec = None, None
    for min_df in (2, 1):
        vec = TfidfVectorizer(stop_words=stop, ngram_range=(1, 2),
                              min_df=min_df, max_df=0.9, sublinear_tf=True)
        try:
            X = vec.fit_transform(docs)
        except ValueError:
            continue
        if X.shape[1] >= max(10, len(df) // 4):
            break
    if X is None or X.shape[1] < 3:
        log("not enough distinct vocabulary to build a map")
        return 1
    log(f"tf-idf matrix: {X.shape[0]} participants x {X.shape[1]} terms "
        f"(min_df={vec.min_df})")

    n_comp = min(10, X.shape[0] - 1, X.shape[1])
    pca = PCA(n_components=n_comp, random_state=0)
    coords = pca.fit_transform(X.toarray())
    evr = pca.explained_variance_ratio_
    log(f"PC1 {evr[0]:.1%} / PC2 {evr[1]:.1%} of variance")

    k = int(np.clip(round(len(df) / 8), 2, 6))
    labels = KMeans(n_clusters=k, n_init=10, random_state=0).fit_predict(coords[:, :4])

    terms = np.array(vec.get_feature_names_out())
    loadings = {}
    for i in range(min(3, n_comp)):
        order = np.argsort(pca.components_[i])
        loadings[f"PC{i+1}"] = {
            "explained_variance": float(evr[i]),
            "positive": terms[order[-10:]][::-1].tolist(),
            "negative": terms[order[:10]].tolist(),
        }
    loadings["_source"] = source_note
    (DOCS_DATA / "taste_terms.json").write_text(json.dumps(loadings, indent=2))

    # name each neighborhood by its most distinctive tf-idf terms
    cluster_names = {}
    Xd = X.toarray()
    for c in range(k):
        mask = labels == c
        centroid = Xd[mask].mean(axis=0) - Xd[~mask].mean(axis=0) if (~mask).any() else Xd[mask].mean(axis=0)
        top = terms[np.argsort(centroid)[-3:]][::-1]
        cluster_names[c] = ", ".join(top)

    # program/role drives marker shape
    if "program" in df.columns:
        programs = df["program"].fillna("Not given").astype(str).str.strip().replace("", "Not given")
    else:
        programs = pd.Series(["Not given"] * len(df))
    prog_levels = [p for p, _ in Counter(programs).most_common()]
    prog_marker = {p: MARKERS[i % len(MARKERS)] for i, p in enumerate(prog_levels)}

    out = pd.DataFrame({
        "participant_id": df["participant_id"],
        "pc1": coords[:, 0],
        "pc2": coords[:, 1],
        "cluster": labels,
        "neighborhood": [cluster_names[c] for c in labels],
        "program": programs.values,
        "mood": df.get("mood", pd.Series([""] * len(df))),
        "song": (df.get("song_title", pd.Series([""] * len(df))).astype(str)
                 + " — " + df.get("song_artist", pd.Series([""] * len(df))).astype(str)),
    })
    out.to_csv(DOCS_DATA / "taste_coords.csv", index=False)

    # static map: color = taste neighborhood, shape = program/role
    palette = plt.get_cmap("tab10")
    cluster_color = {c: palette(c % 10) for c in range(k)}

    fig, ax = plt.subplots(figsize=(9, 6.5))
    for c in range(k):
        for prog in prog_levels:
            m = (labels == c) & (programs.values == prog)
            if not m.any():
                continue
            ax.scatter(coords[m, 0], coords[m, 1], s=95, alpha=0.85,
                       color=cluster_color[c], marker=prog_marker[prog],
                       edgecolors="white", linewidths=0.7)
    ax.axhline(0, lw=0.5, color="#bbb")
    ax.axvline(0, lw=0.5, color="#bbb")
    ax.set_xlabel(f"PC1 — {evr[0]:.1%} of variance")
    ax.set_ylabel(f"PC2 — {evr[1]:.1%} of variance")
    ax.set_title("Musical taste map of the cohort", color="#13294B")

    # two legends: color = neighborhood, shape = program
    from matplotlib.lines import Line2D
    color_handles = [Line2D([], [], marker="o", linestyle="", color=cluster_color[c],
                            label=cluster_names[c], markersize=9) for c in range(k)]
    shape_handles = [Line2D([], [], marker=prog_marker[p], linestyle="", color="#555",
                            label=p, markersize=9) for p in prog_levels]
    leg1 = ax.legend(handles=color_handles, title="taste neighborhood", fontsize=8,
                     title_fontsize=9, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    ax.add_artist(leg1)
    if len(prog_levels) > 1:
        ax.legend(handles=shape_handles, title="program / role", fontsize=8,
                  title_fontsize=9, loc="lower left", bbox_to_anchor=(1.01, 0.0))
    fig.tight_layout()
    fig.savefig(DOCS_ASSETS / "taste_map.png", bbox_inches="tight")
    plt.close(fig)

    # loadings chart
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, pc in zip(axes, ["PC1", "PC2"]):
        if pc not in loadings:
            continue
        pos = loadings[pc]["positive"][:8][::-1]
        i = list(terms).index
        vals = [pca.components_[int(pc[-1]) - 1][i(t)] for t in pos]
        ax.barh(pos, vals, color="#4B9CD3")
        ax.set_title(f"{pc}: terms pulling to the right/top")
    fig.tight_layout()
    fig.savefig(DOCS_ASSETS / "pc_loadings.png", bbox_inches="tight")
    plt.close(fig)

    # nearest taste twins (cosine on the tf-idf space, not the projection)
    sim = cosine_similarity(X)
    np.fill_diagonal(sim, -1)
    rows = []
    ids = df["participant_id"].tolist()
    for i, pid in enumerate(ids):
        for j in np.argsort(sim[i])[-3:][::-1]:
            rows.append({"participant_id": pid, "neighbor": ids[j],
                         "similarity": round(float(sim[i][j]), 3)})
    pd.DataFrame(rows).to_csv(DOCS_DATA / "neighbors.csv", index=False)

    # interactive version (optional dependency)
    try:
        import plotly.express as px

        symbol_arg = {"symbol": "program"} if len(prog_levels) > 1 else {}
        fig = px.scatter(out, x="pc1", y="pc2", color="neighborhood",
                         hover_data=["participant_id", "song", "mood", "program"],
                         labels={"pc1": f"PC1 ({evr[0]:.1%})", "pc2": f"PC2 ({evr[1]:.1%})"},
                         title="Musical taste map — color = taste neighborhood, shape = program",
                         **symbol_arg)
        fig.update_traces(marker=dict(size=13, opacity=0.85,
                                      line=dict(width=1, color="white")))
        fig.write_html(DOCS_ASSETS / "taste_map.html", include_plotlyjs="cdn", full_html=True)
        log("interactive map -> taste_map.html")
    except ImportError:
        log("plotly not installed — skipping interactive map")

    log("taste map complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
