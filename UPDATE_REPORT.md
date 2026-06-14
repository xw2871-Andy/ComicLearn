# ComicLearn / ComicTeach — Project Update Report

_Snapshot of the major upgrade cycle. Turns AP Calculus curriculum
(topic, markdown outline, or textbook PDF) into 6-page Doraemon-style comic
lessons with worksheets, under a multi-stage AI quality-control pipeline._

## The pipeline now

```
Input (topic | markdown | textbook PDF)
  → PDF extract (Mathpix OCR, LaTeX-accurate; pdfplumber fallback)
  → lesson plan            (Claude or Gemini)
  → student worksheet      (Claude or Gemini)
  → 6-scene storyboard + clean dialogue
  → STORY-FLOW QA          (editor reviews narrative; rewrites if flow < 75)
  → pages drawn ONE AT A TIME   (Nano Banana Pro, rolling style reference)
  → PER-PAGE VISUAL QA     (auto-redraw any page scoring < 80)
  → BOOK-LEVEL QA          (all pages judged together for cross-page drift)
  → comic PDF + worksheet
```

## What changed this cycle

### Providers & models
- Dual text/vision provider: **Anthropic Claude OR Google Gemini**, selectable
  per run (UI dropdown, `--provider`, `TEXT_PROVIDER`). Gemini-only setups run
  the entire pipeline end to end.
- Image model upgraded to **Nano Banana Pro** (`gemini-3-pro-image-preview`),
  4:5, with a per-run quality switch: **1K draft / 2K standard / 4K print**.
- Robustness: truncation-aware retries on both clients (long lesson JSON no
  longer comes back half-finished), JSON-repair fallback, and automatic
  fallback to `gemini-2.5-flash` on "location not supported" preview errors.

### Inputs
- **Textbook PDF upload** in the studio (drag-and-drop) and on the CLI, with
  page-range selection and Mathpix OCR when configured.

### Quality control (the core focus)
- **Story-flow QA subagent** — grounded hook, pre-knowledge recall before new
  theory, scene-to-scene bridges, proper theory development; rewrites weak
  storyboards before any image is drawn.
- **Per-page visual QA** — six-axis rubric; auto-redraw threshold raised to 80.
- **Book-level consistency reviewer** — judges all 6 pages side by side for
  character drift, garbled text, and visual storytelling that per-page QA
  can't see; redraws the worst pages anchored on the best page.
- **Keep-better guard** — a redraw that scores LOWER than the page it replaces
  is discarded, so quality only ratchets up (this fixed a real regression
  where redraws were silently making pages worse).
- **Teacher revise loop** — request edits to any single finished page; it is
  re-drawn, re-QA'd, and the PDF rebuilt.
- **Per-page render retries** with backoff so a transient network blip no
  longer discards a whole chapter's completed work.

### Autonomy & self-improvement
- **`run_thomas_marathon.py`** — tests every AP chapter end to end, saves
  params/progress/pages/QA, self-learns between chapters via `tuning/*.md`.
- **`run_thomas_sections.py`** — one comic per textbook SUB-SECTION (76 AP
  sections auto-mapped from the TOC). Components-only output (worksheet,
  storyboard, dialogue, panels, QA), no PDF compile, organized as
  `Thomas_Sections/Chapter_NN/N.M_Title/`.
- **`evaluate_agent.py`** — benchmark harness scoring structure + story +
  visual + book quality, with `--apply` to write learned tuning rules.
- **`review_marathon.py`** — holistic post-run review that consolidates the
  noisy per-chapter tuning into a clean, evidence-backed rule set and proposes
  base-prompt/skill edits.

### Identity / skills ported from OpenClaw
- DoraeMath Architect persona, gadget-driven solutions, slice-of-life variety,
  Bloom's-verb objectives, the `check-image-condition` QA checklist, and the
  exact style/layout anchors are now in the prompt stack. Pages are anchored to
  real Doraemon sample pages for authentic manga quality.

### UI/UX
- 8-step live pipeline view with per-step timing, page-by-page progress,
  QA score badges, click-to-zoom + per-page edit, worksheet download, provider
  and quality selectors that detect which API keys are configured.

## Findings from the first full textbook run (10 chapters)

See `Thomas_Tests/HOLISTIC_REVIEW.md` for the full analysis. Highlights:
- Output quality is **higher than the scores implied**: on-model characters,
  correct calculus, clean multi-panel manga.
- Biggest win: a **rubric contradiction** (QA penalizing pages for showing
  3 bubbles when the storyboard lists 6-8 lines) was inflating the #1 issue and
  capping pages at 82 — now fixed.
- Real remaining issue: **character drift across pages**, worst on pages that
  crowd in supporting cast. Mitigations applied (explicit palette/proportion
  anchor, on-screen cast cap, keep-better redraws). Structural next step:
  per-project character sheets.

## Repository layout

| Path | Purpose |
| --- | --- |
| `curriculum_to_comic/` | Core agent, prompts, providers, QA subagents |
| `curriculum_to_comic/story_qa.py`, `book_qa.py` | Story-flow + book-level QA |
| `curriculum_to_comic/gemini_client.py`, `llm.py` | Gemini provider + factory |
| `curriculum_to_comic/mathpix.py`, `worksheet.py` | PDF OCR + worksheet step |
| `web/` | FastAPI studio + browser UI |
| `run_thomas_sections.py` | Per-section generator (76 AP sections) |
| `run_thomas_marathon.py` | Per-chapter test marathon + self-learning |
| `evaluate_agent.py`, `review_marathon.py` | Eval + holistic improvement |
| `tuning/` | Learned prompt rules (auto-applied at runtime) |
| `IDEAS_ROADMAP.md` | Competitiveness & UX roadmap |

## Not committed (by design)
Generated outputs (`Thomas_Tests/`, `Thomas_Sections/`, `outputs/`), the
copyrighted textbook (`source_materials/`), `.env`, and the virtualenv are
git-ignored — they're large, regenerable, or private.

## Suggested next steps
1. Per-project character sheets (structural cure for drift).
2. Re-run the section marathon with the fixed prompts; compare scoreboards.
3. Text-layer speech bubbles (perfect spelling, free bilingual mode).
4. Code-rendered graphs composited into pages (guaranteed math accuracy).
