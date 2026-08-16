"""Diagnose common `quarto preview` / `quarto render` failures 

    python scripts/doctor.py

Checks the things that actually break this project: a stale styles.css left over
from an older copy, a theme entry pointing at a plain .css file, missing SCSS
layer boundaries, stale Quarto caches, and missing include targets.
Exits non-zero if anything needs fixing.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OK, WARN, BAD = "  ok  ", " warn ", " FAIL "
LAYERS = ("scss:defaults", "scss:rules", "scss:mixins", "scss:functions", "scss:uses")

problems: list[str] = []
fixes: list[str] = []


def say(tag: str, msg: str) -> None:
    print(f"[{tag}] {msg}")


def check_stale_css(fix: bool) -> None:
    """The #1 cause: an old styles.css sitting next to the new styles.scss."""
    css = ROOT / "styles.css"
    scss = ROOT / "styles.scss"
    if css.exists() and scss.exists():
        say(BAD, "Both styles.css (old) and styles.scss (current) exist.")
        say("", "      Quarto picks up the stale .css and fails on layer boundaries.")
        if fix:
            css.unlink()
            say(OK, "  -> deleted styles.css")
        else:
            problems.append("stale styles.css present")
            fixes.append("rm styles.css")
    elif css.exists() and not scss.exists():
        say(BAD, "styles.css exists but styles.scss does not — this is an OLD copy of the project.")
        problems.append("old project version")
        fixes.append("re-download the zip and extract to a CLEAN folder")
    elif scss.exists():
        say(OK, "styles.scss present, no stale styles.css")
    else:
        say(WARN, "no stylesheet found at all")


def check_theme(fix: bool = False) -> None:
    qy = ROOT / "_quarto.yml"
    if not qy.exists():
        say(BAD, "_quarto.yml missing — are you in the project folder?")
        problems.append("no _quarto.yml")
        return
    text = qy.read_text()
    if "styles.css" in text:
        if fix:
            qy.write_text(text.replace("styles.css", "styles.scss"))
            say(OK, "  -> rewrote _quarto.yml to reference styles.scss")
        else:
            say(BAD, "_quarto.yml still references styles.css")
            problems.append("_quarto.yml references styles.css")
            fixes.append("change styles.css -> styles.scss in _quarto.yml")
    elif "styles.scss" in text:
        say(OK, "_quarto.yml references styles.scss")
    else:
        say(WARN, "_quarto.yml has no custom stylesheet reference")


def check_layers() -> None:
    scss = ROOT / "styles.scss"
    if not scss.exists():
        return
    body = scss.read_text()
    found = [l for l in LAYERS if l in body]
    if found:
        say(OK, f"SCSS layer boundaries present: {', '.join(found)}")
    else:
        say(BAD, "styles.scss has no layer boundary comment")
        problems.append("missing scss layer boundary")
        fixes.append("add /*-- scss:defaults --*/ at the top of styles.scss")


def check_page_cells() -> None:
    """Execute each .qmd's python cells so render errors surface here, not in Quarto."""
    import subprocess

    script = ROOT / "scripts" / "check_pages.py"
    if not script.exists():
        return
    r = subprocess.run([sys.executable, str(script)], cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode == 0:
        say(OK, "all .qmd python cells execute")
    else:
        say(BAD, "a .qmd python cell fails — Quarto will error on render")
        for line in (r.stdout or "").splitlines():
            if "FAILED" in line:
                say("", f"      {line.strip()}")
        problems.append("failing .qmd cell")
        fixes.append("python scripts/check_pages.py   # see the failure in context")


def check_caches(fix: bool) -> None:
    stale = [d for d in (ROOT / ".quarto", ROOT / "_freeze", ROOT / "docs") if d.exists()]
    if not stale:
        say(OK, "no stale build caches")
        return
    names = ", ".join(d.name for d in stale)
    if fix:
        for d in stale:
            if d.name != "docs":
                shutil.rmtree(d, ignore_errors=True)
        say(OK, f"  -> cleared build caches ({names})")
    else:
        say(WARN, f"build caches present ({names}); clear them if the error persists")
        fixes.append("rm -rf .quarto _freeze")


def check_includes(fix: bool = False) -> None:
    missing = []
    for qmd in ROOT.glob("*.qmd"):
        for line in qmd.read_text().splitlines():
            if "{{< include" in line:
                target = line.split("include", 1)[1].replace(">}}", "").strip()
                if not (ROOT / target).exists():
                    missing.append(f"{qmd.name} -> {target}")
    if missing and fix:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import runpy
        runpy.run_path(str(Path(__file__).resolve().parent / "bootstrap_placeholders.py"),
                       run_name="__main__")
        say(OK, "  -> generated placeholder partials and images")
    elif missing:
        say(BAD, "include targets missing: " + "; ".join(missing))
        problems.append("missing include targets")
        fixes.append("python scripts/bootstrap_placeholders.py")
    else:
        say(OK, "all {{< include >}} targets resolve")


def main() -> int:
    fix = "--fix" in sys.argv
    print(f"\nChecking project at: {ROOT}\n" + "-" * 62)
    check_stale_css(fix)
    check_theme(fix)
    check_layers()
    check_includes(fix)
    check_page_cells()
    check_caches(fix)
    print("-" * 62)
    if problems:
        print("\nProblems found:")
        for p in problems:
            print(f"  - {p}")
        print("\nSuggested fixes:")
        for f in dict.fromkeys(fixes):
            print(f"  $ {f}")
        print("\nOr let me do it:  python scripts/doctor.py --fix\n")
        return 1
    print("\nAll clear — `quarto preview` should work.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
