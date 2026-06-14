#!/usr/bin/env python3
"""Full-loop agent evaluation & self-improvement harness.

Runs the pipeline on benchmark topics, scores every stage (structural checks
+ the story-flow editor + the visual QA subagent), writes a report, and —
with --apply — distills the failures into "learned tuning notes" that the
prompts automatically load on every future run (see prompts.load_tuning).

The loop:  evaluate -> report -> --apply tuning -> regenerate -> re-evaluate.
Tuning lives in tuning/storyboard.md and tuning/image.md and is appended to
the storyboard system prompt / image prompts as extra hard rules.

Usage (on a machine with API keys in .env):

    python evaluate_agent.py --text-only           # fast, no image credits
    python evaluate_agent.py --quality 1K          # full eval w/ draft images
    python evaluate_agent.py --text-only --apply   # also write tuning notes
    python evaluate_agent.py --topics "Chain Rule" # custom benchmark topics
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EVAL_DIR = ROOT / "eval_runs"
TUNING_DIR = ROOT / "tuning"

DEFAULT_TOPICS = [
    ("Defining Limits and Using Limit Notation", "AP Calculus AB"),
    ("The Chain Rule", "AP Calculus AB"),
    ("Riemann Sums and the Definite Integral", "AP Calculus AB"),
]

VALID_BEATS = {"hook", "context", "definition", "theorem",
               "worked_example", "misconception", "recap"}

META_IMPROVE_SYSTEM = """You are the lead engineer of an educational comic
agent. You receive the aggregated evaluation results of several test runs:
structural failures, story-editor issues, and visual-QA issues.

Distill them into ADDITIVE prompt rules that would prevent the most common
failures. Be concrete and imperative ("Always...", "Never..."), max ~8 rules
per category, no duplicates of rules that obviously already exist.

Return ONLY this JSON, no fences:
{
  "storyboard_rules": [str, ...],   // rules for the storyboard writer
  "image_rules": [str, ...],        // rules for the image-prompt builder
  "summary": str                    // 2-3 sentence diagnosis
}"""


# ----------------------------------------------------------- structural QA #

def check_worksheet(md: str) -> list[str]:
    issues = []
    required = ["Essential Questions", "Learning Objectives",
                "Conceptual Progression", "Worked Examples",
                "Practice Problems", "Misconception"]
    for section in required:
        if section.lower() not in md.lower():
            issues.append(f"worksheet missing section: {section}")
    if "$" not in md:
        issues.append("worksheet has no LaTeX math")
    if len(md) < 1200:
        issues.append(f"worksheet too short ({len(md)} chars)")
    return issues


def check_storyboard(sb) -> list[str]:
    issues = []
    if len(sb.scenes) != 6:
        issues.append(f"storyboard has {len(sb.scenes)} scenes, expected 6")
    beats = [s.pedagogical_beat for s in sb.scenes]
    for b in set(beats) - VALID_BEATS:
        issues.append(f"invalid pedagogical beat: {b}")
    if sb.scenes and sb.scenes[0].pedagogical_beat not in {"hook", "context"}:
        issues.append("scene 1 is not a hook/context beat")
    if sb.scenes and sb.scenes[-1].pedagogical_beat != "recap":
        issues.append("final scene is not a recap beat")
    lens = [len(s.dialogue) for s in sb.scenes]
    for s, n in zip(sb.scenes, lens):
        if not 6 <= n <= 8:
            issues.append(f"scene {s.number} has {n} dialogue lines (want 6-8)")
    if lens and (max(lens) - min(lens)) > 2:
        issues.append(f"dialogue length uneven across scenes: {lens}")
    if not any(s.holographic_math for s in sb.scenes):
        issues.append("no scene carries a holographic_math overlay")
    for s in sb.scenes:
        for d in s.dialogue:
            if "(" in d.text or ")" in d.text:
                issues.append(f"scene {s.number}: stage direction in dialogue")
                break
    return issues


# ------------------------------------------------------------------- main #

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--topics", nargs="*", help="override benchmark topics")
    ap.add_argument("--chapter1", action="store_true",
                    help="benchmark ALL 9 Chapter 1 lessons independently")
    ap.add_argument("--text-only", action="store_true",
                    help="skip image generation + visual QA (fast, cheap)")
    ap.add_argument("--quality", default="1K", choices=["1K", "2K", "4K"],
                    help="image quality when images are generated (default 1K)")
    ap.add_argument("--provider", default="auto",
                    choices=["auto", "anthropic", "gemini"])
    ap.add_argument("--apply", action="store_true",
                    help="write distilled tuning notes to tuning/*.md")
    args = ap.parse_args()

    sys.path.insert(0, str(ROOT))
    from curriculum_to_comic.extractors import from_topic
    from curriculum_to_comic.lesson import build_lesson
    from curriculum_to_comic.llm import get_text_client
    from curriculum_to_comic.story_qa import review_and_fix
    from curriculum_to_comic.storyboard import build_storyboard
    from curriculum_to_comic.worksheet import build_worksheet

    if args.chapter1:
        from generate_chapter1 import LESSONS

        topics = [
            (f"Unit {num} - {title}. Focus: {focus}", "AP Calculus AB")
            for num, title, focus in LESSONS
        ]
    elif args.topics:
        topics = [(t, "AP Calculus AB") for t in args.topics]
    else:
        topics = DEFAULT_TOPICS
    ts = time.strftime("%Y%m%d-%H%M%S")
    out_dir = EVAL_DIR / ts
    out_dir.mkdir(parents=True, exist_ok=True)
    client = get_text_client(args.provider)

    results = []
    for topic, grade in topics:
        print(f"\n=== EVAL: {topic} ===")
        r = {"topic": topic, "structural": [], "story": {}, "visual": [],
             "timings": {}, "error": None}
        t0 = time.time()
        try:
            curriculum = from_topic(topic, grade)

            t = time.time()
            lesson = build_lesson(curriculum, client)
            r["timings"]["lesson_s"] = round(time.time() - t, 1)

            t = time.time()
            worksheet = build_worksheet(lesson, client)
            r["timings"]["worksheet_s"] = round(time.time() - t, 1)
            r["structural"] += check_worksheet(worksheet)

            t = time.time()
            sb = build_storyboard(lesson, client,
                                  cast=["Doraemon", "Nobita"])
            r["timings"]["storyboard_s"] = round(time.time() - t, 1)
            r["structural"] += check_storyboard(sb)

            t = time.time()
            sb, story_rep = review_and_fix(lesson, sb, client)
            r["timings"]["story_qa_s"] = round(time.time() - t, 1)
            r["story"] = story_rep.to_dict()
            if story_rep.revised:
                r["structural"] += [
                    f"(post-revision) {i}" for i in check_storyboard(sb)
                ]

            slug = "".join(c if c.isalnum() else "_" for c in topic.lower())[:40]
            case_dir = out_dir / slug
            case_dir.mkdir(exist_ok=True)
            (case_dir / "worksheet.md").write_text(worksheet, encoding="utf-8")
            (case_dir / "storyboard.json").write_text(
                sb.model_dump_json(indent=2), encoding="utf-8")
            (case_dir / "story_qa.json").write_text(
                json.dumps(story_rep.to_dict(), indent=2), encoding="utf-8")

            if not args.text_only:
                from curriculum_to_comic.book_qa import review_book
                from curriculum_to_comic.illustrator import render_storyboard
                from curriculum_to_comic.qa import StoryboardQAAgent

                t = time.time()
                panels, _ = render_storyboard(
                    sb, client, reference_paths=[], chain_panels=True,
                    resolution=args.quality)
                r["timings"]["render_s"] = round(time.time() - t, 1)

                t = time.time()
                qa = StoryboardQAAgent(client)
                reviews = qa.review_all(sb, panels)
                r["timings"]["visual_qa_s"] = round(time.time() - t, 1)
                r["visual"] = [
                    {"scene": rv.scene.number,
                     "verdict": rv.report.verdict,
                     "score": rv.report.consistency_score,
                     "issues": rv.report.issues[:4]}
                    for rv in reviews
                ]

                # Book-level consistency review (the QA gear-up).
                t = time.time()
                book = review_book(sb, panels, client)
                r["timings"]["book_qa_s"] = round(time.time() - t, 1)
                r["book"] = book.to_dict()
                for pr in book.page_reports:
                    for i in pr.get("issues", [])[:3]:
                        r.setdefault("book_issues", []).append(
                            f"page {pr.get('page')}: {i}")

                panels_dir = case_dir / "panels"
                panels_dir.mkdir(exist_ok=True)
                for p in panels:
                    (panels_dir / f"scene_{p.scene_number:02d}.svg").write_text(
                        p.svg, encoding="utf-8")
        except Exception as exc:
            r["error"] = f"{type(exc).__name__}: {exc}"
            print(f"  !! {r['error']}")
        r["timings"]["total_s"] = round(time.time() - t0, 1)
        results.append(r)
        flow = r["story"].get("final_flow_score", "n/a")
        print(f"  structural issues: {len(r['structural'])} · story flow: {flow}"
              f" · {r['timings']['total_s']}s")

    # ----- aggregate ----- #
    flows = [r["story"].get("final_flow_score") for r in results
             if isinstance(r["story"].get("final_flow_score"), int)
             and r["story"].get("final_flow_score", -1) >= 0]
    vis_scores = [v["score"] for r in results for v in r["visual"]]
    book_scores = [r["book"]["consistency_score"] for r in results
                   if r.get("book") and not r["book"].get("error")]
    all_struct = [i for r in results for i in r["structural"]]
    all_story_issues = [i for r in results for i in r["story"].get("issues", [])]
    all_vis_issues = [i for r in results for v in r["visual"] for i in v["issues"]]
    all_book_issues = [i for r in results for i in r.get("book_issues", [])]
    errors = [r["error"] for r in results if r["error"]]

    summary = {
        "runs": len(results),
        "errors": errors,
        "structural_issue_count": len(all_struct),
        "story_flow_avg": round(statistics.mean(flows), 1) if flows else None,
        "story_revision_rate": round(
            sum(1 for r in results if r["story"].get("revised")) / max(len(results), 1), 2),
        "visual_score_avg": round(statistics.mean(vis_scores), 1) if vis_scores else None,
        "visual_fail_count": sum(1 for r in results for v in r["visual"]
                                 if v["verdict"] == "fail"),
        "book_consistency_avg": round(statistics.mean(book_scores), 1) if book_scores else None,
        "book_issue_count": len(all_book_issues),
    }

    # ----- meta-improvement (the "improve" half of the loop) ----- #
    tuning = {"storyboard_rules": [], "image_rules": [], "summary": ""}
    issue_dump = json.dumps({
        "structural_issues": all_struct[:40],
        "story_editor_issues": all_story_issues[:40],
        "visual_qa_issues": all_vis_issues[:40],
        "book_consistency_issues": all_book_issues[:40],
        "errors": errors,
    }, indent=2)
    if all_struct or all_story_issues or all_vis_issues or all_book_issues:
        try:
            tuning = client.complete_json(
                system=META_IMPROVE_SYSTEM,
                user=f"Aggregated evaluation results:\n{issue_dump}",
                max_tokens=2000, temperature=0.3)
        except Exception as exc:
            tuning["summary"] = f"meta-improve call failed: {exc}"

    # ----- report ----- #
    lines = [
        f"# Agent Evaluation Report — {ts}",
        "",
        f"Mode: {'text-only' if args.text_only else f'full ({args.quality} images)'}"
        f" · provider: {args.provider}",
        "",
        "## Scoreboard",
        "",
        "```json",
        json.dumps(summary, indent=2),
        "```",
        "",
        "## Per-topic results",
        "",
    ]
    for r in results:
        lines.append(f"### {r['topic']}")
        lines.append("")
        lines.append(f"- timings: `{r['timings']}`")
        lines.append(f"- story flow: {r['story'].get('flow_score')} -> "
                     f"{r['story'].get('final_flow_score')} "
                     f"(revised: {r['story'].get('revised')})")
        for i in r["structural"]:
            lines.append(f"- [structural] {i}")
        for i in r["story"].get("issues", []):
            lines.append(f"- [story] {i}")
        for v in r["visual"]:
            lines.append(f"- [visual] scene {v['scene']}: {v['verdict']} "
                         f"({v['score']}) {'; '.join(v['issues'])}")
        if r.get("book"):
            lines.append(f"- [book] consistency {r['book']['consistency_score']} "
                         f"· best page {r['book']['best_page']} "
                         f"· {r['book'].get('summary','')[:160]}")
            for i in r.get("book_issues", []):
                lines.append(f"- [book] {i}")
        if r["error"]:
            lines.append(f"- [ERROR] {r['error']}")
        lines.append("")
    lines += [
        "## Distilled improvement rules",
        "",
        f"_Diagnosis: {tuning.get('summary', '')}_",
        "",
        "### Storyboard rules" ,
        *[f"- {x}" for x in tuning.get("storyboard_rules", [])],
        "",
        "### Image rules",
        *[f"- {x}" for x in tuning.get("image_rules", [])],
        "",
        ("Tuning notes WRITTEN to tuning/ (active on next runs)."
         if args.apply else
         "Run again with --apply to activate these rules via tuning/*.md."),
    ]
    report_path = out_dir / "eval_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    (out_dir / "metrics.json").write_text(
        json.dumps({"summary": summary, "results": results}, indent=2),
        encoding="utf-8")

    # ----- apply tuning ----- #
    if args.apply and (tuning.get("storyboard_rules") or tuning.get("image_rules")):
        TUNING_DIR.mkdir(exist_ok=True)
        stamp = f"\n<!-- from eval {ts} -->\n"
        if tuning.get("storyboard_rules"):
            f = TUNING_DIR / "storyboard.md"
            old = f.read_text(encoding="utf-8") if f.exists() else ""
            f.write_text(old + stamp + "\n".join(
                f"- {x}" for x in tuning["storyboard_rules"]) + "\n",
                encoding="utf-8")
            print(f"tuning applied -> {f.relative_to(ROOT)}")
        if tuning.get("image_rules"):
            f = TUNING_DIR / "image.md"
            old = f.read_text(encoding="utf-8") if f.exists() else ""
            f.write_text(old + stamp + "\n".join(
                f"- {x}" for x in tuning["image_rules"]) + "\n",
                encoding="utf-8")
            print(f"tuning applied -> {f.relative_to(ROOT)}")

    print(f"\nReport: {report_path}")
    print(json.dumps(summary, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
