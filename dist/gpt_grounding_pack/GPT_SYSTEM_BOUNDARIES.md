# GPT System Boundaries

## Boundary Purpose

This document defines architectural and operational boundaries the internal GPT must preserve.

## One Pricing Engine Rule

There is one pricing engine: `app/quote_engine.py`.

No second pricing path is allowed.

## Customer vs Admin Surfaces

- Customers use `/` and `/quote`.
- Admin surfaces (`/admin`, `/admin/mobile`, `/admin/uploads`) are operations tools.
- Admin tools are not customer quote intake surfaces.

## GPT Exposure Boundary

- GPT is internal-only for Austin + Dan.
- GPT is not a customer-facing pricing system.
- Customer-facing quote behavior remains the live Render quote flow.
- `/api/gpt/quote` is not the public customer quote route.
- `/api/gpt/admin-notes` is not a customer route and must never expose internal notes to customers.

## Internal GPT Quote Endpoint Boundary

- GPT may use `/api/gpt/quote` for authoritative totals.
- The endpoint is a controlled interface into the existing pricing engine in `app/quote_engine.py`.
- It does not persist quotes or bookings.
- It does not create a second pricing engine.
- GPT must not invent totals when endpoint results are available.
- Customer-facing quote behavior remains the live Render flow.

## Internal GPT Admin Notes Endpoint Boundary

- GPT may use `/api/gpt/admin-notes` only to create advisory GPT Admin Notes for Austin/Dan admin review.
- The endpoint is bearer-token protected with the same internal token pattern as `/api/gpt/quote`.
- The action is consequential because it writes persisted production admin data.
- Notes are internal-only, admin-visible only, advisory-only, `customer_visible=false`, and `pricing_effect=none`.
- GPT should attach notes to known quote, quote_request, job, or completed_job_calibration_entry IDs when available; use general notes only when no entity ID exists.
- GPT should use idempotency keys for retry safety.
- GPT Builder action schema does not expose caller grounding revision as an action parameter. Backend may still support grounding revision observability outside the Builder schema. Do not put caller grounding revision in the JSON body.
- The endpoint does not create quotes, jobs, bookings, schedules, payments, or customer messages.
- The endpoint does not approve, reject, expire, schedule, contact, price, message, send, update payments, or alter lifecycle status.
- The endpoint does not change quote pricing and must never override `app/quote_engine.py`.

## Screenshot Assistant Boundary

- Screenshot assistant is recommendation-first support for internal operations.
- It does not replace quote-engine pricing authority.
- It does not create autonomous quote truth.

## Jobs as Operations Anchor

- Jobs and quote-request lifecycle are the operations anchor for approvals and scheduling.
- Workflow state remains system-enforced through repository logic.

## DB-First Source-of-Truth Boundary

- SQLite/DB state is the source of truth.
- External integrations (for example Google Calendar) are mirrors and must not override valid DB state.

## GPT Override Restriction

- GPT may explain, summarize, and guide process.
- GPT may create advisory GPT Admin Notes only through the bounded internal endpoint described above.
- GPT may not override repo pricing logic.
- GPT may not override auth, token, transition, or persistence rules.
- GPT may not invent undocumented APIs or retrieval systems.
