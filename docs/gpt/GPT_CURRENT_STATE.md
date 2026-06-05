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
- Desktop admin now includes Daily Ops Board shortcut chips powered by `opsBoardShortcutsByKey` for faster manual navigation from queue cards into existing admin workflows.
- Desktop admin now includes a Follow-Up Message Helper that drafts copy-ready messages for common scenarios.
- Desktop admin now includes an Accepted, Not Booked queue sourced from `accepted_not_booked_items` on the existing ops-queue payload.
- Accepted-not-booked detail rows are capped at 50 while `counts.accepted_not_booked` remains the uncapped true total.
- Desktop admin now includes a Manual Completed Job Calibration Log backed by `GET /admin/api/manual-completed-jobs`, `POST /admin/api/manual-completed-jobs`, and persisted `completed_job_calibration_entries` storage.
- Customer Quote Flow Simplification is complete: the public quote page now uses friendlier customer-facing wording and plain-language progressive disclosure while preserving structured intake field IDs, payload compatibility, and the existing `/quote/calculate` path.
- Quote-request and job lifecycle foundations are implemented and persisted in SQLite.
- Security, abuse controls, and deployment notes are documented and in active use.
- Prelaunch Test Data Cleanup tooling is approved and documented: operators should use the allowlisted dry-run/apply workflow in `scripts/create_prelaunch_test_data_cleanup.py` and `docs/prelaunch_test_data_cleanup.md` rather than ad hoc cleanup steps.
- Completed roadmap work reflected in the repo today:
  - Admin Daily Ops Board read model
  - Admin Action Shortcuts Completion (PR #293)
  - Completed Job Profit Review Report
  - Follow-Up Message Helper
  - Accepted, Not Booked scheduling queue
  - Accepted-not-booked detail row cap
  - Internal Quote Risk Summary
  - Manual Completed Job Calibration Log (PR #296)
  - Prelaunch Test Data Cleanup Tooling (PR #297)
  - Customer Quote Flow Simplification
  - Lead source + repeat customer tracking (no-schema v1)
- Completed-job profit reporting is internal and read-only evidence for owner review and future calibration; it does not change quote pricing.
- Manual Completed Job Calibration Log is internal-only evidence capture for owner review and future pricing planning; it does not change quote pricing and should be used to preserve real completed-job learnings ahead of category-specific pricing PRs.
- Internal Quote Risk Summary is admin-only, read-only/recomputed, desktop-admin-only, and exposed on quote detail as `quote_risk_summary`; it is not customer-visible, not persisted, and has no pricing effect.
- PR #304 GPT Admin Notes backend is complete: the repo has an internal bearer-protected `POST /api/gpt/admin-notes` endpoint, persisted `gpt_admin_notes` storage, admin-auth `GET /admin/api/gpt-notes`, validation, idempotency/retry safety, duplicate handling, rate limiting, audit logging, backup/export/import coverage, and focused tests.
- PR #305 Admin GPT Notes display is complete: desktop admin shows collapsed GPT Notes (Advisory), fetches `/admin/api/gpt-notes`, renders with safe DOM text handling, labels content advisory-only, and keeps GPT notes out of public and mobile surfaces.
- PR #306 GPT Admin Notes Action schema refresh is complete: the Custom GPT action schema and grounding docs now describe `createGptAdminNote` as the bounded, consequential, internal-only advisory-note write action, marked `x-openai-isConsequential: true`, with the grounding pack regenerated.
- PR #307 GPT Action Builder compatibility cleanup is complete: the Builder-facing OpenAPI schema no longer exposes unsupported caller grounding revision as an action parameter, docs wording was updated, and the grounding pack was regenerated.
- Manual GPT Builder refresh after PR #307 is complete: Custom GPT Knowledge files were updated from `dist/gpt_grounding_pack`, Custom GPT Actions schema was updated from `docs/gpt/GPT_ACTIONS_OPENAPI.yaml`, and GPT Builder was saved.
- Manual GPT action verification after PR #307 passed: `getGptQuote` succeeded after Builder schema cleanup, and a live fake `createGptAdminNote` action wrote through the Custom GPT -> Render endpoint -> SQLite -> desktop admin GPT Notes (Advisory) display path. Observed fake note id: `f39e3b09-ff31-4449-a431-dadda7daab6b`.
- PR #293 Admin Action Shortcuts Completion is complete: desktop admin Daily Ops Board cards now expose shortcut chips that route Austin and Dan into existing manual admin flows without changing pricing, customer payloads, mobile admin, Render config, workflows, requirements, or `VERSION`.
- PR #296 Manual Completed Job Calibration Log is complete: desktop admin now supports manual completed-job evidence capture through `/admin/api/manual-completed-jobs` backed by `completed_job_calibration_entries`; this is internal-only, advisory-only evidence capture for future pricing review, not a second pricing engine.
- PR #297 Prelaunch Test Data Cleanup Tooling is complete: the repo now includes an approved allowlisted dry-run/apply cleanup process via `scripts/create_prelaunch_test_data_cleanup.py` plus `docs/prelaunch_test_data_cleanup.md`; operators should use this backup-first workflow instead of ad hoc live cleanup steps.
- PR #287 Customer Quote Flow Simplification did not change backend behavior, pricing, schema, admin, mobile admin, GPT grounding-source schema, Render config, workflows, requirements, or `VERSION`; no forbidden internal risk/pricing/advisory jargon was found in customer quote HTML/JS, and production live-safe smoke passed after deployment.
- PR #298 Launch UI Mobile Polish is complete: fixed mobile quote page horizontal overflow, simplified quote flow section wording, replaced public homepage "admin dashboard" wording with operator-appropriate copy, adjusted mobile homepage call button spacing; no backend, pricing, storage, mobile-admin, Render, workflow, GPT, dependency, or version changes; production live-safe smoke passed after merge.
- PR #299 Booking Request Notification Alerts is complete: added internal booking request notification alert infrastructure. Trigger point is `POST /quote/{quote_id}/booking` after `booking_service.submit_booking_details(...)` succeeds. Notifications are internal-only. SMTP email via Python standard library. Disabled by default unless `BOOKING_REQUEST_NOTIFICATIONS_ENABLED=true`. No customer-facing email/SMS/booking confirmation/calendar scheduling. Notification failure does not break the customer booking response. Added `notification_attempts` SQLite table for duplicate/failure tracking. Sent attempts suppress duplicate emails. Failed/skipped attempts can retry. Fresh pending suppresses race duplicate sends. Stale pending after 15 minutes can retry. SMTP secrets are not logged or stored. Tests monkeypatch SMTP; no real emails sent. `DEPLOYMENT_NOTES.md` documents Render env vars and safe setup. Production live-safe smoke passed after merge (run ID 26102113271, SHA c428bf988fdbe4b06e3463cc47e9393942c10d0d).
- PR #315 Quote First-View Simplification Polish is complete: public quote first-view clarity was tightened while preserving field IDs, option values, payload compatibility, and the existing `/quote/calculate` path.
- PR #316 Admin POST Origin Fail-Closed Hardening is complete: admin POST origin enforcement now fails closed, with focused regression coverage updated. This did not change pricing, schema, customer quote behavior, GPT actions, Render config, dependencies, or `VERSION`.
- PR #318 Demolition Pricing Readiness Plan is complete: the repo now has a docs-only demolition pricing readiness plan for future owner-approved pricing work. It did not change runtime behavior, pricing logic, schema/storage, auth, Render config, workflows, GPT runtime behavior, dependencies, or `VERSION`.
- PR #329 Demolition Pricing Safeguards is merged, live on Render, and production-verified: `/health` reports version `0.12.0` and commit prefix `5a5b4dcbbafb`. Demolition safeguards are runtime pricing behavior in `app/quote_engine.py`, not docs-only readiness. Demolition floors now include controlled demolition around $500, normal demolition around $650+, access-risk demolition around $750+, structure teardown around $1000+, heavy material demolition around $1200+, and heavy + access demolition around $1500+. Owner-review and advisory behavior remains internal/admin-only. GPT does not override pricing, and `app/quote_engine.py` remains the only pricing authority. Local/internal acceptance retest passed for a 16x10 shed teardown at the structure floor, brick/fireplace basement demo at the heavy-access floor, wet shingles and dirt/soil cleanup as heavy material, hazardous/asbestos wording owner-review, and bare kitchen/wall unit wording not falsely triggering access risk.
- PR #319 Launch Readiness Consolidation Cleanup is complete.
- PR #320 Premium Homepage Visual Polish is complete.
- PR #321 Public Brand Hero Colour Alignment is complete.
- PR #322 Homepage Logo Replacement is complete: desktop/mobile homepage logo updated without runtime/pricing/schema/workflow/dependency/version changes.
- PR #323 Desktop Admin Collapsible Section Polish is complete: admin collapsible section polish without runtime/pricing/schema/workflow/dependency/version changes.
- Current verified baseline after PR #329 Demolition Pricing Safeguards merge commit `5a5b4dcbbafb12405c2c32366288e13279763de4`: version is `0.12.0`, version parity passed, GPT grounding parity passed, local/internal demolition acceptance retest passed, full pytest passed with 822 tests, Render `/health` was verified at version `0.12.0` with commit prefix `5a5b4dcbbafb`, and live `/`, `/quote`, `/admin`, and `/admin/mobile` returned 200.

## Notification Policy

Booking request notification infrastructure is installed but **disabled until customer launch**.

Render SMTP/env vars must not be configured until Austin explicitly authorizes customer launch.

Leave these unset until customer launch:

- `BOOKING_REQUEST_NOTIFICATIONS_ENABLED`
- `BOOKING_NOTIFICATION_EMAIL_TO`
- `BOOKING_NOTIFICATION_EMAIL_FROM`
- `BOOKING_NOTIFICATION_SMTP_HOST`
- `BOOKING_NOTIFICATION_SMTP_PORT`
- `BOOKING_NOTIFICATION_SMTP_USERNAME`
- `BOOKING_NOTIFICATION_SMTP_PASSWORD`
- `BOOKING_NOTIFICATION_SMTP_STARTTLS`
- `BOOKING_NOTIFICATION_EMAIL_REPLY_TO`
- `APP_BASE_URL`

When Austin authorizes launch, configure these on Render following `DEPLOYMENT_NOTES.md`, then perform a controlled live notification test before treating notifications as active.

## Partial Or Still Future

- Internal customer notes, job difficulty score, full missing-info detector, job closeout checklist, and review request tracking remain future work.
- Customer-facing GPT/chatbot, automatic SMS/email sending, and auto-calendar scheduling remain future work.
- Demolition pricing safeguards are live through PR #329. Future pricing calibration for other service categories and any later heavy-category refinements remains separate future work and must not be treated as complete.
- Internal GPT current v1 is live for the bounded quote action and the consequential advisory `createGptAdminNote` write action after the PR #307 Builder refresh and manual live fake action verification.
- Photo Evidence / Photo Assistant remains future advisory-only work.
- Customer launch SMTP configuration and controlled live notification test are pending Austin authorization.

## Current Priorities

- Keep repo behavior aligned with docs and deployment reality.
- Prevent memory drift and undocumented assumptions.
- Make narrow, auditable refinements only.
- Preserve one-pricing-engine discipline and protected pricing authority.
- Maintain clear customer/admin operational boundaries.
- Keep Daily Ops Queue items as admin attention flags only; use existing admin surfaces for any manual follow-up.
- Keep Daily Ops Board shortcut chips manual and bounded to existing admin workflows; they should navigate operators faster, not create new pricing or mutation authority.
- Keep the Follow-Up Message Helper advisory-only: copy-ready drafts, no automated sending, no saved message history, and no backend mutation.
- Keep completed-job reporting advisory-only and separate from pricing authority.
- Keep the Manual Completed Job Calibration Log advisory-only and separate from pricing authority; it is evidence capture for owner review, not automated pricing.
- Keep Internal Quote Risk Summary advisory-only and separate from pricing authority; `customer_visible` remains false and `pricing_effect` remains `none`.
- Keep GPT Admin Notes advisory-only and separate from pricing authority; the GPT may create notes only through `createGptAdminNote`, and notes must remain internal-only, admin-visible only, `customer_visible=false`, and `pricing_effect=none`.
- Keep prelaunch cleanup execution backup-first, allowlisted, and operator-run through `scripts/create_prelaunch_test_data_cleanup.py`; do not improvise ad hoc cleanup steps.
- Keep future pricing calibration beyond the live PR #329 demolition safeguards deferred to later category-specific PRs after evidence review; do not imply all pricing work is complete.
- PR #291 lead source + repeat customer tracking is complete (no-schema v1): optional public `lead_source` intake is accepted by `/quote/calculate`, blank/missing maps to `unknown`, invalid nonblank values reject with 422, and lead source persists through existing `request_json` flow into quotes, quote_requests, and jobs.
- Desktop admin quote detail now renders Lead & Customer History while `customer_history` remains admin-only and read-only from normalized 10-digit phone history; customer/public quote and review responses do not expose `customer_history`.
- Phone-history lookup now aligns SQL matching with Python-backed normalization and uncommon separator handling; `last_seen` ordering uses parsed datetimes.
- No pricing influence, no schema migration, and no mobile-admin changes came from PR #291 lead source + repeat customer tracking. `app/quote_engine.py` is now touched only by the separate live PR #329 demolition safeguards and remains the only pricing authority.
- Do not configure Render SMTP/env vars for booking notifications until Austin explicitly authorizes customer launch.
- When Austin authorizes launch, follow `DEPLOYMENT_NOTES.md` Render setup steps and perform a controlled live notification test before treating notifications as active.

## What Should Not Happen Next

- No second pricing engine.
- No customer-facing GPT pricing path.
- No broad speculative architecture work.
- No unnecessary flow rewrites in stable areas.
- No mixing unrelated runtime changes into documentation tasks.
- No GPT or Daily Ops Queue actions that approve, reject, expire, schedule, contact, price, message, update payments, or mutate lifecycle records.
- No GPT writes except the bounded consequential `createGptAdminNote` action for internal advisory admin notes.
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

An internal-only `POST /api/gpt/admin-notes` endpoint now exists as a consequential write action for advisory GPT Admin Notes.

When the action is useful for admin review, follow-up, or calibration context, GPT may create a note through `createGptAdminNote`. It should prefer known `quote`, `quote_request`, `job`, or `completed_job_calibration_entry` IDs, use `related_entity_type=general` only when no entity ID exists, and use an `idempotency_key` for retry safety.

This note action does not create quotes, jobs, bookings, schedules, payments, or customer messages. It does not change pricing, lifecycle status, payment state, admin approvals, customer communications, or customer-visible records. Notes remain internal-only, admin-visible only, advisory-only, `customer_visible=false`, and `pricing_effect=none`.

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

The queue does not approve, reject, expire, schedule, contact, price, message, send, or mutate records. It only shows attention flags from existing admin data. Any GPT write permission is limited to the separate consequential `createGptAdminNote` advisory-note action.

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
