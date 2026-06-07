# Demo Script

Use this for a short incubator review.

## 30-Second Pitch

ComicTeach turns a teacher's lesson into a comic students want to read. A
teacher enters a topic or lesson outline, the system builds a lesson plan,
storyboards it, generates six comic pages, checks visual quality, and exports a
PDF ready for class.

## Two-Minute Product Walkthrough

1. Open the showcase site in `apps/site`.
2. Show the hero and the AP Calculus sample pages.
3. Explain that the pages are generated output, not static concept art.
4. Open the studio at `http://127.0.0.1:8000`.
5. Create or open a project.
6. Start a mock run to show live progress without spending API credits.
7. Open the generated run history and PDF link.
8. If API keys are configured, run a real topic generation from the CLI.

## Local Commands

Studio:

```bash
pip install -e ".[web]"
python run_web.py
```

Showcase site:

```bash
cd apps/site
npm install
npm run dev
```

CLI:

```bash
c2c topic "Limits" --grade "AP Calculus AB"
```

## Key Talking Points

- Built from a real teaching insight, not a generic content generator.
- Produces classroom artifacts: lesson plan, dialogue, panels, QA report, PDF.
- Uses a QA loop to catch unreadable bubbles, math visibility problems, and
  style drift.
- Teachers can use mock demos and sample outputs before spending generation
  credits.
- The architecture supports future standards alignment, voiceover, and more
  image backends.
