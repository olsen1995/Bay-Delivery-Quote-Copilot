# LifeOS — Runtime Architecture (Source of Truth)

This document describes the **as-built** runtime architecture of the LifeOS backend as deployed (Render) and consumed by GPT Actions.

It exists to prevent drift between:

- what’s deployed
- what CI validates
- what documentation claims

## Runtime entry point

### FastAPI app

- `lifeos/main.py`

### Runtime assumption

- The service is executed with working directory / import base such that `lifeos/` is the effective root for imports.

This is why imports like:

- `from routes.mode_router import ModeRouter`

resolve correctly at runtime.

## Stable public API contract (do not break)

### `/ask`

- `GET /ask?message=...&user_id=...`
- `POST /ask` via `application/x-www-form-urlencoded`

Expected response shape (minimum stable fields):

- `summary` (string)
- `user_id` (string)
- `memory` (object)

### `/memory`

- `GET /memory?user_id=...`
- `POST /memory` with JSON body `{ "user_id": "...", "memory": { ... } }`
- `DELETE /memory?user_id=...`

## Static OpenAPI for GPT Actions

### Source location

- `public/.well-known/openapi.json`

### Served location

- `/.well-known/openapi.json`

### Policy

- Treat this OpenAPI file as a contract. Update it only when API behavior/shape changes.
- Keep `servers` defined.
- Keep response schemas explicit (`properties` / `additionalProperties`).
- Keep `x-openai-isConsequential: false` where appropriate for Actions.

## What is wired vs not wired (important)

### Wired (part of deployed request path)

- `lifeos/main.py`
- `lifeos/routes/mode_router.py` (contains `/ask` and `/memory` behavior as currently mounted)
- `lifeos/storage/memory_manager.py` (JSON persistence)
- `public/.well-known/openapi.json` (contract served to GPT Actions)

### Present but not necessarily mounted (verify before assuming)

The repo contains additional modules intended for future integration:

- `lifeos/modes/*`
- other route modules under `lifeos/routes/*`
- Canon subsystems under `lifeos/canon/*`

These may be used by CI or tooling, but should not be assumed part of the deployed request path unless explicitly mounted in `lifeos/main.py`.

## Canon subsystem

Canon lives under:

- `lifeos/canon/*`

CI may validate Canon snapshot/digest integrity using:

- workflows under `.github/workflows/*`
- helper scripts under `scripts/ci/*` (if present)

Canon can evolve independently, but must not break:

- CI snapshot/digest checks
- existing stable API contract

## Validation commands (local)

Run these from repo root unless otherwise specified.

### OpenAPI JSON validity

```bash
python -m json.tool public/.well-known/openapi.json
```

### OpenAPI schema/contract validation (if present)

```bash
python scripts/ci/validate_openapi.py
```

## Change policy

1. Do not change public endpoints casually.
2. Do not change `/ask` response shape without updating OpenAPI and any smoke tests.
3. Prefer incremental “one move = one commit”.
4. Keep docs aligned with reality; this file wins if other docs disagree.

## Last updated

- 2026-02-04
