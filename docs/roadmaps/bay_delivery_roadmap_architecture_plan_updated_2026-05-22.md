# Bay Delivery Quote Copilot - Roadmap & Architecture Plan

Prepared: May 10, 2026
Updated: May 22, 2026
Prepared for: Austin / Bay Delivery

## Executive Principle

Customer side stays simple. Admin side tells Austin and Dan what needs attention. Pricing authority stays protected in `app/quote_engine.py`. Reporting and calibration learn from completed jobs before any pricing changes are made.

The system should stay boring, stable, and profitable. New features should make Bay Delivery easier to operate, not create a second pricing brain, a public chatbot, or a fragile CRM clone.

## May 22 Update Summary

This update refreshes the May 10 roadmap with actual completed work through PR #303 and adds a future GPT-to-admin logging concept.

Key updates:

- Marked completed admin, quote-flow, risk, reporting, scheduling, cleanup, notification, security, and docs work.
- Added current verified production state after redeploy and Production Live-Safe Smoke.
- Added real completed-job calibration evidence already entered into admin.
- Added **GPT Admin Job Logs / GPT Notes** as a future internal-only feature.
- Re-ranked the next practical tasks: production observability first, then GPT admin logging plan, then later pricing/category improvements.
- Preserved all hard boundaries: one pricing engine, SQLite as source of truth, admin-only internal risk, no customer-facing GPT pricing path.

## Current Verified Production State

As of May 22, 2026:

| Area | Status |
| --- | --- |
| Render deploy | Current after redeploy |
| Live health | `ok=true`, `version=0.11.0`, `drive_configured=true`, `commit=65187325cbdb` |
| Production smoke | Passed |
| Smoke run | `https://github.com/olsen1995/Bay-Delivery-Quote-Copilot/actions/runs/26292365349` |
| Smoke head SHA | `65187325cbdbc21897579078207ea2adba4de46b` |
| Live visual audit | Passed with no P1/P2 blockers |
| Public quote copy | Current, old confusing labels removed |
| Manual completed-job calibration entries | Entered |
| Current blockers | No known P1/P2 blockers |

## Recommended Repo Save Location

```text
docs/roadmaps/bay_delivery_system_roadmap_architecture_plan_2026-05-10.md
```

Reason: this is planning/architecture material, not runtime code. The `docs/roadmaps` folder keeps future strategy separate from app, static, tests, workflows, and GPT grounding files.

If saving this updated copy separately, use:

```text
docs/roadmaps/bay_delivery_system_roadmap_architecture_plan_2026-05-22.md
```

## Architecture Rules

- One pricing engine only: `app/quote_engine.py` owns all authoritative quote totals.
- Customer-facing pages should use plain language and avoid business-risk jargon.
- Admin surfaces are for operations, review, follow-up, costing, reporting, and internal evidence capture.
- GPT is internal-only and recommendation-only.
- GPT can summarize, draft, explain, and propose internal notes, but it must not override pricing or mutate job lifecycle status.
- SQLite remains the source of truth.
- Google Calendar is a mirror/convenience layer only.
- Google Drive is backup/support only.
- Completed-job calibration is evidence for owner review, not automatic pricing authority.
- GPT-generated notes/logs, if built later, must be internal-only, admin-visible, advisory-only, auditable, and never customer-facing.

## Target System Architecture

| Layer | Purpose | Boundary Rule | Current Status |
| --- | --- | --- | --- |
| Customer Quote Page | Collect simple job facts | Use plain customer language. Do not show internal risk or pricing jargon. | Complete and visually verified |
| Simple Intake Translator | Turn answers into structured internal facts | Advisory only. Supports risk review but does not set prices. | Partially complete through structured intake/risk context |
| Quote Service | Validate and route quote requests | Backend remains source of truth for request handling. | Complete/stable |
| Protected Pricing Engine | Own all final quote totals | Only `app/quote_engine.py` can calculate authoritative pricing. | Complete/protected |
| Storage / Jobs / Requests | Persist quotes, requests, jobs, statuses, costing, and manual calibration entries | SQLite remains source of truth. | Complete with ongoing additive refinements |
| Admin Daily Ops Board | Show what needs attention now | Simple daily view for leads, bookings, costs, follow-ups, risk. | Complete |
| Admin Action Shortcuts | Route operators faster into existing manual workflows | Navigation/shortcut layer only. No new pricing or lifecycle authority. | Complete v1 |
| Risk Summary + Follow-Up | Explain what is risky and what to ask next | Internal-only guidance. No automatic price changes. | Complete v1 |
| Completed Job Reporting | Learn from actual profit, cost, and margin data | Evidence for owner review and future pricing PRs. | Complete v1 |
| Manual Completed Job Calibration Log | Capture real jobs that did not originate from the public quote flow | Internal-only evidence. No pricing effect. | Complete and in use |
| Booking Notification Alerts | Internal notification infrastructure for submitted booking requests | Disabled until launch authorization. No customer-facing confirmation. | Installed, disabled |
| Production Observability | Monitor uptime, deploy drift, customer-page health, errors, and launch readiness | Free-first, privacy-safe, no admin/customer PII leakage. | Not completed; recommended next plan |
| Internal GPT Layer | Quote support, summarization, draft help, risk explanation | Internal-only and recommendation-only. Never pricing authority. | Partial: quote action exists |
| GPT Admin Job Logs / Notes | Let GPT create admin-visible internal notes for review | Future; must be consequential, audit-logged, admin-only, and pricing_effect=none. | Not completed; planned concept |
| Photo Evidence / Photo Assistant | Attach photos and use advisory image notes later | Do not let image AI auto-price or override quote engine. | Future |

## Completed Work Since May 10

| Area / PR | Status | Notes |
| --- | --- | --- |
| PR #273 - create admin daily ops board read model | Complete | Desktop-admin read-only operations board added. |
| PR #278 - create completed job profit review report | Complete | Admin-only completed-job profit/margin evidence. |
| PR #279 - create GPT grounding roadmap state refresh | Complete | GPT/current-state docs refreshed and grounding parity restored. |
| PR #280 - create follow up message helper | Complete | Desktop-admin copy-ready helper; no sending/history/backend mutation. |
| PR #281 - create accepted not booked scheduling queue | Complete | Accepted/approved unscheduled work surfaced in admin. |
| PR #282 - create accepted not booked detail row cap | Complete | Detail rows capped at 50 while total count remains true/uncapped. |
| PR #283 - create GPT current state refresh for admin workflow | Complete | Docs/GPT current-state aligned with admin workflow work. |
| PR #284 - create live health version parity smoke coverage | Complete | Production smoke now checks health version/commit behavior. |
| PR #285 - create internal quote risk summary | Complete | Desktop-admin-only internal risk summary. No pricing effect. |
| PR #286 - create GPT current state refresh for internal risk summary | Complete | Docs refreshed after risk summary. |
| PR #287 - create customer quote flow simplification | Complete | Customer quote page simplified without backend/pricing drift. |
| PR #288 - create GPT current state refresh for customer quote flow | Complete | Docs refreshed after customer flow work. |
| PR #289 - create customer quote page polish | Complete | Customer-facing copy polish. |
| PR #290 - create admin desktop declutter | Complete | Admin layout/visibility improved. |
| PR #291 - create lead source repeat customer tracking | Complete | No-schema v1 lead source + repeat/customer-history admin context. |
| PR #292 - create GPT current state refresh for lead tracking | Complete | Docs refreshed after lead tracking. |
| PR #293 - create admin action shortcuts completion | Complete | Follow-up shortcut chips added to desktop admin. |
| PR #294 - create homepage logo visibility polish | Complete | Homepage logo presentation improved. |
| PR #295 - create quote page mobile usability polish | Complete | Mobile quote UX tightened; one-form flow preserved. |
| PR #296 - create manual completed job calibration log | Complete | Admin-only manual completed-job evidence table and UI. |
| PR #297 - create prelaunch test data cleanup tooling | Complete | Backup-first allowlisted cleanup tooling and docs. |
| PR #298 - create launch UI mobile polish | Complete | Mobile quote overflow fixed; homepage internal wording removed. |
| PR #299 - create booking request notification alerts | Complete but disabled | Internal SMTP alert infrastructure installed; Render env vars remain unset until launch authorization. |
| PR #300 - create GPT current state refresh for booking alerts | Complete | Docs refreshed after booking notification infrastructure. |
| PR #301 - create idna security lock refresh | Complete | Dependency security lock refresh. |
| PR #302 - fix GPT grounding parity after skill docs | Complete | Generated grounding pack refreshed after docs drift. |
| PR #303 - create Codex review habit guidance | Complete | Repo-scoped Codex safety skill guidance expanded. |
| Production redeploy + live-safe smoke | Complete | Smoke run passed at head SHA `65187325cbdbc21897579078207ea2adba4de46b`. |
| Live visual audit | Complete | No P1/P2 issues; only minor P3 polish. |
| Manual calibration entries | Complete | $1,200 old shed removal and $600 backyard tarp/fence teardown entered. |

## Real Completed-Job Calibration Evidence Already Captured

These entries are now useful evidence for future pricing review, but they do not change pricing automatically.

| Job | Amount Collected | Usefulness |
| --- | ---: | --- |
| Old shed removal / teardown and haul-away | $1,200 CAD | Strong premium demolition/haul-away anchor. Similar work should not be treated like a basic dump run. |
| Backyard tarp / fence teardown and cleanup | $600 CAD | Useful small-to-mid backyard teardown/cleanup anchor where access and debris are manageable. |

## What Is Not Completed Yet

| Item | Status | Recommended Handling |
| --- | --- | --- |
| Production Observability and Launch Monitoring Plan | Not complete | Recommended next task; plan-only first. |
| Better Stack uptime/page monitoring | Not configured | External setup first; repo changes only if needed. |
| Sentry backend error tracking | Not implemented | Future privacy-safe PR only after plan. |
| Microsoft Clarity public-page UX tracking | Not implemented | Future public-pages-only, admin-excluded setup. |
| Google Search Console | Not confirmed complete | External setup; repo change only if verification/sitemap needs it. |
| Customer launch SMTP configuration | Not authorized/configured | Keep env vars unset until launch authorization and controlled test. |
| GPT Admin Job Logs / GPT Notes | Not implemented | Plan-only first; future admin-only auditable write path. |
| Internal customer notes | Not implemented | Future admin-only feature. |
| Job difficulty score | Not implemented | Future risk/triage feature. |
| Full missing-info detector | Not complete | Future admin guidance feature. |
| Job closeout checklist improvements | Not complete | Future post-job/costing refinement. |
| Review request tracking/helper | Not complete beyond message-helper concept | Future customer follow-up workflow; no auto-send yet. |
| Pricing PRs by service category | Not started | Defer until more evidence/review. |
| Photo Evidence / Photo Assistant | Not implemented | Future advisory-only feature. |
| Customer-facing GPT/chatbot | Not implemented | Defer; high risk for underquoting/customer promises. |
| Automatic SMS/email sending | Not implemented | Defer; consent, opt-out, and customer-promise risk. |
| Auto-calendar scheduling | Not implemented | Defer; SQLite remains source of truth and admin confirms bookings. |
| Litestream-style SQLite replication | Not implemented | Future plan-only/disaster recovery review. |

## Roadmap Phases - Updated Status

| Phase | Build | Purpose / Scope | Status |
| --- | --- | --- | --- |
| 0 | Current-state verification | Confirm main, tests, Render /health, public quote, admin/mobile gates, version parity, and GPT pack parity before new work. | Complete and repeated after deploy |
| 1 | Admin Daily Ops Board | Read-only cards for requests, follow-ups, accepted-not-booked, upcoming jobs, missing costs, owner review, stale quotes. | Complete |
| 2 | Admin Action Shortcuts | Practical buttons/chips after the board proves useful. | Complete v1 |
| 3 | Customer Quote Flow Simplification | Calm, fast, human public form while preserving payload compatibility. | Complete |
| 4 | Internal Quote Risk Summary | Admin-only risk level, missing info, suggested action, crew/trailer guidance, pricing caution. | Complete v1 |
| 5 | Completed Job Profit Review Report | Profit/margin, missing-cost counts, owner-review counts, category breakdown. | Complete v1 |
| 6 | Follow-Up Message Helper | Copy-ready customer message drafts for common scenarios. | Complete v1 |
| 7 | Scheduling Fields + Accepted Not Booked Queue | Track requested/confirmed scheduling context and surface accepted-not-booked work. | Complete v1 |
| 8 | Lead Source + Repeat Customer Tracking | Capture lead source and show customer history in admin. | Complete no-schema v1 |
| 9 | Manual Completed Job Calibration Log | Capture real non-public-quote completed jobs for owner review. | Complete and in use |
| 10 | Production Observability and Launch Monitoring | Better uptime, error, UX, search, and backup visibility. | Recommended next plan |
| 11 | GPT Admin Job Logs / Notes | Let GPT send internal admin-visible notes/logs for review. | Future; plan-only first |
| 12 | Job Closeout + Internal Notes + Difficulty Scoring | More complete post-job and customer history intelligence. | Future |
| 13 | Pricing PRs by Service Category | Deliberate category pricing changes after evidence review. | Future/deferred |
| 14 | Photo Evidence / Photo Assistant | Advisory image notes; no auto-pricing. | Future/deferred |
| 15 | Customer-Facing GPT / SMS / Auto Scheduling | Customer automation layer. | Future/high-risk; defer |

## Customer Flow Design

The customer experience should feel like: Tell us what you need, add a few helpful details, send photos if possible, and Bay Delivery will confirm. The public form should not expose internal dispatch, disposal, pricing, or risk language.

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
- owner review
- quote risk advisory
- pricing engine
- profit/margin
- internal assessment

## Admin Experience Design

Admin should hide complexity until it is needed. The top of admin should answer: What needs attention today? Detailed payloads, backup tools, developer diagnostics, calibration internals, and future GPT logs should sit behind lower-level or collapsed sections.

Daily Ops Board cards:

- New Requests
- Needs Follow-Up
- Accepted, Not Booked
- Upcoming Jobs
- Completed, Missing Costs
- Owner Review
- Stale Quotes

## GPT Admin Job Logs / GPT Notes - Proposed Future Feature

### Goal

Let the internal Bay Delivery GPT send structured notes into the admin system for Austin/Dan to review.

This should help capture GPT observations without giving GPT authority over pricing, scheduling, messages, or job status.

### Safe Version

The safe v1 is an internal-only, admin-visible, audit-logged note system.

GPT may create logs such as:

- job observation notes
- quote caution notes
- missing-info recommendations
- photo/access/density risk notes
- follow-up recommendations
- customer-message draft notes
- completed-job calibration observations

GPT must not directly:

- change pricing
- approve or reject quote requests
- schedule jobs
- mark jobs completed/cancelled
- change lifecycle status
- send SMS/email
- create customer-facing messages automatically
- expose internal risk/profit/margin data to customers
- create a second pricing path

### Proposed Data Shape

Possible table name:

```text
gpt_admin_logs
```

Possible fields:

| Field | Purpose |
| --- | --- |
| `log_id` | Unique log id |
| `created_at` | Timestamp |
| `source` | `internal_gpt` |
| `related_entity_type` | `quote`, `quote_request`, `job`, `manual_calibration`, or `general` |
| `related_entity_id` | Optional id for the related entity |
| `title` | Short admin-facing title |
| `summary` | Main log body |
| `recommendation` | Optional suggested next step |
| `risk_flags` | Optional internal risk labels |
| `follow_up_needed` | Boolean advisory flag |
| `customer_visible` | Hardcoded false |
| `pricing_effect` | Hardcoded `none` |
| `created_by` | `internal_gpt` or operator source |

### Proposed API Shape

Future endpoint options:

```text
POST /api/gpt/admin-log
GET /admin/api/gpt-logs
```

Recommendation:

- `POST /api/gpt/admin-log` should use the internal GPT bearer token.
- It should be marked as consequential because it writes production admin data.
- It should validate allowed entity types and max lengths.
- It should rate-limit or otherwise prevent spam.
- It should audit successful and failed attempts.
- It should not accept customer-visible logs.
- It should not accept pricing-effect values other than `none`.

### Proposed Admin UI

Recommended v1 surface:

- Desktop admin only.
- Collapsed section: `GPT Notes / GPT Job Logs`.
- Optional detail placement later on quote/job detail views.
- Do not add to mobile admin v1 unless there is a strong field-use reason.
- Clearly label every note as GPT-generated and advisory.

### Recommended PR Breakdown

| Order | PR Title | Scope |
| --- | --- | --- |
| 1 | create GPT admin job log plan | Docs/plan only; no implementation. |
| 2 | create GPT admin log storage and API | Add table, POST endpoint, validation, auth, audit, tests. |
| 3 | create admin GPT notes display | Desktop-admin read-only display. No mobile/customer exposure. |
| 4 | create GPT admin log action schema refresh | Update GPT OpenAPI schema, grounding docs, and exported pack after backend is live. |

### Risk Review

| Level | Risk |
| --- | --- |
| P1 | GPT accidentally mutates pricing, lifecycle status, scheduling, customer messages, or exposes internal notes publicly. Must be structurally prevented. |
| P2 | GPT logs too much sensitive PII or creates noisy/spammy admin clutter. Needs validation, length caps, and clear UI separation. |
| P3 | Admin UI could become crowded. Keep logs collapsed and clearly advisory. |

## Production Observability and Launch Monitoring - Recommended Next Plan

Before adding more feature work, plan production visibility.

Recommended free-first stack:

| Tool / Area | Purpose | Status |
| --- | --- | --- |
| Existing Production Live-Safe Smoke | Health/version/commit/page safety | Complete and working |
| Better Stack free tier | Uptime/page monitoring | Not configured |
| Sentry free Developer tier | Backend error tracking | Not implemented |
| Microsoft Clarity | Public-page UX friction only | Not implemented |
| Google Search Console | Search/indexing visibility | Not confirmed complete |
| Backup freshness/admin visibility | Confirm backup confidence | Future |

Monitoring boundaries:

- Do not record admin sessions in analytics tools.
- Do not send customer phone/address/job notes/photos to analytics unless deliberately reviewed and privacy-safe.
- Do not leak internal risk/profit/margin data.
- Keep launch tools free-first until there is a clear business reason to pay.

## Add / Fix / Refine / Remove - Updated

### Add / Already Added

| Item | Status | Why |
| --- | --- | --- |
| Lead source tracking | Complete no-schema v1 | Helps know where leads come from. |
| Repeat customer marker/history | Complete no-schema v1 | Helps trust good customers and spot patterns. |
| Manual completed-job calibration log | Complete | Captures real job evidence without fake lifecycle jobs. |
| Booking request notification infrastructure | Installed, disabled | Prevents missed booking requests after launch authorization. |
| Prelaunch test data cleanup tooling | Complete | Safe backup-first cleanup process. |

### Add / Still Future

| Item | Why |
| --- | --- |
| Production observability plan | Prevent deploy drift, missed downtime, page issues, and invisible backend failures. |
| GPT admin job logs / notes | Preserve useful GPT observations inside admin without giving GPT authority. |
| Internal customer notes | Track good customer, slow payer, no-show risk, recurring underestimation patterns. |
| Job difficulty score | Internal 1-5 triage from easy curbside through manual-review risk. |
| Missing-info detector | Show exactly what to ask for: photos, item count, access, disposal type, preferred date. |
| Job closeout checklist | Collected amount, payment method, actual labour/disposal/fuel/other costs, underpriced marker, notes. |
| Review request helper/tracking | Generate and track review requests after completed jobs. |

### Fix / Refine

| Area | Refinement |
| --- | --- |
| Admin hierarchy | Keep top as Daily Ops Board; middle as Requests/Jobs/Costing; bottom as Reports/Backup/Settings/Developer/GPT logs. |
| Customer copy | Keep local, helpful wording. Avoid internal labels and numbered-step confusion. |
| Risk wording | Use practical admin wording: review before approving, ask for photos, likely 2-person job, disposal uncertain. |
| Mobile admin | Keep lean: today jobs, customer phone/address, notes, status, mark completed, collected amount later. |
| Quote page polish | Minor future cleanup: residual `Step 5` photo guidance wording and `Small Moves` vs `Small Moving` consistency. |

### Remove / Avoid

| Thing | Reason |
| --- | --- |
| Admin-side quote drafting as primary flow | Keep admin as operations. Use public quote flow and internal GPT separately for drafts. |
| Raw JSON in main workflow | Hide raw request payloads/details behind a details/developer section. |
| Customer-facing risk jargon | Do not show pricing risk, manual review, recommended trailer, under-margin, or operating-cost gap to customers. |
| Automatic smart price adjustment | Avoid until enough completed-job evidence exists. Pricing changes must be deliberate PRs. |
| Customer accounts/login | Too much friction for local service jobs. Customers should not need passwords for a dump run. |
| GPT lifecycle mutation | GPT should not approve, schedule, complete, cancel, price, or send customer messages automatically. |

## Pricing Change Order

Pricing changes should wait until admin risk summaries, completed-job reporting, and manual calibration evidence are reviewed. Then change one service category per PR with focused tests and before/after calibration cases.

| Order | Category | Reason |
| --- | --- | --- |
| 1 | Demolition / rip-out | Highest risk. Shed and teardown calibration supports premium handling. Add premium/manual-review floors and strong minimum protections first. |
| 2 | Moving labour | Protect 2-worker minimums, stairs, long carry, inside work, and customer-belonging risk. |
| 3 | Heavy/dense dump runs | Protect concrete, tile, bricks, dirt, wet debris, shingles, drywall, and disposal uncertainty. |
| 4 | Scrap pickups | Protect inside/basement/heavy/awkward scrap jobs while keeping curbside scrap simple. |
| 5 | Delivery | Add protections for distance, weather, stairs, item value/care, and enclosed trailer needs. |

## Updated Next Task Recommendation

### Recommended next task

```text
create production observability and launch monitoring plan
```

Mode:

```text
Plan-only. Do not implement.
```

Why this comes next:

- Production is now deployed and smoke-tested.
- Live visual audit found no P1/P2 issues.
- Manual calibration entries are already entered.
- Monitoring protects production before adding more capabilities.
- Better Stack, Sentry, Clarity, Search Console, and backup monitoring need privacy and scope decisions before any repo changes.

### Recommended next GPT/repo task after observability planning

```text
create GPT admin job log plan
```

Mode:

```text
Plan-only. Do not implement.
```

Why:

- GPT admin logs are useful, but they touch schema/storage, auth, GPT Actions, admin UI, audit logging, privacy, and production data.
- It should be designed before any implementation PR.

## Codex / Agent Usage Rules

| Task Type | Tool | Plan-only? | Pursue Goal / Goal Mode |
| --- | --- | ---: | ---: |
| Production observability plan | Codex | Yes | Off |
| GPT admin job log plan | Codex | Yes | Off |
| Read-only live visual audit | VS Code Repo Maintainer | No implementation | Off |
| Narrow UI/copy/static PR | Codex | Brief plan then implement | On if scope is narrow |
| Review-comment fix | Codex | Brief plan then implement | On |
| Pricing/schema/auth/Render-sensitive work | Codex | Yes first | Off until approved |

## Updated Exact Future PR Sequence

| Order | PR Title | Scope | Status |
| --- | --- | --- | --- |
| 1 | create production observability and launch monitoring plan | Plan free-first production monitoring, error tracking, UX tracking, search visibility, and backup monitoring. | Next recommended |
| 2 | create GPT admin job log plan | Plan internal GPT-to-admin notes/logging without implementation. | After observability plan or if GPT workflow is prioritized |
| 3 | create privacy safe Sentry integration | Backend error tracking with PII-safe config. | Future |
| 4 | create public page analytics boundary | Optional Clarity/Search Console/public-page tracking plan or implementation. | Future |
| 5 | create GPT admin log storage and API | Add internal-only GPT note write path with audit logging. | Future, only after plan approval |
| 6 | create admin GPT notes display | Desktop-admin display for GPT-generated advisory notes. | Future |
| 7 | create GPT admin log action schema refresh | Update GPT Action schema and grounding after backend support is live. | Future |
| 8 | create job closeout checklist improvements | Improve post-job costing/evidence capture. | Future |
| 9 | create pricing readiness review | Review completed-job/manual calibration evidence before category pricing PRs. | Future |
| 10 | create demolition pricing safeguards | First category-specific pricing PR, if evidence supports it. | Future/deferred |

## Codex Prompt Seed - Production Observability Plan

```text
REASONING:
High

MODE:
Plan-only. Do not implement. Do not modify files. Do not create a branch. Do not open a PR.

TASK:
Create a Production Observability and Launch Monitoring Plan for Bay Delivery Quote Copilot.

GOAL:
Plan the safest free-first monitoring setup for launch: Better Stack, Sentry, Microsoft Clarity, Google Search Console, existing GitHub smoke tests, Render logs, and future backup freshness visibility.

BOUNDARIES:
No pricing changes. No customer quote flow changes. No admin behavior changes. No schema/storage changes. No Render/workflow/requirements/VERSION changes. No third-party scripts or SDKs in this task. Do not mutate production data.

FINAL REPORT:
Return the recommended free-first stack, P1/P2/P3 concerns, implementation order, whether repo changes are needed now, and confirm no files were modified.
```

## Codex Prompt Seed - GPT Admin Job Log Plan

```text
REASONING:
Extra High

MODE:
Plan-only. Do not implement. Do not modify files. Do not create a branch. Do not open a PR.

TASK:
Plan a safe internal GPT-to-admin job log feature for Bay Delivery Quote Copilot.

GOAL:
Design an internal-only, admin-visible, audit-logged GPT notes/logs feature where GPT can record advisory job observations, quote cautions, missing-info recommendations, follow-up suggestions, and calibration observations.

BOUNDARIES:
GPT must not change pricing, approve/reject quote requests, schedule jobs, mark jobs complete, mutate lifecycle status, send SMS/email, create customer-facing messages automatically, expose internal data to customers, or create a second pricing engine.

FINAL REPORT:
Return proposed architecture, endpoint/table/UI options, auth/consequential-action recommendation, required tests, PR breakdown, P1/P2/P3 risks, whether to proceed now or defer, and confirmation no files were modified.
```

## Final Operating Loop

```text
Customer submits simple quote
  -> system captures useful hidden facts
  -> admin sees clear risk, lead source, customer history, missing info, and scheduling state
  -> Austin/Dan approve, follow up, or book manually
  -> job gets completed
  -> actual costs and calibration evidence are entered
  -> system shows profit and underpricing patterns
  -> GPT may summarize/advisory-log observations internally only
  -> pricing is improved carefully by category through deliberate PRs
```

The goal is not to build a flashy quote calculator. The goal is to build a small business operating system that protects margin, reduces missed follow-ups, preserves real-world job learnings, and makes daily decisions easier.
