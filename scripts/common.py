"""Shared paths, config loading, and small helpers."""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"                # raw + intermediate (git-ignored except samples)
DOCS_DATA = ROOT / "docs_data"      # published, anonymized data
DOCS_ASSETS = ROOT / "docs_assets"  # published charts
SCHEMAS = ROOT / "schemas"

for _d in (DATA, DOCS_DATA, DOCS_ASSETS):
    _d.mkdir(parents=True, exist_ok=True)


def load_env() -> None:
    """Load .env if python-dotenv is available; env vars always win."""
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env", override=False)
    except Exception:
        pass


def env(name: str, default: str | None = None) -> str | None:
    load_env()
    v = os.environ.get(name, default)
    return v.strip() if isinstance(v, str) else v


def norm_title(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip().rstrip(":?").strip().lower()


def _spec() -> dict:
    return yaml.safe_load((SCHEMAS / "columns.yml").read_text()) or {}


def column_map() -> dict[str, str]:
    """{normalized exact title -> internal key}. Kept for backwards compatibility."""
    out: dict[str, str] = {}
    for key, rules in _spec().items():
        titles = rules.get("exact", []) if isinstance(rules, dict) else rules
        for t in titles or []:
            out[norm_title(t)] = key
    return out


def resolve_columns(headers: list[str]) -> tuple[dict[str, str], list[str]]:
    """Map real sheet headers to internal keys.

    Exact (normalized) matches win; anything left over is matched against the
    regex patterns in columns.yml. This is what lets the pipeline keep working
    when a question is reworded. Returns ({header: key}, [unmapped headers]).
    """
    spec = _spec()
    exact = column_map()
    patterns = {k: (r.get("patterns", []) if isinstance(r, dict) else [])
                for k, r in spec.items()}

    mapping: dict[str, str] = {}
    taken: set[str] = set()

    for h in headers:  # pass 1 — exact
        key = exact.get(norm_title(h))
        if key and key not in taken:
            mapping[h] = key
            taken.add(key)

    for h in headers:  # pass 2 — regex
        if h in mapping:
            continue
        n = norm_title(h)
        for key, pats in patterns.items():
            if key in taken:
                continue
            if any(re.search(p, n, flags=re.I) for p in pats or []):
                mapping[h] = key
                taken.add(key)
                break

    unmapped = [h for h in headers if h not in mapping]
    return mapping, unmapped


def anon_id(raw: str, salt: str | None = None) -> str:
    """Stable, non-reversible participant ID."""
    salt = salt or env("ANON_SALT", "immersion") or "immersion"
    h = hashlib.sha256(f"{salt}::{str(raw).strip().lower()}".encode()).hexdigest()
    return f"p{h[:8]}"


def split_multi(value: str) -> list[str]:
    """Split a comma / semicolon / 'and' separated answer into clean items."""
    if not value:
        return []
    parts = re.split(r"[;,]|\band\b|\|", str(value), flags=re.I)
    return [p.strip() for p in parts if p and p.strip()]


def log(msg: str) -> None:
    print(f"[immersion] {msg}", flush=True)
