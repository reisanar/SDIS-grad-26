"""Step 0 — pull Google Form responses into data/raw_responses.csv.

Four ingestion modes. Nothing downstream cares which ran.

"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pandas as pd

from common import DATA, env, log

RAW = DATA / "raw_responses.csv"


def from_service_account() -> pd.DataFrame | None:
    sheet_id = env("GOOGLE_SHEET_ID")
    creds_raw = env("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not (sheet_id and creds_raw):
        return None
    # A path that doesn't exist means "not configured" — skip quietly rather
    # than raising a confusing import error for an optional dependency.
    looks_like_path = creds_raw.strip().startswith((".", "/", "~")) or creds_raw.endswith(".json")
    if looks_like_path and not Path(creds_raw).expanduser().exists():
        return None
    import gspread
    from google.oauth2.service_account import Credentials

    info = json.loads(Path(creds_raw).read_text()) if Path(creds_raw).exists() else json.loads(creds_raw)
    creds = Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    ws_name = env("GOOGLE_WORKSHEET")
    sh = gspread.authorize(creds).open_by_key(sheet_id)
    ws = sh.worksheet(ws_name) if ws_name else sh.sheet1
    rows = ws.get_all_records()
    log(f"fetched {len(rows)} rows via service account")
    return pd.DataFrame(rows)


def from_link_shared_sheet() -> pd.DataFrame | None:
    """Sheet ID + link sharing, no credentials."""
    sheet_id = env("GOOGLE_SHEET_ID")
    if not sheet_id:
        return None
    from sheet_io import fetch_public_sheet

    df = fetch_public_sheet(sheet_id, env("GOOGLE_WORKSHEET"), env("GOOGLE_SHEET_GID"))
    log(f"fetched {len(df)} rows from the link-shared sheet")
    return df


def from_published_csv() -> pd.DataFrame | None:
    url = env("FORM_CSV_URL")
    if not url:
        return None
    import requests

    r = requests.get(url, timeout=60)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    log(f"fetched {len(df)} rows via published CSV")
    return df


def from_local() -> pd.DataFrame | None:
    path = Path(env("LOCAL_CSV") or RAW)
    if not path.exists():
        return None
    df = pd.read_csv(path)
    log(f"loaded {len(df)} rows from {path}")
    return df


def main() -> int:
    labels = {
        "from_service_account": "service account",
        "from_link_shared_sheet": "link-shared sheet",
        "from_published_csv": "published CSV",
        "from_local": "local file",
    }
    for fn in (from_service_account, from_link_shared_sheet, from_published_csv, from_local):
        try:
            df = fn()
        except Exception as exc:  # keep trying the next mode
            log(f"{labels.get(fn.__name__, fn.__name__)} unavailable: "
                f"{str(exc).splitlines()[0]}")
            continue
        if df is not None and len(df):
            df.to_csv(RAW, index=False)
            log(f"wrote {RAW} ({len(df)} rows, {len(df.columns)} columns)")
            return 0
    log("no response source configured — set GOOGLE_SHEET_ID, FORM_CSV_URL, or LOCAL_CSV")
    return 1


if __name__ == "__main__":
    sys.exit(main())
