# Bay Delivery Quote Copilot

## Stack

- Python FastAPI backend
- SQLite storage
- Optional Google Drive integration
- Pytest test suite

## Repo conventions

- Application code lives in `app/`
- Tests live in `tests/`
- Developer tooling belongs in `tools/`
- Do not place temporary debug helpers in `scripts/`
- Keep diffs minimal and PR-safe
- Avoid formatting-only rewrites

## Important architecture notes

- FastAPI middleware ordering matters: the LAST middleware added runs FIRST
- SQLite should use WAL mode and busy_timeout in production
- CORS must never use wildcard origins when `allow_credentials=True`
- Google Drive integration is optional and should fail gracefully
- Admin endpoints must remain authenticated
- Abuse protections should remain in place for public and admin endpoints

## Test workflow

Always run after code changes:

python -m compileall app tests
pytest -q

## Preferred change style

- Minimal diffs
- Avoid unnecessary refactors
- Preserve existing architecture unless explicitly asked
- Show patch before applying edits when possible
