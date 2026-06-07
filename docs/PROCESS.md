# Process Narrative

ComicTeach began as ComicLearn: a manual classroom experiment for turning AP
Calculus lessons into story-driven comic pages. The original work lived in an
OpenClaw workspace with separate prompt skills for curriculum design,
storyboarding, image generation, and audio/video experiments.

The repository now packages that workflow as a product.

## 1. Classroom Insight

Students are more willing to start difficult math when the first interaction is
a story instead of a dense worksheet. The earliest prototypes used familiar
comic-style tutoring scenes to explain limits, derivatives, extrema, and other
AP Calculus ideas.

## 2. Manual Workflow

The original OpenClaw process had four separate steps:

| Step | Manual artifact |
| --- | --- |
| Curriculum designer | Topic breakdown, objectives, misconceptions |
| Storyboard writer | Six-scene lesson arc with dialogue |
| Image generator | One page or panel per scene |
| QA reviewer | Visual consistency and math readability checks |

This worked for demos, but it was too fragile for real teacher use.

## 3. Productized Agent

The current code turns those steps into a recoverable pipeline:

| Stage | Product behavior |
| --- | --- |
| Ingest | Accept topic, markdown, or PDF text |
| Plan | Generate structured objectives and teaching beats |
| Storyboard | Produce a six-scene script with math purpose in each scene |
| Render | Generate panels through SVG or image backend |
| QA | Score visual quality and rerender failed panels |
| Compile | Export a printable PDF plus machine-readable artifacts |

Each stage writes intermediate files so a run can be debugged or resumed.

## 4. Teacher Studio

The web studio adds the surface a teacher expects:

- Account and session handling
- Project library
- Topic and markdown generation tabs
- Live progress stream
- Panel gallery
- Run history
- PDF download
- Mock mode for demos without API credits

## 5. Incubator Delivery

The repository now separates raw invention from presentation:

- `curriculum_to_comic/` demonstrates the technical engine.
- `web/` demonstrates a usable teacher workflow.
- `samples/` demonstrates generated output quality.
- `apps/site/` demonstrates public product positioning.
- `docs/` explains the build process and current milestone.
