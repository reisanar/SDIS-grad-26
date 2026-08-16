"""A dependency-free word cloud.

The `wordcloud` package needs a C extension that fails to build on plenty of
machines (and in some CI images). This renders a comparable layout with
matplotlib alone: size scales with frequency, and a spiral placement search with
bounding-box collision tests keeps words from overlapping.

    render_wordcloud({"NC": 12, "TX": 5, ...}, "out.png", title="...")
"""
from __future__ import annotations

import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.transforms import Bbox

PALETTE = ["#13294B", "#4B9CD3", "#00A5AD", "#EF426F", "#FFD100", "#C4D600", "#7BAFD4"]


def _boxes_overlap(a: Bbox, b: Bbox, pad: float = 2.0) -> bool:
    return not (a.x1 + pad < b.x0 or b.x1 + pad < a.x0
                or a.y1 + pad < b.y0 or b.y1 + pad < a.y0)


def render_wordcloud(freqs: dict[str, int], out_path, title: str = "",
                     width: float = 9.0, height: float = 5.0,
                     max_words: int = 60, min_font: float = 10.0,
                     max_font: float = 64.0) -> bool:
    """Draw a word cloud. Returns False if there's nothing to draw."""
    items = [(w, c) for w, c in sorted(freqs.items(), key=lambda x: -x[1]) if w and c > 0]
    if not items:
        return False
    items = items[:max_words]

    counts = [c for _, c in items]
    hi, lo = max(counts), min(counts)

    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=13, color="#13294B", pad=12)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    placed: list[Bbox] = []
    for i, (word, count) in enumerate(items):
        # sqrt scaling keeps a single dominant term from swamping the canvas
        frac = 1.0 if hi == lo else (count - lo) / (hi - lo)
        size = min_font + (max_font - min_font) * math.sqrt(frac)
        color = PALETTE[i % len(PALETTE)]

        angle = 0 if (i % 7) else 90  # occasional vertical word for texture
        done = False
        # Archimedean spiral outward from the centre until it fits
        for step in range(2000):
            t = step * 0.30
            r = 0.75 * t
            x = 50 + r * math.cos(t)
            y = 50 + r * math.sin(t) * 0.62  # squash vertically to fill a wide canvas
            if not (2 < x < 98 and 3 < y < 97):
                continue
            txt = ax.text(x, y, word, fontsize=size, color=color, ha="center",
                          va="center", rotation=angle, fontweight="bold" if i < 3 else "normal",
                          alpha=0.92)
            bb = txt.get_window_extent(renderer=renderer)
            if any(_boxes_overlap(bb, p) for p in placed):
                txt.remove()
                continue
            placed.append(bb)
            done = True
            break
        if not done:
            continue  # canvas is full; skip the rest quietly

    fig.tight_layout()
    fig.savefig(out_path, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return True
