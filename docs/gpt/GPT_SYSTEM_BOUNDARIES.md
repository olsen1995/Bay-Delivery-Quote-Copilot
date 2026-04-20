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

## Internal GPT Quote Endpoint Boundary

- GPT may use `/api/gpt/quote` for authoritative totals.
- The endpoint is a controlled interface into the existing pricing engine in `app/quote_engine.py`.
- It does not persist quotes or bookings.
- It does not create a second pricing engine.
- GPT must not invent totals when endpoint results are available.
- Customer-facing quote behavior remains the live Render flow.

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
- GPT may not override repo pricing logic.
- GPT may not override auth, token, transition, or persistence rules.
- GPT may not invent undocumented APIs or retrieval systems.
