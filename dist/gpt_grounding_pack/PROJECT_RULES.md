# Bay Delivery Quote Copilot — Project Rules

Agents must read this file before performing architectural changes, security reviews, refactors, deployment-sensitive fixes, schema changes, or pricing changes.

This document defines architecture invariants, security rules, pricing and business guardrails, and change-scope rules for the repository.

Violating these rules can break production workflows, pricing integrity, or deployment safety.

---

## Core Architecture Rules

SQLite is the source of truth.

Google Calendar is a mirror only.

Database writes must occur before external API calls.

Calendar sync failures must not corrupt or roll back valid database state.

Route handlers must remain thin orchestration layers.

Business logic belongs in:

- app/services/

SQL and persistence logic belong in:

- app/storage/

External API wrappers belong in:

- app/integrations/

Do not move business logic into route handlers.

Do not move SQL or persistence policy into services or routes.

---

## Layer Responsibilities

### Routes

Routes may:

- validate and bind request inputs
- call services
- return HTTP responses

Routes must not:

- contain durable business policy
- perform raw SQL
- directly orchestrate external integrations
- contain pricing logic beyond passing structured inputs to services

### Services

Services orchestrate workflows.

Services may call:

- storage functions
- integration clients

Services must not:

- perform raw SQL
- contain FastAPI route definitions
- directly manipulate framework request objects
- duplicate storage-layer responsibilities

### Storage

All SQL belongs in app/storage.

Storage code may:

- read and write SQLite
- manage transactions
- enforce persistence-safe allowlists

Storage code must not:

- call external APIs
- contain route logic
- contain frontend assumptions

### Integrations

External API wrappers belong in app/integrations.

Integration code must be isolated from route and storage concerns.

Integration failures must not silently corrupt database state.

---

## Pricing and Business Rules

Pricing changes must be narrow, auditable, and intentionally scoped.

Do not broadly reprice multiple service lanes unless explicitly requested.

Preserve these business principles:

- Bay Delivery should not try to be the cheapest mover.
- Moving is a selective lane and should protect margin.
- Tiny junk jobs must remain believable.
- Large haul-away, cleanup, and estate jobs must not flatten too cheaply.
- Convenience, awkwardness, dense materials, access, disposal risk, and real labor must matter.

Prefer:

- floors
- anchors
- narrowly scoped adders
- service-specific adjustments
- targeted calibration backed by tests

Avoid:

- noisy global repricing
- broad multipliers applied across unrelated lanes
- flattening large-job pricing curves
- mixing unrelated pricing changes in one pass

Do not change unrelated service lanes in the same pricing task.

Preserve recent pricing calibrations unless explicitly instructed otherwise.

---

## Refactor Workflow Rules

When performing refactors:

1. Read this file first.
2. Explain the proposed refactor plan.
3. Move one feature area at a time.
4. Preserve endpoint paths and request and response behavior.
5. Ensure the app still imports and compiles after each step.
6. Ensure tests continue to pass after each step.

Never refactor the entire application at once.

Preferred order of refactor:

1. Scheduling
2. Quotes and booking
3. Uploads and attachments
4. Backup and restore
5. Optional utilities

Do not mix refactors with pricing, deployment hardening, or schema-tightening work.

---

## Storage Layer Rules

All SQL belongs in app/storage.

Rules:

- Use parameterized queries.
- Use allowlists for dynamic field updates.
- Avoid dynamic SQL construction except for explicitly allowlisted field selection or update patterns.
- Use safe transactions.

SQLite must run with:

- WAL mode
- busy timeout
- safe transaction handling

Schema changes must be backward-compatible unless explicitly approved.

Do not rename or drop columns used by live workflows without a dedicated migration plan.

Do not couple schema changes with unrelated pricing, UI, or deployment work.

---

## Scheduling Rules

Scheduling must follow the database-first workflow.

Correct pattern:

1. Update the job record in the database.
2. Attempt Google Calendar sync.
3. If Calendar fails:
   - update calendar_sync_status
   - record calendar_last_error
   - do not roll back valid database state

Cancel workflow must preserve scheduling history.

Calendar is a mirror, not the source of truth.

---

## Schema Compatibility Rules

Request and response schemas are part of the public contract.

Do not tighten validation or forbid previously accepted fields without:

- inspecting current callers
- checking logs and tests for compatibility risk
- scoping the change as a separate narrow pass

Prefer additive schema changes over breaking changes.

Schema-tightening work must not be mixed with unrelated pricing, UI, refactor, or deployment work.

Unknown-field handling changes require explicit review of compatibility risk.

---

## Security Rules

Admin endpoints must require authentication and fail closed.

Customer flows must use secure tokens:

- accept_token
- booking_token

Tokens must be validated before any state-changing write.

Auth and token checks must happen before:

- state-changing writes
- file uploads
- privileged data access

Customer PII rules:

- customer name and phone must not be editable after quote creation
- external integrations must receive minimal PII

Google Calendar events must never contain:

- phone numbers
- full notes
- sensitive customer data

Do not weaken:

- request size limits
- admin lockout protections
- trusted proxy and client IP handling
- token authorization checks
- security headers

Do not expose secrets in logs, tests, fixtures, screenshots, or documentation.

Security fixes must be narrow and auditable.

---

## Deployment and Environment Rules

Production behavior may depend on environment variables.

Agents must inspect deployment-sensitive environment configuration before proposing code changes for:

- CORS
- proxy and forwarded IP trust
- auth credentials
- storage backend selection
- Google integration settings
- deployment-only security behavior

Prefer env-only fixes when the issue is operational and the code already supports the intended behavior.

Production configs must not rely on localhost development defaults.

Do not mix deployment hardening with unrelated pricing, UI, refactor, or schema-tightening work.

When production safety depends on environment configuration, document the expected production value clearly.

---

## Frontend Compatibility Rules

The frontend uses static HTML, CSS, and JavaScript.

Backend API compatibility must be preserved.

Never rename form fields used by API endpoints unless explicitly instructed.

Never change payload shape, field names, or response contract without explicit approval.

Frontend styling changes must not alter API payloads.

Do not mix frontend polish with backend behavior changes unless explicitly requested.

---

## AI Image Estimation Rules

AI may suggest structured inputs only.

AI must never determine final price.

Final pricing must always be calculated by the pricing engine.

Image analysis must live in:

- app/services/ai_estimation_service.py

AI-derived inputs must remain auditable and overridable by deterministic pricing rules.

---

## Change Scope Rules

Each task should have one clear purpose.

Do not combine in one PR or change set:

- pricing changes
- deployment and security hardening
- schema tightening
- UI behavior changes
- refactors

Prefer this sequence:

1. inspect first
2. confirm root cause
3. implement the smallest safe diff only
4. verify with targeted tests or live-safe checks

No broad refactors during focused fixes.

No formatting-only churn.

No opportunistic cleanup during narrow production fixes.

Prefer vertical slices and incremental changes over sweeping edits.

---

## Testing Requirements

All code changes must pass:
python -m compileall app tests
pytest -q

In addition:

- pricing changes must add or update targeted pricing tests
- API contract changes must add or update validation and contract coverage
- security changes should include targeted regression coverage when practical
- deployment-only fixes should include a documented live verification procedure if no code changes are made

If tests fail, fix with minimal changes.

Do not widen PR scope just to improve unrelated tests.

---

## Code Quality Rules

Keep modules small and focused.

Avoid growing main.py with business logic.

Prefer explicit code over clever abstractions.

Preserve existing API behavior unless explicitly requested otherwise.

Keep tests passing at all times.

Do not introduce unnecessary dependencies.

Do not rewrite entire files when a narrow diff is sufficient.

---

## Agent Workflow Rules

Agents must prefer:

- minimal diffs
- incremental refactors
- vertical-slice changes
- narrow, auditable fixes
- inspect-first workflow

Agents must avoid:

- rewriting entire files
- renaming APIs without approval
- changing request payload formats without approval
- introducing unnecessary dependencies
- mixing unrelated concerns in one task

If the root cause is not yet confirmed, inspect before changing code.

If an env-only or ops-only fix is sufficient, do not invent a code PR.

If something is risky or ambiguous, preserve it and report it rather than forcing cleanup or behavior change.
