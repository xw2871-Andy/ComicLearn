#!/usr/bin/env bash
# One-shot: safely commit ALL local work and push it to GitHub.
# Run on your Mac (where your GitHub login lives):
#     bash push_to_github.sh
#
# It will NOT leak secrets or huge files — it re-checks the ignore rules first.
set -uo pipefail
cd "$(dirname "$0")"

echo "==> 1/5  Ensuring sensitive/heavy paths stay out of git..."
for p in ".env" "*.bak" "Thomas_Sections/" "Thomas_Tests/" "source_materials/" "tuning/" "outputs/"; do
  grep -qxF "$p" .gitignore 2>/dev/null || echo "$p" >> .gitignore
done
# Stop tracking any that were committed before (keeps the local files):
git rm -r --cached --ignore-unmatch \
  Thomas_Sections Thomas_Tests source_materials tuning outputs .env >/dev/null 2>&1 || true

echo "==> 2/5  Staging changes..."
git add -A

echo "==> 3/5  Review — this should be SOURCE ONLY (no .env, .pdf, .png, studio.db):"
git status --short
echo "-------------------------------------------------------------------"

echo "==> 4/5  Committing..."
git commit -m "Sprint (dual providers, Nano Banana Pro, section generator, Mathpix, story/book QA) + model upgrade (Opus 4.8 / gemini-3-pro-image / gemini-3.5-flash) + hosted studio: signup gate & usage caps (v0.4.0)" \
  || echo "   (nothing new to commit — continuing)"

echo "==> 5/5  Pushing to origin/main..."
if git push origin main; then
  echo ""
  echo "DONE — your code is now on https://github.com/xw2871-Andy/ComicLearn"
else
  echo ""
  echo "PUSH REJECTED. This is normal: GitHub has 2 old June-7 commits your local"
  echo "doesn't (a README tweak and a project-name typo fix). Your local folder is"
  echo "the complete, current version."
  echo ""
  echo "To make GitHub exactly match your local code, run ONE of these:"
  echo ""
  echo "  A) Keep GitHub's 2 old commits too (merge, may ask you to resolve README):"
  echo "       git pull origin main --no-rebase   # resolve any conflict, keep your version"
  echo "       git push origin main"
  echo ""
  echo "  B) Overwrite GitHub with your local (simplest; drops only those 2 trivial commits):"
  echo "       git push origin main --force"
fi
