"""Run the whole pipeline: fetch -> clean -> analyze -> map -> playlists -> snippets.

    python scripts/run_all.py            # everything
    python scripts/run_all.py --no-fetch # reuse the responses already on disk
    python scripts/run_all.py --only 03  # a single step

Steps that lack credentials log a warning and are skipped; the site still builds.
"""
from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = ["bootstrap_placeholders", "00_fetch_responses", "01_preprocess", "02_demographics",
         "03_taste_map", "04_match_tracks", "05_spotify_playlist", "06_apple_music",
         "07_render_snippets"]
REQUIRED = {"01_preprocess"}  # only this one is fatal; every other step degrades


def run(step: str) -> int:
    print(f"\n===== {step} =====", flush=True)
    try:
        runpy.run_path(str(HERE / f"{step}.py"), run_name="__main__")
        return 0
    except SystemExit as e:
        return int(e.code or 0)
    except Exception as exc:
        print(f"[immersion] {step} raised: {exc}", flush=True)
        return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--only")
    args = ap.parse_args()

    steps = [s for s in STEPS if not (args.no_fetch and s.startswith("00"))]
    if args.only:
        steps = [s for s in STEPS if s.startswith(args.only)]

    failed = []
    for s in steps:
        code = run(s)
        if code:
            failed.append(s)
            if s in REQUIRED:
                print(f"[immersion] {s} is required — stopping.", flush=True)
                return 1
    print(f"\n[immersion] done. skipped/failed: {failed or 'none'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
