# AI Comic Book — Studio

A comicsmaker-style web UI on top of the `curriculum_to_comic` agent.

Studio gives every user their own login, a project library, and a live
streaming run pane that calls the same pipeline the CLI uses:

```
ingest  →  lesson  →  storyboard  →  render  →  QA + PDF
```

Each step's progress, every rendered panel, and the final PDF link are pushed to
the browser over Server-Sent Events. Runs are stored in SQLite so users can
reopen old runs and download their PDFs later.

---

## 1. Install (one-time)

From the project root:

```bash
pip install -e ".[web]"
```

This installs the core dependencies plus `fastapi`, `uvicorn[standard]`, and
`python-multipart`.

Sandbox note: if your environment blocks PyPI (Anthropic Cowork sandbox does),
run this command on your host machine instead.

## 2. Optional: configure the Gemini backend

The default image backend is `svg`, which is sandbox-safe and needs no API key.
To use the real Gemini "Nano Banana" backend, drop credentials into a `.env`
file at the project root:

```
ANTHROPIC_API_KEY=your_claude_key_here   # required for lesson + storyboard
GEMINI_API_KEY=your_gemini_key_here      # only required for the Gemini backend
```

`ANTHROPIC_API_KEY` is required for every backend (Claude writes the lesson
plan and storyboard). The Cowork sandbox blocks egress to
`generativelanguage.googleapis.com`, so Gemini calls must be made from the host
machine, not the sandbox.

## 3. Launch the studio

```bash
python run_web.py
```

Then open <http://127.0.0.1:8000>.

Environment overrides (all optional):

| Variable             | Default                    | Purpose                                |
| -------------------- | -------------------------- | -------------------------------------- |
| `HOST`               | `127.0.0.1`                | Bind address                            |
| `PORT`               | `8000`                     | Bind port                               |
| `DEFAULT_OUTPUT_DIR` | `./outputs`                | Where runs, PDFs, and panels are saved |
| `C2C_DB_PATH`        | `outputs/studio.db`        | SQLite DB file                          |

## 4. First-run walkthrough

1. Open <http://127.0.0.1:8000>. You'll see the login screen — click
   "Create one" and sign up with your email + a password (min 8 chars).
2. The sidebar appears. Click **+ New project** and fill in name, grade, and
   optional cast (e.g. `Doraemon, Nobita`).
3. In the generator card, pick a tab (Topic / Markdown), type a title, and
   choose a backend:
   - `SVG` — sandbox-safe, always works.
   - `Gemini Nano Banana 2` — uses your `GEMINI_API_KEY`.
   - `Mock` — recycles the Unit 1.1 showcase pages so you can demo the UI
     without spending tokens.
4. Click **Generate 6-page comic**. The stepper turns red as each phase runs,
   panels stream into the gallery, and the **Download PDF** link appears when
   step 5 finishes.
5. Re-open old runs from the **Run history** card at any time.

## 5. Architecture cheat-sheet

```
web/
├── app.py        FastAPI routes + SSE endpoint + static SPA mount
├── auth.py       PBKDF2 password hashing + cookie sessions (stdlib only)
├── db.py         SQLite schema + helpers (users / sessions / projects / runs / events)
├── runner.py     Background-thread pipeline runner + in-memory pub/sub bus
└── static/
    ├── index.html, styles.css, app.js
```

- **No ORM.** `db.py` opens a fresh `sqlite3` connection per call.
- **No browser storage.** Auth is an HTTP-only session cookie (`c2c_sess`,
  30-day TTL).
- **SSE catch-up.** Every event is also written to the `events` table with a
  monotonic `seq`. When a browser reconnects mid-run, the server replays from
  `Last-Event-ID` before joining the live bus.
- **Lazy AI imports.** `runner.py` only imports `anthropic`, `svglib`,
  `reportlab`, and `pdfplumber` *inside* the function that needs them, so the
  web layer can boot even if those wheels failed to install.

## 6. API quick-reference

All `/api/*` routes return JSON. Auth-gated routes require the `c2c_sess`
cookie set by `/api/login` or `/api/signup`.

| Method | Path                                | Purpose                                  |
| ------ | ----------------------------------- | ---------------------------------------- |
| POST   | `/api/signup`                       | Create account + start session           |
| POST   | `/api/login`                        | Authenticate + start session             |
| POST   | `/api/logout`                       | Drop session cookie                      |
| GET    | `/api/me`                           | Bootstrap current user                   |
| GET    | `/api/projects`                     | List my projects                         |
| POST   | `/api/projects`                     | Create project                           |
| PATCH  | `/api/projects/{id}`                | Edit project metadata                    |
| DELETE | `/api/projects/{id}`                | Delete project + cascade runs            |
| GET    | `/api/projects/{id}/runs`           | List runs in a project                   |
| POST   | `/api/projects/{id}/runs`           | Start a new run (returns `{run_id}`)     |
| GET    | `/api/runs/{id}`                    | Run metadata + replayed events           |
| GET    | `/api/runs/{id}/stream`             | Server-Sent Events stream                |
| GET    | `/assets/runs/{path}`               | Auth-gated panel / PDF download          |
| GET    | `/assets/showcase/{path}`           | Public showcase asset                    |
| GET    | `/api/health`                       | Healthcheck                              |

## 7. Smoke test (already passing)

The framework-agnostic pieces (`db`, `auth`, `runner` mock) have a self-
contained smoke test. Re-run any time with:

```bash
python - <<'PY'
import os; os.environ["C2C_DB_PATH"] = "/tmp/c2c-smoke.db"
from web import db, auth, runner
# ... see project notes for the full script
PY
```

The full studio (FastAPI app + browser SPA) requires the `[web]` extras
installed and `python run_web.py` running, then open the URL in a browser.

## 8. Known limitations

- **PDF source ingest** (`source_kind=pdf`) is not yet wired into the web
  runner; CLI still supports it.
- The Gemini backend will not work from inside the Cowork sandbox (egress
  blocked); use your host machine.
- The studio is single-node only. A second worker won't see the in-memory
  `RunBus`; runs survive across restarts via the `events` table, but live SSE
  fan-out is per-process.
