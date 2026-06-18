---
name: bay-delivery-pr-safety-review
description: Use for Bay Delivery Quote Copilot repo planning, PR review, implementation prompts, CI debugging, post-merge verification, dependency lock refreshes, GPT grounding docs, protected-surface checks, Render/live-smoke decisions, and production-safety workflow. This skill protects pricing authority, customer/admin boundaries, production data, and Austin's preferred P1/P2/P3 review style.
---

<!-- cspell:words Uvicorn Supabase -->

# Bay Delivery PR Safety Review Skill

Use this skill when working in the Bay Delivery Quote Copilot repository.

Bay Delivery Quote Copilot is production business infrastructure for Bay Delivery in North Bay, Ontario. It is a real quoting and operations backend, not a sandbox.

## When to Use

Use this skill for:
- Bay Delivery implementation prompts.
- PR review and review-comment follow-up.
- Docs/template/skill updates that change repo workflow expectations.
- Pricing-adjacent analysis or guardrail design.
- Protected-surface validation and final report prep.
- Release/smoke/verification tasks where evidence quality matters.

## Do Not Use For

Do not use this skill as permission to:
- broaden a narrow task into a refactor
- change pricing, auth, storage, workflows, or Render config without explicit scope
- auto-commit or auto-push because a review tool or Fix button suggested a patch
- mutate production data
- invent a second process system outside the existing Bay Delivery repo structure

## Project Identity

Technology stack:
- Python 3.11
- FastAPI
- Uvicorn
- SQLite
- Static HTML/CSS/JS
- Render
- GitHub Actions
- Playwright smoke tests

Do not introduce React, Supabase, Stripe, frontend SPA frameworks, hosted backend replacements, or architecture changes that replace FastAPI + SQLite + static HTML/CSS/JS + Render unless Austin explicitly asks and approves.

If the task input is invalid, contradictory, or missing a required approval/scope detail, stop, describe the issue clearly, and ask for clarification before editing files or running risky commands.

Primary goals:
- Prevent undercharging.
- Protect margins.
- Keep customer quote flow reliable.
- Keep admin operations simple and useful.
- Keep production behavior understandable and auditable.

## Non-Negotiable Business Rules

Protect these unless Austin explicitly starts a pricing-change task:

- One pricing engine only: app/quote_engine.py.
- Do not create a second pricing system.
- GPT/internal assistants may advise but must not override pricing authority.
- Cash: no HST, rounded to nearest $5.
- EMT/e-transfer: add 13% HST and round to cents.
- Travel minimum: $20 gas + $20 wear = $40 minimum.
- Service minimums:
  - Dump run: $50
  - Small move: $60
  - Demolition: $75
  - Other: $50
- Labour internal anchors:
  - Primary: $20/hr
  - Helper: $16/hr
- Mattress disposal:
  - $60 per mattress
  - $60 per box spring
- Scrap pickup:
  - Curbside: free
  - Inside removal: $30
- Currency is CAD.

Any task touching pricing, quote totals, quote risk, customer quote payloads, or app/quote_engine.py is high-risk.

## Current Baseline Notes

Recent completed work includes:
- PR #309 create version 0.12.0 bump.
- PR #310 create launch readiness current state docs refresh.
- PR #311 create booking notification status visibility.
- PR #312 create quote page step heading clarity polish.
- PR #315 create quote first-view simplification polish.
- PR #316 create admin post origin fail closed hardening.
- PR #318 create demolition pricing readiness plan.

Current verified baseline:
- Main is verified through PR #318 and current main commit `ef569102df5f12a4f92acbc8054cf645aeffe2e5`.
- Latest verified main context: PR #318 `create demolition pricing readiness plan`.
- Current version: `0.12.0`.
- GPT grounding parity passed previously.
- Full pytest passed previously: 719 passed.
- Render parity verified at version `0.12.0` with commit `ef569102df5f`.

Booking notification infrastructure exists but remains disabled until Austin authorizes customer launch.

Do not configure these Render/env vars unless Austin explicitly authorizes customer launch:
- BOOKING_REQUEST_NOTIFICATIONS_ENABLED
- BOOKING_NOTIFICATION_EMAIL_TO
- BOOKING_NOTIFICATION_EMAIL_FROM
- BOOKING_NOTIFICATION_SMTP_HOST
- BOOKING_NOTIFICATION_SMTP_PORT
- BOOKING_NOTIFICATION_SMTP_USERNAME
- BOOKING_NOTIFICATION_SMTP_PASSWORD
- BOOKING_NOTIFICATION_SMTP_STARTTLS
- BOOKING_NOTIFICATION_EMAIL_REPLY_TO
- APP_BASE_URL

Do not run live tests that create quotes, booking requests, emails, calendar events, or production data unless Austin explicitly authorizes that exact operation.

## Austin's Preferred Output Style

Always lead with the answer or recommendation first.

For PR reviews:
1. Give merge/no-merge first.
2. Then use P1/P2/P3 review format.
3. End with the exact next action.

For Codex prompts:
- Always state recommended reasoning level.
- Always say whether to use plan-only or skip plan-only.
- Do not include a separate ROLE line.
- Use clean headings:
  - MODE
  - TASK
  - CURRENT BASELINE
  - SCOPE
  - DO NOT CHANGE
  - FILES ALLOWED
  - VALIDATION
  - PROTECTED DIFF
  - FINAL REPORT
  - STOP CONDITION
- Use one clean copy-paste block.
- Avoid nested markdown fences.
- Avoid weird generated IDs.
- Keep prompts practical and tightly scoped.

For VS Code Agent prompts:
- Do not include a reasoning level.
- Use one clean copy-paste block.
- Include scope, allowed files, forbidden files, validation, protected diff, final report, and stop condition.

For implementation guidance:
- Prefer narrow PRs.
- When directly providing code, prefer one clean copy-paste block instead of fragmented snippets.
- Avoid broad refactors.
- Avoid unrelated cleanup.
- Do not mix docs, runtime, dependency, schema, workflow, and pricing changes in one PR unless explicitly approved.

For implementation final reports:
- Always include files changed.
- Always include validation results.
- Always include protected no-go diff result.
- Always include pre-commit reviewer simulation results.
- Include pricing red-team review results when applicable.
- Always include P1/P2/P3 self-review.
- Always include commit hash and PR link.
- Always confirm whether the PR was left unmerged.

## Plan-Only Decision Rules

Use plan-only first when the task changes a high-risk surface:
- Pricing changes.
- Schema/storage migrations.
- Customer-facing flow changes.
- Admin mutation workflows.
- GPT grounding strategy changes.
- Architecture/refactors.
- New data fields.
- Anything touching app/quote_engine.py.
- Workflows, Render config, or dependency strategy.
- Broad multi-file changes.
- Anything with production data mutation risk.

Skip separate plan-only when the task is already narrow and low-risk:
- Narrow review-comment fixes.
- Docs-only refreshes with clear scope.
- Generated GPT grounding pack parity fixes.
- Test-only fixes.
- Static copy/CSS polish.
- Direct CI failure fixes when root cause is known.
- Post-merge verification.
- Read-only audits.

Tie-breaker:
- If the task touches both high-risk and low-risk areas, use plan-only.
- If the risk is unclear, use plan-only.
- Even when skipping plan-only, briefly state the plan before implementation.

## High-Value Review Habits to Practice

Use these habits especially when reviewing or fixing Bay Delivery PRs.

### 1. Review-Fix Regression Isolation

When a review comment identifies a bug, first create or identify one targeted failing test that proves the bug.

Then patch only the owning helper, query, or small behavior path.

Avoid broad refactors.

Examples:
- A desktop-admin ReferenceError should be covered by the smallest static or JavaScript regression check possible.
- A backend photo-request gating bug should be covered by targeted tests around missing_info, attachment_count, and quote-linked photo signals.
- A read-model ordering bug should be fixed in the query or order key, not by rewriting the whole read model.

### 2. Protected-Surface Validation Discipline

Before every narrow PR, explicitly identify protected surfaces.

Then prove the PR did not touch unrelated protected areas.

Always finish with:
- focused tests
- full pytest when appropriate
- protected no-go diff
- clear final report

Protected surfaces usually include:
- pricing authority
- quote totals
- customer quote payloads
- GPT grounding docs/generated pack
- workflows
- Render config
- dependencies
- mobile admin
- production cleanup tooling

### 3. Release-Verification Contract Design

For release and production verification tasks, express expectations as contracts, not vibes.

Prefer:
- explicit CLI flags
- one health fetch path
- commit/version parity checks
- structured workflow-run reporting
- exact url/status/conclusion/createdAt/headSha output

Do not rely on ad hoc manual release checks when a repeatable script or workflow contract is possible.

### 4. Docs and GPT Publication Unit

When source docs feed generated artifacts, treat `docs/gpt/*`, `dist/gpt_grounding_pack/*`, manifest parity, and any repo skill/template files that carry the same business rules or current-state guidance as one publish unit.

If docs/gpt changes:
- regenerate dist/gpt_grounding_pack
- update manifest hashes
- run GPT grounding parity
- stage ignored generated files intentionally if required
- verify source docs, exported files, manifest, and any paired skill/template guidance all match

Do not merge docs/GPT changes with stale generated output.

### 5. Contract-Safe Static UX Polish

For static UI polish, prefer CSS/layout fixes before changing JS behavior or payload contracts.

When improving visible UX:
- preserve field IDs
- preserve enum values
- preserve payload construction
- preserve endpoint behavior
- avoid public leakage of internal pricing, risk, or admin language

Use tests to prove the public quote contract stayed intact.

### 6. Pricing Phrase Adversarial Matrix Design

When a PR changes pricing wording, safeguard phrases, owner-review phrases, or other quote/pricing text interpretation, require a phrase-level adversarial matrix before commit.

The matrix is not optional for wording-only pricing work just because totals are unchanged.

It must show:
- target positives that should still trigger protection
- near-miss negatives that must stay below the safeguard
- mixed context cases where true demolition/pricing targets appear alongside access, cleanup, debris, or route wording
- word-order and descriptor variations
- punctuation and separator variations
- plural/singular and verb-form variations
- preserved legacy positives from existing accepted behavior

Recent examples that should have been in the matrix up front:
- `old shed removal`
- `large deck demolition with fence access`
- `roof tear-off`
- `shed demolition and yard cleanup`
- `full carport teardown`

### 7. Quote-Engine Oracle Parity for Owner-Review Read Models

When `app/storage.py`, admin owner-review SQL, or any read-model logic tries to mirror `quote_engine` owner-review outcomes, use `quote_engine` as the oracle and prove parity with focused tests.

Required discipline:
- create or identify one failing parity test before the read-model patch
- derive expected owner-review outcomes from `quote_engine`, not from duplicated handwritten assumptions
- keep storage/read-model logic non-authoritative and local to the admin/reporting surface
- add adversarial parity coverage for separators, plural/singular wording, negative-context guards, and text-only requests

Do not claim parity because the phrases "look similar". Prove it with an oracle-backed corpus.

### 8. Security Boundary Trigger Discipline

Treat boundary-hardening PRs as security-scan work even when they look small or docs-adjacent.

Auto-trigger `codex-security:security-diff-scan` when a PR touches:
- docs or API exposure rules
- pre-auth admin boundaries
- CSP, origin, CORS, or header behavior
- dependency pins or security-audit remediations

The review must explicitly confirm the customer path did not widen and that the protected diff stayed inside the intended boundary surface.

### 9. Narrow Dependency-Audit and Lock Hygiene

Dependency audit or lock refresh work is its own narrow workflow, not an excuse to mix in runtime cleanup.

For dependency-only PRs:
- keep the diff limited to dependency files unless Austin explicitly expands scope
- show why each pin changed
- run lockfile freshness and security verification
- prove no runtime, pricing, storage, schema, Render, workflow, or GPT drift came along for the ride

If a dependency fix appears to require unrelated runtime edits, stop and report instead of broadening the PR.

## Active Defaults and Trigger-Only Overlays

Keep the Bay Delivery workflow opinionated but not bloated.

Active defaults for normal Bay Delivery repo PR work:
- superpowers:receiving-code-review
  - classify review comments comment-by-comment as P1, P2, or P3
  - for every accepted review comment that changes behavior, add at least one targeted regression test
  - add a short gap-closed note before push
- bay-delivery-pr-safety-review
  - treat this as the main Bay-specific safety gate
  - pricing-sensitive work must include the pricing red-team pass
  - docs/GPT work must include the docs/GPT publication pass as one publish unit
- verification-before-completion
  - require a clean working tree before completion
  - require targeted tests plus relevant full-suite or grouped validation
  - require protected no-go diff evidence
  - require a final what changed and what did not change report

Trigger-only overlays:
- superpowers:test-driven-development only for pricing, public quote, GPT/admin-boundary, storage/read-model, and customer-facing behavior changes
  - create or identify the failing or covering contract test first, then patch only the owning surface
- superpowers:test-driven-development is mandatory for pricing phrase or safeguard wording changes
  - build the pricing phrase adversarial matrix before commit, not after review comments arrive
- superpowers:test-driven-development is mandatory for admin/storage/read-model owner-review matching changes
  - use `quote_engine` as the oracle and keep the read-model parity corpus in focused tests
- Browser/Playwright verification only for static, UI, or public-page changes
  - verify `/`, `/quote`, `/admin`, and `/admin/mobile` at desktop and mobile widths
  - fail the overlay on overflow, weak CTA visibility, internal-language leakage, broken responsive layout, or oversized assets
  - do not assume Vercel deployment behavior; Bay Delivery deploys on Render
- codex-security:security-diff-scan only for admin, auth, CSP, public-exposure, docs exposure, headers, origin/CORS/CSP, dependency security fixes, or customer-path boundary changes
  - check pre-auth admin surfaces, docs exposure, CSP/origin behavior, dependency-pin scope, and no customer-path drift

Other specialized workflows like CI triage or systematic debugging still apply when the task is specifically a CI or environment failure, but they are not part of the default Bay Delivery repo-safety stack.

Do not load every overlay for every task. Apply only the overlays the task actually triggers.

## Protected Surfaces

Before implementation, identify protected surfaces.

Common protected files and areas:
- app/quote_engine.py
- app/services/quote_service.py
- app/main.py when public endpoints are affected
- app/storage.py when schema/storage is affected
- static/quote.html
- static/quote.js
- static/quote.css
- static/admin_mobile.html
- static/admin_mobile.js
- render.yaml
- .github/workflows/*
- requirements.txt
- requirements.lock.txt
- VERSION
- docs/gpt/*
- dist/gpt_grounding_pack/*
- cleanup tooling and production scripts

Do not touch protected areas unless they are explicitly in scope.

For pricing-sensitive work, protected surfaces also include:
- customer totals
- cash/EMT/HST behavior
- advisory/risk metadata that can influence operator pricing judgment
- business-rule wording that could widen or weaken a pricing safeguard

## Required Evidence

Every implementation task should leave a short evidence trail.

Required evidence:
- exact files changed
- validation commands run and results
- protected no-go diff result
- pre-commit reviewer simulation result
- P1/P2/P3 self-review
- commit hash
- PR link if opened

Required when applicable:
- pricing red-team review result for pricing/quote-engine/customer-total/business-rule tasks
- pricing phrase adversarial matrix evidence for pricing or safeguard wording tasks
- quote-engine oracle parity evidence for admin/storage/read-model owner-review matching tasks
- focused test additions or updates for review-fix regressions
- Render/live verification evidence for deployment-impacting checks

Bay examples from recent review patterns:
- PR review follow-ups can pass tests and still miss review-level issues before commit.
- Public quote/page polish needs explicit proof that IDs, selectors, payload shape, and wording boundaries stayed stable.
- Pricing safeguard work needs adversarial checks against near-miss wording, not just happy-path tests.
- Owner-review read models can drift from `quote_engine` unless parity is proven with an oracle-backed corpus.
- Security-boundary hardening and dependency-audit fixes need explicit boundary-scope review even when the code diff is small.
- Docs/template/process changes should tighten evidence quality without creating a second workflow system.

## Required Validation

For most repo PRs, run:
- git diff --check
- .\.venv\Scripts\python.exe tools\check_version_parity.py
- .\.venv\Scripts\python.exe tools\check_gpt_grounding_pack_parity.py
- .\.venv\Scripts\python.exe -m compileall app tools scripts tests

Run focused tests relevant to the change.

For most implementation PRs, also run:
- .\.venv\Scripts\python.exe -m pytest -q

For static/customer/admin UI changes, include:
- .\.venv\Scripts\python.exe -m pytest -q tests/test_static_assets.py
- .\.venv\Scripts\python.exe -m pytest -q tests/test_launch_smoke_playwright.py

For booking/quote lifecycle changes, consider:
- tests/test_quote_request_transitions.py
- tests/test_booking_notifications.py
- tests/test_admin_ops_queue.py
- tests/test_manual_completed_jobs.py
- tests/test_admin_job_costing.py

For dependency changes, include:
- lockfile freshness logic
- full tests
- pip-audit -r requirements.lock.txt

## Dependency Lock Refresh Rule

If changing requirements.txt or requirements.lock.txt, prefer Linux/Docker/WSL for lock generation.

Avoid native Windows pip-compile when possible because Windows can add platform-specific entries such as colorama that GitHub Ubuntu CI may not keep.

If Windows lock generation is unavoidable, verify the resolved pins, protected diff, pip-audit result, and CI lockfile behavior before committing.

Preferred Docker command from repo root:
docker run --rm -v "${PWD}:/repo" -w /repo python:3.11 bash -lc "python -m pip install --upgrade 'pip<25.3' && python -m pip install pip-tools==7.4.1 && pip-compile --resolver=backtracking --output-file requirements.lock.txt requirements.txt"

After lock refresh, confirm expected dependency pins and run pip-audit.

Dependency-only workflow requirements:
- keep the PR dependency-only unless Austin explicitly widens scope
- explain whether the change came from security audit remediation, freshness, or compatibility
- run the dependency-only protected diff and confirm no runtime/pricing/storage/schema/Render/workflow/GPT drift
- if a dependency issue truly requires runtime code changes, stop first and ask for widened scope

Expected pip-audit result:
- No known vulnerabilities found.

## GPT Grounding Docs Rule

If editing docs/gpt/*, regenerate dist/gpt_grounding_pack.

Always keep source docs and generated pack in parity.

If the docs change also updates business rules, current-state guidance, or repo workflow expectations, review any paired skill/template guidance in the same pass so the source docs, generated pack, manifest, and repo guidance do not drift.

Run:
- .\.venv\Scripts\python.exe tools\check_gpt_grounding_pack_parity.py

If parity fails on Windows but seems correct locally, check LF/CRLF normalization and committed blob hashes before guessing.

Docs/GPT PRs should not change runtime, pricing, Render, workflows, dependencies, or version markers unless explicitly scoped.

## Production and Render Rules

Production live-safe smoke is required after runtime/customer/admin/deployment-impacting merges.

Production live-safe smoke is usually not required for:
- docs-only PRs
- GPT grounding pack only PRs
- comments/README-only changes
- local-only scripts unless they affect production workflows

Never mutate production data unless Austin explicitly approves in the active task thread, a GitHub PR/review comment, or another written repo-visible instruction.

For production cleanup:
- require backup first
- use approved allowlisted cleanup tooling
- never do ad hoc database deletion
- never run --apply unless Austin explicitly approves after dry-run review

## PR Review Format

Always review with this structure:

1. Merge call:
   - Merge
   - Do not merge
   - Merge after checks
   - Needs fix

2. P1 blockers:
   - correctness
   - data loss
   - security
   - pricing authority breakage
   - production breakage

3. P2 issues:
   - important bugs
   - stale docs that change operator behavior
   - missing tests
   - CI failures

4. P3 polish:
   - wording
   - PR body cleanup
   - non-blocking maintainability

For self-review before commit:
- P1 means merge-blocking correctness, security, pricing, auth, deploy, or customer-impact risk.
- P2 means important workflow, validation, consistency, or UX issues that should be fixed before merge.
- P3 means non-blocking polish, clarity, or follow-up notes.

5. Required next action:
   - exact command or prompt
   - whether to use Codex, VS Code Agent, or manual terminal
   - whether plan-only is needed

## Protected Diff Patterns

Use protected diff checks that match the task scope.

For skill/template/process-only PRs:
git diff main...HEAD -- app static tests scripts tools docs/gpt dist/gpt_grounding_pack render.yaml .github/workflows requirements.txt requirements.lock.txt VERSION DEPLOYMENT_NOTES.md

Expected:
- no output

For docs/GPT-only PRs:
git diff main...HEAD -- app static tests scripts tools render.yaml .github/workflows requirements.txt requirements.lock.txt VERSION DEPLOYMENT_NOTES.md

Expected:
- no output

For dependency-only PRs:
git diff main...HEAD -- app static tests scripts tools docs/gpt dist/gpt_grounding_pack docs/roadmaps render.yaml .github/workflows VERSION DEPLOYMENT_NOTES.md

Expected:
- no output

For static UI-only PRs:
git diff main...HEAD -- app scripts tools render.yaml .github/workflows docs/gpt dist/gpt_grounding_pack requirements.txt requirements.lock.txt VERSION

Expected:
- no output

For post-merge checks:
git diff HEAD~1..HEAD -- <protected paths>

Expected result depends on the PR scope.

## Pre-Commit Reviewer Simulation

Before committing or pushing, review the actual diff as if you are the GitHub reviewer trying to block the PR.

Must check:
- false positives
- false negatives
- customer wording variants
- access/location confusion
- substring traps
- plural/singular variants
- verb variants
- tier ordering
- cash/EMT/HST preservation
- customer/internal boundary
- forbidden file changes
- protected no-go diff
- task expansion beyond prompt scope

If any issue is found:
- fix before committing
- add or update focused tests if applicable
- rerun validation
- rerun protected no-go diff

For docs/template/skill-only tasks, explicitly confirm:
- only allowed docs/template/skill files changed
- no runtime code changed
- no test files changed
- no static UI changed
- no workflow/config/dependency/version/data changes
- guidance does not contradict pricing authority rules
- no duplicated giant checklist where a skill reference is cleaner

## Pricing Red-Team Review Before Commit

This review is required when touching:
- app/quote_engine.py
- quote logic
- customer totals
- cash/EMT/HST
- advisory metadata
- demolition safeguards
- business-rule pricing

Must check:
- intended high-risk jobs that should trigger protection
- similar normal jobs that must not trigger
- false positives caused by near-miss demolition wording
- access/location wording that must not become target
- debris wording that must not become target
- cleanup wording that must not become target
- plural/singular variants
- verb variants
- substring traps
- old acceptance examples
- non-demolition baseline
- customer-facing response shape
- cash/EMT/HST totals
- safeguarded and non-safeguarded totals preserve cash/EMT/HST behavior

For pricing-sensitive reviews that change pricing wording, safeguard phrases, or quote/pricing text interpretation, also require a pricing phrase adversarial matrix before commit.

The matrix must cover:
- target-only positive
- access-only false positive
- target plus access combined
- cleanup/debris/removal near miss
- simple structure removal
- word-order swaps
- punctuation/separator variants
- existing vocabulary preservation
- substring traps
- customer/internal boundary
- payment math

For every new pricing safeguard or phrase-matching rule, include at least:
- one clean positive
- one clean false positive
- one positive mixed with access/location wording
- one cleanup/debris near miss
- one common alternate customer wording
- one punctuation or separator variant when phrase matching is involved
- one substring trap
- one existing-vocabulary preservation check when the rule touches known target vocabularies

Do not commit until this matrix is checked.

Fix valid P1/P2 findings before commit.

If the required fix would need forbidden files or broad matching, stop and report instead of expanding scope.

Near-miss examples to review explicitly:
- deck access is not deck demolition
- fence access is not fence demolition
- wall-to-wall carpet is not wall demolition
- drywall is not wall
- waterproofing/proofing is not roofing
- wall panel is not electrical panel
- utility room is not utility-line risk
- yard cleanup alone is not heavy mixed debris

If a pricing-sensitive task cannot show this review clearly, stop before commit.

## Codex Fix Button Guardrails

When using Codex review comments or the Fix button:
- review context loading is allowed
- it is not permission to auto-commit or auto-push
- pre-commit reviewer simulation is still required
- pricing-sensitive fixes still require pricing red-team review
- scope must not broaden just because review comments mention deferred follow-up areas

## Final Report Requirements

Every implementation or review-fix final report should include:

1. Brief plan summary
2. Whether implementation proceeded
3. Branch name
4. Commit hash
5. PR link if opened
6. Files changed
7. Exact behavior/docs/tests changed
8. Validation results
9. Protected diff result
10. Pre-commit reviewer simulation results
11. Pricing red-team review results when applicable
12. P1/P2/P3 self-review
13. Any skipped validation
14. Risks/limitations
15. Clear next step

## Stop Conditions

Stop and report instead of guessing if:
- tests fail and root cause is unclear
- protected diff shows unexpected changes
- production data mutation would be required
- Render/env var changes would be required
- pricing behavior would change unexpectedly
- lockfile output differs between Windows and Linux
- GPT grounding parity fails after regeneration
- GitHub checks are red
- there are unresolved P1/P2 review threads
- pre-commit reviewer simulation finds an unresolved blocker
- a pricing-sensitive task cannot show pricing red-team review evidence
- the prompt/template/skill update would duplicate a giant checklist instead of referencing the authoritative skill

If Austin approval is required and unavailable, stop and wait for Austin's written approval instead of assuming approval or using a substitute approver.

Do not merge automatically unless Austin explicitly asks.
