#!/usr/bin/env python3
"""Post-marathon QA review & agent self-improvement (consolidation pass).

Run this AFTER the chapter marathon. It does the "whole round of QA" you'd do
by hand, but over every chapter at once:

  1. Aggregates QA evidence from all Thomas_Tests/Chapter_*/ outputs
     (story_qa, per-page qa_reports, book_qa) into hard metrics + the most
     frequent recurring issues.
  2. Has a "principal engineer" LLM pass study that evidence and produce a
     CLEAN, consolidated, deduplicated set of tuning rules (replacing the
     noisy per-chapter accumulation) PLUS concrete recommended edits to the
     base prompts and OpenClaw skills.
  3. Writes Thomas_Tests/REVIEW_AND_IMPROVE.md (the report) and, with
     --apply, rewrites tuning/storyboard.md and tuning/image.md with the
     consolidated rules so every future run is improved.

    python review_marathon.py            # analyze + write report (safe)
    python review_marathon.py --apply    # also rewrite tuning/*.md

Unlike the per-chapter learning (additive, runs DURING the marathon), this is
a holistic refactor: it throws away redundant rules and keeps only the
highest-signal guidance backed by evidence across the whole textbook.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TESTS_DIR = ROOT / "Thomas_Tests"
TUNING_DIR = ROOT / "tuning"


PRINCIPAL_SYSTEM = """You are the principal engineer of an educational comic
generation agent (textbook -> 6-page Doraemon manga that teaches a math
chapter). You are doing a HOLISTIC quality review after generating many
chapters. You receive aggregate metrics and the most frequent QA issues from
three reviewers: a story-flow editor, a per-page visual QA, and a whole-book
consistency reviewer.

Your job: find the SYSTEMIC weaknesses (problems that recur across chapters,
not one-off flukes) and fix them at the source. Produce:

1. A small, CLEAN, deduplicated set of tuning rules that would most improve
   future runs — these REPLACE all prior accumulated rules, so include only
   the highest-signal, evidence-backed ones. Imperative and concrete.
2. Concrete recommended edits to the BASE prompts (storyboard system prompt,
   image-prompt anchors, the visual-QA rubric, the story-flow rubric) and to
   the OpenClaw skills — phrased as specific "change X to Y / add Z" notes a
   developer can apply by hand.
3. A prioritized diagnosis: the top 3 root causes limiting quality and what
   to do about each.

Be evidence-driven: tie every recommendation to a pattern in the data. Prefer
fewer, sharper rules over many vague ones.

Return ONLY this JSON, no fences:
{
  "diagnosis": str,
  "top_root_causes": [ {"cause": str, "evidence": str, "fix": str}, ... ],
  "consolidated_storyboard_rules": [str, ...],
  "consolidated_image_rules": [str, ...],
  "base_prompt_edits": [ {"target": str, "change": str, "why": str}, ... ],
  "skill_edits": [ {"skill": str, "change": str}, ... ]
}"""


def _load(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _theme(issue: str) -> str:
    """Coarse-bucket an issue string so we can count recurring themes."""

    s = issue.lower()
    buckets = {
        "character drift / off-model": ["on-model", "off-model", "bell", "collar",
                                        "proportion", "character design", "face"],
        "text / bubble legibility": ["bubble", "text", "spell", "garbled",
                                     "legib", "truncat", "dialogue"],
        "math overlay accuracy": ["math", "formula", "notation", "equation",
                                  "overlay", "latex"],
        "palette / style shift": ["palette", "color", "style", "linework", "shade"],
        "panel density / layout": ["panel", "density", "gutter", "layout", "row"],
        "story flow / bridging": ["bridge", "abrupt", "jump", "flow", "transition",
                                  "intro", "pre-knowledge", "recall"],
        "scene fidelity": ["fidelity", "missing", "depict", "background", "setting"],
    }
    for name, kws in buckets.items():
        if any(k in s for k in kws):
            return name
    return "other"


def aggregate() -> dict:
    chapters = sorted(
        d for d in TESTS_DIR.glob("Chapter_*") if d.is_dir()
    ) if TESTS_DIR.is_dir() else []
    rows, all_issues = [], []
    story_flows, page_avgs, page_mins, book_scores = [], [], [], []
    theme_counter = collections.Counter()

    for cdir in chapters:
        issues = _load(cdir / "issues.json") or {}
        sc = issues.get("scores", {})
        if not sc and not (cdir / "qa_reports.json").exists():
            continue  # chapter never finished
        rows.append({"chapter": cdir.name, "scores": sc})
        if isinstance(sc.get("story_flow"), int):
            story_flows.append(sc["story_flow"])
        if isinstance(sc.get("page_qa_avg"), (int, float)):
            page_avgs.append(sc["page_qa_avg"])
        if isinstance(sc.get("page_qa_min"), int):
            page_mins.append(sc["page_qa_min"])
        if isinstance(sc.get("book_consistency"), int):
            book_scores.append(sc["book_consistency"])
        for kind in ("story", "visual", "book"):
            for it in issues.get(kind, []):
                all_issues.append(it)
                theme_counter[_theme(it)] += 1

    avg = lambda xs: round(statistics.mean(xs), 1) if xs else None
    return {
        "chapters_analyzed": len(rows),
        "rows": rows,
        "metrics": {
            "story_flow_avg": avg(story_flows),
            "page_qa_avg": avg(page_avgs),
            "page_qa_min_avg": avg(page_mins),
            "book_consistency_avg": avg(book_scores),
            "book_below_75": sum(1 for s in book_scores if s < 75),
            "chapters_with_book_score": len(book_scores),
        },
        "top_themes": theme_counter.most_common(),
        "issue_samples": all_issues[:60],
    }


def write_report(agg: dict, improve: dict, applied: bool) -> Path:
    m = agg["metrics"]
    lines = [
        "# Post-Marathon QA Review & Improvement Plan",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M')} · "
        f"chapters analyzed: {agg['chapters_analyzed']}",
        "",
        "## Aggregate quality metrics",
        "",
        f"- Story-flow avg: **{m['story_flow_avg']}**",
        f"- Per-page QA avg: **{m['page_qa_avg']}** (worst-page avg {m['page_qa_min_avg']})",
        f"- Book-consistency avg: **{m['book_consistency_avg']}** "
        f"({m['book_below_75']}/{m['chapters_with_book_score']} chapters below 75)",
        "",
        "## Most frequent issue themes (across all chapters)",
        "",
    ]
    for theme, count in agg["top_themes"]:
        lines.append(f"- {theme}: {count}")
    lines += ["", "## Diagnosis", "", improve.get("diagnosis", "—"), "",
              "## Top root causes", ""]
    for rc in improve.get("top_root_causes", []):
        lines.append(f"### {rc.get('cause','')}")
        lines.append(f"- Evidence: {rc.get('evidence','')}")
        lines.append(f"- Fix: {rc.get('fix','')}")
        lines.append("")
    lines += ["## Recommended base-prompt edits (apply by hand)", ""]
    for e in improve.get("base_prompt_edits", []):
        lines.append(f"- **{e.get('target','')}**: {e.get('change','')}  \n"
                     f"  _why: {e.get('why','')}_")
    lines += ["", "## Recommended skill edits", ""]
    for e in improve.get("skill_edits", []):
        lines.append(f"- **{e.get('skill','')}**: {e.get('change','')}")
    lines += [
        "",
        "## Consolidated tuning rules "
        + ("(WRITTEN to tuning/*.md — active now)" if applied
           else "(run with --apply to activate)"),
        "",
        "### Storyboard",
        *[f"- {r}" for r in improve.get("consolidated_storyboard_rules", [])],
        "",
        "### Image",
        *[f"- {r}" for r in improve.get("consolidated_image_rules", [])],
        "",
    ]
    path = TESTS_DIR / "REVIEW_AND_IMPROVE.md"
    TESTS_DIR.mkdir(exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def apply_tuning(improve: dict) -> list[str]:
    TUNING_DIR.mkdir(exist_ok=True)
    written = []
    stamp = f"<!-- consolidated by review_marathon {time.strftime('%Y-%m-%d %H:%M')} -->\n"
    for key, fname in (("consolidated_storyboard_rules", "storyboard.md"),
                       ("consolidated_image_rules", "image.md")):
        rules = [str(r).strip() for r in improve.get(key, []) if str(r).strip()]
        if not rules:
            continue
        f = TUNING_DIR / fname
        # Back up the noisy accumulated version before replacing it.
        if f.exists():
            f.with_suffix(".md.bak").write_text(
                f.read_text(encoding="utf-8"), encoding="utf-8")
        f.write_text(stamp + "\n".join(f"- {r}" for r in rules) + "\n",
                     encoding="utf-8")
        written.append(str(f.relative_to(ROOT)))
    return written


def run_review(provider: str = "auto", apply: bool = False) -> int:
    sys.path.insert(0, str(ROOT))
    from curriculum_to_comic.llm import get_text_client

    agg = aggregate()
    if agg["chapters_analyzed"] == 0:
        print("No finished chapters found in Thomas_Tests/. Run the marathon first.")
        return 1

    print(f"Analyzing {agg['chapters_analyzed']} chapters…")
    print("Aggregate metrics:", json.dumps(agg["metrics"]))
    print("Top issue themes:", agg["top_themes"][:5])

    client = get_text_client(provider)
    evidence = {
        "metrics": agg["metrics"],
        "recurring_issue_themes": agg["top_themes"],
        "issue_samples": agg["issue_samples"],
        "current_tuning_rule_counts": {
            p.name: len([l for l in p.read_text(encoding="utf-8").splitlines()
                         if l.startswith("- ")])
            for p in TUNING_DIR.glob("*.md")
        } if TUNING_DIR.is_dir() else {},
    }
    try:
        improve = client.complete_json(
            system=PRINCIPAL_SYSTEM,
            user="Aggregate QA evidence from the full chapter marathon:\n"
                 + json.dumps(evidence, indent=2),
            max_tokens=4000,
            temperature=0.3,
        )
    except Exception as exc:
        print(f"Principal-review LLM call failed: {exc}")
        improve = {"diagnosis": f"(LLM call failed: {exc})"}

    written = apply_tuning(improve) if apply else []
    report = write_report(agg, improve, applied=bool(written))
    print(f"\nReview report: {report}")
    if written:
        print("Consolidated tuning written (backups saved as *.md.bak):")
        for w in written:
            print("  -", w)
    else:
        print("Run again with --apply to activate the consolidated tuning.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--provider", default="auto",
                    choices=["auto", "anthropic", "gemini"])
    ap.add_argument("--apply", action="store_true",
                    help="rewrite tuning/*.md with the consolidated rules")
    args = ap.parse_args()
    return run_review(provider=args.provider, apply=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
