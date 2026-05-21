---
name: bay-delivery-pr-safety-review
description: Use for Bay Delivery Quote Copilot repo planning, PR review, implementation prompts, CI debugging, post-merge verification, dependency lock refreshes, GPT grounding docs, protected-surface checks, Render/live-smoke decisions, and production-safety workflow. This skill protects pricing authority, customer/admin boundaries, production data, and Austin's preferred P1/P2/P3 review style.
---

<!-- cspell:words Uvicorn Supabase -->

# Bay Delivery PR Safety Review Skill

Use this skill when working in the Bay Delivery Quote Copilot repository.

Bay Delivery Quote Copilot is production business infrastructure for Bay Delivery in North Bay, Ontario. It is a real quoting and operations backend, not a sandbox.

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
  - $50 per mattress
  - $50 per box spring
- Scrap pickup:
  - Curbside: free
  - Inside removal: $30
- Currency is CAD.

Any task touching pricing, quote totals, quote risk, customer quote payloads, or app/quote_engine.py is high-risk.

## Current Baseline Notes

Recent completed work includes:
- PR #298 Launch UI Mobile Polish.
- PR #299 Booking Request Notification Alerts.
- PR #301 idna security lock refresh.
- PR #300 GPT current-state refresh for booking alerts.

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

### 4. Docs and Generated-Artifact Publication Hygiene

When source docs feed generated artifacts, treat them as one publish unit.

If docs/gpt changes:
- regenerate dist/gpt_grounding_pack
- update manifest hashes
- run GPT grounding parity
- stage ignored generated files intentionally if required
- verify source and exported files match

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

Expected pip-audit result:
- No known vulnerabilities found.

## GPT Grounding Docs Rule

If editing docs/gpt/*, regenerate dist/gpt_grounding_pack.

Always keep source docs and generated pack in parity.

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

5. Required next action:
   - exact command or prompt
   - whether to use Codex, VS Code Agent, or manual terminal
   - whether plan-only is needed

## Protected Diff Patterns

Use protected diff checks that match the task scope.

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
10. Any skipped validation
11. Risks/limitations
12. Clear next step

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

If Austin approval is required and unavailable, stop and wait for Austin's written approval instead of assuming approval or using a substitute approver.

Do not merge automatically unless Austin explicitly asks.
