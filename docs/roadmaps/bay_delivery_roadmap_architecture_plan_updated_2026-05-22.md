# Bay Delivery Quote Copilot - Roadmap & Architecture Plan

Prepared: May 10, 2026
Updated: May 23, 2026
Prepared for: Austin / Bay Delivery

## Executive Principle

Customer side stays simple. Admin side tells Austin and Dan what needs attention. Pricing authority stays protected in `app/quote_engine.py`. Reporting and calibration learn from completed jobs before any pricing changes are made.

The system should stay boring, stable, and profitable. New features should make Bay Delivery easier to operate, not create a second pricing brain, a public chatbot, or a fragile CRM clone.

## May 23 Update Summary

This update refreshes the May 10 roadmap with actual completed work through PR #307 and the manual GPT Builder/live action verification that followed.

Key updates:

- Marked completed admin, quote-flow, risk, reporting, scheduling, cleanup, notification, security, and docs work.
- Added current verified production state after redeploy and Production Live-Safe Smoke.
- Added real completed-job calibration evidence already entered into admin.
- Marked the GPT Admin Notes pipeline complete: backend/storage/API, desktop admin display, GPT Action schema/docs/grounding, Builder compatibility cleanup, Custom GPT refresh, `getGptQuote` action retest, and live fake `createGptAdminNote` action/admin display verification.
- Re-ranked the next practical tasks: launch-readiness/current-state audit after this roadmap sync first, then booking notification failure/skipped-send visibility planning as a later candidate, then later pricing/category improvements.
- Preserved all hard boundaries: one pricing engine, SQLite as source of truth, admin-only internal risk, no customer-facing GPT pricing path.

## Current Verified Repo / GPT State

As of May 23, 2026:

| Area | Status |
| --- | --- |
| Main verification | Verified through PR #307 |
| Latest verified main commit | `83f58e5 create GPT action builder compatibility cleanup (#307)` |
| Version parity | Passed: `0.11.0` |
| GPT grounding pack parity | Passed |
| Compileall | Passed |
| Focused GPT/admin/static tests | `tests/test_gpt_admin_notes.py` 28 passed; `tests/test_gpt_quote_endpoint.py` 12 passed; `tests/test_static_assets.py` 36 passed |
| Full pytest | Passed: 711 |
| Protected no-go diff after PR #307 | No output |
| Custom GPT Knowledge | Updated from `dist/gpt_grounding_pack` after PR #307 |
| Custom GPT Actions schema | Updated from `docs/gpt/GPT_ACTIONS_OPENAPI.yaml` after PR #307 |
| GPT Builder | Updated and saved |
| Manual `getGptQuote` action test | Passed after Builder schema cleanup |
| Manual live fake admin-note action test | Passed through Custom GPT -> Render endpoint -> SQLite -> desktop admin GPT Notes display |
| Observed fake GPT Admin Note id | `f39e3b09-ff31-4449-a431-dadda7daab6b` |
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
| Production Observability | Monitor uptime, deploy drift, customer-page health, errors, and launch readiness | Free-first, privacy-safe, no admin/customer PII leakage. | Not completed; later plan candidate |
| Internal GPT Layer | Quote support, summarization, draft help, risk explanation, and bounded advisory admin notes | Internal-only and recommendation-only. Never pricing authority. | Complete current v1: quote action and GPT Admin Notes action verified |
| GPT Admin Notes | Let GPT create admin-visible internal advisory notes for Austin/Dan review | Consequential, audit-logged, admin-only, `customer_visible=false`, and `pricing_effect=none`. | Complete current v1 |
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
| PR #304 - create GPT admin notes storage and API | Complete | Internal bearer-protected GPT Admin Notes POST endpoint, persisted storage, admin GET endpoint, validation, idempotency/retry safety, duplicate handling, audit logging, backup/export/import coverage, Starlette security fix, and tests. |
| PR #305 - create admin GPT notes display | Complete | Collapsed read-only desktop admin GPT Notes (Advisory) display with safe DOM text rendering, fetch/display handling, empty/error states, desktop-only exposure, and static tests. |
| PR #306 - create GPT admin notes action schema refresh | Complete | Added `createGptAdminNote` to GPT Action schema/docs/grounding, marked `x-openai-isConsequential: true`, and regenerated the grounding pack. |
| PR #307 - create GPT action builder compatibility cleanup | Complete | Removed unsupported `X-GPT-Grounding-Revision` action parameter from the Builder-facing OpenAPI schema, updated docs wording, and regenerated the grounding pack. |
| Manual Custom GPT Builder refresh after PR #307 | Complete | Knowledge files and Actions schema were updated from repo-generated sources; Builder was saved. |
| Manual GPT action verification after PR #307 | Complete | `getGptQuote` passed after Builder schema cleanup, and a live fake `createGptAdminNote` action wrote through Render to SQLite and appeared in desktop admin GPT Notes (Advisory). |
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
| Booking notification failure/skipped-send admin visibility | Not implemented | Later candidate after launch-readiness/current-state audit; plan first before admin/runtime work. |
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
| 10 | GPT Admin Notes | Let GPT send internal admin-visible advisory notes for review. | Complete current v1 |
| 11 | Launch-Readiness / Current-State Audit | Re-check repo, GPT Builder, Render/live state, docs parity, and launch blockers after this roadmap sync. | Recommended next task |
| 12 | Production Observability and Launch Monitoring | Better uptime, error, UX, search, and backup visibility. | Later plan candidate |
| 13 | Booking Notification Failure Visibility | Show failed/skipped booking notification attempts clearly in desktop admin before launch. | Later plan candidate |
| 14 | Job Closeout + Internal Notes + Difficulty Scoring | More complete post-job and customer history intelligence. | Future |
| 15 | Pricing PRs by Service Category | Deliberate category pricing changes after evidence review. | Future/deferred |
| 16 | Photo Evidence / Photo Assistant | Advisory image notes; no auto-pricing. | Future/deferred |
| 17 | Customer-Facing GPT / SMS / Auto Scheduling | Customer automation layer. | Future/high-risk; defer |

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

## GPT Admin Notes - Completed Current v1

### Goal

Let the internal Bay Delivery GPT send structured advisory notes into the admin system for Austin/Dan to review.

This should help capture GPT observations without giving GPT authority over pricing, scheduling, messages, or job status.

### Completed Safe Version

The completed v1 is an internal-only, admin-visible, audit-logged note system.

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

### Completed Data/API Shape

Completed table:

```text
gpt_admin_notes
```

Completed interfaces:

- Internal GPT write action: `POST /api/gpt/admin-notes`, bearer-token protected by `GPT_INTERNAL_API_TOKEN`.
- Admin read path: `GET /admin/api/gpt-notes`, admin-auth protected.
- GPT Action operation: `createGptAdminNote`.
- Action is marked consequential because it writes persisted production admin data.
- Notes are advisory-only, internal-only, admin-visible only, `customer_visible=false`, and `pricing_effect=none`.
- Backend validation, idempotency/retry safety, duplicate handling, rate limiting, audit logging, backup/export/import coverage, and tests are complete.
- GPT Builder action schema no longer exposes unsupported caller grounding revision as an action parameter.
- Desktop admin shows a collapsed read-only `GPT Notes (Advisory)` section with safe DOM text rendering, empty/error states, and no mobile/customer exposure.

### Manual Verification Completed

- Custom GPT Knowledge files were updated from `dist/gpt_grounding_pack` after PR #307.
- Custom GPT Actions schema was updated from `docs/gpt/GPT_ACTIONS_OPENAPI.yaml` after PR #307.
- GPT Builder was updated and saved.
- Manual `getGptQuote` action test passed after Builder schema cleanup.
- Manual live fake `createGptAdminNote` action test passed through Custom GPT -> Render endpoint -> SQLite -> desktop admin GPT Notes display.
- Observed fake note id: `f39e3b09-ff31-4449-a431-dadda7daab6b`.

### Risk Review

| Level | Risk |
| --- | --- |
| P1 | GPT accidentally mutates pricing, lifecycle status, scheduling, customer messages, or exposes internal notes publicly. Must be structurally prevented. |
| P2 | GPT notes could become noisy or include unnecessary PII. Existing validation, length caps, and advisory UI separation reduce this risk; operator review still matters. |
| P3 | Admin UI could become crowded. Keep logs collapsed and clearly advisory. |

## Production Observability and Launch Monitoring - Later Plan Candidate

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
| Booking notification failure/skipped-send visibility | Help Austin/Dan see failed or skipped internal booking alert attempts before launch. |
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
launch-readiness/current-state audit after roadmap sync
```

Mode:

```text
Read-only audit. Do not mutate production data.
```

Why this comes next:

- Main is verified through PR #307, and GPT Builder/live action verification has completed.
- Roadmap/current-state docs need to be treated as freshly synced before the next launch decision.
- A launch-readiness pass should re-check repo state, GPT grounding/current-state parity, live Render health/version/commit, public quote/admin entry points, and any remaining launch blockers before new feature work.
- This protects production and avoids choosing the next feature from stale docs.

### Recommended next feature candidate after launch-readiness audit

```text
show booking notification failures/skipped sends in desktop admin before launch
```

Mode:

```text
Plan first. Implement only as a narrow follow-up PR if launch-readiness audit is clear.
```

Why:

- Booking notification infrastructure exists but remains disabled until launch authorization.
- Failed/skipped notification attempts are tracked internally but are not yet operator-visible in desktop admin.
- This is useful before launch, but it should not displace the immediate launch-readiness/current-state audit.

## Codex / Agent Usage Rules

| Task Type | Tool | Plan-only? | Pursue Goal / Goal Mode |
| --- | --- | ---: | ---: |
| Launch-readiness/current-state audit | Codex or VS Code Agent | Read-only | Off |
| Booking notification failure visibility plan | Codex | Yes | Off |
| Production observability plan | Codex | Yes | Off |
| Read-only live visual audit | VS Code Repo Maintainer | No implementation | Off |
| Narrow UI/copy/static PR | Codex | Brief plan then implement | On if scope is narrow |
| Review-comment fix | Codex | Brief plan then implement | On |
| Pricing/schema/auth/Render-sensitive work | Codex | Yes first | Off until approved |

## Updated Exact Future PR Sequence

| Order | PR Title | Scope | Status |
| --- | --- | --- | --- |
| 1 | create launch readiness current state audit | Read-only verification of repo, GPT Builder/live action state, Render health/version/commit, public quote/admin shells, docs parity, and launch blockers. | Next recommended |
| 2 | create booking notification failure visibility plan | Plan desktop-admin visibility for failed/skipped notification attempts before launch. | Later candidate after audit |
| 3 | create production observability and launch monitoring plan | Plan free-first production monitoring, error tracking, UX tracking, search visibility, and backup monitoring. | Future |
| 4 | create privacy safe Sentry integration | Backend error tracking with PII-safe config. | Future |
| 5 | create public page analytics boundary | Optional Clarity/Search Console/public-page tracking plan or implementation. | Future |
| 6 | create job closeout checklist improvements | Improve post-job costing/evidence capture. | Future |
| 7 | create pricing readiness review | Review completed-job/manual calibration evidence before category pricing PRs. | Future |
| 8 | create demolition pricing safeguards | First category-specific pricing PR, if evidence supports it. | Future/deferred |

## Codex Prompt Seed - Launch-Readiness / Current-State Audit

```text
REASONING:
High

MODE:
Read-only audit. Do not modify files. Do not create a branch. Do not open a PR. Do not mutate production data.

TASK:
Run a launch-readiness/current-state audit for Bay Delivery Quote Copilot after the roadmap/current-state docs sync.

GOAL:
Verify current repo/main state, docs/GPT grounding parity, Custom GPT Builder/action state from available evidence, Render live health/version/commit, public quote/admin entry points, and remaining launch blockers before choosing any new feature work.

BOUNDARIES:
No pricing changes. No customer quote flow changes. No admin behavior changes. No schema/storage changes. No Render/workflow/requirements/VERSION changes. Do not submit live quote forms, create bookings, write GPT notes, send notifications, clean data, or trigger customer-facing actions.

FINAL REPORT:
Return verified repo commit/version, validation results, GPT grounding/current-state status, live Render health/version/commit status, public/admin page audit results, protected no-go result, P1/P2/P3 launch blockers, and the next recommended task.
```

## Codex Prompt Seed - Booking Notification Failure Visibility Plan

```text
REASONING:
High

MODE:
Plan-only. Do not implement. Do not modify files. Do not create a branch. Do not open a PR.

TASK:
Plan desktop-admin visibility for booking notification failed/skipped sends before launch.

GOAL:
Design the smallest operator-visible way to show booking notification attempt failures/skipped sends so Austin/Dan can catch missed internal alerts before launch authorization.

BOUNDARIES:
No customer-facing messaging changes. No notification sending behavior changes. No SMTP/env var changes. No pricing changes. No customer quote flow changes. No mobile-admin changes unless explicitly justified later. Do not mutate production data.

FINAL REPORT:
Return proposed read path, desktop-admin display option, tests, protected surfaces, P1/P2/P3 risks, and whether to proceed only after launch-readiness audit is clear.
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
