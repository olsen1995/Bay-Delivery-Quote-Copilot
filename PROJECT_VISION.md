# Bay Delivery Quote Copilot — Project Vision

## What this repo is

**Bay Delivery Quote Copilot** is a small web app + API for Bay Delivery (North Bay, Ontario) that:

- Gives customers quick, consistent **estimates** for common services
- Lets customers **request a booking window** (accept/decline quote → request becomes a booking request)
- Gives the operator (admin) a clean dashboard to **review, approve/reject, and track jobs**
- Protects business rules so we don’t undercharge, and supports “Render free tier” reality (ephemeral disk)

This project is intentionally practical: **quotes + booking requests + job tracking + backups** — not a giant CRM.

---

## Current state (March 2026)

- The project is in **stable cleanup / refinement mode** (no longer rescue mode).
- Core customer quote flow and admin review/approval flow are stable and in regular use.
- Security hardening baselines are in place, including CSP fixes for quote/admin/admin-uploads, request protections, and abuse-control cleanup.
- Admin UX and frontend polish passes are complete.
- Smoke test contract alignment, version/docs/release alignment, and dependency cleanup are complete.

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

## What is already done (stable baseline)

- Quote contract behavior is stable across UI, API, smoke test, and regression tests.
- Booking lifecycle status transitions are enforced and tested (`customer_pending` → `customer_accepted/customer_declined` → `admin_approved/rejected`).
- Admin dashboard and backend route behavior are aligned with Basic Auth protection for admin APIs.
- Backup/recovery workflow is practical for Render reality (DB JSON export/import plus optional Drive snapshot/restore when configured).
- Undercharge protection invariants are covered by tests for core pricing rules.
- Reliability baseline is in place: health/version reporting, clean JSON errors, and practical operational logging.

## Done enough for now

The product is "done enough" when it reliably protects margin, supports real booking operations, and remains understandable to operate and maintain without overengineering.

Today that means:

- Customer quotes and decisions work end-to-end.
- Admin review/approval workflow works end-to-end.
- Core security/hardening controls are active.
- Recovery paths exist for ephemeral hosting.
- Key pricing and workflow regressions are covered by tests.

---

## Remaining non-urgent improvements

1. Expand runbook depth for operations (restore drills, failure playbooks, release cadence notes).
2. Keep tightening edge-case validation and abuse controls as real usage data accumulates.
3. Continue small UX refinements in quote/admin surfaces without changing API contracts.
4. Add focused regression tests only where new bugs are discovered.
5. Keep docs/version/release artifacts aligned as part of normal maintenance.

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
