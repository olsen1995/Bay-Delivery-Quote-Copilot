# Bay Delivery Quote Copilot — Project Vision

## What this repo is

**Bay Delivery Quote Copilot** is a small production web app + API for Bay Delivery in North Bay, Ontario.

It helps Bay Delivery:

- give customers quick, consistent estimates for common services
- collect simple job details and photos
- let customers accept, decline, or request a booking window
- give Austin and Dan a clean admin workflow for leads, jobs, follow-ups, risk review, scheduling, costing, and reporting
- protect business rules so Bay Delivery does not undercharge
- learn from completed-job costs before changing pricing
- support Render free-tier reality, including ephemeral disk and backup/restore workflows

This project is intentionally practical.

It is not a giant CRM.

It is not a sandbox.

It is not a pricing experiment.

The goal is a small business operating system that protects margin, reduces missed follow-ups, and makes daily decisions easier.

---

## Current state (May 2026)

The project is in **stable operations / roadmap refinement mode**.

The app has moved beyond a basic quote calculator. It now supports a stronger operating workflow:

- customer quote flow
- quote decisions and booking requests
- admin request/job management
- daily ops visibility
- follow-up shortcuts
- internal risk summaries
- completed-job profit review
- backup/recovery support
- protected pricing authority

Current verified baseline markers:

- Main is verified through PR #316 and current main commit `04511871e1c2e194f6a743f61a297bd4b3d1aa63`.
- Latest verified main context: PR #316 `create admin post origin fail closed hardening`, followed by docs/notes commit `0451187`.
- Current repo version: `0.12.0`.

Recent roadmap work completed:

1. **Admin Daily Ops Board**
   - Read-only desktop admin cards for operational queues.
   - Helps identify new requests, follow-ups, accepted-not-booked work, upcoming jobs, missing costs, owner review items, and stale quotes.

2. **Admin Ops Board Action Shortcuts**
   - Practical desktop admin shortcuts for follow-up/status workflows.
   - Keeps admin actions narrow and intentional.

3. **Customer Quote Flow Simplification**
   - Public quote flow is calmer, clearer, and lower-friction.
   - Customer copy avoids internal risk and pricing jargon.
   - Existing payload compatibility is preserved.

4. **Internal Quote Risk Summary**
   - Desktop admin shows a compact internal risk summary using existing advisory and risk-assessment data.
   - This helps Austin/Dan see access concerns, heavy-material concerns, disposal uncertainty, photos/details needs, and owner-review signals.
   - This does not change prices.

5. **Completed Job Profit Review Report**
   - Desktop admin includes an internal completed-job profit review report.
   - The report uses existing completed-job costing fields to show collected revenue, known costs, profit, margin, missing cost data, owner-review flags, and category breakdowns.
   - This is read-only and exists to support owner review and future pricing calibration.

6. **Launch Readiness Current-State Docs Refresh**
   - Baseline documentation and verification guidance were refreshed to support launch-safe operations.

7. **Booking Notification Status Visibility**
   - Internal workflow visibility for booking notification status was improved without changing pricing authority.

8. **Quote Page Step Heading Clarity Polish**
   - Customer quote-step heading clarity was improved while preserving payload compatibility and quote-flow behavior.

9. **Quote First-View Simplification Polish**
   - Customer quote first-view clarity was improved while preserving the public quote contract.

10. **Admin POST Origin Fail-Closed Hardening**
   - Admin POST origin enforcement was hardened to fail closed, with regression coverage updated.

Current repo version:

- `0.12.0`

---

## Current Stack

- **Backend:** FastAPI / Python
- **Frontend:** Static HTML/CSS/JavaScript served from `/static`
- **Storage:** SQLite local file
- **Hosting:** Render
- **Backups:** Local JSON export/import plus optional Google Drive Vault snapshot/restore when configured
- **Admin auth:** Basic Auth for admin surfaces and admin APIs
- **Customer security:** customer decision and booking flows use secure tokens where applicable

Render free tier has an ephemeral disk, so backup/export/restore workflows remain important.

SQLite remains the operational source of truth.

Google Calendar and Google Drive are support tools only.

---

## Executive principle

Customer side stays simple.

Admin side tells Austin and Dan what needs attention.

Pricing authority stays protected in:

- `app/quote_engine.py`

Completed-job reporting learns from real jobs before any pricing changes are made.

---

## What the app does today

### Customer side

1. Customer opens `/quote`.
2. Customer describes the job in simple language.
3. Customer provides helpful structured details such as:
   - service type
   - access difficulty
   - estimated hours
   - crew size where applicable
   - trailer/load indicators where applicable
   - mattress/box spring counts
   - scrap pickup details
   - photos when available
4. App calls `POST /quote/calculate`.
5. Customer sees:
   - `cash_total_cad`
   - `emt_total_cad`
   - clear customer-facing quote guidance
6. Customer can accept or decline.
7. Accepted quote/request information moves into the admin workflow for review, follow-up, approval, and eventual job handling.

Customer-facing language should stay plain, calm, and helpful.

Customer-facing pages must not expose internal risk, margin, owner-review, completed-job costing, dispatch, or pricing-advisory language.

---

### Admin side

1. Admin opens `/admin`.
2. Admin authenticates using Basic Auth.
3. Admin reviews:
   - Daily Ops Board
   - quote requests
   - quotes
   - jobs
   - completed-job costing
   - internal risk summaries
   - completed-job profit review report
   - backup/restore tools
4. Admin can:
   - review leads
   - approve/reject requests
   - track follow-up status
   - see accepted-not-booked work
   - create/track jobs through existing workflows
   - enter completed-job costing
   - review profit/margin evidence after jobs are complete
5. Admin reports help identify what needs attention, but they do not automatically change pricing.

Admin is allowed to show operational complexity.

Admin can show risk, missing info, owner-review flags, costing, and profit/margin evidence.

---

## Business Rules that must stay true

- **Cash:** no HST
- **EMT/e-transfer:** add 13% HST
- **Travel minimum:** at least $20 gas + $20 wear, for a $40 travel minimum
- **Big items:** require 2 workers
- **Labour cost anchors:** Austin/operator around $20/hr; helper around $16/hr
- **Mattress disposal:** $50 per mattress
- **Box spring disposal:** $50 per box spring
- **Scrap pickup:** curbside can be free; inside removal has a $30 charge
- Quotes must include margin and should not be at-cost
- Pricing authority must remain in `app/quote_engine.py`

The system should protect Bay Delivery from undercharging while still keeping customer-facing quotes believable.

---

## What is already done

The current stable baseline includes:

- Customer quote flow and `/quote/calculate`
- Customer accept/decline/request workflow
- Admin authentication and protected admin APIs
- Admin dashboard for quotes, requests, and jobs
- Admin Daily Ops Board
- Admin follow-up/action shortcuts
- Customer quote flow simplification
- Internal Quote Risk Summary
- Completed Job Profit Review Report
- Completed-job costing fields and admin handling
- Backup/export/import workflow
- Google Drive snapshot/restore support when configured
- Version parity checks
- GPT grounding pack parity checks
- CI and Unicode guard workflows
- Security hardening baselines
- Dependency audit hardening
- Static asset tests and regression coverage
- Pricing/business-rule regression tests

---

## Roadmap direction

The project roadmap is intentionally conservative.

The sequence is:

1. Admin Daily Ops Board
2. Admin Ops Board Action Shortcuts
3. Customer Quote Flow Simplification
4. Internal Quote Risk Summary
5. Completed Job Profit Review Report
6. Follow-Up Message Helper
7. Scheduling Fields + Accepted Not Booked Queue
8. Pricing PRs by service category
9. Internal GPT Upgrade
10. Photo Evidence / Photo Assistant

Completed so far:

- Admin Daily Ops Board
- Admin Ops Board Action Shortcuts
- Customer Quote Flow Simplification
- Internal Quote Risk Summary
- Completed Job Profit Review Report
- Launch Readiness Current-State Docs Refresh
- Booking Notification Status Visibility
- Quote Page Step Heading Clarity Polish

Next likely roadmap item:

- Follow-Up Message Helper

The Follow-Up Message Helper should generate copy-ready internal/admin messages for common situations such as:

- no reply
- need photos
- accepted but not booked
- customer asking for cheaper price
- completed job follow-up
- review request

It should not send messages automatically unless a future PR explicitly scopes that behavior.

---

## Pricing calibration direction

Pricing changes should not happen just because a report exists.

Completed-job reporting creates evidence.

Owner review turns evidence into judgment.

Pricing PRs happen later, one service category at a time.

Later pricing order:

1. Demolition / rip-out
2. Moving labour
3. Heavy/dense dump runs
4. Scrap pickups
5. Delivery

Each pricing PR should include:

- focused tests
- before/after examples
- service-specific reasoning
- protected no-go checks
- no unrelated cleanup
- no broad global repricing

Completed-job data should help answer:

- Which services are underpriced?
- Which jobs are painful even when profitable?
- Which jobs are missing cost data?
- Which categories create margin problems?
- Which assumptions need adjustment?

Completed-job reports are evidence, not automatic pricing authority.

---

## AI and GPT direction

GPT is internal-only and recommendation-only.

GPT can help Austin/Dan:

- summarize quote requests
- explain internal risk
- draft follow-up messages
- explain completed-job findings
- suggest questions to ask the customer
- support owner review

GPT must never:

- override the pricing engine
- create a second pricing system
- expose internal risk or profit details to customers
- mutate jobs/quotes automatically
- become the source of truth

Any GPT grounding update should be deliberate and paired with grounding pack parity checks.

---

## SEO and growth direction

SEO and growth work is valuable, especially for searches like:

- junk removal North Bay
- dump runs North Bay
- scrap pickup North Bay
- furniture removal North Bay
- appliance removal North Bay
- mattress removal North Bay

However, SEO/growth pages are backlog items unless Austin explicitly moves them ahead of the operational roadmap.

A future growth PR may add pages such as:

- `/junk-removal-north-bay`
- `/dump-runs-north-bay`
- `/scrap-pickup-north-bay`
- `/small-moves-north-bay`
- `/appliance-removal-north-bay`
- `/mattress-removal-north-bay`

Those pages should be simple, local, crawlable, customer-facing, and linked clearly to `/quote`.

They must not interfere with pricing, admin workflows, customer payloads, GPT grounding, or roadmap safety work.

---

## Done enough for now

The product is done enough when it reliably:

- gives customers clear estimates
- collects the right job details
- protects pricing rules
- avoids customer-facing complexity
- helps admin see what needs attention
- prevents missed follow-ups
- supports booking/job workflows
- allows completed-job closeout
- reports profit/margin evidence
- keeps backup/recovery practical
- remains understandable to operate and maintain

Today, that means:

- customer quote flow works end-to-end
- admin review/approval workflow works end-to-end
- daily ops visibility exists
- internal risk visibility exists
- completed-job profit reporting exists
- core security controls are active
- recovery paths exist for ephemeral hosting
- key pricing and workflow regressions are covered by tests

---

## Remaining improvements

### Near-term roadmap

1. Follow-Up Message Helper
2. Scheduling Fields + Accepted Not Booked Queue
3. Internal GPT upgrade for admin summaries and message drafting
4. Photo evidence / photo assistant, advisory-only

### Later pricing work

1. Demolition / rip-out pricing review
2. Moving labour pricing review
3. Heavy/dense dump run pricing review
4. Scrap pickup access-risk pricing review
5. Delivery distance/weather/enclosed-trailer pricing review

### Backlog / growth

1. Junk removal North Bay landing page
2. Dump runs North Bay landing page
3. Scrap pickup North Bay landing page
4. Google Business Profile / reviews / SEO support content
5. Service-area content and local proof pages

### Ongoing maintenance

1. Keep docs, version markers, and release notes aligned.
2. Keep dependency audit green.
3. Keep GPT grounding pack parity green.
4. Keep tests focused and meaningful.
5. Keep admin/customer/mobile boundaries protected.
6. Keep PRs narrow, auditable, and reversible.

---

## Repo conventions

- Prefer clear, boring API contracts over cleverness.
- Backend is the source of truth for business rules.
- Pricing authority stays in `app/quote_engine.py`.
- Avoid duplicate business rules across frontend/backend.
- When changing behavior, add or extend regression tests.
- Keep customer pages simple.
- Keep admin reports internal.
- Do not mix unrelated work in one PR.
- Open/update PRs and stop.
- Merge only after Austin explicitly approves.
- Post-merge verify `main` before starting the next feature.

---

## How to run locally

Start API:

- `python -m uvicorn app.main:app --reload`

Visit:

- Customer/home: `http://127.0.0.1:8000/`
- Quote: `http://127.0.0.1:8000/quote`
- Admin: `http://127.0.0.1:8000/admin`

Common validation from repo root:

- `python tools/check_version_parity.py`
- `python tools/check_gpt_grounding_pack_parity.py`
- `python -m compileall app tools scripts tests`
- `python -m pytest -q`

On the local Windows repo venv, use:

- `.\.venv\Scripts\python.exe tools\check_version_parity.py`
- `.\.venv\Scripts\python.exe tools\check_gpt_grounding_pack_parity.py`
- `.\.venv\Scripts\python.exe -m compileall app tools scripts tests`
- `.\.venv\Scripts\python.exe -m pytest -q`

---

## Final operating loop

Customer submits a simple quote.

The system captures useful structured facts.

Admin sees risk, missing info, and follow-up needs.

Austin/Dan approve, follow up, or book.

The job gets completed.

Actual costs are entered.

The system shows profit and underpricing patterns.

Pricing is improved carefully by category in later dedicated PRs.

That is the product vision.
