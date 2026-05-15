# GPT Current State

## Status Snapshot

Bay Delivery Quote Copilot is stable and production-usable.

The project is in a hardening / controlled-expansion phase focused on drift prevention, operational clarity, and reliability rather than broad feature expansion.

## What Is Already Complete

- Live customer quote flow is established on Render (`/` + `/quote`).
- Single pricing authority is established in `app/quote_engine.py` with config-backed service rules.
- Pricing authority enforces a universal $60 CAD minimum floor on final quote outputs.
- Admin operations surfaces exist (`/admin`, `/admin/mobile`, `/admin/uploads`) with protected admin actions.
- Desktop admin now includes a read-only Daily Ops Queue backed by `GET /admin/api/ops-queue`.
- Desktop admin now includes a Follow-Up Message Helper that drafts copy-ready messages for common scenarios.
- Desktop admin now includes an Accepted, Not Booked queue sourced from `accepted_not_booked_items` on the existing ops-queue payload.
- Accepted-not-booked detail rows are capped at 50 while `counts.accepted_not_booked` remains the uncapped true total.
- Customer Quote Flow Simplification is complete: the public quote page now uses friendlier customer-facing wording and plain-language progressive disclosure while preserving structured intake field IDs, payload compatibility, and the existing `/quote/calculate` path.
- Quote-request and job lifecycle foundations are implemented and persisted in SQLite.
- Security, abuse controls, and deployment notes are documented and in active use.
- Completed roadmap work reflected in the repo today:
	- Admin Daily Ops Board read model
	- Completed Job Profit Review Report
	- Follow-Up Message Helper
	- Accepted, Not Booked scheduling queue
	- Accepted-not-booked detail row cap
	- Internal Quote Risk Summary
	- Customer Quote Flow Simplification
- Completed-job profit reporting is internal and read-only evidence for owner review and future calibration; it does not change quote pricing.
- Internal Quote Risk Summary is admin-only, read-only/recomputed, desktop-admin-only, and exposed on quote detail as `quote_risk_summary`; it is not customer-visible, not persisted, and has no pricing effect.
- PR #287 Customer Quote Flow Simplification did not change backend behavior, pricing, schema, admin, mobile admin, GPT grounding-source schema, Render config, workflows, requirements, or `VERSION`; no forbidden internal risk/pricing/advisory jargon was found in customer quote HTML/JS, and production live-safe smoke passed after deployment.

## Partial Or Still Future

- Admin action shortcuts are only partial, not complete.
- Lead source tracking, repeat customer marker, internal customer notes, job difficulty score, full missing-info detector, job closeout checklist, and review request tracking remain future work.
- Customer-facing GPT/chatbot, automatic SMS/email sending, and auto-calendar scheduling remain future work.
- Pricing PRs by service category have not started.
- Internal GPT upgrade has not started beyond current grounding/state docs.
- Photo Evidence / Photo Assistant remains future advisory-only work.

## Current Priorities

- Keep repo behavior aligned with docs and deployment reality.
- Prevent memory drift and undocumented assumptions.
- Make narrow, auditable refinements only.
- Preserve one-pricing-engine discipline and protected pricing authority.
- Maintain clear customer/admin operational boundaries.
- Keep Daily Ops Queue items as admin attention flags only; use existing admin surfaces for any manual follow-up.
- Keep the Follow-Up Message Helper advisory-only: copy-ready drafts, no automated sending, no saved message history, and no backend mutation.
- Keep completed-job reporting advisory-only and separate from pricing authority.
- Keep Internal Quote Risk Summary advisory-only and separate from pricing authority; `customer_visible` remains false and `pricing_effect` remains `none`.
- Keep pricing changes deferred to later category-specific PRs after evidence review.
- Next recommended task after this docs refresh: Lead source + repeat customer tracking, because the customer quote flow is now cleaner and admin risk review is stronger; the next best business value is learning where leads come from and identifying repeat customers before pricing changes or heavier admin mutations.
- Admin action shortcuts completion is useful, but it can drift into backend mutations and operational workflow changes. Job closeout checklist improvements are valuable, but likely touch job/cost capture flows and should wait until lead/repeat customer signal is captured.

## What Should Not Happen Next

- No second pricing engine.
- No customer-facing GPT pricing path.
- No broad speculative architecture work.
- No unnecessary flow rewrites in stable areas.
- No mixing unrelated runtime changes into documentation tasks.
- No GPT or Daily Ops Queue actions that approve, reject, expire, schedule, contact, price, message, or mutate records.
- No automated follow-up sending, no saved follow-up message history, and no customer-facing exposure of internal helper content.
- No automatic pricing changes from completed-job reporting.

## GPT Grounding Goal

GPT grounding is an internal alignment goal for Austin + Dan.

It is not a customer-facing product behavior change.

The purpose is to improve consistency and reduce drift while preserving existing production flows.

Pricing authority remains unchanged in `app/quote_engine.py`.

An internal-only `POST /api/gpt/quote` endpoint now exists as a non-persistent interface into that pricing authority.

When the endpoint is available, GPT should use its returned totals rather than inventing totals or generating independent pricing.

This internal endpoint does not replace the customer quote flow, booking flow, or live Render customer path, and it is not a customer-facing quote route.

## Daily Ops Queue Grounding

The desktop admin Daily Ops Queue is a read-only operations attention list.

- Endpoint: `GET /admin/api/ops-queue`.
- Access: admin-auth required.
- Surface: desktop `/admin` only; it is not part of mobile admin.
- Loading: best-effort frontend loading so core admin data remains usable if the queue fails.
- Data source: targeted read-only SQLite queries through the existing `app/storage.py` implementation path.
- Sections: accepted requests needing approval, follow-up marked / needs attention, accepted or approved work not yet booked, completed jobs missing costing, jobs missing schedule, jobs missing booking preferences, and stale pending estimates.

The accepted-not-booked queue is additive inside the existing ops-queue response.

- Payload field: `accepted_not_booked_items`.
- Scope: accepted or approved unscheduled work with scheduling readiness and missing scheduling fields.
- Detail cap: return at most 50 detail rows ordered by `datetime(submitted_at) DESC, item_type ASC, item_id ASC`.
- Count semantics: `counts.accepted_not_booked` remains the true uncapped total.

For "What should I do today?" style questions, GPT should tell Austin/Dan to check the Daily Ops Queue first, then use the existing admin sections for manual review and follow-up.

The queue does not approve, reject, expire, schedule, contact, price, message, send, or mutate records. It only shows attention flags from existing admin data.

## Follow-Up Message Helper Grounding

The desktop admin Follow-Up Message Helper is internal-only and advisory-only.

- Surface: desktop `/admin` only; it is not part of mobile admin or customer quote pages.
- Behavior: generates copy-ready message drafts for common follow-up situations.
- Delivery: no automated sending.
- Persistence: no saved message history.
- Mutations: no backend mutation or schema change.

GPT may describe the helper as a drafting aid, but it must not present it as an auto-send system or as customer-facing behavior.

## Internal Quote Risk Summary Grounding

The desktop admin Internal Quote Risk Summary is internal-only, advisory-only, and read-only.

- Endpoint field: `quote_risk_summary` on `GET /admin/api/quotes/{quote_id}`.
- Access: admin-auth quote detail only.
- Surface: desktop `/admin` quote detail only; it is not part of customer quote pages, quote view, GPT quote response, or mobile admin.
- Persistence: server-derived and recomputed from existing persisted context; it is not stored in request or job JSON.
- Scope: risk level, practical reasons, missing info, suggested action, crew/trailer guidance, and pricing caution.
- Photo/scheduling context: persisted scheduling and photo context are considered so preferred date/window/photos are not falsely reported missing.
- Suggested action: `request_photos` is used only when photos are actually missing.
- Visibility and pricing: `customer_visible` remains false and `pricing_effect` remains `none`.
- Styling semantics: low, medium, high, and owner-review risk levels use risk-specific badge classes.

The PR #285 refresh also restored `normalizeBooleanLike()` for Follow-Up Message Helper prompt builders. The summary does not change pricing authority, quote totals, schema, customer flow, mobile admin, GPT grounding schema, Render config, workflows, requirements, or `VERSION`.

## Completed-Job Profit Review Grounding

The desktop admin Completed Job Profit Review report is internal-only and read-only.

- Endpoint: `GET /admin/api/completed-job-profit-report`.
- Access: admin-auth required.
- Surface: desktop `/admin` only; it is not part of customer quote pages or mobile admin.
- Scope: completed-job costing/report evidence (known cost/profit/margin, missing-cost flags, owner-review signals, category breakdown).

This report informs owner review and later category-specific pricing PR planning. It does not calculate authoritative quote totals and does not override `app/quote_engine.py`.

## Conservative Truth Rule

When current state is ambiguous, use conservative wording and verify against repository truth instead of guessing.
