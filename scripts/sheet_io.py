"""Read a Google Sheet that's shared with 'Anyone with the link'.

No credentials, no service account, no 'Publish to web' step. Just the sheet ID
from the URL (and optionally the tab's gid):

    https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit?gid=<GID>
                                          ^^^^^^^^^^        ^^^^^

You can paste the whole URL into GOOGLE_SHEET_ID and both values are extracted.

Google exposes two credential-free endpoints for link-shared sheets. 
"""
from __future__ import annotations

import io
import re
import urllib.parse

import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (cohort-snapshot)"}


def extract_sheet_id(value: str) -> str:
    """Accept a bare ID or a full Google Sheets URL."""
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", value or "")
    return m.group(1) if m else (value or "").strip()


def extract_gid(value: str) -> str | None:
    """Pull the tab id out of a full URL (?gid=... or #gid=...)."""
    m = re.search(r"[?&#]gid=(\d+)", value or "")
    return m.group(1) if m else None


def _urls(sheet_id: str, gid: str | None, worksheet: str | None) -> list[str]:
    """Candidate CSV endpoints, most reliable first."""
    base = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
    out: list[str] = []

    if gid:
        out.append(f"{base}/export?format=csv&gid={gid}")
        out.append(f"{base}/gviz/tq?tqx=out:csv&gid={gid}")
    if worksheet:
        name = urllib.parse.quote(worksheet)
        out.append(f"{base}/gviz/tq?tqx=out:csv&sheet={name}")
    # first/default tab
    out.append(f"{base}/export?format=csv")
    out.append(f"{base}/gviz/tq?tqx=out:csv")
    return out


def fetch_public_sheet(sheet_id_or_url: str, worksheet: str | None = None,
                       gid: str | None = None) -> pd.DataFrame:
    """Return the sheet as a DataFrame, or raise with an actionable message."""
    sheet_id = extract_sheet_id(sheet_id_or_url)
    gid = gid or extract_gid(sheet_id_or_url)

    errors: list[str] = []
    for url in _urls(sheet_id, gid, worksheet):
        try:
            r = requests.get(url, headers=UA, timeout=45, allow_redirects=True)
        except requests.RequestException as exc:
            errors.append(f"{url.split('?')[0]}: {exc}")
            continue

        # Google returns an HTML sign-in page when the sheet isn't link-shared
        ctype = r.headers.get("Content-Type", "")
        if not r.ok or "text/html" in ctype:
            errors.append(f"{url.split('?')[0]}: HTTP {r.status_code} ({ctype.split(';')[0]})")
            continue

        try:
            df = pd.read_csv(io.StringIO(r.text))
        except Exception as exc:
            errors.append(f"{url.split('?')[0]}: unparseable ({exc})")
            continue

        if len(df.columns) > 1:
            return df
        errors.append(f"{url.split('?')[0]}: parsed only {len(df.columns)} column")

    raise RuntimeError(
        "Could not read the sheet without credentials.\n"
        "  1. Open the sheet -> Share -> General access -> 'Anyone with the link' (Viewer)\n"
        "  2. Check GOOGLE_SHEET_ID is the string between /d/ and /edit\n"
        "  3. If the responses are on a second tab, include its gid\n"
        "  Tried: " + " | ".join(errors)
    )
