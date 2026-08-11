"""Step 1 — rename, filter by consent, anonymize, tidy.

Inputs : data/raw_responses.csv
Outputs: data/clean.csv                (internal, includes hashed id only)
         docs_data/responses_anon.csv  (published, safe to commit)
"""
from __future__ import annotations

import sys

import pandas as pd

from common import DATA, DOCS_DATA, anon_id, log, resolve_columns, split_multi

RAW = DATA / "raw_responses.csv"
CLEAN = DATA / "clean.csv"
PUBLISHED = DOCS_DATA / "responses_anon.csv"

DROP_FROM_PUBLIC = ["email", "display_name", "hometown"]
TEXT_KEYS = ["goals", "taste_text"]


def main() -> int:
    if not RAW.exists():
        log("no raw_responses.csv — run 00_fetch_responses.py first")
        return 1

    df = pd.read_csv(RAW)
    if df.empty:
        log("the sheet has headers but no responses yet — nothing to process")
        df.to_csv(CLEAN, index=False)
        df.to_csv(PUBLISHED, index=False)
        return 0
    renamed, unmapped = resolve_columns(list(df.columns))
    df = df.rename(columns=renamed)
    log(f"mapped {len(renamed)} columns: {sorted(set(renamed.values()))}")
    if unmapped:
        log(f"unmapped (ignored): {unmapped}")

    before = len(df)
    if "consent" in df:
        df = df[df["consent"].astype(str).str.strip().str.lower().str.startswith("y")]
        log(f"consent filter: {before} -> {len(df)} rows")

    key_source = "email" if "email" in df else df.columns[0]
    df["participant_id"] = [anon_id(v) for v in df[key_source]]
    df = df.drop_duplicates(subset="participant_id", keep="last")

    for k in ("artists", "genres", "background"):
        if k in df:
            df[k + "_list"] = df[k].fillna("").map(split_multi)

    for k in TEXT_KEYS:
        if k in df:
            df[k] = df[k].fillna("").astype(str).str.strip()

    for k in ("song_title", "song_artist"):
        if k in df:
            df[k] = df[k].fillna("").astype(str).str.strip()
    if {"song_title", "song_artist"} <= set(df.columns):
        df = df[(df["song_title"] != "") & (df["song_artist"] != "")]
        log(f"rows with a usable song pick: {len(df)}")

    df.to_csv(CLEAN, index=False)

    public = df.drop(columns=[c for c in DROP_FROM_PUBLIC if c in df.columns])
    public.to_csv(PUBLISHED, index=False)
    log(f"wrote {CLEAN} and {PUBLISHED} ({len(df)} participants)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
