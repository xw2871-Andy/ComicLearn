#!/usr/bin/env bash
# Minimal smoke run. Requires ANTHROPIC_API_KEY in your env.
set -euo pipefail

# 1. Topic-only mode
c2c topic "Riemann Sums" --grade "AP Calculus AB"

# 2. Markdown outline mode
c2c markdown ./examples/sample_lesson_outline.md \
    --grade "AP Calculus AB" \
    --topic "Riemann Sums"
