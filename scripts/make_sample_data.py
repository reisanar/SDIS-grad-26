"""Generate a synthetic response sheet that mimics real Google Form output.

    python scripts/make_sample_data.py --n 42

Deliberately messy, because real responses are: mixed-case state answers, full
state names where 2 letters were requested, a few international families, and
undergraduate backgrounds written 30 different ways. That mess is what exercises
the canonicalizer — if the pipeline survives this file, it will survive your
cohort.
"""
from __future__ import annotations

import argparse
import random

import pandas as pd

from common import DATA, log

# Column titles mirror the live form. The pipeline also pattern-matches, so
# small wording differences on your side are fine.
# Column titles mirror the LIVE SDIS form exactly, so sample runs reproduce
# what you will see with real responses. --schema classic uses the older wording.
# EXACT headers and column ORDER from the live SDIS export. Note the trailing
# space in the "makes you feel" question — reproduced deliberately so sample
# files are byte-comparable with a real export.
LIVE_COLUMNS = [
    "Timestamp",
    "What is your program (or role) at SDIS?",
    "What is your undergraduate background?",
    "Where did you grow up? (city, state/country)",
    "What is the title of one song that has been on your mind recently?",
    "Who performs it?",
    "In a sentence, describe how this song makes you feel ",
    "Which genres to you listen to the most?",
]

Q_LIVE = {
    "timestamp": LIVE_COLUMNS[0],
    "program": LIVE_COLUMNS[1],
    "background": LIVE_COLUMNS[2],
    "hometown": LIVE_COLUMNS[3],
    "song_title": LIVE_COLUMNS[4],
    "song_artist": LIVE_COLUMNS[5],
    "taste": LIVE_COLUMNS[6],
    "genres": LIVE_COLUMNS[7],
}

Q_CLASSIC = {
    "timestamp": "Timestamp",
    "email": "Email Address",
    "consent": "May we include your (anonymized) answers in the cohort snapshot?",
    "program": "Which program or role best describes you?",
    "background": "What was your undergraduate background?",
    "family": "Which state or country does your family live in? (Use 2 letters for the state, e.g., NC, TX, FL)",
    "artists": "Name up to 3 artists you love",
    "song_title": "One song that has to be on the cohort playlist",
    "song_artist": "Who performs it?",
    "taste": "Describe your music taste in a sentence",
    "mood": "Pick a mood word for your song",
}

# Exact options from the live SDIS form. Weighted so master's students dominate,
# which is what a real immersion cohort looks like.
PROGRAMS = (["MS in DS"] * 14 + ["PhD in DS"] * 5 + ["CHIP PhD"] * 2 + ["CHIP MS"] * 2
            + ["MS in LS"] * 3 + ["MS in IS"] * 3 + ["PhD in ILS"] * 2
            + ["Faculty"] * 3 + ["Staff"] * 2)

# Exact options from the live SDIS form (checkboxes, so people pick several).
GENRES = ["Pop", "Metal", "Classical", "Folk", "Jazz", "Electronic", "Reggaeton",
          "Indie Rock", "R&B", "Country", "Hip-hop", "Latin", "Other"]

# "city, state/country" — the shape the live form asks for
CITIES = ["Raleigh, NC", "Durham, NC", "Charlotte, NC", "Chapel Hill, NC", "Cary, NC",
          "Atlanta, GA", "Austin, TX", "Houston, TX", "Miami, FL", "Orlando, FL",
          "Richmond, VA", "Columbia, SC", "New York, NY", "Brooklyn, NY",
          "Los Angeles, CA", "San Diego, CA", "Chicago, IL", "Columbus, OH",
          "Philadelphia, PA", "Boston, MA", "Newark, NJ", "Baltimore, MD",
          "Nashville, TN", "Seattle, WA", "Denver, CO", "Detroit, MI",
          "Washington, DC", "Mumbai, India", "Beijing, China", "Sao Paulo, Brazil",
          "Lagos, Nigeria", "Seoul, South Korea", "Mexico City, Mexico",
          "Berlin, Germany", "Bogota, Colombia", "Hanoi, Vietnam"]

# These sentences ARE the taste map — the tf-idf vocabulary comes from here, so
# they are written with deliberately varied emotional registers and imagery.
# Loose thematic families (nostalgia, energy, calm, melancholy, joy, motion)
# give PCA real structure to find, the way a real cohort's answers would.
# The free-text sentence IS the taste map, so sample answers are COMPOSED rather
# than drawn from a fixed list: each respondent gets a unique sentence built from
# an emotional family (nostalgia, energy, calm, melancholy, joy, connection).
# Shared vocabulary within a family and distinct vocabulary across families is
# exactly the structure PCA should find — and it means no two people submit the
# identical string, which is what would happen with a small fixed list.
FEELING_FAMILIES = {
    "nostalgia": {
        "openers": ["nostalgic for", "homesick for", "wistful about", "reminded of",
                    "transported back to"],
        "objects": ["a summer that may not have happened", "my mother's kitchen",
                    "riding in my dad's truck", "the house I grew up in",
                    "people I have lost touch with", "my first apartment",
                    "long drives with my sister", "an old journal entry"],
        "tails": ["and I cannot explain why", "in a way that aches a little",
                  "every single time it plays", "before I even recognize the intro",
                  "though I was barely there"],
    },
    "energy": {
        "openers": ["energized", "hyped up", "invincible", "restless", "fired up",
                    "electric"],
        "objects": ["like I could run through a wall", "like starting something huge",
                    "like arguing with someone about anything",
                    "like sprinting up a hill", "like the day just began",
                    "like taking a risk I have been avoiding"],
        "tails": ["without deciding to", "and slightly reckless about it",
                  "in the best possible way", "before the first chorus ends", ""],
    },
    "calm": {
        "openers": ["calm", "settled", "grounded", "peaceful", "steady", "unhurried"],
        "objects": ["like the world slowed down", "like a long breath out",
                    "like putting down something heavy", "like rain on a quiet afternoon",
                    "like everything will be fine", "like walking with no destination"],
        "tails": ["for three whole minutes", "which I badly needed",
                  "and I stop checking my phone", "in a way nothing else manages", ""],
    },
    "melancholy": {
        "openers": ["quietly devastated", "tender", "bruised", "lonely", "hollowed out",
                    "aching"],
        "objects": ["in a cinematic way", "like pressing a healing scar",
                    "like rain on a train window", "like the end of a long chapter",
                    "like missing someone who is still here"],
        "tails": ["and weirdly comforted by that", "but I keep coming back to it",
                  "which I have decided to enjoy", "and I let it happen", ""],
    },
    "joy": {
        "openers": ["giddy", "joyful", "warm", "free", "delighted", "buoyant"],
        "objects": ["like dancing badly alone at midnight", "like a room full of people I love",
                    "like laughing at something nobody else heard",
                    "like skipping class on the first warm day",
                    "like driving with every window down"],
        "tails": ["and sitting still becomes impossible", "for no defensible reason",
                  "until the song ends", "and I play it twice", ""],
    },
    "connection": {
        "openers": ["seen", "understood", "known", "connected", "recognized"],
        "objects": ["like someone wrote down a thought I never said",
                    "like meeting a version of myself from years ago",
                    "like my family is in the room", "like someone else gets it",
                    "like a language I did not know I spoke"],
        "tails": ["without having to explain anything", "which is rare",
                  "and a little exposed by that", "in the middle of an ordinary day", ""],
    },
}


def compose_feeling(rng) -> str:
    fam = rng.choice(list(FEELING_FAMILIES))
    d = FEELING_FAMILIES[fam]
    sentence = f"{rng.choice(d['openers'])} {rng.choice(d['objects'])}"
    tail = rng.choice(d["tails"])
    if tail:
        sentence += f" {tail}"
    return sentence

# intentionally inconsistent — this is the point
STATES = ["NC", "NC", "NC", "nc", "North Carolina", "Raleigh, NC", "TX", "tx", "Texas",
          "FL", "GA", "VA", "SC", "NY", "CA", "ca", "IL", "OH", "PA", "MA", "NJ",
          "MD", "TN", "WA", "CO", "MI", "DC"]
COUNTRIES = ["India", "china", "Brazil", "Nigeria", "South Korea", "Mexico",
             "Germany", "Colombia", "Vietnam", "usa"]

BACKGROUNDS = [
    "Computer Science", "CS", "comp sci", "B.S. Computer Science",
    "Statistics", "stats", "Statistics and Analytics", "Biostatistics",
    "Mathematics", "Applied Math", "math",
    "Economics", "Econ", "Business Administration", "Finance", "Marketing",
    "Biology", "biology and chemistry", "Neuroscience", "Public Health",
    "Psychology", "psych", "Sociology", "Political Science", "poli sci",
    "English Literature", "History", "Philosophy", "Music Performance",
    "Mechanical Engineering", "Industrial Engineering", "Physics",
    "Geography and GIS", "Environmental Science", "Communications",
    "Journalism", "Education", "Nursing", "Data Science", "Information Science",
]

ARTISTS = ["Kendrick Lamar", "Phoebe Bridgers", "Bad Bunny", "Radiohead", "Beyonce",
           "Miles Davis", "Taylor Swift", "Fela Kuti", "Bjork", "The Strokes",
           "Sufjan Stevens", "Rosalia", "Tyler, The Creator", "Chopin", "Fleetwood Mac",
           "SZA", "Frank Ocean", "Daft Punk", "Bob Marley", "Aretha Franklin",
           "Caetano Veloso", "Burna Boy", "Karol G", "Jacob Collier", "Nina Simone"]

SONGS = [("Alright", "Kendrick Lamar"), ("Motion Sickness", "Phoebe Bridgers"),
         ("Tití Me Preguntó", "Bad Bunny"), ("Idioteque", "Radiohead"),
         ("Freedom", "Beyonce"), ("So What", "Miles Davis"), ("Cruel Summer", "Taylor Swift"),
         ("Water No Get Enemy", "Fela Kuti"), ("Hyperballad", "Bjork"),
         ("Reptilia", "The Strokes"), ("Chicago", "Sufjan Stevens"), ("Malamente", "Rosalia"),
         ("EARFQUAKE", "Tyler, The Creator"), ("Dreams", "Fleetwood Mac"),
         ("Good Days", "SZA"), ("Pyramids", "Frank Ocean"), ("Get Lucky", "Daft Punk"),
         ("Three Little Birds", "Bob Marley"), ("Respect", "Aretha Franklin"),
         ("Last Last", "Burna Boy"), ("Feeling Good", "Nina Simone"),
         # deliberately odd capitalization — the catalog lookup normalizes it
         ("DtMf", "Bad Bunny"),
         ("NUEVAYoL", "Bad Bunny"), ("BAILE INoLVIDABLE", "Bad Bunny"),
         ("Not Like Us", "Kendrick Lamar"), ("Espresso", "Sabrina Carpenter"),
         ("Texas Hold 'Em", "Beyonce"), ("Birds of a Feather", "Billie Eilish")]

PHRASES = [
    "moody guitars and sad lyrics", "anything with a heavy bassline",
    "old jazz records and new hip hop", "whatever my roommate is playing",
    "high energy pop for the gym, piano at night", "very online electronic music",
    "songs my parents played on road trips", "loud, fast, and short",
    "quiet folk when I need to think", "latin pop, no apologies",
    "90s r&b and anything with strings", "soundtracks and video game music",
    "bluegrass, which surprises people", "afrobeats all summer long",
    "classical in the morning, techno at night",
]
MOODS = ["energetic", "chill", "nostalgic", "focus", "dance", "melancholy"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=42)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=None)
    ap.add_argument("--schema", choices=["live", "classic"], default="live",
                    help="'live' mirrors the current SDIS form; 'classic' the fuller version")
    args = ap.parse_args()
    rng = random.Random(args.seed)

    # Guarantee a few anchor tracks appear at least once, so a sample run always
    # exercises the tricky cases (odd capitalization, accents, apostrophes)
    # instead of leaving it to chance.
    ANCHORS = [("DtMf", "Bad Bunny"),
               ("Tití Me Preguntó", "Bad Bunny"),
               ("Texas Hold 'Em", "Beyonce"),
               ("Not Like Us", "Kendrick Lamar")]
    assigned = {}
    for j, anchor in enumerate(ANCHORS[:args.n]):
        assigned[j] = anchor

    rows = []
    for i in range(args.n):
        title, artist = assigned.get(i) or rng.choice(SONGS)
        ts = f"2027/03/{rng.randint(1, 7):02d} {rng.randint(8,17)}:{rng.randint(10,59)}:00"
        if args.schema == "live":
            Q = Q_LIVE
            rows.append({
                Q["timestamp"]: ts,
                Q["program"]: rng.choice(PROGRAMS),
                Q["background"]: rng.choice(BACKGROUNDS),
                Q["hometown"]: rng.choice(CITIES),
                Q["genres"]: ", ".join(rng.sample(GENRES, rng.randint(2, 4))),
                Q["song_title"]: title,
                Q["song_artist"]: artist,
                Q["taste"]: compose_feeling(rng),
            })
        else:
            Q = Q_CLASSIC
            family = rng.choice(COUNTRIES) if rng.random() < 0.22 else rng.choice(STATES)
            rows.append({
                Q["timestamp"]: ts,
                Q["email"]: f"student{i:03d}@unc.edu",
                Q["consent"]: "Yes" if rng.random() > 0.05 else "No",
                Q["program"]: rng.choice(PROGRAMS),
                Q["background"]: rng.choice(BACKGROUNDS),
                Q["family"]: family,
                Q["artists"]: ", ".join(rng.sample(ARTISTS, 3)),
                Q["song_title"]: title,
                Q["song_artist"]: artist,
                Q["taste"]: rng.choice(PHRASES),
                Q["mood"]: rng.choice(MOODS),
            })

    out = args.out or (DATA / "raw_responses.csv")
    frame = pd.DataFrame(rows)
    if args.schema == "live":   # preserve the live export's exact column order
        frame = frame[LIVE_COLUMNS]
    frame.to_csv(out, index=False)
    bg_key = (Q_LIVE if args.schema == "live" else Q_CLASSIC)["background"]
    log(f"wrote {out} with {len(rows)} synthetic responses using the "
        f"'{args.schema}' form schema "
        f"({len(set(r[bg_key] for r in rows))} distinct background spellings)")


if __name__ == "__main__":
    main()
