# Bay Delivery Quote Copilot - Roadmap & Architecture Plan

Prepared: May 10, 2026
Prepared for: Austin / Bay Delivery

## Executive Principle

Customer side stays simple. Admin side tells Austin and Dan what needs attention. Pricing authority stays protected in `app/quote_engine.py`. Reporting learns from completed jobs before any pricing changes are made.

## Recommended Repo Save Location

```text
docs/roadmaps/bay_delivery_system_roadmap_architecture_plan_2026-05-10.md
```

Reason: this is planning/architecture material, not runtime code. The `docs/roadmaps` folder keeps future strategy separate from app, static, tests, workflows, and GPT grounding files.

## Executive Summary

Bay Delivery Quote Copilot is no longer just a quote calculator. The next stage should make it a daily operating system for leads, jobs, follow-ups, risk review, and completed-job profitability.

The recommended build path is intentionally conservative:

1. Improve the admin operating view first.
2. Simplify the public customer flow second.
3. Add internal risk summaries and completed-job reports.
4. Change production pricing only after real data supports it.
5. Make pricing changes one service category at a time.

## Architecture Rules

- One pricing engine only: `app/quote_engine.py` owns all authoritative quote totals.
- Customer-facing pages should use plain language and avoid business-risk jargon.
- Admin surfaces are for operations, review, follow-up, costing, and reporting.
- GPT is internal-only and recommendation-only.
- SQLite remains the source of truth.
- Completed-job calibration is evidence for owner review, not automatic pricing authority.

## Target System Architecture

| Layer | Purpose | Boundary Rule |
|---|---|---|
| Customer Quote Page | Collect simple job facts | Use plain customer language. Do not show internal risk or pricing jargon. |
| Simple Intake Translator | Turn answers into structured internal facts | Advisory only. It supports risk review but does not set prices. |
| Quote Service | Validate and route quote requests | Backend remains source of truth for request handling. |
| Protected Pricing Engine | Own all final quote totals | Only app/quote_engine.py can calculate authoritative pricing. |
| Storage / Jobs / Requests | Persist quotes, requests, jobs, statuses, and costing | SQLite remains source of truth. Calendar/Drive are supporting tools only. |
| Admin Daily Ops Board | Show what needs attention now | Simple daily view for Austin/Dan: leads, bookings, costs, follow-ups, risk. |
| Risk Summary + Follow-Up | Explain what is risky and what to ask next | Internal-only guidance. No automatic price changes. |
| Completed Job Reporting | Learn from actual profit, cost, and margin data | Evidence for owner review and future pricing PRs. |
| Internal GPT Layer | Summarize, draft messages, and explain risk | Internal-only and recommendation-only. Never pricing authority. |

## Roadmap Phases

| Phase | Build | Purpose / Scope |
|---|---|---|
| 0 | Current-state verification | Confirm main, tests, Render /health, public quote, admin/mobile gates, version parity, and GPT pack parity before new work. |
| 1 | Admin Daily Ops Board | Create read-only cards for new requests, follow-ups, accepted-not-booked, upcoming jobs, missing costs, owner review, and stale quotes. |
| 2 | Admin Action Shortcuts | Add practical buttons after the board proves useful: ask follow-up, mark contacted, waiting, not ready, create job, enter costs, close/archive. |
| 3 | Customer Quote Flow Simplification | Make the public form calm, fast, and human. Keep risk fields in the background. Preserve payload compatibility. |
| 4 | Internal Quote Risk Summary | Translate structured intake fields into admin-only risk level, missing info, suggested action, crew/trailer suggestions, and pricing caution. |
| 5 | Completed Job Profit Review Report | Surface completed-job profit/margin, missing-cost counts, owner-review counts, and category breakdown inside admin. |
| 6 | Follow-Up Message Helper | Generate copy-ready customer messages for no reply, need photos, accepted-not-booked, cheaper request, completed job, and review request. |
| 7 | Scheduling Fields + Accepted Not Booked Queue | Track confirmed date/window, duration estimate, crew, and truck/trailer setup. Keep SQLite as source of truth. |
| 8+ | Pricing PRs by Service Category | Only after real reporting/risk visibility: demolition, moving, dense dump runs, scrap access risk, delivery distance/weather. |
| 9 | Internal GPT Upgrade | Let GPT summarize ops board, risk, follow-ups, and calibration findings. Still internal-only and advisory. |
| 10 | Photo Evidence / Photo Assistant | Attach photos and use advisory image notes later. Do not let image AI auto-price or override quote_engine.py. |

## Customer Flow Design

The customer experience should feel like: Tell us what you need, add a few helpful details, send photos if possible, and Bay Delivery will confirm.

Recommended customer steps:

1. What do you need help with?
2. Tell us what needs to be moved, removed, delivered, or cleaned up.
3. Where is it located: curbside, main floor, apartment/elevator, stairs, basement, long carry, or not sure?
4. Does it include special/heavy items: mattress, appliance, fridge/freezer/AC, construction debris, concrete/bricks/tile/dirt, scrap metal, or not sure?
5. Photos help us quote faster and avoid surprises.
6. Name, phone number, optional email, and preferred day/time.

Customer-facing words to avoid:

- manual review required
- disposal risk
- dense material classification
- recommended trailer
- labour underpriced
- operating-cost target gap

## Admin Experience Design

Admin should hide complexity until it is needed. The top of admin should answer: What needs attention today?

Daily Ops Board cards:

- New Requests
- Needs Follow-Up
- Accepted, Not Booked
- Upcoming Jobs
- Completed, Missing Costs
- Owner Review
- Stale Quotes

## Internal Quote Risk Summary

Use structured intake fields to generate a compact internal card. This should be advisory only and should not change quote totals.

Example:

```text
Risk Level: Medium
Why: Basement access, stairs, no photos, mixed load.
Suggested Action: Ask for photos and confirm item/bag count before approving.
Crew Suggestion: 2 workers likely.
Trailer Suggestion: Single axle likely; enclosed if weather-sensitive.
Pricing Caution: Access may increase labour time.
```

## Completed Job Profit Review

Completed-job costing should become the truth meter for pricing decisions.

Rules:

- Below 20% known margin = owner review.
- Missing costs = incomplete; do not trust the profit conclusion yet.
- Reports should show both overall summary and category breakdown.
- The report should stay internal and read-only until a separate pricing PR is planned.

## Add / Fix / Refine / Remove

### Add

| Item | Why |
|---|---|
| Lead source tracking | Add simple source options: Facebook, Google, referral, Marketplace, repeat customer, other. Helps know what marketing works. |
| Repeat customer marker | Show previous job count/last job on admin cards. Helps trust good customers and spot patterns. |
| Internal customer notes | Track good customer, slow payer, no-show risk, heavy items underestimated before, needs clear quote. |
| Job difficulty score | Internal 1-5 difficulty score to simplify triage: easy curbside through manual-review risk. |
| Missing-info detector | Show exactly what to ask for: photos, item count, access details, disposal type, preferred date. |
| Job closeout checklist | Collected amount, payment method, actual labour/disposal/fuel/other costs, underpriced marker, notes. |
| Review request helper | Generate and track review requests after completed jobs. |

### Fix / Refine

| Area | Refinement |
|---|---|
| Admin hierarchy | Top: Daily Ops Board. Middle: Requests/Jobs/Costing. Bottom: Reports/Backup/Settings/Developer tools. |
| Customer copy | Use local, helpful wording: Tell us what you need help with. Photos help us quote faster and avoid surprises. |
| Risk wording | Use practical wording: Review before approving, ask for photos, likely 2-person job, disposal uncertain. |
| Mobile admin | Keep it lean: today jobs, customer phone/address, notes, status, mark completed, maybe collected amount. |

### Remove / Avoid

| Thing | Reason |
|---|---|
| Admin-side quote drafting | Keep admin as operations. Use public quote flow and internal GPT separately for drafts. |
| Raw JSON in main workflow | Hide raw request payloads/details behind a details/developer section. |
| Customer-facing risk jargon | Do not show pricing risk, manual review, recommended trailer, under-margin, or operating-cost gap to customers. |
| Automatic smart price adjustment | Avoid until enough completed-job evidence exists. Pricing changes must be deliberate PRs. |
| Customer accounts/login | Too much friction for local service jobs. Customers should not need passwords for a dump run. |

## Pricing Change Order

| Order | Category | Reason |
|---|---|---|
| 1 | Demolition / rip-out | Highest risk. Add premium/manual-review floors and strong minimum protections first. |
| 2 | Moving labour | Protect 2-worker minimums, stairs, long carry, inside work, and heavy/customer-belonging risk. |
| 3 | Heavy/dense dump runs | Protect against concrete, tile, bricks, dirt, wet debris, shingles, drywall, and scale/disposal uncertainty. |
| 4 | Scrap pickups | Protect inside/basement/heavy/awkward scrap jobs while keeping curbside scrap simple. |
| 5 | Delivery | Add protections for distance, weather, stairs, item value/care, and enclosed trailer needs. |

## Exact PR Sequence

| Order | PR Title | Scope |
|---|---|---|
| 1 | create admin daily ops board read model | Desktop admin read-only summary cards. No pricing, customer, schema, Render, workflow, or GPT changes. |
| 2 | create admin ops board action shortcuts | Add follow-up/status shortcuts after the board is confirmed useful. |
| 3 | create customer quote flow simplification | Improve public wording and layout using progressive disclosure. Keep quote behavior compatible. |
| 4 | create internal quote risk summary | Admin-only risk card from structured intake fields. No quote total changes. |
| 5 | create completed job profit review report | Admin report using completed-job costing data and analyzer concepts. Internal-only. |
| 6 | create follow up message helper | Copy-ready message drafts for common customer situations. No automated sending yet. |
| 7 | create job scheduling fields and accepted not booked queue | Booking/date/window fields and queue visibility. SQLite remains source of truth. |

## Best Immediate Next PR

```text
create admin daily ops board read model
```

Scope: desktop admin only, read-only summary cards, no pricing changes, no customer-form changes, no Render/workflow/GPT changes, and no schema change unless strictly necessary.

This comes before customer-form cleanup because more customer leads are only useful if admin is clean enough to handle them.

## Codex Prompt Seed

```text
Create an Admin Daily Ops Board read model for Bay Delivery Quote Copilot. Plan first, then implement only if the plan stays narrow. Scope is desktop admin only. Add read-only summary cards for new quote requests, needs follow-up, accepted but not booked, upcoming jobs, completed jobs missing costs, owner-review jobs, and stale quotes. Do not change app/quote_engine.py, pricing logic, public quote behavior, GPT grounding, Render config, workflows, requirements, or customer form behavior. Add focused tests for backend/read-model behavior and static admin markers as appropriate. Validate with version parity, GPT grounding parity, compileall, focused tests, and full pytest if practical.
```

## Commit Text

Commit headline:

```text
create admin daily ops board read model
```

Commit description:

```text
Add a desktop-admin read-only Daily Ops Board that surfaces operational queues for new requests, follow-ups, accepted-not-booked leads, upcoming jobs, missing completed-job costs, owner-review items, and stale quotes. Keep the change admin-only and advisory-only with no pricing, customer flow, Render, workflow, or GPT grounding changes.
```

## Final Operating Loop

```text
Customer submits simple quote
  -> system captures useful hidden facts
  -> admin sees clear risk and missing info
  -> Austin/Dan approve, follow up, or book
  -> job gets completed
  -> actual costs are entered
  -> system shows profit and underpricing patterns
  -> pricing is improved carefully by category
```

The goal is not to build a flashy quote calculator. The goal is to build a small business operating system that protects margin, reduces missed follow-ups, and makes daily decisions easier.
