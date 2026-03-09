# Bay Delivery Quote Copilot — Project Rules

Agents must read this file before performing architectural changes, security reviews, or refactors.

This document defines architecture invariants and security rules for the repository.

Violating these rules can break production workflows.

---

## Core Architecture Rules

SQLite is the source of truth.

Google Calendar is a mirror only.

Database writes must occur **before external API calls**.

Calendar sync failures must **not corrupt or roll back valid DB state**.

Route handlers must stay thin.

Business logic belongs in:

app/services/

SQL and persistence logic belong in:

app/storage/

External API wrappers belong in:

app/integrations/

---

## Refactor Workflow Rules

When performing refactors:

1. Read this file first.
2. Explain the proposed refactor plan.
3. Move one feature area at a time.
4. Preserve endpoint paths and request/response behavior.
5. Ensure compilation succeeds after each change.
6. Ensure tests continue to pass after each step.

Never refactor the entire application at once.

Preferred order of refactor:

1. Scheduling
2. Quotes and booking
3. Uploads and attachments
4. Backup and restore
5. Optional utilities

---

## Service Layer Rules

Services orchestrate workflows.

Services may call:

- storage functions
- integration clients

Services must NOT:

- perform raw SQL
- contain FastAPI route definitions
- directly manipulate request objects

Routes may call services.

Routes must NOT contain business logic.

---

## Storage Layer Rules

All SQL belongs in `app/storage`.

Rules:

- Use parameterized queries
- Use allowlists for dynamic field updates
- Avoid building SQL strings dynamically
- Use safe transactions

SQLite must run with:

- WAL mode
- busy_timeout
- safe transaction handling

---

## Scheduling Rules

Scheduling must follow the DB-first workflow.

Correct pattern:

1. Update job record in database.
2. Attempt Google Calendar sync.
3. If Calendar fails:
   - update calendar_sync_status
   - record calendar_last_error
   - DO NOT roll back database state.

Cancel workflow must preserve scheduling history.

---

## Security Rules

Admin endpoints must require authentication.

Customer flows must use secure tokens:

- accept_token
- booking_token

Tokens must be validated **before any state-changing write**.

Customer PII rules:

Customer name and phone must not be editable after quote creation.

External integrations must receive **minimal PII**.

Google Calendar events must never contain:

- phone numbers
- full notes
- sensitive customer data

---

## Frontend Compatibility Rules

The frontend uses static HTML + JavaScript.

Backend API compatibility must be preserved.

Never rename form fields used by API endpoints unless explicitly instructed.

Frontend styling changes must not alter API payloads.

---

## Testing Requirements

All code changes must pass:

python -m compileall app tests

pytest -q

If tests fail, fix with minimal changes.

---

## AI Image Estimation Rules

AI may suggest structured inputs only.

AI must never determine final price.

Final pricing must always be calculated by the pricing engine.

Image analysis must live in:

app/services/ai_estimation_service.py

---

## Code Quality Rules

Keep modules small and focused.

Avoid growing main.py with business logic.

Prefer explicit code over clever abstractions.

Preserve existing API behavior unless explicitly requested otherwise.

Keep tests passing at all times.

---

## Agent Safety Rules

Agents must prefer:

- minimal diffs
- incremental refactors
- vertical slice changes

Agents must avoid:

- rewriting entire files
- renaming APIs
- changing request payload formats
- introducing unnecessary dependencies
