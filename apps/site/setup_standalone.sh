#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# ComicTeach site — Standalone setup + launcher (macOS / Linux)
#
# What this does:
#   1. Copies this project to ~/comicteach-site (so it lives outside Cowork).
#   2. Installs Node deps (npm install).
#   3. Boots Next.js dev server at http://localhost:3000.
#
# Re-running is safe: each step skips itself if already done.
#
# Usage:
#   bash setup_standalone.sh                # default: ~/comicteach-site
#   bash setup_standalone.sh /custom/path
#   bash setup_standalone.sh --sync         # re-copy source files
#   bash setup_standalone.sh --clean        # nuke node_modules first
#   bash setup_standalone.sh --no-launch    # set up but don't start dev server
#   bash setup_standalone.sh --build        # production build instead of dev
# -----------------------------------------------------------------------------

set -euo pipefail

DEST="$HOME/comicteach-site"
SYNC=0
CLEAN=0
LAUNCH=1
MODE=dev

for arg in "$@"; do
  case "$arg" in
    --sync)       SYNC=1 ;;
    --clean)      CLEAN=1 ;;
    --no-launch)  LAUNCH=0 ;;
    --build)      MODE=build ;;
    -h|--help)    sed -n '2,20p' "$0"; exit 0 ;;
    -*) echo "Unknown flag: $arg" >&2; exit 2 ;;
    *)  DEST="$arg" ;;
  esac
done

SRC="$(cd "$(dirname "$0")" && pwd)"
if [ ! -f "$SRC/package.json" ] || [ ! -f "$SRC/next.config.mjs" ]; then
  echo "ERROR: $SRC doesn't look like the ComicTeach site (no package.json + next.config.mjs)." >&2
  exit 1
fi

echo "==> Source:      $SRC"
echo "==> Destination: $DEST"

# ----- copy ------------------------------------------------------------------
if [ ! -d "$DEST" ]; then
  mkdir -p "$DEST"
  SYNC=1
fi

if [ "$SYNC" = "1" ]; then
  echo "==> Copying project files (excluding node_modules, .next, .git)"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a \
      --exclude='node_modules/' \
      --exclude='.next/' \
      --exclude='.git/' \
      --exclude='out/' \
      --exclude='.vercel/' \
      "$SRC/" "$DEST/"
  else
    cp -R "$SRC/." "$DEST/"
    rm -rf "$DEST/node_modules" "$DEST/.next" "$DEST/.git" "$DEST/out" "$DEST/.vercel"
  fi
fi

cd "$DEST"

# ----- node check ------------------------------------------------------------
if ! command -v node >/dev/null 2>&1; then
  echo "ERROR: Node.js not found." >&2
  echo "  Install via Homebrew: brew install node@20" >&2
  echo "  Or download:          https://nodejs.org/" >&2
  exit 1
fi

NODE_VERSION="$(node -p 'process.versions.node')"
NODE_MAJOR="$(echo "$NODE_VERSION" | cut -d. -f1)"
if [ "$NODE_MAJOR" -lt 18 ]; then
  echo "ERROR: Node 18.17+ required (found $NODE_VERSION)." >&2
  echo "  brew install node@20 && brew link --overwrite node@20" >&2
  exit 1
fi
echo "==> Using Node $NODE_VERSION"

# ----- npm install -----------------------------------------------------------
if [ "$CLEAN" = "1" ] && [ -d "$DEST/node_modules" ]; then
  echo "==> --clean: removing node_modules"
  rm -rf "$DEST/node_modules" "$DEST/.next"
fi

if [ ! -d "$DEST/node_modules" ] || [ "$SYNC" = "1" ]; then
  echo "==> Installing dependencies (this takes ~30s on first run)"
  if command -v pnpm >/dev/null 2>&1; then
    pnpm install
  elif command -v yarn >/dev/null 2>&1; then
    yarn install
  else
    npm install
  fi
else
  echo "==> Dependencies already installed (--clean to reinstall)"
fi

# ----- launch ----------------------------------------------------------------
echo ""
echo "============================================================"
echo " Setup complete."
echo "   Project:  $DEST"
echo "   Dev:      cd $DEST && npm run dev    # → http://localhost:3000"
echo "   Build:    cd $DEST && npm run build && npm start"
echo "   Deploy:   cd $DEST && npx vercel --prod"
echo "============================================================"
echo ""

if [ "$LAUNCH" = "1" ]; then
  if [ "$MODE" = "build" ]; then
    echo "==> Production build"
    npm run build
    echo "==> Starting production server on http://localhost:3000"
    exec npm start
  else
    echo "==> Dev server on http://localhost:3000  (Ctrl-C to stop)"
    exec npm run dev
  fi
fi
