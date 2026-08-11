"""Show how YOUR Google Sheet's headers map to the pipeline's internal keys.

    python scripts/inspect_sheet.py                      # uses .env / env vars
    python scripts/inspect_sheet.py --sheet-id 1ZVwPO... # or pass the ID directly
    python scripts/inspect_sheet.py --csv data/raw_responses.csv

Run this FIRST when connecting a real form. It tells you which questions were
recognized, which were ignored, and which expected fields are missing — before
you spend time debugging an empty chart.
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd

from common import DATA, env, log, resolve_columns

# What the pipeline genuinely needs vs. what is a nice-to-have.
REQUIRED = ["song_title", "song_artist"]
RECOMMENDED = ["program", "background", "taste_text"]
# key -> (alternative key that covers it, explanation)
FALLBACKS = {"family_location": ("hometown", "the location word cloud uses `hometown` instead")}
OPTIONAL_NOTES = {
    "consent": "no consent question — ALL responses will be included",
    "artists": "no artists question — the taste map leans on genres and free text",
    "email": "no email collected — IDs are hashed from the timestamp instead",
}


def load(args) -> pd.DataFrame | None:
    if args.csv:
        return pd.read_csv(args.csv)
    sheet_id = args.sheet_id or env("GOOGLE_SHEET_ID")
    if sheet_id:
        from sheet_io import fetch_public_sheet

        return fetch_public_sheet(sheet_id, env("GOOGLE_WORKSHEET"), env("GOOGLE_SHEET_GID"))
    url = env("FORM_CSV_URL")
    if url:
        import requests, io

        r = requests.get(url, timeout=60)
        r.raise_for_status()
        return pd.read_csv(io.StringIO(r.text))
    local = DATA / "raw_responses.csv"
    return pd.read_csv(local) if local.exists() else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet-id")
    ap.add_argument("--csv")
    args = ap.parse_args()

    try:
        df = load(args)
    except Exception as exc:
        log(f"could not read the sheet: {exc}")
        return 1
    if df is None:
        log("nothing to inspect — pass --sheet-id or --csv, or set GOOGLE_SHEET_ID")
        return 1

    mapping, unmapped = resolve_columns(list(df.columns))
    inverse = {v: k for k, v in mapping.items()}

    print(f"\n{len(df)} rows, {len(df.columns)} columns\n" + "=" * 78)
    print(f"{'INTERNAL KEY':<18} {'FORM QUESTION'}")
    print("-" * 78)
    for key in sorted(set(mapping.values())):
        q = inverse[key]
        print(f"{key:<18} {q[:58]}")

    found = set(mapping.values())

    blocking = [k for k in REQUIRED if k not in found]
    if blocking:
        print("\n" + "!" * 78)
        print("MISSING — the pipeline cannot build a playlist without these:")
        for k in blocking:
            print(f"  - {k}")
        print("Fix: add the question's exact wording under that key's `exact:` list")
        print("     in schemas/columns.yml, or loosen its `patterns:`.")

    soft = [k for k in RECOMMENDED if k not in found]
    if soft:
        print("\nRECOMMENDED but not found (those charts are simply skipped):")
        for k in soft:
            print(f"  - {k}")

    notes = []
    for k, (alt, why) in FALLBACKS.items():
        if k not in found:
            notes.append(f"{k}: {why}" if alt in found
                         else f"{k}: not found, and no `{alt}` either — that chart is skipped")
    for k, why in OPTIONAL_NOTES.items():
        if k not in found:
            notes.append(f"{k}: {why}")
    if notes:
        print("\nFYI — handled automatically, no action needed:")
        for n in notes:
            print(f"  - {n}")

    if unmapped:
        print("\nIGNORED COLUMNS (not used by the pipeline):")
        for u in unmapped:
            print(f"  - {u[:70]}")

    # quick fill-rate report so you can see which questions people skip
    print("\n" + "=" * 78)
    print(f"{'KEY':<18} {'ANSWERED':<10} SAMPLE VALUE")
    print("-" * 78)
    for key in sorted(set(mapping.values())):
        col = df[inverse[key]]
        filled = col.notna() & (col.astype(str).str.strip() != "")
        sample = str(col[filled].iloc[0])[:38] if filled.any() else ""
        print(f"{key:<18} {filled.sum():>3}/{len(df):<6} {sample}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
