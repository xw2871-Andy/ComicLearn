#!/usr/bin/env python3
"""Generate Chapter 1 (AP Calculus AB Unit 1: Limits and Continuity).

One command produces a 6-page Doraemon comic + student worksheet per lesson,
organized under Chapter_1_Limits/:

    python generate_chapter1.py              # full chapter (resumable)
    python generate_chapter1.py --only 1.1   # pilot a single lesson
    python generate_chapter1.py --from 1.4   # resume from lesson 1.4
    python generate_chapter1.py --no-qa      # skip the QA subagent

The script is RESUMABLE: lessons whose folder already contains a finished PDF
are skipped, so you can stop (Ctrl+C) and rerun at any time.
"""

from __future__ import annotations

import argparse
import base64
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAPTER_DIR = ROOT / "Chapter_1_Limits"

# ----------------------------------------------------------------- lessons #

LESSONS = [
    ("1.1", "Introducing Calculus: Can Change Occur at an Instant?",
     "Average vs instantaneous rate of change; why limits are needed; "
     "speedometer/odometer intuition (CED 1.1)"),
    ("1.2", "Defining Limits and Using Limit Notation",
     "Intuitive definition of a limit; lim_{x->c} f(x) = L notation; "
     "one-sided limits (CED 1.2)"),
    ("1.3", "Estimating Limit Values from Graphs and Tables",
     "Reading limits off graphs (holes, jumps) and numeric tables; when a "
     "limit does not exist (CED 1.3-1.4)"),
    ("1.4", "Determining Limits Using Algebraic Properties",
     "Limit laws: sum, product, quotient, composition; evaluating by direct "
     "substitution (CED 1.5-1.6)"),
    ("1.5", "Determining Limits Using Algebraic Manipulation",
     "Factoring and canceling 0/0 forms, rationalizing with conjugates, "
     "simplifying complex fractions (CED 1.6-1.7)"),
    ("1.6", "Squeeze Theorem and Special Trig Limits",
     "Squeeze theorem; lim_{x->0} sin(x)/x = 1 and (1-cos x)/x = 0 "
     "(CED 1.8-1.9)"),
    ("1.7", "Continuity, Discontinuities, and Removing Them",
     "Continuity at a point and on intervals; removable, jump, and infinite "
     "discontinuities; redefining f to remove a hole (CED 1.10-1.13)"),
    ("1.8", "Infinite Limits, Limits at Infinity, and Asymptotes",
     "Vertical and horizontal asymptotes via infinite limits and limits at "
     "infinity; end behavior of rational functions (CED 1.14-1.15)"),
    ("1.9", "Intermediate Value Theorem",
     "IVT statement, hypotheses (continuity on [a,b]), and using it to "
     "guarantee roots; Unit 1 capstone recap (CED 1.16)"),
]

GRADE = "AP Calculus AB"
CAST = ["Doraemon", "Nobita"]


# ------------------------------------------------------------------ helpers #

def slug(num: str, title: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_")
    return f"{num}_{s[:48]}".rstrip("_")


def extract_pages_as_png(panels_dir: Path, pages_dir: Path) -> int:
    """Pull the embedded PNGs out of the SVG wrappers for easy viewing."""

    pages_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for svg_file in sorted(panels_dir.glob("scene_*.svg")):
        m = re.search(r"base64,([^\"']+)", svg_file.read_text(encoding="utf-8"))
        num = re.search(r"(\d+)", svg_file.stem)
        idx = int(num.group(1)) if num else n + 1
        if m:
            (pages_dir / f"page_{idx}.png").write_bytes(
                base64.b64decode(m.group(1))
            )
        else:  # SVG-backend panel: keep the vector file
            shutil.copy2(svg_file, pages_dir / f"page_{idx}.svg")
        n += 1
    return n


def organize(run_dir: Path, lesson_dir: Path) -> None:
    lesson_dir.mkdir(parents=True, exist_ok=True)
    for name in ("worksheet.md", "storyboard.json", "dialogue.txt",
                 "lesson.json", "qa_reports.json", "book.json"):
        src = run_dir / name
        if src.exists():
            shutil.copy2(src, lesson_dir / name)
    for pdf in run_dir.glob("*_comic.pdf"):
        shutil.copy2(pdf, lesson_dir / pdf.name)
    panels = run_dir / "panels"
    if panels.is_dir():
        extract_pages_as_png(panels, lesson_dir / "pages")


def mark_done(num: str) -> None:
    wp = CHAPTER_DIR / "WORKPLAN.md"
    if not wp.exists():
        return
    text = wp.read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines():
        if line.startswith(f"| {num} |") and "| pending |" in line:
            line = line.replace("| pending |", "| done |")
        lines.append(line)
    wp.write_text("\n".join(lines) + "\n", encoding="utf-8")


def lesson_finished(lesson_dir: Path) -> bool:
    return lesson_dir.is_dir() and any(lesson_dir.glob("*_comic.pdf"))


# --------------------------------------------------------------------- main #

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", help="generate a single lesson, e.g. --only 1.1")
    ap.add_argument("--from", dest="start", help="start from lesson N, e.g. --from 1.4")
    ap.add_argument("--no-qa", action="store_true", help="skip the QA subagent")
    ap.add_argument("--provider", default="auto",
                    choices=["auto", "anthropic", "gemini"])
    ap.add_argument("--quality", default="2K", choices=["1K", "2K", "4K"],
                    help="image quality: 1K draft (fast/cheap), 2K standard, 4K print")
    args = ap.parse_args()

    sys.path.insert(0, str(ROOT))
    from curriculum_to_comic.agent import ComicAgent
    from curriculum_to_comic.extractors import from_topic

    todo = LESSONS
    if args.only:
        todo = [l for l in LESSONS if l[0] == args.only]
        if not todo:
            print(f"No lesson {args.only}. Choices: {[l[0] for l in LESSONS]}")
            return 1
    elif args.start:
        nums = [l[0] for l in LESSONS]
        if args.start not in nums:
            print(f"No lesson {args.start}. Choices: {nums}")
            return 1
        todo = LESSONS[nums.index(args.start):]

    CHAPTER_DIR.mkdir(exist_ok=True)
    t_chapter = time.time()
    done, skipped, failed = [], [], []

    for num, title, focus in todo:
        lesson_dir = CHAPTER_DIR / slug(num, title)
        if lesson_finished(lesson_dir):
            print(f"== {num} already finished — skipping ({lesson_dir.name})")
            skipped.append(num)
            continue

        print(f"\n=== Lesson {num}: {title} ===")
        t0 = time.time()
        try:
            agent = ComicAgent(
                output_dir=CHAPTER_DIR / "_runs",
                provider=args.provider,
                cast=CAST,
                run_qa=not args.no_qa,
                qa_retries=1,
                image_quality=args.quality,
            )
            topic = f"Unit {num} - {title}. Focus: {focus}"
            result = agent.run(from_topic(topic, GRADE))
            organize(Path(result.book.run_dir), lesson_dir)
            mark_done(num)
            done.append(num)
            print(f"=== {num} done in {(time.time()-t0)/60:.1f} min "
                  f"-> {lesson_dir.relative_to(ROOT)}")
        except KeyboardInterrupt:
            print("\nInterrupted — rerun this script to resume where you left off.")
            return 130
        except Exception as exc:
            failed.append(num)
            print(f"!!! {num} FAILED: {exc}\n    (rerun the script to retry)")

    print(f"\nChapter summary: {len(done)} generated, {len(skipped)} skipped, "
          f"{len(failed)} failed in {(time.time()-t_chapter)/60:.1f} min")
    if failed:
        print("Failed lessons:", ", ".join(failed))
    print(f"Outputs: {CHAPTER_DIR}")
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
