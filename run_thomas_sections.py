#!/usr/bin/env python3
"""Section-level Thomas' Calculus generator — ONE comic per sub-chapter.

Unlike run_thomas_marathon.py (one 6-page comic per whole chapter), this
generates a separate 6-page comic + worksheet for EVERY textbook SECTION
(e.g. Chapter 2 -> 2.1, 2.2, 2.3, 2.4, 2.5, 2.6 = six lessons). Sections and
their exact page ranges are auto-discovered from the textbook's table of
contents, so nothing is hardcoded.

    python run_thomas_sections.py                 # all 77 AP sections (long!)
    python run_thomas_sections.py --chapters 2    # just Ch 2's sections (2.1-2.6)
    python run_thomas_sections.py --chapters 1 2  # Ch 1 and 2
    python run_thomas_sections.py --sections 2.1 2.2
    python run_thomas_sections.py --quality 2K
    python run_thomas_sections.py --list          # preview the section list, no generation

Components-only output (no PDF compile — faster). Per sub-section folder:
  Thomas_Sections/Chapter_NN_<name>/N.M_<title>/
    worksheet.md          (1) student worksheet
    storyboard.json       (2) storyboard
    dialogue.txt          (3) clean dialogue (audio script)
    pages/page_N.png      (4) panel images
    qa.json               (5) QA — per-page + whole-book consistency review

Resumable (sections with pages + qa.json are skipped). Self-learns between
sections via tuning/*.md. There are ~77 AP sections; at ~10-15 min each this
is a multi-hour run — start with one chapter.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import io
import json
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PDF_PATH = ROOT / "source_materials" / "AP_Calculus_Thomas.pdf"
OUT_DIR = ROOT / "Thomas_Sections"

# Chapter -> (name, course). Sections are discovered from the PDF outline.
CHAPTER_META = {
    1:  ("Functions", "AP Calculus AB"),
    2:  ("Limits and Continuity", "AP Calculus AB"),
    3:  ("Derivatives", "AP Calculus AB"),
    4:  ("Applications of Derivatives", "AP Calculus AB"),
    5:  ("Integrals", "AP Calculus AB"),
    6:  ("Applications of Definite Integrals", "AP Calculus AB"),
    7:  ("Transcendental Functions", "AP Calculus AB"),
    8:  ("Techniques of Integration", "AP Calculus BC"),
    9:  ("First-Order Differential Equations", "AP Calculus BC"),
    10: ("Infinite Sequences and Series", "AP Calculus BC"),
    11: ("Parametric Equations and Polar Coordinates", "AP Calculus BC"),
}
# Sections that are software/tool how-tos, not AP math content — skipped.
SKIP_SECTIONS = {(1, 4)}  # 1.4 Graphing with Software

CAST = ["Doraemon", "Nobita"]

# Full AP-relevant section table, transcribed from the textbook's table of
# contents: (chapter, section, title, pdf_page_start). End pages are computed
# from the next section's start. Hardcoded so no PDF-outline library
# (pypdf) is required — the pipeline itself only needs pdfplumber.
SECTIONS_RAW: list[tuple[int, int, str, int]] = [
    (1, 1, "Functions and Their Graphs", 20),
    (1, 2, "Combining Functions; Shifting and Scaling Graphs", 33),
    (1, 3, "Trigonometric Functions", 40),
    (1, 4, "Graphing with Software", 48),
    (2, 1, "Rates of Change and Tangent Lines to Curves", 57),
    (2, 2, "Limit of a Function and Limit Laws", 64),
    (2, 3, "The Precise Definition of a Limit", 75),
    (2, 4, "One-Sided Limits", 84),
    (2, 5, "Continuity", 91),
    (2, 6, "Limits Involving Infinity; Asymptotes of Graphs", 102),
    (3, 1, "Tangent Lines and the Derivative at a Point", 121),
    (3, 2, "The Derivative as a Function", 125),
    (3, 3, "Differentiation Rules", 134),
    (3, 4, "The Derivative as a Rate of Change", 143),
    (3, 5, "Derivatives of Trigonometric Functions", 153),
    (3, 6, "The Chain Rule", 159),
    (3, 7, "Implicit Differentiation", 167),
    (3, 8, "Related Rates", 172),
    (3, 9, "Linearization and Differentials", 181),
    (4, 1, "Extreme Values of Functions on Closed Intervals", 202),
    (4, 2, "The Mean Value Theorem", 210),
    (4, 3, "Monotonic Functions and the First Derivative Test", 216),
    (4, 4, "Concavity and Curve Sketching", 221),
    (4, 5, "Applied Optimization", 233),
    (4, 6, "Newton's Method", 245),
    (4, 7, "Antiderivatives", 250),
    (5, 1, "Area and Estimating with Finite Sums", 267),
    (5, 2, "Sigma Notation and Limits of Finite Sums", 277),
    (5, 3, "The Definite Integral", 284),
    (5, 4, "The Fundamental Theorem of Calculus", 297),
    (5, 5, "Indefinite Integrals and the Substitution Method", 308),
    (5, 6, "Definite Integral Substitutions and the Area Between Curves", 315),
    (6, 1, "Volumes Using Cross-Sections", 333),
    (6, 2, "Volumes Using Cylindrical Shells", 344),
    (6, 3, "Arc Length", 352),
    (6, 4, "Areas of Surfaces of Revolution", 357),
    (6, 5, "Work and Fluid Forces", 363),
    (6, 6, "Moments and Centers of Mass", 372),
    (7, 1, "Inverse Functions and Their Derivatives", 389),
    (7, 2, "Natural Logarithms", 397),
    (7, 3, "Exponential Functions", 405),
    (7, 4, "Exponential Change and Separable Differential Equations", 416),
    (7, 5, "Indeterminate Forms and L'Hopital's Rule", 426),
    (7, 6, "Inverse Trigonometric Functions", 435),
    (7, 7, "Hyperbolic Functions", 447),
    (7, 8, "Relative Rates of Growth", 455),
    (8, 1, "Using Basic Integration Formulas", 466),
    (8, 2, "Integration by Parts", 471),
    (8, 3, "Trigonometric Integrals", 479),
    (8, 4, "Trigonometric Substitutions", 485),
    (8, 5, "Integration of Rational Functions by Partial Fractions", 490),
    (8, 6, "Integral Tables and Computer Algebra Systems", 498),
    (8, 7, "Numerical Integration", 504),
    (8, 8, "Improper Integrals", 513),
    (8, 9, "Probability", 524),
    (9, 1, "Solutions, Slope Fields, and Euler's Method", 545),
    (9, 2, "First-Order Linear Equations", 553),
    (9, 3, "Applications", 559),
    (9, 4, "Graphical Solutions of Autonomous Equations", 565),
    (9, 5, "Systems of Equations and Phase Planes", 572),
    (10, 1, "Sequences", 582),
    (10, 2, "Infinite Series", 595),
    (10, 3, "The Integral Test", 605),
    (10, 4, "Comparison Tests", 611),
    (10, 5, "Absolute Convergence; The Ratio and Root Tests", 616),
    (10, 6, "Alternating Series and Conditional Convergence", 623),
    (10, 7, "Power Series", 630),
    (10, 8, "Taylor and Maclaurin Series", 641),
    (10, 9, "Convergence of Taylor Series", 646),
    (10, 10, "Applications of Taylor Series", 653),
    (11, 1, "Parametrizations of Plane Curves", 668),
    (11, 2, "Calculus with Parametric Curves", 677),
    (11, 3, "Polar Coordinates", 686),
    (11, 4, "Graphing Polar Coordinate Equations", 690),
    (11, 5, "Areas and Lengths in Polar Coordinates", 694),
    (11, 6, "Conic Sections", 699),
    (11, 7, "Conics in Polar Coordinates", 707),
]
# First page after the AP-relevant content (Ch 12 begins here) — bounds the
# last section's page range.
_END_BOUNDARY = 719


def discover_sections() -> list[dict]:
    """Return the AP-relevant sections with computed page ranges.

    Page-end is the page before the next heading (section or chapter), so each
    section gets only its own pages.
    """

    raw = sorted(SECTIONS_RAW, key=lambda s: s[3])
    secs = []
    for i, (ch, sec, title, pg) in enumerate(raw):
        nxt = raw[i + 1][3] if i + 1 < len(raw) else _END_BOUNDARY
        if (ch, sec) in SKIP_SECTIONS or ch not in CHAPTER_META:
            continue
        secs.append({
            "chapter": ch, "section": sec, "title": title,
            "page_start": pg, "page_end": max(pg, nxt - 1),
            "course": CHAPTER_META[ch][1],
        })
    return secs


def slug(text: str, n: int = 44) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")[:n]


def section_dir(s: dict) -> Path:
    ch_name = CHAPTER_META[s["chapter"]][0]
    cdir = OUT_DIR / f"Chapter_{s['chapter']:02d}_{slug(ch_name)}"
    # Clean sub-section folder name: "2.1_Rates_of_Change_and_Tangent_Lines"
    return cdir / f"{s['chapter']}.{s['section']}_{slug(s['title'])}"


def finished(d: Path) -> bool:
    return (d / "qa.json").exists() and (d / "pages" / "page_6.png").exists()


def extract_pages(panels_dir: Path, pages_dir: Path) -> None:
    pages_dir.mkdir(parents=True, exist_ok=True)
    for svg in sorted(panels_dir.glob("scene_*.svg")):
        m = re.search(r"base64,([^\"']+)", svg.read_text(encoding="utf-8"))
        num = re.search(r"(\d+)", svg.stem)
        idx = int(num.group(1)) if num else 0
        if m:
            (pages_dir / f"page_{idx}.png").write_bytes(base64.b64decode(m.group(1)))
        else:
            shutil.copy2(svg, pages_dir / f"page_{idx}.svg")


def organize(run_dir: Path, sdir: Path) -> None:
    """Keep ONLY the 5 core components; merge QA into one qa.json."""

    # (1) worksheet, (2) storyboard, (3) dialogue
    for name in ("worksheet.md", "storyboard.json", "dialogue.txt"):
        src = run_dir / name
        if src.exists():
            shutil.copy2(src, sdir / name)
    # (4) panel images
    if (run_dir / "panels").is_dir():
        extract_pages(run_dir / "panels", sdir / "pages")
    # (5) QA — combine per-page + whole-book review into one file
    qa = {}
    pp = run_dir / "qa_reports.json"
    bk = run_dir / "book_qa.json"
    if pp.exists():
        try:
            qa["pages"] = json.loads(pp.read_text(encoding="utf-8"))
        except Exception:
            qa["pages"] = []
    if bk.exists():
        try:
            qa["book"] = json.loads(bk.read_text(encoding="utf-8"))
        except Exception:
            qa["book"] = {}
    if qa.get("pages"):
        scores = [r.get("consistency_score", 0) for r in qa["pages"]]
        qa["summary"] = {
            "page_avg": round(sum(scores) / len(scores), 1) if scores else None,
            "page_min": min(scores) if scores else None,
            "book_consistency": qa.get("book", {}).get("consistency_score"),
        }
    (sdir / "qa.json").write_text(json.dumps(qa, indent=2), encoding="utf-8")


class _Tee(io.TextIOBase):
    def __init__(self, *s): self._s = s
    def write(self, x):
        for st in self._s:
            try: st.write(x)
            except Exception: pass
        return len(x)
    def flush(self):
        for st in self._s:
            try: st.flush()
            except Exception: pass


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chapters", nargs="*", type=int, help="limit to these chapters")
    ap.add_argument("--sections", nargs="*", help="limit to e.g. 2.1 2.2")
    ap.add_argument("--quality", default="1K", choices=["1K", "2K", "4K"])
    ap.add_argument("--provider", default="auto", choices=["auto", "anthropic", "gemini"])
    ap.add_argument("--max-pages", type=int, default=14, help="textbook pages per section")
    ap.add_argument("--no-learn", action="store_true")
    ap.add_argument("--list", action="store_true", help="just print the section plan")
    args = ap.parse_args()

    if not PDF_PATH.exists():
        print(f"Textbook missing: {PDF_PATH}"); return 1

    secs = discover_sections()
    if args.chapters:
        secs = [s for s in secs if s["chapter"] in args.chapters]
    if args.sections:
        want = set(args.sections)
        secs = [s for s in secs if f"{s['chapter']}.{s['section']}" in want]

    if not secs:
        print("No matching sections."); return 1

    if args.list:
        cur = None
        for s in secs:
            if s["chapter"] != cur:
                cur = s["chapter"]
                print(f"\nChapter {cur} — {CHAPTER_META[cur][0]} ({CHAPTER_META[cur][1]})")
            print(f"  {s['chapter']}.{s['section']}  p{s['page_start']}-{s['page_end']}  {s['title']}")
        print(f"\n{len(secs)} sections. Est. ~{len(secs)*15//60}h-{len(secs)*18//60}h at 1K.")
        return 0

    sys.path.insert(0, str(ROOT))
    from curriculum_to_comic.agent import ComicAgent
    from curriculum_to_comic.config import SETTINGS
    from curriculum_to_comic.extractors import from_pdf

    OUT_DIR.mkdir(exist_ok=True)
    done = skipped = failed = 0
    t0all = time.time()

    for s in secs:
        sec_id = f"{s['chapter']}.{s['section']}"
        sdir = section_dir(s)
        if finished(sdir):
            log(f"{sec_id} '{s['title']}' already done — skipping"); skipped += 1; continue

        sdir.mkdir(parents=True, exist_ok=True)
        hi = min(s["page_end"], s["page_start"] + args.max_pages - 1)
        log(f"=== {sec_id}: {s['title']} ({s['course']}) · pages {s['page_start']}-{hi} ===")
        t0 = time.time()
        run_root = sdir / "_run"
        try:
            agent = ComicAgent(
                output_dir=run_root, provider=args.provider, cast=CAST,
                run_qa=True, qa_retries=1, image_quality=args.quality,
                compile_pdf_output=False,  # components-only: skip PDF for speed
            )
            topic = f"Thomas Section {sec_id}: {s['title']}"
            curriculum = from_pdf(
                PDF_PATH, topic=topic, grade_level=s["course"],
                page_range=(s["page_start"], hi), client=agent.claude,
                on_status=lambda m: print(f"  [pdf] {m}"),
            )
            result = agent.run(curriculum)
            organize(Path(result.book.run_dir), sdir)
            shutil.rmtree(run_root, ignore_errors=True)  # drop intermediates
            done += 1
            log(f"{sec_id} done in {(time.time()-t0)/60:.1f} min -> {sdir.relative_to(ROOT)}")
        except KeyboardInterrupt:
            log("Interrupted — rerun to resume."); return 130
        except Exception as exc:
            failed += 1
            log(f"{sec_id} FAILED: {exc} (continuing)")
            try:  # salvage whatever was produced, then clean intermediates
                rr = run_root / "runs"
                if rr.is_dir():
                    organize(max(rr.iterdir(), key=lambda p: p.stat().st_mtime), sdir)
                shutil.rmtree(run_root, ignore_errors=True)
            except Exception:
                pass

    log(f"Sections finished: {done} done, {skipped} skipped, {failed} failed "
        f"in {(time.time()-t0all)/60:.0f} min")
    log(f"Outputs: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
