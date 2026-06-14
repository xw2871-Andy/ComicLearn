# ComicLearn

ComicLearn is the public repository for my ComicLearn prototype: an AI learning
studio that turns curriculum material into short, teachable comics. It combines
lesson extraction, pedagogy-aware storyboarding, comic panel generation, visual
QA, and a web studio for teachers to manage projects and download finished PDF
lessons.

This repo is organized for startup incubator review: the working product code is
at the root, the polished showcase site is in `apps/site`, and the process notes
in `docs/` explain how the prototype moved from manual OpenClaw workflows to a
runnable product.

## What Is Delivered

| Area | Status | Where |
| --- | --- | --- |
| Curriculum-to-comic agent | Working CLI + Python package | `curriculum_to_comic/` |
| Teacher web studio | Working FastAPI + static SPA | `web/`, `run_web.py` |
| Visual QA loop | Implemented, with retry feedback | `curriculum_to_comic/qa.py` |
| Sample AP Calculus outputs | Included for review and mock demos | `samples/` |
| Public showcase site | Next.js app with real generated pages | `apps/site/` |
| Incubator docs | Process, architecture, demo, checklist | `docs/` |

## Product Flow

```
Input lesson (topic / markdown / textbook PDF)
  -> lesson plan extraction          (Claude or Gemini)
  -> student worksheet (markdown)    (Claude or Gemini)
  -> six-scene storyboard            (Claude or Gemini)
  -> dialogue script
  -> page rendering, ONE page at a time with rolling style references
                                     (Nano Banana Pro / gemini-3-pro-image)
  -> visual QA subagent + rerender   (Claude or Gemini vision)
  -> printable comic PDF
```

Supported inputs:

- Topic prompt, such as `Riemann Sums`
- Markdown or plain-text lesson outline
- Textbook PDF — uploaded in the web studio or via the CLI. Extracted with
  Mathpix OCR (LaTeX-accurate math) when configured, else pdfplumber.

Generated artifacts:

- `lesson.json`
- `worksheet.md` (student-facing, downloadable in the studio)
- `storyboard.json`
- `dialogue.txt`
- page images
- `qa_reports.json`
- final comic PDF
- `book.json` run manifest

## Quickstart: Teacher Studio

```bash
git clone git@github.com:xw2871-Andy/ComicTeach.git
cd ComicTeach
python -m venv .venv
source .venv/bin/activate
pip install -e ".[web]"
cp .env.example .env
python run_web.py
```

Open `http://127.0.0.1:8000`.

The web studio includes signup/login, projects, run history, a live generation
pane, mock demo mode, and authenticated access to generated PDFs.

## Quickstart: CLI

```bash
pip install -e .
c2c topic "Limits" --grade "AP Calculus AB" --out outputs
```

Useful variants:

```bash
c2c markdown examples/sample_lesson_outline.md \
  --topic "Definite Integrals" \
  --grade "AP Calculus AB"

c2c pdf ./textbook.pdf \
  --topic "Riemann Sums" \
  --grade "AP Calculus AB" \
  --pages 380-400
```

## Showcase Site

The incubator-facing website lives in `apps/site`.

```bash
cd apps/site
npm install
npm run dev
```

Open `http://localhost:3000`.

The site uses real generated AP Calculus pages copied into
`apps/site/public/showcase`, so reviewers can see the delivery quality without
running the AI pipeline.

## Configuration

Create `.env` from `.env.example`.

| Variable | Purpose |
| --- | --- |
| `TEXT_PROVIDER` | `auto`, `anthropic`, or `gemini` — which model writes the lesson plan, worksheet, storyboard, and runs visual QA. Also selectable per run in the studio UI |
| `ANTHROPIC_API_KEY` | Optional. Enables Claude as the text/QA provider |
| `GEMINI_API_KEY` | **Required for image generation** (Nano Banana Pro). Also enables Gemini as the text/QA provider |
| `GEMINI_IMAGE_MODEL` | Defaults to `gemini-3-pro-image` (Nano Banana Pro) |
| `GEMINI_IMAGE_RESOLUTION` | `1K`, `2K` (default), or `4K` page renders |
| `MATHPIX_APP_ID` / `MATHPIX_APP_KEY` | Optional. Mathpix OCR for textbook PDF input (clean LaTeX math) |
| `IMAGE_BACKEND` | `gemini` (default), `svg`, or mock/demo modes where supported |
| `C2C_OUTPUT_DIR` | Output folder for generated runs |
| `C2C_DB_PATH` | SQLite path for the web studio |

At least one of `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` must be set; a
Gemini-only setup runs the entire pipeline (text + QA + images) on Gemini.
Every page render is anchored to the authentic Doraemon sample pages in
`samples/references/doraemon_style_ref_*.jpg`, plus the previously generated
page, so the whole book stays on-model and consistent.

## Repository Map

| Path | Purpose |
| --- | --- |
| `curriculum_to_comic/` | Core agent, prompts, data models, renderers, QA |
| `web/` | FastAPI studio backend and browser UI |
| `samples/` | Lesson plans, references, and finished comic pages |
| `examples/` | CLI examples |
| `tests/` | Smoke tests for the pipeline contracts |
| `apps/site/` | Next.js showcase site |
| `docs/` | Process, architecture, demo script, delivery checklist |

## Review Guide

For the fastest review:

1. Read `docs/PROCESS.md` for the build story.
2. Open `apps/site` to see the polished public presentation.
3. Run the web studio with mock mode for a no-credit product demo.
4. Run the CLI with a small topic if API credentials are available.

## License

MIT.
