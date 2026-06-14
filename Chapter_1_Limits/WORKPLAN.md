# Workplan — Chapter 1: Limits and Continuity (AP Calculus AB, Unit 1)

**Goal:** Produce the first full chapter of DoraeMath comic lessons — one 6-page
Doraemon comic + one student worksheet per lesson — aligned to the College
Board AP Calculus AB CED, Unit 1.

**Output folder:** `Chapter_1_Limits/` (this folder)

```
Chapter_1_Limits/
  WORKPLAN.md                  <- this file
  1.1_Introducing_Calculus/
    worksheet.md               <- student handout (AP-aligned, LaTeX math)
    storyboard.json            <- 6-scene script
    dialogue.txt               <- clean TTS-ready dialogue
    pages/page_1.png … page_6.png
    qa_reports.json            <- QA verdicts per page (threshold 70)
    <lesson>_comic.pdf         <- printable comic book
  1.2_Defining_Limits/ …       (same structure per lesson)
```

## Lesson list (College Board Unit 1 alignment)

| # | Lesson | CED topics covered | Status |
|---|--------|--------------------|--------|
| 1.1 | Introducing Calculus: Can Change Occur at an Instant? | 1.1 | pending |
| 1.2 | Defining Limits and Using Limit Notation | 1.2 | pending |
| 1.3 | Estimating Limit Values from Graphs and Tables | 1.3–1.4 | pending |
| 1.4 | Determining Limits Using Algebraic Properties | 1.5–1.6 | pending |
| 1.5 | Determining Limits Using Algebraic Manipulation | 1.6–1.7 | pending |
| 1.6 | Squeeze Theorem and Special Trig Limits | 1.8–1.9 | pending |
| 1.7 | Continuity, Discontinuities, and Removing Them | 1.10–1.13 | pending |
| 1.8 | Infinite Limits, Limits at Infinity, Asymptotes | 1.14–1.15 | pending |
| 1.9 | Intermediate Value Theorem (Unit 1 capstone) | 1.16 | pending |

## Pipeline settings (per lesson)

- **Text/reasoning:** auto (Claude when key present, else Gemini) — lesson plan,
  worksheet, storyboard, QA vision
- **Images:** Nano Banana Pro (`gemini-3-pro-image-preview`), 2K, 4:5,
  generated strictly one page at a time with rolling reference + the 3 authentic
  Doraemon sample pages as style anchors
- **Cast:** Doraemon (gadget-wielding teacher) · Nobita (curious student);
  Gian/Suneo/Mom for mathematical tension where the storyboard calls for it
- **QA:** on, score threshold 80 — any page below 80 (or hard fail) is
  auto-redrawn once with the reviewer's suggestions
- **Per-lesson definition of done:** 6 pages all QA ≥ 80, worksheet has exact
  Unit alignment + essential questions + worked examples + practice problems,
  PDF compiles, files organized in this folder

## Execution order

1. **Pilot — Lesson 1.1** end to end; inspect page quality, timing, and cost
   before committing to the batch.
2. **Review checkpoint** — Andy approves pilot quality (or requests prompt
   tweaks; the per-page revise loop in the studio can patch individual pages).
3. **Batch lessons 1.2 → 1.9** sequentially (image consistency requires
   sequential pages; lessons themselves also run one at a time to respect API
   rate limits).
4. **Chapter assembly** — update this table to `done` per lesson; final pass
   checks cross-lesson character/style consistency.

## Estimates (per lesson, observed from pilot)

- Text steps: ~1–2 min · 6 pages at 2K: ~4–7 min · QA: overlapped (≈0 extra)
- Total: **~6–9 min per lesson**, ≈ 60–80 min for the full chapter
- Image cost: 6–8 Nano Banana Pro 2K generations per lesson (incl. QA retries)
