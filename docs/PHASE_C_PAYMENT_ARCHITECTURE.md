# Phase C Payment Architecture

## Summary

Phase C adds deposit-backed booking only after estimator and booking-request flows are already stable.

This document is a planning blueprint, not an instruction to implement the full payment flow in one pass.

The recommended approach is a narrow staged rollout:

1. Phase C1 — schema + persistence groundwork only
2. Phase C2 — hosted checkout initiation only
3. Phase C3 — webhook/payment reconciliation only
4. Phase C4 — admin guardrails + UI visibility
5. Phase C5 — rejection/refund workflow polish

## Current Flow

- Quote creation is `POST /quote/calculate` in `app/main.py`, which delegates to `app/services/quote_service.py`.
- Pricing authority remains only `app/quote_engine.py`.
- Quotes are persisted via `save_quote()` with an `accept_token`.
- Customer acceptance/decline is `POST /quote/{quote_id}/decision`.
- `app/services/booking_service.py` validates the persisted `accept_token`, creates or updates one `quote_requests` row per `quote_id`, and moves status to `customer_accepted` or `customer_declined`.
- Booking preferences are captured separately by `POST /quote/{quote_id}/booking`.
- This requires `status == customer_accepted` plus a valid `booking_token`, then persists `requested_job_date`, `requested_time_window`, and `notes` onto the existing `quote_requests` row.
- Admin review is `POST /admin/api/quote-requests/{request_id}/decision`.
- `booking_service.process_admin_decision()` moves `customer_accepted -> admin_approved` or `customer_accepted -> rejected`.
- Admin approval immediately creates a `jobs` row if one does not already exist for the quote.
- Scheduling and Google Calendar sync happen later through `app/services/job_scheduling_service.py`, with DB-first then Calendar mirror.

## Relevant Files

- `app/services/quote_service.py`
- `app/services/booking_service.py`
- `app/services/job_scheduling_service.py`
- `app/storage.py`
- `app/update_fields.py`
- `app/main.py`
- `static/quote.js`
- `static/admin.js`
- `static/admin_mobile.js`
- `app/integrations/google_calendar_client.py`
- `tests/test_quote_request_transitions.py`

## Existing Authority Points

- Pricing authority: `app/quote_engine.py` only
- Customer state-change authority: persisted `accept_token` and `booking_token`, both validated server-side
- Quote-request lifecycle authority: `validate_quote_request_transition()` in `app/update_fields.py`
- Admin approval authority: authenticated `/admin/api/*` plus `customer_accepted -> admin_approved` transition enforcement
- Job/schedule authority: job is only created on admin approval
- Calendar writes occur only after DB writes

## Recommended Deposit Insertion Point

The safest deposit insertion point is:

- after booking preferences are submitted to `quote_requests`
- before admin approval creates a job

This keeps current authority intact:

- customer can express intent and pay a deposit
- customer still cannot self-schedule
- customer still cannot create a job
- admin approval remains the gate for `admin_approved` and job creation

Do not insert deposit logic into:

- quote calculation
- `app/quote_engine.py`
- Google Calendar flow

## Architecture Plan

### Payment Flow

- Keep the current quote and accept flow unchanged through `customer_accepted` and booking preference submission.
- Add a hosted-checkout initiation step tied to an existing `quote_requests` row in `customer_accepted`.
- Compute the deposit from persisted quote totals only, never from fresh request inputs.
- Conservative default: derive from persisted `emt_total_cad` because hosted checkout is an electronic payment path and repo tax policy already distinguishes cash vs electronic totals.
- Persist a local payment attempt record first, then call Stripe Checkout, then update the local record with the returned session/payment identifiers.
- If Stripe creation fails, keep the request intact and mark only payment state as failed/open.
- Payment success must not auto-approve, auto-schedule, or create a job.
- Payment success only unlocks admin review.

### Minimum Schema Additions

Add summary fields on `quote_requests` for admin/customer gating:

- `deposit_required_cad`
- `deposit_status`
- `deposit_paid_at`
- `deposit_refund_status`
- `deposit_refunded_at`
- `deposit_last_error`

Add a small dedicated payment-attempt table for provider truth and retries:

- `payment_attempt_id`
- `request_id`
- `provider`
- `amount_cad`
- `checkout_session_id`
- `payment_intent_id`
- `status`
- `created_at`
- `updated_at`
- `refund_id`
- `last_error`

Add a webhook-event idempotency table:

- `provider_event_id`
- `provider`
- `event_type`
- `received_at`
- `processed_at`
- `payload_json`

Store deposit policy config in:

- `config/business_profile.json`

Use a new booking/payments section there rather than hardcoding policy in routes or deep service branches.

### Webhook / Callback Shape

- Browser success/cancel callbacks should be UX-only and read from SQLite.
- Browser callbacks must not be trusted as payment authority.
- Stripe webhook should be authoritative for `deposit_status` changes.
- Webhook handling must include signature verification and idempotent event processing.
- Webhook reconciliation should use persisted request/payment identifiers.
- Unknown or mismatched provider objects should be ignored safely.
- Webhook updates should modify only payment-related state.

Recommended provider events to handle narrowly:

- checkout completed / payment succeeded
- payment failed / expired
- refund succeeded / failed

### Admin Guardrails

- Keep `quote_requests.status` lifecycle unchanged if possible.
- Use separate deposit state instead of inventing many new request statuses.
- Admin approval route should hard-block unless:
  - request status is `customer_accepted`
  - deposit is not required, or deposit summary state is `paid`
- Admin reject should remain available from `customer_accepted`, but if deposit is already paid it must trigger refund workflow or explicit manual-follow-up state before returning success.
- Admin UI should show clear payment badges and remove or disable `Approve` when deposit is unpaid or stale.

### Reject / Refund Handling

- Current reject path only flips `quote_requests.status` to `rejected`.
- No refund logic exists now.
- For Phase C, rejection of a paid request should call refund orchestration after DB intent is recorded, then persist `deposit_refund_status` as:
  - `pending`
  - `succeeded`
  - `failed`
  - `manual_review`
- If refund initiation fails, the request should still be visibly rejected in ops with a durable manual-follow-up state.
- Do not silently leave a paid request looking clean.
- Post-approval cancellation refunds are a separate workflow and stay out of scope unless explicitly added later.

### Source-of-Truth Protection

- SQLite remains authoritative for request state, payment state, refund state, and approval gating.
- External provider IDs are references attached to local records.
- Provider callbacks reconcile into SQLite, not the reverse.
- Deposit amount must be derived from stored quote totals plus config policy.
- Deposit logic must never re-run pricing logic.

### Calendar Mirror Protection

- No Calendar changes on checkout creation, payment success, refund, or request rejection.
- Calendar remains job/schedule-only and continues DB-first through `job_scheduling_service.py`.

### Pricing Authority Protection

- Do not put deposit logic in `app/quote_engine.py`.
- Do not add a second pricing path.
- Deposit calculation is a booking policy applied to already-persisted quote totals.
- Deposit calculation must not mutate quote totals, rerun the engine, or dynamically reprice at booking time.

## Risks

### State Consistency

- The repo currently has no payment persistence layer.
- Bolting payment state directly onto only `quote_requests` risks losing retry history and webhook provenance.
- Current `quote_requests` statuses are terminal after `admin_approved` or `rejected`.
- Overloading lifecycle status for payment phases would make transition rules brittle.

### Payment Failure Modes

- Checkout session creation can fail after a local row is created.
- That requires explicit `failed` / `open` state, not rollback assumptions.
- Duplicate webhook deliveries can double-apply payment/refund state unless provider event IDs are persisted and processed idempotently.
- Multiple checkout attempts for one request can leave stale session links unless one attempt is marked active and others superseded.

### Approval / Review Risks

- Admin approval currently creates the job immediately.
- Without a hard deposit check, a paid/unpaid race could create jobs before reconciliation finishes.
- Admin reject after payment but before refund completion can leave the system in a rejected-but-still-paid state unless refund status is first-class and visible.

### Customer / Operator Confusion

- Current customer copy says admin reviews and confirms the job after booking request.
- Adding checkout must not imply payment equals approval or scheduling confirmation.
- Admin UI currently treats `customer_accepted` as actionable.
- Without explicit deposit badges and disabled approve controls, operators can misread unpaid requests.

### Rollback Concerns

- Partial rollout is risky if webhook reconciliation is absent.
- Checkout-only without reconciliation creates stale paid/unpaid ambiguity.
- A broad one-pass launch would combine schema, external integration, admin gating, and refund behavior in the most failure-prone area of the live system.

## Implementation Slices

### Phase C1

#### Phase C1 - Goal

- Add payment/deposit persistence and config groundwork only, with no user-visible payment behavior.

#### Phase C1 - Files

- `app/storage.py`
- `config/business_profile.json`
- likely new payment-storage tests

#### Phase C1 - Risk

- Low to medium

#### Phase C1 - Validation

- schema init/backfill tests
- storage read/write tests
- existing quote-request/job transition tests unchanged
- `python tools/check_version_parity.py`
- `pytest -q`

#### Phase C1 - Must Not Change

- quote totals
- request statuses
- admin approval behavior
- job creation timing
- calendar behavior

### Phase C2

#### Phase C2 - Goal

- Add hosted checkout initiation for an existing accepted booking request, with deposit amount derived from persisted totals and config.

#### Phase C2 - Files

- `app/main.py`
- new `app/services/payment_service.py`
- new `app/integrations/stripe_checkout_client.py`
- `static/quote.js`
- `static/quote.html`

#### Phase C2 - Risk

- Medium

#### Phase C2 - Validation

- unit tests for deposit amount derivation
- Stripe session creation success/failure handling
- request state unchanged on provider failure
- customer messaging asserts no approval/scheduling promise

#### Phase C2 - Must Not Change

- `app/quote_engine.py`
- admin approval gate semantics
- job creation on payment success
- Calendar writes

### Phase C3

#### Phase C3 - Goal

- Add webhook reconciliation and authoritative payment/refund state transitions.

#### Phase C3 - Files

- `app/main.py`
- `app/services/payment_service.py`
- `app/storage.py`
- webhook-focused tests

#### Phase C3 - Risk

- High

#### Phase C3 - Validation

- signature verification tests
- duplicate event idempotency tests
- stale-object mismatch tests
- payment success/failure/refund reconciliation tests
- no unintended request/job mutations

#### Phase C3 - Must Not Change

- customer self-scheduling
- quote recalculation
- admin approval creating jobs only after explicit review

### Phase C4

#### Phase C4 - Goal

- Wire admin approval guardrails and admin/mobile UI visibility to deposit state.

#### Phase C4 - Files

- `app/services/booking_service.py`
- `app/main.py`
- `static/admin.js`
- `static/admin_mobile.js`
- `tests/test_quote_request_transitions.py`
- `tests/test_static_assets.py`

#### Phase C4 - Risk

- Medium to high

#### Phase C4 - Validation

- approval blocked when deposit is required but unpaid
- approval allowed when paid
- reject path correct for paid vs unpaid requests
- UI badges/actions align with backend guardrails

#### Phase C4 - Must Not Change

- existing quote-request lifecycle authority
- job scheduling flow
- Google Calendar mirror-only behavior

### Phase C5

#### Phase C5 - Goal

- Polish rejection/refund workflow, operator messaging, and customer post-checkout/post-reject communication.

#### Phase C5 - Files

- `app/services/payment_service.py`
- `app/services/booking_service.py`
- `app/main.py`
- `static/quote.js`
- `static/admin.js`
- `static/admin_mobile.js`

#### Phase C5 - Risk

- Medium to high

#### Phase C5 - Validation

- reject-with-refund happy path
- refund failure/manual-review path
- customer copy tests
- admin visibility for pending/failed refunds
- regression tests for unchanged approval/job/calendar flows

#### Phase C5 - Must Not Change

- pricing engine outputs
- admin-approval requirement
- no customer self-scheduling
- no calendar authority shift

## Recommendation

Go, but only with the narrow staged approach above.

No-go for a single-pass Phase C implementation because the current repo has no payment audit/idempotency layer, and admin approval currently creates jobs immediately.

## Best First Slice

### Recommended: Phase C1

**Focus:** schema + persistence groundwork only

## Notes

- The cleanest insertion point is between booking preference submission and admin approval.
- Rejection currently has no refund/follow-up path and must be added conservatively.
- Google Calendar is already correctly isolated to post-job scheduling and should stay untouched by payment events.
- Keep `quote_requests.status` focused on customer/admin workflow and add separate deposit state instead of expanding status transitions into payment micro-states.
- Deposit base should be explicitly confirmed before implementation if Bay Delivery does not want it tied to the persisted electronic-payment total.
