"""Collapse messy free-text answers into groups you can actually plot.

Undergraduate background is the hard case: 40 people produce 35 spellings of
about 12 real fields ("CS", "comp sci", "Computer Science ", "B.S. Computer
Science"). This maps them to canonical families with keyword rules, keeps an
`Other` bucket, and reports what it could not classify so you can extend it.

US state codes get their own helper since that question asks for 2 letters but
people will inevitably type "North Carolina" or "nc ".
"""
from __future__ import annotations

import re

# --- undergraduate background -------------------------------------------------
# Order matters: the FIRST family whose pattern matches wins, so put more
# specific fields before broader ones (e.g. biostatistics before biology).
BACKGROUND_RULES: list[tuple[str, str]] = [
    ("Data Science",            r"\bdata sci|\bdata analytic|\bds\b"),
    ("Biostatistics",           r"biostat"),
    ("Statistics",              r"\bstat(istic)?s?\b|\bstat\b"),
    ("Computer Science",        r"comp(uter)?\.?\s?sci|\bcs\b|software|comp sci|informatics"),
    ("Mathematics",             r"\bmath|applied math"),
    ("Economics",               r"\becon"),
    ("Business & Finance",      r"business|finance|account|marketing|\bmba\b|management"),
    ("Engineering",             r"engineer|\bece\b|\bme\b\b"),
    ("Physics",                 r"physic|astronom"),
    ("Chemistry",               r"chem"),
    ("Biology & Life Sciences", r"\bbio(logy|logical)?\b|genetic|neuro|ecolog|zoolog|botan"),
    ("Public Health",           r"public health|\bmph\b|epidemiolog|health polic"),
    ("Psychology",              r"psych"),
    ("Sociology & Anthropology", r"sociolog|anthropolog"),
    ("Political Science",       r"polit(ical)? sci|government|international relations|\bpoli sci\b"),
    ("Geography & GIS",         r"geograph|\bgis\b|geospatial|environment"),
    ("Communications & Media",  r"communicat|journalis|media studies|advertis"),
    ("English & Literature",    r"english|literature|writing|linguist"),
    ("History",                 r"histor"),
    ("Philosophy",              r"philosoph"),
    ("Music & Arts",            r"\bmusic|\bart\b|art history|theat|film|design|dance"),
    ("Education",               r"educat|teaching"),
    ("Nursing & Medicine",      r"nurs|\bmed(icine|ical)?\b|pharma|dent"),
]

_STOP = {"a", "an", "the", "of", "in", "and", "or", "bs", "ba", "b.s.", "b.a.",
         "bachelor", "bachelors", "degree", "major", "minor", "science", "sciences",
         "studies", "study", "arts", "my", "was", "is", "with", "double"}


def canonical_background(value: str) -> str:
    """Map one free-text background answer to a canonical family."""
    v = str(value or "").strip().lower()
    if not v:
        return ""
    for label, pattern in BACKGROUND_RULES:
        if re.search(pattern, v):
            return label
    return "Other"


def background_tokens(value: str) -> list[str]:
    """Cleaned words for the word cloud — keeps the raw variety on purpose."""
    v = re.sub(r"[^a-z\s]", " ", str(value or "").lower())
    out = []
    for w in v.split():
        if len(w) > 2 and w not in _STOP:
            out.append(w.capitalize())
    return out


# --- US states / countries ----------------------------------------------------
STATE_NAMES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV", "wisconsin": "WI",
    "wyoming": "WY", "district of columbia": "DC", "washington dc": "DC", "puerto rico": "PR",
}

VALID_CODES = set(STATE_NAMES.values())

COUNTRY_ALIASES = {
    "usa": "USA", "us": "USA", "u.s.": "USA", "united states": "USA", "america": "USA",
    "uk": "UK", "united kingdom": "UK", "england": "UK", "great britain": "UK",
    "prc": "China", "peoples republic of china": "China", "mainland china": "China",
    "south korea": "South Korea", "korea": "South Korea", "republic of korea": "South Korea",
    "uae": "UAE", "drc": "DR Congo",
}


def canonical_location(value: str) -> str:
    """Normalize a location answer to a 2-letter state code or a country name.

    Handles: 'NC', 'nc ', 'North Carolina', 'Raleigh, NC', 'India', 'usa'.
    Returns '' when the answer is unusable.
    """
    v = re.sub(r"\s+", " ", str(value or "").strip())
    if not v:
        return ""
    low = v.lower().strip(" .,")

    if len(low) == 2 and low.upper() in VALID_CODES:      # already a code
        return low.upper()
    if low in STATE_NAMES:                                 # full state name
        return STATE_NAMES[low]
    if low in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[low]

    # "Raleigh, NC" / "Charlotte NC" -> take a trailing 2-letter code
    m = re.search(r"[,\s]([a-zA-Z]{2})$", v)
    if m and m.group(1).upper() in VALID_CODES:
        return m.group(1).upper()

    for name, code in STATE_NAMES.items():                 # state name inside a phrase
        if re.search(rf"\b{re.escape(name)}\b", low):
            return code

    # "Sao Paulo, Brazil" / "Seoul, South Korea" -> keep the country, drop the city
    if "," in v:
        tail = v.rsplit(",", 1)[1].strip()
        if tail:
            tl = tail.lower().strip(" .")
            if tl in COUNTRY_ALIASES:
                return COUNTRY_ALIASES[tl]
            if len(tail) == 2 and tail.upper() in VALID_CODES:
                return tail.upper()
            return tail.title() if len(tail) <= 24 else tail[:24].title()

    return v.title() if len(v) <= 24 else v[:24].title()   # assume it's a country
