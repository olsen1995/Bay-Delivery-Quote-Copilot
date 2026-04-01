> ⚠️ Archived — This document reflects a previous state of the project and may no longer be accurate.
> Refer to `docs/CURRENT_STATE.md` for the latest source of truth.

# Repository Audit — 2026-03-22

> **Historical snapshot:** This document reflects repository state as of 2026-03-22. It is retained for history and may not match the current `main` branch.


## Scope

This audit covered repository health, test status, security-oriented guardrails, dependency integrity, and a light manual review of core backend flows. No pricing math or business rules were modified as part of this audit.

## Commands run

- `python -m compileall app tests`
- `pytest -q`
- `python -m pip check`
- `python tools/scan_bidi_controls.py`
- `rg -n --hidden -g '!*.png' -g '!*.jpg' -g '!*.jpeg' -g '!*.sqlite3' -g '!node_modules' -g '!__pycache__' "(AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z\-_]{35}|sk-[A-Za-z0-9]{20,}|BEGIN (RSA|OPENSSH|PRIVATE) KEY|password\s*=\s*['\"][^'\"]+['\"]|secret\s*=\s*['\"][^'\"]+['\"])" .`

## Results

### Automated checks

- `compileall` passed for `app/` and `tests/`.
- `pytest -q` passed: **256 tests passed** with **2 deprecation warnings** from `httpx` raw upload usage in upload-size tests.
- `pip check` reported **no broken requirements**.
- The bidi-control scan reported **no bidi control characters found**.
- A repository search for common secret and private-key patterns returned **no matches** in tracked source files.

### Manual review highlights

- The application has explicit request-size and rate-limit middleware for quote and admin write paths.
- Admin API routes are protected with Basic Auth plus an in-memory failed-attempt lockout.
- Database initialization and backup/restore logic are written with schema-aware helpers intended to keep inserts forward/backward compatible.
- The smoke-test script supports both read-only (`live-safe`) and stateful flows, which is a strong operational check for deployed environments.

## Findings

### Low-risk / informational

1. **Minor comment drift in `app/main.py`.**
   The file contained stale comments describing a past import-order fix that no longer matches the current file structure. This audit removes those comments to reduce confusion during future maintenance.

2. **Rate limiting and admin lockout are process-local.**
   Current protections are in-memory, which is fine for a single-process deployment but may not enforce globally across multiple instances or after process restarts. This is not a correctness bug in the current codebase, but it is worth noting if deployment topology changes.

3. **Tests expose an upstream deprecation warning.**
   Two tests still trigger `httpx`'s deprecation warning for raw byte uploads. The suite passes today, but a future `httpx` upgrade may eventually require adjusting those test helpers.

## Recommendations

1. Add a lightweight CI job that runs the same baseline used here: compile, pytest, bidi scan, and a dependency integrity or vulnerability step.
2. If the app is ever scaled beyond a single process/instance, consider moving auth lockout and rate-limiting state to a shared store.
3. When convenient, update the affected upload tests to use the newer `httpx` content/file API to eliminate the current warnings.

## Net change from this audit

- Added this audit report for maintainers.
- Removed stale maintenance comments from `app/main.py`.
- No API contracts, pricing behavior, schema rules, or business logic were changed.
