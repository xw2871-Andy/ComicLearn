# Versioning

ComicLearn uses semantic versions in `MAJOR.MINOR.PATCH` form.

Before every public GitHub update:

1. Choose the next version in `VERSION`.
2. Add the newest entry at the top of `RELEASES.json`.
3. Add the matching section at the top of `CHANGELOG.md`.
4. Commit with a message like `Release v0.4.2: Short title`.
5. Tag the commit with `v0.4.2` and push the tag.

Use this rule of thumb:

- Patch: bug fix or small operational improvement.
- Minor: new user-visible workflow or meaningful product capability.
- Major: breaking change, data migration, or incompatible deployment change.

Studio exposes the same records through `/api/releases`, and the sidebar
version opens the in-app version history.
