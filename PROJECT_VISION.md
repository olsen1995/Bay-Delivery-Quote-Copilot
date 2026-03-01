# Bay Delivery Quote Copilot — Project Vision

## What this repo is

**Bay Delivery Quote Copilot** is a small web app + API for Bay Delivery (North Bay, Ontario) that:

- Gives customers quick, consistent **estimates** for common services
- Lets customers **request a booking window** (accept/decline quote → request becomes a booking request)
- Gives the operator (admin) a clean dashboard to **review, approve/reject, and track jobs**
- Protects business rules so we don’t undercharge, and supports “Render free tier” reality (ephemeral disk)

This project is intentionally practical: **quotes + booking requests + job tracking + backups** — not a giant CRM.

---

## Current Stack

- **Backend:** FastAPI (Python)
- **Frontend:** Static HTML/CSS/JS served from `/static`
- **Storage:** SQLite (local file)
- **Hosting:** Render (free tier = **ephemeral disk**, DB resets on redeploy)
- **Backups:** Local JSON export/import + optional Google Drive Vault snapshot (when configured)

---

## What the app does today (core workflow)

### Customer side

1. Customer opens `/quote`
2. Fills job details (service type, hours, crew size, add-ons)
3. App calls `POST /quote/calculate`
4. Customer sees totals:
   - `cash_total_cad` (cash = tax-free)
   - `emt_total_cad` (EMT adds 13% HST)
5. Optional: customer uploads up to 5 photos (Drive required)
6. Customer chooses **accept** or **decline** via `POST /quote/{quote_id}/decision`
   - Accept creates/updates a `quote_request` record

### Admin side

1. Admin opens `/admin`
2. Admin authenticates using Basic Auth (`ADMIN_USERNAME` / `ADMIN_PASSWORD`)
3. Admin reviews:
   - Recent quotes
   - Booking requests
   - Jobs
   - Uploads (if Drive configured)
4. Admin approves/rejects booking requests
   - Approve creates a job record automatically

---

## Business Rules (must stay true)

- **Cash:** no tax
- **EMT:** adds 13% HST
- **Minimums:** always include at least **$20 gas + $20 wear & tear**
- **Big items:** require **2 workers**
- **Labour floors:** for 2 workers, minimum labour cost floor is **$40 cost** (business rule; profit margin is added in pricing)
- **Scrap pickup:** curbside = $0 (picked up next time in area), inside = $30 flat
- Quotes should include **margin**, not “at cost”

---

## What “Done / Completed” looks like (end state)

### 1) Quote contract is stable

- `/quote/calculate` accepts the exact fields the UI sends
- Returns a single consistent JSON contract used by the UI, tests, and docs
- Aliases and normalization **cannot bypass validation** (ex: “moving” must still require pickup/dropoff)

### 2) Booking lifecycle is a strict state machine

Quote request statuses are consistent and enforced:

- `customer_pending`
- `customer_accepted`
- `customer_declined`
- `admin_approved`
- `rejected`

No silent drift. Every transition is validated, and timestamps clear correctly.

### 3) Admin dashboard matches backend routes

Admin UI only calls endpoints that exist.
No “token-only” ghost auth references in UI/docs/scripts if backend is Basic-only.

### 4) Render recovery is real

Because Render free tier resets DB:

- Admin can export DB to JSON
- Admin can import DB JSON backup
- Optional: Drive Vault snapshot/list/restore when Drive configured

### 5) Undercharge protection (tests)

We have a small suite of pricing invariant tests that:

- Catch accidental removal of gas/wear minimums
- Catch HST rule regressions
- Catch scrap pickup rule regressions
- Catch moving 4-hour minimum + 2-worker minimum regressions

### 6) Demo-ready reliability

- Health endpoint indicates:
  - version
  - whether Drive is configured
- Errors return clean JSON, not raw stack traces
- Minimal logging that helps debug production failures quickly

---

## Roadmap (execution order)

1. **Contract correctness** (quote calculate + UI wiring + alias validation)
2. **Admin UI ↔ backend parity** (remove non-existent routes or implement them)
3. **Auth consistency** (Basic-only or token-only; pick one and purge leftovers)
4. **Backup/restore completeness** (DB export/import + Drive snapshot/list)
5. **State machine enforcement** (request/job transitions locked)
6. **Pricing invariant tests** (undercharge protection)
7. **Security hardening** (CORS tightening, import validation, upload sanitization)
8. **Release checklist + runbook** (how to deploy, how to recover)

---

## Repo Conventions

- Prefer clear, boring API contracts over cleverness
- When changing behavior, add/extend a regression test
- Avoid duplicate business rules across frontend/backend (backend is the source of truth)

---

## How to run locally (typical)

- Start API:
  - `python -m uvicorn app.main:app --reload`
- Visit:
  - Customer: `http://127.0.0.1:8000/`
  - Quote: `http://127.0.0.1:8000/quote`
  - Admin: `http://127.0.0.1:8000/admin`
