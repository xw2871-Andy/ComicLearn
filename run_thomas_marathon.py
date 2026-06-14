#!/usr/bin/env python3
"""Autonomous Thomas' Calculus test marathon — zero clicking required.

One command tests EVERY AP-relevant chapter of Thomas' Calculus (14th ed,
source_materials/AP_Calculus_Thomas.pdf), runs the full pipeline per chapter
(PDF extract -> lesson -> worksheet -> storyboard -> story QA -> pages drawn
one-by-one -> per-page QA -> book QA -> comic PDF), saves EVERYTHING under
Thomas_Tests/, and SELF-LEARNS between chapters: each chapter's QA issues are
distilled into tuning rules (tuning/*.md) that every later chapter
automatically uses. A scoreboard report shows whether quality climbs.

    python run_thomas_marathon.py                  # all chapters, 1K draft
    python run_thomas_marathon.py --quality 2K     # final quality
    python run_thomas_marathon.py --chapters 2 3   # subset
    python run_thomas_marathon.py --no-learn       # disable tuning updates

Resumable: chapters with a finished comic PDF are skipped on rerun.

Per chapter, Thomas_Tests/Chapter_NN_<name>/ contains:
    params.json     title/topic, grade/course, text engine, image quality,
                    thresholds, tuning state, page range, timings
    progress.log    full timestamped pipeline log
    worksheet.md, storyboard.json, dialogue.txt
    story_qa.json, qa_reports.json, book_qa.json
    pages/page_N.png and the final *_comic.pdf
    issues.json     everything the reviewers flagged (feeds the learning loop)
"""

from __future__ import annotations

import argparse
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
TESTS_DIR = ROOT / "Thomas_Tests"
TUNING_DIR = ROOT / "tuning"
MAX_TUNING_RULES = 30  # cap per file so prompts never bloat

# Chapter -> (title, pdf_page_start, pdf_page_end, course, focus)
CHAPTERS = {
    1:  ("Functions", 20, 56, "AP Calculus AB",
         "Functions and their graphs, combining/shifting/scaling, trig functions"),
    2:  ("Limits and Continuity", 57, 120, "AP Calculus AB",
         "Rates of change, limit laws, one-sided limits, continuity, asymptotes"),
    3:  ("Derivatives", 121, 201, "AP Calculus AB",
         "Derivative at a point and as a function, rules, chain rule, implicit, related rates"),
    4:  ("Applications of Derivatives", 202, 266, "AP Calculus AB",
         "Extreme values, MVT, first/second derivative tests, curve sketching, optimization, antiderivatives"),
    5:  ("Integrals", 267, 332, "AP Calculus AB",
         "Riemann sums, definite integral, Fundamental Theorem of Calculus, substitution"),
    6:  ("Applications of Definite Integrals", 333, 388, "AP Calculus AB",
         "Volumes by cross-sections and shells, arc length"),
    7:  ("Transcendental Functions", 389, 465, "AP Calculus AB",
         "Inverse functions, logs and exponentials, L'Hopital's rule, inverse trig"),
    8:  ("Techniques of Integration", 466, 544, "AP Calculus BC",
         "Integration by parts, partial fractions, improper integrals"),
    9:  ("First-Order Differential Equations", 545, 581, "AP Calculus BC",
         "Slope fields, Euler's method, separable and logistic equations"),
    10: ("Infinite Sequences and Series", 582, 667, "AP Calculus BC",
         "Sequences, series convergence tests, power series, Taylor and Maclaurin series"),
    11: ("Parametric Equations and Polar Coordinates", 668, 718, "AP Calculus BC",
         "Parametric curves and their calculus, polar coordinates, polar areas"),
}

CAST = ["Doraemon", "Nobita"]


# ------------------------------------------------------------------ helpers #

class _Tee(io.TextIOBase):
    def __init__(self, *streams):
        self._streams = streams

    def write(self, s):
        for st in self._streams:
            try:
                st.write(s)
            except Exception:
                pass
        return len(s)

    def flush(self):
        for st in self._streams:
            try:
                st.flush()
            except Exception:
                pass


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def chapter_dir_for(num: int) -> Path:
    title = CHAPTERS[num][0]
    s = re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_")[:44]
    return TESTS_DIR / f"Chapter_{num:02d}_{s}"


def finished(cdir: Path) -> bool:
    return cdir.is_dir() and any(cdir.glob("*_comic.pdf"))


def extract_pages_as_png(panels_dir: Path, pages_dir: Path) -> None:
    pages_dir.mkdir(parents=True, exist_ok=True)
    import base64

    for svg_file in sorted(panels_dir.glob("scene_*.svg")):
        m = re.search(r"base64,([^\"']+)", svg_file.read_text(encoding="utf-8"))
        n = re.search(r"(\d+)", svg_file.stem)
        idx = int(n.group(1)) if n else 0
        if m:
            (pages_dir / f"page_{idx}.png").write_bytes(base64.b64decode(m.group(1)))
        else:
            shutil.copy2(svg_file, pages_dir / f"page_{idx}.svg")


def organize(run_dir: Path, cdir: Path) -> None:
    for name in ("worksheet.md", "storyboard.json", "dialogue.txt",
                 "lesson.json", "story_qa.json", "qa_reports.json",
                 "book_qa.json", "book.json"):
        src = run_dir / name
        if src.exists():
            shutil.copy2(src, cdir / name)
    for pdf in run_dir.glob("*_comic.pdf"):
        shutil.copy2(pdf, cdir / pdf.name)
    panels = run_dir / "panels"
    if panels.is_dir():
        extract_pages_as_png(panels, cdir / "pages")


def collect_issues(cdir: Path) -> dict:
    """Everything reviewers flagged for this chapter, for the learning loop."""

    out = {"story": [], "visual": [], "book": [], "scores": {}}
    try:
        sq = json.loads((cdir / "story_qa.json").read_text(encoding="utf-8"))
        out["story"] = sq.get("issues", [])
        out["scores"]["story_flow"] = sq.get("final_flow_score")
        out["scores"]["story_revised"] = sq.get("revised")
    except Exception:
        pass
    try:
        qrs = json.loads((cdir / "qa_reports.json").read_text(encoding="utf-8"))
        scores = [r.get("consistency_score", 0) for r in qrs]
        out["scores"]["page_qa_avg"] = round(sum(scores) / len(scores), 1) if scores else None
        out["scores"]["page_qa_min"] = min(scores) if scores else None
        out["scores"]["pages_redrawn"] = sum(1 for r in qrs if r.get("retry_count", 0) > 0)
        for r in qrs:
            for i in r.get("issues", []):
                if not i.startswith("QA reviewer call failed"):
                    out["visual"].append(f"scene {r.get('scene_number')}: {i}")
    except Exception:
        pass
    try:
        bq = json.loads((cdir / "book_qa.json").read_text(encoding="utf-8"))
        out["scores"]["book_consistency"] = bq.get("consistency_score")
        out["scores"]["book_regens"] = len(bq.get("regenerated_pages", []))
        for pr in bq.get("page_reports", []):
            for i in pr.get("issues", []):
                out["book"].append(f"page {pr.get('page')}: {i}")
    except Exception:
        pass
    return out


# ------------------------------------------------------------ learning loop #

META_IMPROVE_SYSTEM = """You are the lead engineer of an educational comic
agent. You receive the QA findings from ONE generated comic chapter:
story-editor issues, per-page visual QA issues, and whole-book consistency
issues.

Distill them into ADDITIVE prompt rules that would prevent these specific
failures in FUTURE chapters. Imperative, concrete, max 5 rules per category,
no rules that merely restate obvious existing guidance.

Return ONLY this JSON, no fences:
{"storyboard_rules": [str, ...], "image_rules": [str, ...], "summary": str}"""


def learn_from(issues: dict, client, chapter_label: str) -> dict:
    payload = {
        "story_editor_issues": issues["story"][:20],
        "visual_qa_issues": issues["visual"][:30],
        "book_consistency_issues": issues["book"][:30],
    }
    if not any(payload.values()):
        return {"storyboard_rules": [], "image_rules": [], "summary": "no issues"}
    try:
        tuning = client.complete_json(
            system=META_IMPROVE_SYSTEM,
            user=f"Findings from {chapter_label}:\n{json.dumps(payload, indent=2)}",
            max_tokens=1500,
            temperature=0.3,
        )
    except Exception as exc:
        return {"storyboard_rules": [], "image_rules": [],
                "summary": f"learning call failed: {exc}"}
    for key, fname in (("storyboard_rules", "storyboard.md"),
                       ("image_rules", "image.md")):
        rules = [str(r).strip() for r in tuning.get(key, []) if str(r).strip()]
        if rules:
            _append_tuning(TUNING_DIR / fname, rules, chapter_label)
    return tuning


def _append_tuning(f: Path, new_rules: list[str], label: str) -> None:
    """Append deduped rules; keep only the newest MAX_TUNING_RULES bullets."""

    TUNING_DIR.mkdir(exist_ok=True)
    existing_lines = f.read_text(encoding="utf-8").splitlines() if f.exists() else []
    existing_rules = [l for l in existing_lines if l.startswith("- ")]
    seen = {l[2:].strip().lower() for l in existing_rules}
    added = [f"- {r}" for r in new_rules if r.lower() not in seen]
    if not added:
        return
    rules = (existing_rules + added)[-MAX_TUNING_RULES:]
    f.write_text(
        f"<!-- auto-tuned; latest from {label} {time.strftime('%Y-%m-%d %H:%M')} -->\n"
        + "\n".join(rules) + "\n",
        encoding="utf-8",
    )


# ------------------------------------------------------------------- report #

def write_report(rows: list[dict]) -> Path:
    lines = [
        "# Thomas' Calculus Test Marathon — Scoreboard",
        "",
        f"Updated: {time.strftime('%Y-%m-%d %H:%M')}",
        "",
        "| Ch | Title | Course | Story flow | Page QA avg/min | Book | Redraws | Time | Status |",
        "|----|-------|--------|-----------|-----------------|------|---------|------|--------|",
    ]
    for r in rows:
        sc = r.get("scores", {})
        lines.append(
            f"| {r['num']} | {r['title'][:34]} | {r['course'].split()[-1]} "
            f"| {sc.get('story_flow', '—')}{' (rev)' if sc.get('story_revised') else ''} "
            f"| {sc.get('page_qa_avg', '—')}/{sc.get('page_qa_min', '—')} "
            f"| {sc.get('book_consistency', '—')} "
            f"| {sc.get('pages_redrawn', 0) or 0}+{sc.get('book_regens', 0) or 0} "
            f"| {r.get('minutes', '—')}m | {r['status']} |"
        )
    lines += [
        "",
        "Redraws column = per-page QA redraws + book-QA redraws.",
        "Self-learning: after each chapter, reviewer findings are distilled into",
        "tuning/storyboard.md and tuning/image.md, which all later chapters load",
        "automatically. Rising scores across rows = the loop is working.",
        "",
        "## Learning log",
        "",
    ]
    for r in rows:
        if r.get("learned_summary"):
            lines.append(f"- After Ch {r['num']}: {r['learned_summary']}")
    path = TESTS_DIR / "marathon_report.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------- main #

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chapters", nargs="*", type=int,
                    help=f"subset, e.g. --chapters 2 3 (default: all {sorted(CHAPTERS)})")
    ap.add_argument("--quality", default="1K", choices=["1K", "2K", "4K"],
                    help="image quality (default 1K for the test marathon)")
    ap.add_argument("--provider", default="auto",
                    choices=["auto", "anthropic", "gemini"])
    ap.add_argument("--max-pages", type=int, default=30,
                    help="cap textbook pages extracted per chapter (default 30)")
    ap.add_argument("--no-learn", action="store_true",
                    help="disable the between-chapter tuning updates")
    ap.add_argument("--no-review", action="store_true",
                    help="skip the holistic review-and-improve pass at the end")
    args = ap.parse_args()

    if not PDF_PATH.exists():
        print(f"Textbook missing: {PDF_PATH}")
        return 1

    sys.path.insert(0, str(ROOT))
    from curriculum_to_comic.agent import ComicAgent
    from curriculum_to_comic.config import SETTINGS
    from curriculum_to_comic.extractors import from_pdf

    nums = args.chapters or sorted(CHAPTERS)
    bad = [n for n in nums if n not in CHAPTERS]
    if bad:
        print(f"Unknown chapters {bad}. Valid: {sorted(CHAPTERS)}")
        return 1

    TESTS_DIR.mkdir(exist_ok=True)
    rows: list[dict] = []
    t_marathon = time.time()

    for n in nums:
        title, p_lo, p_hi, course, focus = CHAPTERS[n]
        cdir = chapter_dir_for(n)
        row = {"num": n, "title": title, "course": course, "status": "pending"}
        rows.append(row)

        if finished(cdir):
            log(f"Ch {n} '{title}' already finished — skipping")
            row["status"] = "done (cached)"
            row["scores"] = collect_issues(cdir)["scores"]
            write_report(rows)
            continue

        cdir.mkdir(parents=True, exist_ok=True)
        hi = min(p_hi, p_lo + args.max_pages - 1)
        t0 = time.time()
        log(f"=== Ch {n}: {title} ({course}) · textbook pages {p_lo}-{hi} ===")

        progress = (cdir / "progress.log").open("a", encoding="utf-8")
        tee = _Tee(sys.stdout, progress)
        try:
            with contextlib.redirect_stdout(tee):
                agent = ComicAgent(
                    output_dir=cdir / "_run",
                    provider=args.provider,
                    cast=CAST,
                    run_qa=True,
                    qa_retries=1,
                    image_quality=args.quality,
                )
                params = {
                    "chapter": n,
                    "title_topic": f"Thomas Ch {n}: {title}",
                    "grade_course": course,
                    "text_engine": agent.provider,
                    "image_engine": "Nano Banana Pro "
                                    f"({SETTINGS.gemini_image_model})",
                    "image_quality": args.quality,
                    "qa_score_threshold": SETTINGS.qa_score_threshold,
                    "source": f"{PDF_PATH.name} pages {p_lo}-{hi}",
                    "tuning_active": sorted(
                        p.name for p in TUNING_DIR.glob("*.md")
                    ) if TUNING_DIR.is_dir() else [],
                    "started": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                (cdir / "params.json").write_text(
                    json.dumps(params, indent=2), encoding="utf-8")

                curriculum = from_pdf(
                    PDF_PATH,
                    topic=f"Thomas Ch {n}: {title} — {focus}",
                    grade_level=course,
                    page_range=(p_lo, hi),
                    client=agent.claude,
                    on_status=lambda m: print(f"  [pdf] {m}"),
                )
                result = agent.run(curriculum)

            run_dir = Path(result.book.run_dir)
            organize(run_dir, cdir)
            issues = collect_issues(cdir)
            (cdir / "issues.json").write_text(
                json.dumps(issues, indent=2), encoding="utf-8")
            row["scores"] = issues["scores"]
            row["minutes"] = round((time.time() - t0) / 60, 1)
            row["status"] = "done"
            params["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
            params["minutes"] = row["minutes"]
            (cdir / "params.json").write_text(
                json.dumps(params, indent=2), encoding="utf-8")
            log(f"Ch {n} done in {row['minutes']} min · scores: {row['scores']}")

            # ---- self-learning between chapters ---- #
            if not args.no_learn:
                tuned = learn_from(issues, agent.claude, f"Chapter {n} ({title})")
                row["learned_summary"] = tuned.get("summary", "")
                nrules = len(tuned.get("storyboard_rules", [])) + len(
                    tuned.get("image_rules", []))
                if nrules:
                    log(f"learned {nrules} new tuning rule(s) -> next chapters "
                        f"use them automatically")
        except KeyboardInterrupt:
            row["status"] = "interrupted"
            write_report(rows)
            print("\nInterrupted — rerun to resume from this chapter.")
            return 130
        except Exception as exc:
            row["status"] = f"FAILED: {str(exc)[:80]}"
            log(f"Ch {n} FAILED: {exc} (continuing with next chapter)")
            # Salvage partial work: copy whatever artifacts the run already
            # produced (lesson/worksheet/storyboard/pages) so a late failure
            # — e.g. a network blip during rendering — doesn't discard the
            # minutes of text generation already completed.
            try:
                runs_root = cdir / "_run" / "runs"
                if runs_root.is_dir():
                    latest = max(runs_root.iterdir(), key=lambda p: p.stat().st_mtime)
                    organize(latest, cdir)
                    salvaged = sorted(
                        p.name for p in cdir.iterdir()
                        if p.suffix in {".md", ".json", ".txt"}
                    )
                    if salvaged:
                        log(f"   salvaged partial artifacts: {salvaged}")
            except Exception:
                pass
        finally:
            progress.close()
        write_report(rows)

    report = write_report(rows)
    done = sum(1 for r in rows if str(r["status"]).startswith("done"))
    log(f"Marathon finished: {done}/{len(rows)} chapters in "
        f"{(time.time() - t_marathon) / 60:.0f} min")
    log(f"Scoreboard: {report}")

    # Holistic review-and-improve pass over ALL chapters: consolidate the
    # noisy per-chapter tuning into a clean, evidence-backed rule set and
    # write the improvement report. Fully automatic (the "whole round of QA").
    if not args.no_review and done >= 2 and not args.no_learn:
        log("Running holistic review-and-improve pass over all chapters…")
        try:
            from review_marathon import run_review
            run_review(provider=args.provider, apply=True)
        except Exception as exc:
            log(f"Review pass skipped ({exc}); run review_marathon.py manually.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
