# ComicTeach

ComicTeach is the public repository for my ComicLearn prototype: an AI learning
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
Input lesson
  -> lesson plan extraction
  -> six-scene storyboard
  -> dialogue script
  -> panel rendering
  -> visual QA and optional rerender
  -> printable comic PDF
```

Supported inputs:

- Topic prompt, such as `Riemann Sums`
- Markdown or plain-text lesson outline
- Textbook PDF page range through the CLI

Generated artifacts:

- `lesson.json`
- `storyboard.json`
- `dialogue.txt`
- panel images
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
| `ANTHROPIC_API_KEY` | Required for lesson planning, storyboarding, SVG rendering, and visual QA |
| `GEMINI_API_KEY` | Optional image backend for Nano Banana/Gemini image generation |
| `IMAGE_BACKEND` | `svg`, `gemini`, or mock/demo modes where supported |
| `C2C_OUTPUT_DIR` | Output folder for generated runs |
| `C2C_DB_PATH` | SQLite path for the web studio |

The default SVG path is the most reliable local demo because it does not require
image generation credits.

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
