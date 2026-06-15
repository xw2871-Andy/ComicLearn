# Changelog

All notable ComicLearn releases are recorded here. Each new public GitHub update
should bump `VERSION`, add an entry to `RELEASES.json`, and prepend a matching
section below.

## [0.4.2] - 2026-06-16

### Added

- Added a token-protected admin usage endpoint at `/api/admin/usage`.
- Added production account usage reporting without exposing password hashes,
  session tokens, or provider secrets.

## [0.4.1] - 2026-06-15

### Added

- Added shared release metadata so Studio and GitHub can show visible version
  history.
- Added a version history modal in Studio from `/api/releases`.

### Fixed

- Retried Anthropic requests without `temperature` when a newer model rejects
  that deprecated parameter.
- Made the web app and Python package read from the same `VERSION` source.

## [0.4.0] - 2026-06-14

### Added

- Launched the hosted ComicLearn Studio deployment through Vercel and Railway.
- Added invite-only signup, daily usage caps, and persistent Railway storage.
- Added hosted provider configuration checks while keeping API keys on the
  backend.

### Changed

- Updated the generation stack for Claude text, Gemini image generation,
  Mathpix OCR, and story/art QA.
