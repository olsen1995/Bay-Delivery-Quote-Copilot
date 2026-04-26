# Bay Delivery Customer Release and Operator Upgrade Plan

## Purpose

This document preserves the next strategic improvement direction for Bay Delivery Quote Copilot.

The system is a production quoting and booking-support tool for Bay Delivery in North Bay, Ontario. The goal is to make the public Render customer flow feel professional, trustworthy, and resilient, then improve admin/operator usefulness without destabilizing pricing or architecture.

This is a roadmap and architecture planning document. It is not the pricing source of truth and must not override runtime code.

---

## Current Strategic Principle

Make the customer flow release-quality first. Then improve operator usefulness. Then add feedback loops that make future quoting smarter.

Do not destabilize pricing, auth, schema, Render deployment, or customer flow casually.

---

## Locked Boundaries

- One pricing engine only: `app/quote_engine.py`.
- Do not create a second pricing system.
- Do not make AI customer-facing for pricing decisions.
- Do not auto-override quote totals from advisory logic.
- Do not treat this document as runtime source-of-truth.
- Keep future PRs narrow, auditable, and reversible.
- Protect Bay Delivery margins.
- Cash remains no HST.
- EMT/e-transfer remains +13% HST.
- Customer booking remains subject to Bay Delivery review and confirmation.

---

## Phase 1 - Customer Release Readiness

Goal: make the public Render pages feel professional, trustworthy, and hard to break.

Focus areas:

- Homepage clarity.
- Quote page clarity.
- Mobile-first customer QA.
- Recoverable customer-facing error states.
- No dead-end customer paths.
- Trust and FAQ copy.
- Service-area clarity.
- Cash vs EMT/HST clarity.
- Accessibility basics.
- Clean browser console.
- Broken asset/link checks.

Success standard:

A real customer can land on the site from Facebook, understand the offer, request an estimate, recover from mistakes/errors, and feel confident Bay Delivery will follow up.

---

## Phase 2 - Customer Fallback and Manual Review Safety

Goal: if automatic quoting fails, the customer should still become a lead.

Potential improvements:

- Clear fallback message when automatic estimate generation fails.
- Prominent call/text/email contact path.
- Explain that Bay Delivery can still review the job manually.
- Later: save a manual-review request without generating a price.

Boundary:

Do not give fake prices if quote calculation fails.

---

## Phase 3 - Lead Pipeline and Follow-Up System

Goal: help Bay Delivery close more jobs without lowering prices.

Future admin lead states may include:

- New estimate.
- Quoted.
- Customer viewed.
- Accepted estimate.
- Booking requested.
- Needs follow-up.
- Declined.
- Stale/cold.
- Completed.

Potential admin actions:

- Mark followed up.
- Add note.
- Copy customer message.
- Mark lost.
- Mark booked.
- Mark completed.

Business reason:

A quote not followed up is money leaking out of the truck bed.

---

## Phase 4 - Completed Job Costing and Profit Feedback Loop

Goal: learn from real jobs without changing quote logic blindly.

Admin-only completed job fields could include:

- Actual hours.
- Actual crew size.
- Actual disposal cost.
- Actual fuel/travel issue.
- Final amount collected.
- Payment method.
- Underquoted / fair / profitable / painful.
- Notes.

Potential reporting:

- Gross revenue.
- Estimated labour cost.
- Known disposal cost.
- Rough margin.
- Quote accuracy notes.

Boundary:

Start as reporting only. Do not automatically change pricing from feedback data.

---

## Phase 5 - Quote Risk and Confidence Flags

Goal: warn Austin/Dan when a quote may be under-specified or risky.

Possible flags:

- No photos.
- Vague description.
- Heavy or dense material.
- Access difficulty unclear.
- Trailer fill missing.
- Large item count mismatch.
- Long carry, stairs, or basement risk.
- Demolition debris risk.

Boundary:

Advisory first. Do not auto-override pricing.

---

## Phase 6 - Admin Daily Ops Board

Goal: make the system easier to run day-to-day from phone or desktop.

Possible sections:

- Today’s jobs.
- Upcoming booking requests.
- Accepted but unscheduled estimates.
- Jobs needing confirmation.
- Jobs needing completion notes.
- Leads needing follow-up.

---

## Phase 7 - Customer Message Template System

Goal: help Austin/Dan respond faster and more professionally.

Possible templates:

- Quote reply.
- Need photos.
- Need address/details.
- Follow-up after estimate.
- Booking confirmation.
- Running late.
- Job completed thank-you.
- Declined estimate response.

Boundary:

Templates should support human review, not auto-send without approval.

---

## Phase 8 - Photo and Job Evidence System

Goal: connect photos to quotes/jobs for proof, marketing, and future calibration.

Potential uses:

- Before/after proof.
- Dump receipts.
- Scope disputes.
- Facebook posts.
- Pricing calibration later.

This is valuable but more complex, so it should come after simpler admin, lead, and costing upgrades.

---

## Explicit Non-Goals For Now

- No customer-facing AI quote bot.
- No second pricing engine.
- No automatic AI price override.
- No full admin redesign.
- No customer accounts.
- No online payments yet.
- No broad schema migration without a narrow plan.
- No large frontend redesign without a launch-readiness audit first.

---

## Recommended Next Planning Task

Run a customer-facing Render launch-readiness audit before implementing more customer-facing changes.

Audit:

- `/`
- `/quote`
- `/static/favicon.svg`
- customer quote form behavior
- validation/error states
- quote result clarity
- accept/decline explanation
- booking request explanation
- mobile friendliness
- accessibility basics
- broken links/assets
- console errors if browser tooling is available

Rank findings by:

- customer impact
- business risk
- breakage risk
- implementation size

---

## Suggested Future PR Order

Recommended order after this document is created:

1. Customer-facing Render launch-readiness audit.
2. Small customer fallback/error clarity PR, if the audit finds a real gap.
3. Trust/FAQ/service-area clarity polish, if needed.
4. Lead pipeline planning audit.
5. Completed job costing/profit feedback loop planning audit.
6. Admin daily ops board planning audit.
7. Message template system planning audit.
8. Photo/job evidence planning audit.

Each task should start with audit/planning first, then implementation only if the scope is narrow and safe.

---

## Implementation Guardrails For Future Work

For every future PR connected to this plan:

- Plan first, then implement in the same task.
- Keep the PR narrow.
- Avoid unrelated cleanup.
- Do not touch pricing unless the task explicitly requires pricing work.
- Do not modify `app/quote_engine.py` unless explicitly requested.
- Do not change customer booking semantics without explicit approval.
- Do not create a second pricing path.
- Do not make GPT or AI customer-facing for price authority.
- Prefer admin-only advisory/reporting before automated behaviour.
- Validate with tests and report exact results.
- Review for drift before opening PR.

---

## Owner/Operator Summary

The next major system improvement is not more quote math. The next major improvement is making the customer-facing Render flow release-quality, then building operator tools that help Bay Delivery follow up, complete jobs, record real costs, and learn from profit/loss feedback.

The long-term win is a clean loop:

Estimate -> Customer response -> Job booked -> Actual job result -> Profit/loss -> Better future quoting

That loop should improve Bay Delivery decisions without destabilizing the single pricing engine.
