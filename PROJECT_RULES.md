# Bay Delivery Quote Copilot — Project Rules

Agents must read this file before performing architectural changes, security reviews, refactors, deployment-sensitive fixes, schema changes, pricing changes, admin workflow changes, customer-flow changes, or roadmap feature work.

This document defines architecture invariants, security rules, pricing and business guardrails, roadmap discipline, validation expectations, and change-scope rules for the repository.

Violating these rules can break production workflows, pricing integrity, admin safety, customer compatibility, or deployment stability.

---

## Project Identity

Bay Delivery Quote Copilot is production infrastructure for Bay Delivery in North Bay, Ontario.

It is a real quoting, request, admin, follow-up, scheduling, costing, and reporting system.

It is not a sandbox.

It is not an experiment.

The system goal is:

- protect margin
- prevent undercharging
- keep customer requests simple
- help Austin and Dan see what needs attention
- track completed-job costs before pricing changes
- improve pricing deliberately, one category at a time

---

## Executive Principle

Customer side stays simple.

Admin side tells Austin and Dan what needs attention.

Pricing authority stays protected in:

- `app/quote_engine.py`

Reporting learns from completed jobs before any pricing changes are made.

---

## Core Architecture Rules

SQLite is the source of truth.

Google Calendar is a mirror only.

Google Drive is a support/backup tool only.

Database writes must occur before external API calls.

Calendar sync failures must not corrupt or roll back valid database state.

Route handlers must remain thin orchestration layers.

Business logic belongs in:

- `app/services/`

SQL and persistence logic belong in:

- `app/storage.py`

External API wrappers belong in:

- `app/integrations/`

Do not move business logic into route handlers.

Do not move SQL or persistence policy into services or routes.

Do not make Google Calendar, Google Drive, GPT, or frontend JavaScript the source of truth for operational state.

---

## Layer Responsibilities

### Routes

Routes may:

- validate and bind request inputs
- enforce authentication/authorization gates
- call services
- return HTTP responses

Routes must not:

- contain durable business policy
- perform raw SQL
- directly orchestrate external integrations
- contain pricing logic beyond passing structured inputs to services
- contain report math if the math is non-trivial

### Services

Services orchestrate workflows.

Services may call:

- storage functions
- integration clients
- pure calculation/report helpers

Services may contain:

- admin read-model logic
- advisory/report aggregation
- workflow coordination
- non-pricing business policy

Services must not:

- perform raw SQL
- contain FastAPI route definitions
- directly manipulate framework request objects
- duplicate storage-layer responsibilities
- create a second pricing engine

### Storage

All SQL belongs in `app/storage.py`.

Storage code may:

- read and write SQLite
- manage transactions
- enforce persistence-safe allowlists
- return raw rows or targeted read-model source rows

Storage code must not:

- call external APIs
- contain route logic
- contain frontend assumptions
- contain pricing policy unless it is persistence validation only
- contain complex report presentation logic

### Integrations

External API wrappers belong in `app/integrations/`.

Integration code must be isolated from route and storage concerns.

Integration failures must not silently corrupt database state.

---

## Pricing Authority Rules

`app/quote_engine.py` is the only authoritative pricing engine.

Only `app/quote_engine.py` may calculate authoritative quote totals.

Do not create duplicate pricing logic in:

- services
- admin UI
- customer frontend
- GPT docs
- reports
- tests
- calibration scripts
- storage helpers
- route handlers

Reports, advisories, admin summaries, GPT outputs, and calibration tools may inform owner review, but they must not change quote totals.

Do not call pricing calculation functions from reporting/read-model features unless the task explicitly requires it and the plan explains why.

Do not change pricing logic unless the task is explicitly a pricing PR.

Do not change quote totals unless the task is explicitly a pricing PR.

Do not change cash/EMT/HST behavior unless the task is explicitly a pricing PR.

Do not change service minimums unless the task is explicitly a pricing PR.

Do not change `config/business_profile.json` pricing behaviour unless explicitly requested and scoped.

---

## Pricing and Business Rules

Pricing changes must be narrow, auditable, and intentionally scoped.

Do not broadly reprice multiple service lanes unless explicitly requested.

Preserve these business principles:

- Bay Delivery should not try to be the cheapest mover.
- Moving is a selective lane and should protect margin.
- Tiny junk jobs must remain believable.
- Large haul-away, cleanup, and estate jobs must not flatten too cheaply.
- Convenience, awkwardness, dense materials, access, disposal risk, and real labour must matter.

Prefer:

- floors
- anchors
- narrowly scoped adders
- service-specific adjustments
- targeted calibration backed by tests
- before/after pricing scenarios

Avoid:

- noisy global repricing
- broad multipliers applied across unrelated lanes
- flattening large-job pricing curves
- mixing unrelated pricing changes in one pass
- automatic smart price adjustment from reports or AI

Do not change unrelated service lanes in the same pricing task.

Preserve recent pricing calibrations unless explicitly instructed otherwise.

---

## Pricing Change Order

Pricing changes should wait until admin risk summaries and completed-job reporting are useful.

Then change one service category per PR with focused tests and before/after calibration cases.

Approved later pricing order:

1. Demolition / rip-out
2. Moving labour
3. Heavy/dense dump runs
4. Scrap pickups
5. Delivery

Do not start pricing PRs early unless Austin explicitly overrides the roadmap.

## Semantic Combination Review Matrix

Future pricing-sensitive PRs that touch `app/quote_engine.py`, quote totals, demolition safeguards, access/material/structure phrase matching, or owner-review/advisory pricing metadata must review semantic combinations, not only isolated positive and isolated false-positive examples.

Required review rows:

- Target-only positive: example `large deck demolition`. Expected: safeguard triggers.
- Access-only false positive: example `deck access to remove cabinets`. Expected: safeguard does not trigger.
- Target plus access combined: example `large deck demolition with deck access`. Expected: safeguard still triggers because the demolition target is explicit.
- Cleanup/debris/removal near miss: example `old lumber cleanup and removal`. Expected: cleanup/debris wording does not become demolition-heavy unless the demolition target is explicit.
- Simple structure removal: example `old shed removal`. Expected: protected if the target is a clear structure and removal is already accepted customer language.
- Word-order swaps: examples `tear off roof` and `roof tear-off` and `roof tear off`. Expected: common safe customer word orders are covered.
- Existing vocabulary preservation: examples `gazebo`, `outbuilding`, `carport`, `shed`, `deck`, `fence`. Expected: new safeguards do not accidentally drop existing protected structure terms, and do not invent a broad new taxonomy unless explicitly scoped.
- Substring traps: examples `waterproofing is not roofing`, `proofing is not roofing`, `wall-to-wall carpet is not wall demolition`, `drywall is not wall demolition`. Expected: no accidental substring matches.
- Customer/internal boundary: customer-facing quote responses must not expose owner-review, risk, margin, admin, advisory, or internal wording.
- Payment math: cash remains no HST and rounded correctly; EMT/e-transfer adds 13% HST and rounds to cents; no hardcoded EMT totals; no second pricing path.

Required review rule for every new pricing safeguard or phrase-matching rule:

- include at least one clean positive
- include at least one clean false positive
- include at least one positive mixed with access/location wording
- include at least one cleanup/debris near miss
- include at least one common alternate customer wording
- include at least one substring trap
- include an existing-vocabulary preservation check when the rule touches known target vocabularies

Do not commit until this matrix is checked.

Fix valid P1/P2 findings before commit.

If the required fix would need forbidden files or broad matching, stop and report instead of expanding scope.

---

## Customer/Admin Boundary Rules

Customer-facing pages must use simple, helpful language.

Customer-facing pages must not expose internal business-risk language.

Customer-facing pages must not expose:

- internal risk summaries
- quote risk advisory fields
- internal risk assessment fields
- owner-review flags
- profit or margin language
- completed-job costing data
- underquoted/painful job labels
- recommended trailer/internal dispatch notes
- pricing caution language
- operating-cost gaps
- raw request JSON
- admin-only statuses
- developer diagnostics

Admin surfaces may show:

- follow-up status
- quote risk advisory
- internal risk assessment
- owner-review flags
- missing information
- completed-job costs
- profit/margin reporting
- scheduling and booking queues
- internal notes
- calibration evidence
- operational risk signals

Customer side stays calm.

Admin side carries the complexity.

---

## Current Roadmap Discipline

Follow the roadmap order unless Austin explicitly changes it.

Current verified baseline:

- Main is verified through PR #323 plus follow-up cSpell commit `15b9d7b` (short SHA).
- Latest completed PR baseline: PR #323 `create desktop admin collapsible section polish`.
- Latest verified main commit after PR #323 (full SHA): `15b9d7b35a22aef982772f729cdad05829991418 add "Avenir" to cSpell custom words list`.
- Current version: `0.12.0`.

Instruction hierarchy:

- Use `docs/instruction_hierarchy.md` when repo instructions, templates, skills, memory, or current-state docs appear to conflict. In the exported GPT grounding pack, this file is shipped as `instruction_hierarchy.md`.

Current active roadmap/current-state sequence:

1. Keep project instructions and current-state documentation aligned with verified baseline before new broad feature work.
2. Continue customer quote-page simplification follow-on work with payload compatibility preserved.
3. Continue admin follow-up/scheduling workflow improvements only when explicitly scoped.
4. Defer pricing PRs by service category until evidence and explicit approval.
5. Keep internal GPT and photo-assistant changes separately scoped.

Do not skip ahead to SEO/growth, GPT, image AI, or pricing work while an earlier roadmap safety/reporting feature is still pending, unless Austin explicitly approves the reorder.

Backlog/growth ideas such as SEO landing pages are valuable, but they should not displace active roadmap safety/reporting work without explicit approval.

---

## Completed Job Reporting Rules

Completed-job costing is the truth meter for future pricing decisions.

Completed-job reporting is evidence for owner review and future pricing PRs.

Completed-job reporting is not automatic pricing authority.

Completed-job reports must remain:

- admin/internal-only
- read-only unless explicitly scoped otherwise
- separate from customer quote flow
- separate from pricing calculation
- separate from GPT grounding unless explicitly planned

Completed-job reports may show:

- final amount collected
- actual labour cost
- actual disposal cost
- actual fuel cost
- actual other costs
- known profit
- known margin
- missing cost fields
- payment status
- job profit status
- owner-review flags
- service/category breakdowns

Missing costs mean the job closeout is incomplete.

If costs are missing, do not trust the profit or margin conclusion.

Zero collected amount means the job closeout is incomplete unless explicitly handled in a dedicated future workflow.

Below 20% known margin may trigger owner review.

`job_profit_status` may be used as an operator/admin signal, but numeric margin and missing-cost completeness must remain explicit.

Completed-job reports must not automatically alter pricing.

---

## Follow-Up and Admin Workflow Rules

Admin workflows should make daily work clearer.

Admin screens should help answer:

- What needs attention today?
- What leads need follow-up?
- What accepted jobs are not booked?
- What upcoming jobs are scheduled?
- What completed jobs are missing costs?
- What jobs need owner review?
- What stale quotes need closing or re-quoting?

Admin shortcuts must be narrow and intentional.

Read-only cards should not mutate records.

Mutation buttons must reuse existing authenticated endpoints when possible.

Do not create duplicate mutation paths for the same admin action unless explicitly justified.

---

## GPT Boundary Rules

GPT is internal-only and recommendation-only.

GPT can:

- summarize
- draft customer messages
- explain risk
- help Austin/Dan review operations
- suggest follow-up questions
- support owner review

GPT must not:

- override pricing
- create a second pricing system
- expose admin/internal data to customers
- become the source of truth
- automatically mutate jobs/quotes/requests
- replace SQLite as the operational record

GPT grounding changes must be scoped separately and paired with grounding pack parity/export checks when applicable.

---

## Refactor Workflow Rules

When performing refactors:

1. Read this file first.
2. Explain the proposed refactor plan.
3. Move one feature area at a time.
4. Preserve endpoint paths and request/response behaviour.
5. Ensure the app still imports and compiles after each step.
6. Ensure tests continue to pass after each step.

Never refactor the entire application at once.

Preferred order of refactor:

1. Scheduling
2. Quotes and booking
3. Uploads and attachments
4. Backup and restore
5. Optional utilities

Do not mix refactors with pricing, deployment hardening, security hardening, schema-tightening work, roadmap features, or UI polish.

---

## Storage Layer Rules

All SQL belongs in `app/storage.py`.

Rules:

- Use parameterized queries.
- Use allowlists for dynamic field updates.
- Avoid dynamic SQL construction except for explicitly allowlisted field selection or update patterns.
- Use safe transactions.
- Keep storage helpers persistence-focused.
- Prefer targeted read helpers for report source rows.

SQLite must run with:

- WAL mode
- busy timeout
- safe transaction handling

Schema changes must be backward-compatible unless explicitly approved.

Do not rename or drop columns used by live workflows without a dedicated migration plan.

Do not couple schema changes with unrelated pricing, UI, reporting, deployment, or refactor work.

---

## Scheduling Rules

Scheduling must follow the database-first workflow.

Correct pattern:

1. Update the job record in the database.
2. Attempt Google Calendar sync.
3. If Calendar fails:
   - update `calendar_sync_status`
   - record `calendar_last_error`
   - do not roll back valid database state

Cancel workflow must preserve scheduling history.

Calendar is a mirror, not the source of truth.

---

## Schema Compatibility Rules

Request and response schemas are part of the public contract.

Do not tighten validation or forbid previously accepted fields without:

- inspecting current callers
- checking logs and tests for compatibility risk
- scoping the change as a separate narrow pass

Prefer additive schema changes over breaking changes.

Schema-tightening work must not be mixed with unrelated pricing, UI, refactor, reporting, or deployment work.

Unknown-field handling changes require explicit review of compatibility risk.

---

## Security Rules

Admin endpoints must require authentication and fail closed.

Customer flows must use secure tokens:

- `accept_token`
- `booking_token`

Tokens must be validated before any state-changing write.

Auth and token checks must happen before:

- state-changing writes
- file uploads
- privileged data access
- admin reports
- backup/export/import/restore actions

Customer PII rules:

- customer name and phone must not be editable after quote creation
- external integrations must receive minimal PII

Google Calendar events must never contain:

- phone numbers
- full notes
- sensitive customer data

Do not weaken:

- request size limits
- admin lockout protections
- trusted proxy and client IP handling
- token authorization checks
- security headers
- origin/referer protections on admin mutations

Do not expose secrets in logs, tests, fixtures, screenshots, documentation, exports, or PR comments.

Security fixes must be narrow and auditable.

---

## Deployment and Environment Rules

Production behaviour may depend on environment variables.

Agents must inspect deployment-sensitive environment configuration before proposing code changes for:

- CORS
- proxy and forwarded IP trust
- auth credentials
- storage backend selection
- Google integration settings
- deployment-only security behaviour
- Render behaviour
- live-safe smoke behaviour

Prefer env-only fixes when the issue is operational and the code already supports the intended behaviour.

Production configs must not rely on localhost development defaults.

Do not mix deployment hardening with unrelated pricing, UI, reporting, refactor, roadmap features, or schema-tightening work.

When production safety depends on environment configuration, document the expected production value clearly.

---

## Frontend Compatibility Rules

The frontend uses static HTML, CSS, and JavaScript.

Backend API compatibility must be preserved.

Never rename form fields used by API endpoints unless explicitly instructed.

Never change payload shape, field names, IDs, or response contract without explicit approval.

Frontend styling changes must not alter API payloads.

Do not mix frontend polish with backend behaviour changes unless explicitly requested.

Customer quote page changes must preserve:

- `/quote/calculate` usage
- existing payload keys
- booking/accept token behaviour
- structured intake compatibility
- customer-friendly wording

Desktop admin changes must not leak into:

- customer quote assets
- mobile admin assets
- public responses

Mobile admin must remain lean unless explicitly scoped.

---

## AI Image Estimation Rules

AI may suggest structured inputs only.

AI must never determine final price.

Final pricing must always be calculated by the pricing engine.

Image analysis must live in:

- `app/services/ai_estimation_service.py`

AI-derived inputs must remain auditable and overridable by deterministic pricing rules.

Do not allow image AI to auto-price or override `app/quote_engine.py`.

---

## Change Scope Rules

Each task should have one clear purpose.

Do not combine in one PR or change set:

- pricing changes
- deployment hardening
- security hardening
- dependency updates
- schema tightening
- UI behaviour changes
- refactors
- GPT grounding changes
- roadmap features
- docs cleanup
- SEO/growth work

Prefer this sequence:

1. inspect first
2. confirm root cause
3. implement the smallest safe diff only
4. verify with targeted tests or live-safe checks
5. open/update PR
6. stop

No broad refactors during focused fixes.

No formatting-only churn.

No opportunistic cleanup during narrow production fixes.

Prefer vertical slices and incremental changes over sweeping edits.

Docs-only PRs must stay docs-only.

Dependency/security lock refresh PRs must stay dependency-only.

---

## Testing Requirements

All code changes must pass the repo’s standard validation unless explicitly waived with a reason.

Default validation from repo root:

```powershell
cd C:\Repos\Bay-Delivery-Quote-Copilot

git status --short --branch

git diff --check

.\.venv\Scripts\python.exe tools\check_version_parity.py

.\.venv\Scripts\python.exe tools\check_gpt_grounding_pack_parity.py

.\.venv\Scripts\python.exe -m compileall app tools scripts tests

.\.venv\Scripts\python.exe -m pytest -q
```

Also run focused tests based on files changed.

Examples:

- pricing changes must add or update targeted pricing tests
- API contract changes must add or update validation and contract coverage
- security changes should include targeted regression coverage when practical
- deployment-only fixes should include a documented live verification procedure if no code changes are made
- admin UI changes should run static/admin tests
- admin read-model changes should run related admin/storage tests
- completed-job reporting changes should run job costing, ops queue, static assets, and full suite

If tests fail, fix with minimal changes.

Do not widen PR scope just to improve unrelated tests.

If Playwright is missing locally, report it as environment-skipped unless the task explicitly asks to install it.

---

## Protected Diff Rules

Before committing or opening/updating a PR, run a protected diff check appropriate to the task.

Common protected diff command for branch work:

```powershell
git diff main...HEAD -- app/quote_engine.py app/services/quote_service.py config/business_profile.json render.yaml .github/workflows docs/gpt dist/gpt_grounding_pack requirements.txt requirements.lock.txt VERSION static/quote.html static/quote.js static/quote.css static/admin_mobile.html static/admin_mobile.js
```

Expected result:

- no output unless the PR explicitly targets those files

For broader admin/backend work, include additional protected files as appropriate:

```powershell
git diff main...HEAD -- app/quote_engine.py app/services/quote_service.py app/main.py app/storage.py app/services/admin_ops_queue.py config/business_profile.json render.yaml .github/workflows docs/gpt dist/gpt_grounding_pack requirements.txt requirements.lock.txt VERSION static/quote.html static/quote.js static/quote.css static/admin_mobile.html static/admin_mobile.js
```

For post-merge verification of the latest merge:

```powershell
git diff HEAD~1..HEAD -- app/quote_engine.py app/services/quote_service.py app/main.py app/storage.py app/services/admin_ops_queue.py config/business_profile.json render.yaml .github/workflows docs/gpt dist/gpt_grounding_pack requirements.txt requirements.lock.txt VERSION static/quote.html static/quote.js static/quote.css static/admin_mobile.html static/admin_mobile.js
```

Expected result:

- no output unless the merged PR explicitly targeted those files

If main has advanced after a specific PR merge, do not use `HEAD~1..HEAD` to verify that older PR.

Use merge-aware diff:

```powershell
git diff --name-only "<merge_commit>^1" "<merge_commit>"
```

and protected diff:

```powershell
git diff "<merge_commit>^1" "<merge_commit>" -- app/quote_engine.py app/services/quote_service.py app/main.py app/storage.py app/services/admin_ops_queue.py config/business_profile.json render.yaml .github/workflows docs/gpt dist/gpt_grounding_pack requirements.txt requirements.lock.txt VERSION static/quote.html static/quote.js static/quote.css static/admin_mobile.html static/admin_mobile.js
```

---

## PR Workflow Rules

Default repo workflow:

1. Verify current state.
2. Plan.
3. Implement in a narrow branch.
4. Validate.
5. Run protected diff check.
6. Open/update PR.
7. Stop.
8. Review PR.
9. Merge only after Austin explicitly says to merge.
10. Post-merge verify `main`.
11. Start the next task only after verification passes.

Agents must not merge unless Austin explicitly says to merge.

After opening or updating a PR, stop.

Do not start the next feature from the same PR task.

Use squash merge for PRs that have multiple cleanup/review-fix commits unless Austin chooses otherwise.

---

## Post-Merge Verification Rules

After merging a PR, run read-only post-merge verification on `main`.

Post-merge verification must:

- sync `main`
- confirm working tree is clean
- confirm merge evidence
- confirm changed files are expected
- run version parity
- run GPT grounding parity
- run compileall
- run focused tests
- run full suite when practical
- run protected diff check
- confirm customer/admin/mobile/backend/GPT/deployment boundaries

Post-merge verification must not:

- modify files
- create branches
- commit
- push
- open PRs
- fix issues during the verification task
- run live mutation endpoints

If a post-merge failure appears, report it clearly and classify it as:

- environment issue
- actual repo risk
- verification-method issue

Do not patch during post-merge verification.

---

## Code Quality Rules

Keep modules small and focused.

Avoid growing `main.py` with business logic.

Prefer explicit code over clever abstractions.

Preserve existing API behaviour unless explicitly requested otherwise.

Keep tests passing at all times.

Do not introduce unnecessary dependencies.

Do not rewrite entire files when a narrow diff is sufficient.

Do not stage unrelated files, generated artifacts, screenshots, local shortcuts, `.codex/*` files, or temporary outputs unless explicitly requested.

---

## Agent Workflow Rules

Agents must prefer:

- minimal diffs
- incremental refactors
- vertical-slice changes
- narrow, auditable fixes
- inspect-first workflow
- plan-first workflow for risky or architecture-sensitive work
- full-file awareness before editing important files

Agents must avoid:

- rewriting entire files
- renaming APIs without approval
- changing request payload formats without approval
- introducing unnecessary dependencies
- mixing unrelated concerns in one task
- carrying dirty working-tree changes across branches
- stashing unrelated changes unless explicitly approved
- continuing after protected files unexpectedly change

If the root cause is not yet confirmed, inspect before changing code.

If an env-only or ops-only fix is sufficient, do not invent a code PR.

If something is risky or ambiguous, preserve it and report it rather than forcing cleanup or behaviour change.

If the working tree is dirty with unrelated changes, stop and report before switching branches or editing.

---

## Final Operating Loop

Target loop:

Customer submits simple quote.

System captures useful structured facts.

Admin sees clear risk, missing info, and follow-up needs.

Austin/Dan approve, follow up, or book.

Job gets completed.

Actual costs are entered.

System shows profit and underpricing patterns.

Pricing is improved carefully by category in later dedicated PRs.

The goal is not a flashy quote calculator.

The goal is a small business operating system that protects margin, reduces missed follow-ups, and makes daily decisions easier.
