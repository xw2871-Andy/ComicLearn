# ComicLearn — Competitiveness & UX Brainstorm

The core bet: teachers don't buy "AI images," they buy **lesson-ready,
print-ready, on-curriculum comics with zero cleanup**. Everything below is
ranked by how much it strengthens that promise.

## The moat: guaranteed consistency & accuracy

This is the current weak point (and every competitor's weak point) — whoever
solves "every page looks like the same book and every formula is right" wins.

1. **Canonical character sheets per project (highest impact).** On project
   creation, generate ONE reference sheet per character (front/side/expressions,
   fixed palette hex codes) and attach it to every page request forever.
   Today we anchor on 3 sample pages + rolling reference; a dedicated sheet
   makes drift structurally harder. Cheap to build on the existing
   reference-image plumbing.
2. **Code-rendered math, AI-rendered story.** Graphs, axes, and formulas are
   where AI images fail accuracy. Render graphs with Matplotlib/Desmos-style
   code and composite them INTO the page (or into a panel slot) instead of
   asking the image model to draw them. Formulas come out pixel-perfect and
   QA stops flagging mangled notation. This is the single biggest accuracy
   win available.
3. **Text-layer speech bubbles.** Ask Nano Banana for EMPTY bubbles, then
   typeset dialogue programmatically (SVG text on top of the PNG). Perfect
   spelling guaranteed, instant text edits without redrawing, and built-in
   translation/bilingual mode for free. Worth a prototype behind a toggle.
4. **QA stack now in place (keep tightening thresholds as quality rises):**
   story editor (flow ≥ 75) → per-page vision QA (score ≥ 70) → book-level
   reviewer (all pages side by side, drift/garbled-text/storytelling, ≥ 75)
   → teacher per-page revise loop. The eval harness (`evaluate_agent.py
   --chapter1 --apply`) closes the loop by distilling failures into prompt
   rules automatically.
5. **Regression benchmark.** Keep `eval_runs/` history; before any prompt or
   model change, rerun the Chapter 1 benchmark and compare scoreboards. Never
   ship a change that lowers book-consistency or flow averages.

## Teacher UX (make it feel like a classroom tool, not an AI tool)

6. **One-click classroom kit per lesson:** comic PDF + worksheet + answer key
   + a 5-question exit ticket generated from the worksheet. Teachers value
   the bundle far more than any single artifact.
7. **Shareable read-only links** for students/parents (no login), plus
   Google Classroom / Canvas export. Distribution beats features.
8. **Editable dialogue before rendering:** show the storyboard as editable
   text between Story QA and page rendering ("approve storyboard" gate,
   optional toggle). Teachers love control; it also saves wasted image spend
   on storyboards they'd reject.
9. **Audio mode (already in the OpenClaw skill design):** TTS per character
   from dialogue.txt (Noiz voice profiles) → read-along comic for younger
   students and accessibility compliance.
10. **Bilingual editions** (English/Chinese/Spanish) from the same storyboard
    — near-zero extra cost with the text-layer bubbles from #3.
11. **Class library & pacing view:** organize lessons by unit (the Chapter 1
    folder structure, but in the studio UI), mark "taught," attach dates.

## Competitive positioning

12. **Curriculum-native is the differentiator.** Generic comic makers
    (Canva, generic GPT wrappers) can't claim CED alignment, misconception
    forecasting, or QA-verified math. Lead marketing with "AP-aligned,
    teacher-reviewed pipeline," show the QA reports publicly — the QA
    appendix in each PDF is a trust feature competitors can't fake.
13. **Doraemon is demo-only.** For a sellable product, ship 2-3 ORIGINAL
    recurring characters (own the IP) with the same teacher/student dynamic;
    keep licensed-character mode for personal classroom use. This also
    unlocks Teachers-Pay-Teachers / district sales legally.
14. **Per-unit pricing intuition:** teachers think in units/chapters, not
    tokens. "Generate Unit 1 (9 comic lessons + worksheets) — $X" with draft
    (1K) free previews and paid 2K/4K finals maps cleanly onto the existing
    quality tiers.
15. **Subjects beyond calculus:** the pipeline is subject-agnostic (lesson →
    worksheet → storyboard → pages). Physics, chemistry, biology, history
    timelines. AP Calc proves rigor; breadth multiplies the market.

## Suggested order of attack

Phase 1 (this month): character sheets (#1), Chapter 1 benchmark + tuning
loop runs (`--chapter1 --apply`), storyboard approval gate (#8).
Phase 2: code-rendered math composite (#2), classroom kit (#6), share links (#7).
Phase 3: text-layer bubbles + bilingual (#3/#10), audio (#9), original cast (#13).
