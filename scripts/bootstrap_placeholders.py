"""Create the files the .qmd pages reference, so `quarto preview` works on a
fresh clone BEFORE any data exists.

Quarto's `{{< include >}}` is a hard error when the target is missing, and a
referenced image that doesn't exist renders as a broken box. This writes
harmless placeholders for all of them. Every real pipeline step overwrites its
own placeholder, so this is safe to run any time 
Run automatically at the start of run_all.py, or by hand:

    python scripts/bootstrap_placeholders.py
"""
from __future__ import annotations

import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common import DOCS_ASSETS, ROOT, log

PARTIALS = {
    "_generated.md": """::: {.callout-note}
## No responses yet
This page fills in automatically once the survey has responses and the pipeline
has run. To see it with realistic sample data:

```bash
python scripts/make_sample_data.py --n 42
python scripts/run_all.py --no-fetch
```
:::
""",
    "_tastemap.md": """*The component interpretation appears here once the taste map has been
generated. Run `python scripts/run_all.py --no-fetch` after creating sample
data, or wait for real responses.*
""",
    "_playlist.md": """*The playlist appears here once responses come in and
`scripts/04_match_tracks.py` has run. No credentials are required for that step.*
""",
}

PLACEHOLDER_IMAGES = {
    "taste_map.png": "Taste map\n\nRun the pipeline to generate this",
    "pc_loadings.png": "Component loadings\n\nRun the pipeline to generate this",
    "program.png": "Charts appear after the first responses",
}

PLACEHOLDER_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Taste map</title>
<style>body{font-family:system-ui,-apple-system,sans-serif;display:flex;
align-items:center;justify-content:center;height:90vh;margin:0;color:#555;
text-align:center;background:#fafafa}</style></head>
<body><div><h3 style="color:#13294B">Interactive taste map</h3>
<p>This becomes a live scatter plot once the pipeline has run.<br>
<code>python scripts/run_all.py --no-fetch</code></p></div></body></html>
"""


def write_placeholder_image(path, text: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.text(0.5, 0.5, text, ha="center", va="center", fontsize=14, color="#888", wrap=True)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_edgecolor("#ddd")
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    made = []
    for name, body in PARTIALS.items():
        p = ROOT / name
        if not p.exists():
            p.write_text(body)
            made.append(name)

    for name, text in PLACEHOLDER_IMAGES.items():
        p = DOCS_ASSETS / name
        if not p.exists():
            write_placeholder_image(p, text)
            made.append(name)

    html = DOCS_ASSETS / "taste_map.html"
    if not html.exists():
        html.write_text(PLACEHOLDER_HTML)
        made.append("taste_map.html")

    log(f"placeholders created: {made or 'none needed'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
