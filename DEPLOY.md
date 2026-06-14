# Deploying ComicLearn Studio (hosted, on your keys)

This guide puts the web studio online so other people can use it through a link
and sign in. **Your API keys live on the host as environment variables — never
in the repo, never visible to users.** You pay for API usage, so signup is
gated by an invite code and runs are rate-limited.

The repo is already set up for this: it ships `railway.toml`, a `Dockerfile`,
a `/api/health` check, and accounts/login built into the studio.

---

## What you need first

- A **GitHub repo** with the current code pushed (see Step 1).
- A **Railway** account (railway.app) — easiest path; any Docker host works.
- Your keys: **`GEMINI_API_KEY`** (required — images + can run text too),
  optionally **`ANTHROPIC_API_KEY`** (Claude text/QA) and
  **`MATHPIX_APP_ID` / `MATHPIX_APP_KEY`** (LaTeX-accurate PDF OCR).

---

## Step 1 — Push the code to GitHub (safely)

Run from the project root. This keeps your `.env`, the textbook PDF, generated
sections, backups, and `studio.db` **out** of the repo:

```bash
cd "/Users/xingkaiwang/Documents/Codex/AGI/AGI Builder/ComicLearn"
rm -f .git/index.lock
for p in "Thomas_Sections/" "Thomas_Tests/" "source_materials/" "tuning/" "outputs/" "*.bak"; do
  grep -qxF "$p" .gitignore 2>/dev/null || echo "$p" >> .gitignore
done
git rm -r --cached --ignore-unmatch Thomas_Sections Thomas_Tests source_materials tuning outputs >/dev/null 2>&1
git add -A
git status --short        # confirm: NO .env, .pdf, .png, studio.db, Thomas_*
git commit -m "Hosted studio: signup gate, usage caps, server-side keys, model upgrade"
git push origin main
```

> If `git push` asks for a password, use a GitHub **personal access token**, not
> your account password.

---

## Step 2 — Create the Railway project

1. In Railway, **New Project → Deploy from GitHub repo**, pick your ComicLearn repo.
2. Railway reads `railway.toml` automatically (build = `pip install -e '.[web]'`,
   start = `python run_web.py`, health check = `/api/health`).
3. Railway injects a `PORT` — the app detects it and binds `0.0.0.0` for you.

---

## Step 3 — Set environment variables (in Railway, not the repo)

Open your service → **Variables** and add:

| Variable | Value | Why |
|---|---|---|
| `GEMINI_API_KEY` | *your key* | **Required.** Image generation (Nano Banana Pro) + can run all text steps. |
| `ANTHROPIC_API_KEY` | *your key* | Optional. Enables Claude (Opus 4.8) for text/QA. |
| `TEXT_PROVIDER` | `auto` | `auto` prefers Claude when its key is set, else Gemini. |
| `MATHPIX_APP_ID` / `MATHPIX_APP_KEY` | *your keys* | Optional. LaTeX-accurate PDF OCR. |
| `SIGNUP_INVITE_CODE` | *a secret phrase* | **Strongly recommended.** Users must enter this to register. |
| `SIGNUP_ALLOWED_EMAIL_DOMAINS` | e.g. `nyu.edu,school.edu` | Optional extra gate by email domain. |
| `MAX_RUNS_PER_USER_PER_DAY` | `10` | Caps per-user comics/day (0 = unlimited). |
| `MAX_RUNS_GLOBAL_PER_DAY` | `100` | Caps total comics/day across everyone. |
| `C2C_DB_PATH` | `/data/studio.db` | Accounts DB on the persistent volume (Step 4). |
| `DEFAULT_OUTPUT_DIR` | `/data/outputs` | Generated comics on the volume. |
| `C2C_OUTPUT_DIR` | `/data/outputs` | Same, for any CLI/agent code paths. |

Optional model/cost tuning (defaults are already current):

| Variable | Default | Note |
|---|---|---|
| `C2C_REASONING_MODEL` | `claude-opus-4-8` | Set to `claude-sonnet-4-6` to cut cost. |
| `GEMINI_IMAGE_RESOLUTION` | `2K` | `1K` is ~half the render time/cost. |
| `GEMINI_IMAGE_MODEL` | `gemini-3-pro-image` | Nano Banana Pro (GA). |
| `GEMINI_TEXT_MODEL` | `gemini-3.5-flash` | Stable; used when text runs on Gemini. |

> The `/api/config` endpoint only ever reports whether a key is *present*
> (`true`/`false`) — it never returns the key values.

---

## Step 4 — Add a persistent volume

Railway containers have an ephemeral filesystem; without a volume, every
redeploy wipes accounts and generated comics.

1. Service → **Volumes → New Volume**, mount path **`/data`**.
2. Make sure `C2C_DB_PATH`, `DEFAULT_OUTPUT_DIR`, `C2C_OUTPUT_DIR` point inside
   `/data` (Step 3). The app creates those folders on first run.

---

## Step 5 — Deploy and verify

1. Railway builds and deploys; wait for the health check on `/api/health` to pass.
2. Open the public URL. The sidebar footer should read **v0.4.0** (proof the new
   build is live).
3. Visit `https://<your-url>/api/config` — you should see
   `{"providers":{"gemini":true,...}}`. If a provider shows `false`, its key
   isn't set.

---

## Step 6 — Invite people

Share two things: the **URL** and the **invite code** you set in
`SIGNUP_INVITE_CODE`. On the sign-in screen they click "Create one", enter the
code in the **Access code** field, and register. Without the code, signup is
refused.

To revoke access later: change `SIGNUP_INVITE_CODE` (stops new signups on the
old code) — existing accounts keep working until you remove them from the DB.

---

## Cost & safety notes

- **Each comic ≈ 6+ Nano Banana Pro images** (~$0.13 each at 1K/2K) plus text
  steps. The per-user and global daily caps bound your maximum daily spend —
  tune them to your budget. Set `GEMINI_IMAGE_RESOLUTION=1K` to roughly halve
  image cost.
- **Keys never enter the repo.** They exist only in Railway's Variables. `.env`
  and `*.bak` are gitignored, and nothing key-related is tracked by git.
- **Watch your provider dashboards** (Google AI Studio / Anthropic) and set
  billing alerts there as a backstop.
- Residual cost vector: the per-page **revise** action also spends one image
  credit per use; it's gated by the same daily budget, but a determined user
  could revise repeatedly within their cap. Lower the caps if that's a concern.

---

## Troubleshooting

- **App deploys but URL won't load** → ensure the platform sets `PORT` (Railway
  does) or set `HOST=0.0.0.0` explicitly.
- **Accounts/comics vanish after redeploy** → the `/data` volume isn't mounted,
  or the path vars don't point inside it (Step 4).
- **"This studio is invite-only"** on signup → expected; enter the access code.
- **Images 400/403** → the `GEMINI_API_KEY` is wrong or lacks Generative
  Language API access; confirm at aistudio.google.com/apikey.
- **Verify the live version** any time at `/api/config` and the sidebar `v0.4.0`.

---

## Alternative: any Docker host

The included `Dockerfile` runs the same app. Build and run with the same env
vars and a volume at `/data`:

```bash
docker build -t comiclearn .
docker run -p 8000:8000 \
  -e GEMINI_API_KEY=... -e SIGNUP_INVITE_CODE=... \
  -e C2C_DB_PATH=/data/studio.db -e DEFAULT_OUTPUT_DIR=/data/outputs \
  -v comiclearn_data:/data \
  comiclearn
```
