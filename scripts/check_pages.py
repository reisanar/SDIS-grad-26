"""Execute the python cells of every .qmd the way Quarto does, without Quarto.

    python scripts/check_pages.py                # all pages
    python scripts/check_pages.py workshop.qmd   # one page

Catches the class of failure where a page renders fine with 40 responses but
crashes with 5 (empty vocabulary, too few PCA components, missing columns).
Run it after any change to a .qmd, and before a session with live data.
"""
import re, sys, io, contextlib
from pathlib import Path

def run_qmd(path):
    src = Path(path).read_text()
    cells = re.findall(r"```\{python\}\n(.*?)```", src, re.S)
    ns = {}
    def display(x): print(f"  [display] {type(x).__name__}")
    ns["display"] = display
    for i, cell in enumerate(cells, 1):
        body = "\n".join(l for l in cell.splitlines() if not l.strip().startswith("#|"))
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                exec(compile(body, f"{path}:cell{i}", "exec"), ns)
        except ModuleNotFoundError as e:
            print(f"  cell {i}: SKIPPED -> missing package '{e.name}'. "
                  "Run: pip install -r requirements.txt")
            return None   # environment problem, not a page bug
        except Exception as e:
            print(f"  cell {i}: FAILED -> {type(e).__name__}: {e}")
            return False
        out = buf.getvalue().strip()
        print(f"  cell {i}: ok" + (f" | {out.splitlines()[0][:70]}" if out else ""))
    return True

targets = sys.argv[1:] or sorted(str(p) for p in Path(".").glob("*.qmd"))
results = []
for f in targets:
    print(f"\n=== {f} ===")
    results.append(run_qmd(f))

if any(r is False for r in results):
    print("\nRESULT: FAILURES ABOVE — Quarto will error on these")
    sys.exit(1)
if any(r is None for r in results):
    print("\nRESULT: could not fully check (missing packages) — "
          "run `pip install -r requirements.txt`")
    sys.exit(0)
print("\nRESULT: all cells executed")
sys.exit(0)
