#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# ComicTeach — Standalone setup + launcher (macOS / Linux)
#
# What this does, in order:
#   1. Detects where it lives.
#   2. Copies the project to a clean standalone folder (default: ~/ComicTeach)
#      so the agent runs independently of any Cowork / OpenClaw mount.
#   3. Creates a dedicated Python virtual environment (.venv) inside that folder
#      so we never touch your conda base.
#   4. Installs the project with the `web` extras (FastAPI + Uvicorn).
#   5. Boots the studio at http://127.0.0.1:8000.
#
# Re-running is safe: each step skips itself if it's already done. To re-sync
# files from the source after editing, pass `--sync`. To rebuild the venv from
# scratch, pass `--clean`.
#
# Usage:
#   bash setup_standalone.sh                # default: ~/ComicTeach
#   bash setup_standalone.sh /custom/path   # custom destination
#   bash setup_standalone.sh --sync         # re-copy source files
#   bash setup_standalone.sh --clean        # nuke .venv first
#   bash setup_standalone.sh --no-launch    # set up but don't start the server
# -----------------------------------------------------------------------------

set -euo pipefail

# ----- parse args ------------------------------------------------------------
DEST="$HOME/ComicTeach"
SYNC=0
CLEAN=0
LAUNCH=1

for arg in "$@"; do
  case "$arg" in
    --sync)       SYNC=1 ;;
    --clean)      CLEAN=1 ;;
    --no-launch)  LAUNCH=0 ;;
    -h|--help)
      sed -n '2,25p' "$0"
      exit 0
      ;;
    -*)
      echo "Unknown flag: $arg" >&2
      exit 2
      ;;
    *)
      DEST="$arg"
      ;;
  esac
done

# ----- locate source ---------------------------------------------------------
SRC="$(cd "$(dirname "$0")" && pwd)"
if [ ! -f "$SRC/pyproject.toml" ] || [ ! -f "$SRC/run_web.py" ]; then
  echo "ERROR: $SRC doesn't look like the ComicTeach project (no pyproject.toml + run_web.py)." >&2
  exit 1
fi

echo "==> Source:      $SRC"
echo "==> Destination: $DEST"

# ----- copy ------------------------------------------------------------------
if [ ! -d "$DEST" ]; then
  echo "==> Creating $DEST"
  mkdir -p "$DEST"
  SYNC=1
fi

if [ "$SYNC" = "1" ]; then
  echo "==> Copying project files (excluding caches, venv, outputs)"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a \
      --exclude='.venv/' \
      --exclude='__pycache__/' \
      --exclude='*.pyc' \
      --exclude='.pytest_cache/' \
      --exclude='outputs/' \
      --exclude='.git/' \
      --exclude='node_modules/' \
      "$SRC/" "$DEST/"
  else
    cp -R "$SRC/." "$DEST/"
    rm -rf "$DEST/.venv" "$DEST/__pycache__" "$DEST/.pytest_cache" "$DEST/outputs"
  fi
fi

cd "$DEST"

# ----- preserve .env if user already customized it ---------------------------
if [ ! -f "$DEST/.env" ] && [ -f "$SRC/.env" ]; then
  cp "$SRC/.env" "$DEST/.env"
  echo "==> Copied .env from source"
elif [ -f "$DEST/.env" ]; then
  echo "==> Keeping existing .env in destination"
fi

# ----- pick python interpreter ----------------------------------------------
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "ERROR: No python interpreter found on PATH." >&2
  exit 1
fi

PY_VERSION="$($PY -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
echo "==> Using $PY ($PY_VERSION)"

case "$PY_VERSION" in
  3.1[0-9]*|3.[2-9][0-9]*) : ;;
  *)
    echo "ERROR: Python 3.10+ required (found $PY_VERSION). Install from https://www.python.org/downloads/ or via 'brew install python@3.12'." >&2
    exit 1
    ;;
esac

# ----- venv ------------------------------------------------------------------
if [ "$CLEAN" = "1" ] && [ -d "$DEST/.venv" ]; then
  echo "==> --clean: removing existing .venv"
  rm -rf "$DEST/.venv"
fi

if [ ! -d "$DEST/.venv" ]; then
  echo "==> Creating virtual environment at $DEST/.venv"
  "$PY" -m venv "$DEST/.venv"
fi

# shellcheck source=/dev/null
source "$DEST/.venv/bin/activate"

echo "==> Upgrading pip"
python -m pip install --upgrade pip >/dev/null

# ----- install ---------------------------------------------------------------
NEED_INSTALL=1
if python -c "import fastapi, uvicorn, curriculum_to_comic" >/dev/null 2>&1; then
  NEED_INSTALL=0
fi

if [ "$NEED_INSTALL" = "1" ] || [ "$SYNC" = "1" ]; then
  echo "==> Installing project + [web] extras (this may take a minute)"
  pip install -e ".[web]"
else
  echo "==> Dependencies already installed (use --clean to reinstall)"
fi

# ----- sanity check ----------------------------------------------------------
python -c "
import curriculum_to_comic, fastapi, uvicorn
from web import app, db, auth, runner
print('==> Sanity check: all modules import cleanly')
" || { echo "ERROR: import sanity check failed."; exit 1; }

if ! grep -q '^ANTHROPIC_API_KEY=' "$DEST/.env" 2>/dev/null; then
  echo ""
  echo "WARNING: ANTHROPIC_API_KEY not found in $DEST/.env"
  echo "         The lesson + storyboard agents need it. Add it before running."
  echo ""
fi

echo ""
echo "============================================================"
echo " Setup complete."
echo "   Project:  $DEST"
echo "   Activate: source $DEST/.venv/bin/activate"
echo "   Launch:   python run_web.py"
echo "============================================================"
echo ""

# ----- launch ----------------------------------------------------------------
if [ "$LAUNCH" = "1" ]; then
  echo "==> Booting studio on http://127.0.0.1:8000  (Ctrl-C to stop)"
  exec python run_web.py
fi
