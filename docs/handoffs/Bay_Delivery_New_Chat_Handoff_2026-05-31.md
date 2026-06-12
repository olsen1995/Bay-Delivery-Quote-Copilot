# Bay Delivery Quote Copilot — New Chat Handoff

Prepared: 2026-05-31  
Purpose: Start a fresh ChatGPT chat without losing the important context from this long Bay Delivery Quote Copilot workflow.

## 1. Handoff Purpose

Continue helping Austin with Bay Delivery Quote Copilot safely, practically, and in the same working style.

The project is production infrastructure for Bay Delivery in North Bay, Ontario. It is not LifeOS, not Canon, not a governance experiment, and not a sandbox. It supports real customer quote/admin operations.

The next chat should act like a Bay Delivery repo/project co-pilot:
- review PRs deeply before merge
- create best-possible Codex/VS Code Agent prompts
- protect pricing and production data
- keep work narrow and auditable
- give clear P1/P2/P3 reviews
- recommend the best next task in order

## 2. Austin’s Working Preferences

Default answer style:
1. Recommendation first.
2. Then why.
3. Then step-by-step instructions.
4. Then exact copy-paste commands/prompts when useful.

Tone:
- laid-back but intelligent
- direct and honest
- practical owner/operator thinking
- supportive but not sugar-coated
- push back if risky, wasteful, too broad, or overengineered
- no shallow guesses
- clearly say what still needs verification

Prompt preference:
- Give the best final prompt immediately.
- Do not give a “pretty good” prompt then list add-ons.
- Bake all current lessons into the prompt.
- Use one clean copy-paste block.
- Avoid nested markdown fences inside prompts.
- Avoid weird generated IDs.
- Include exact scope, allowed files, strict do-not-change, validation, protected no-go diff, PR title, commit headline/description, final report, stop conditions.

PR review preference:
Start with:
- Merge
- Do not merge yet
- Needs re-review
- Fix-forward acceptable

Then:
- GitHub mergeable: yes/no/unknown
- Bay Delivery merge-ready: yes/no/unknown
- P1 blockers
- P2 blockers
- P3 notes
- validation assessment
- scope/protected-surface assessment
- review comments/thread status
- final next step

Important correction learned in this chat:
- Green CI and GitHub “mergeable” are not enough.
- For all Bay Delivery PRs, review the actual diff, PR comments/threads, scope, protected files, validation, and source-of-truth traceability before saying merge.
- For docs/current-state PRs, also verify dates, PR numbers, PR titles, full SHAs, generated grounding parity, and whether the PR body conflicts with the committed docs.

## 3. Tool / Agent Preferences

Use ChatGPT for:
- strategy
- next-step decisions
- PR review
- merge/no-merge judgment
- P1/P2/P3 blocker review
- prompt creation
- business/pricing reasoning
- launch/readiness decisions

Use Codex for:
- backend/runtime changes
- schema/storage/import/export work
- auth/security changes
- GPT endpoints
- GPT Action schema changes
- pricing-adjacent logic
- admin UI behavior that affects workflow
- test-heavy PRs
- CI/Render-sensitive changes
- dependency/security fixes
- architecture-sensitive audits
- PR reviews where correctness is uncertain

Use VS Code Agent for:
- docs-only PRs
- roadmap/current-state syncs
- version bump PRs
- simple static copy checks
- read-only post-merge verification
- branch/status verification
- local validation commands
- live visual/browser checks when Browser/Chrome is available

Codex defaults:
- New Codex task/chat: YES
- Repo: C:\Repos\Bay-Delivery-Quote-Copilot
- Branch from latest main: YES for implementation, NO for read-only audits
- Goal mode / Pursue goal: OFF unless explicitly requested
- Plan Mode: ON for risky/broad/unclear work, OFF for approved narrow implementation
- Reasoning: Medium for narrow docs/static; High for audits/security/workflow/Render/pricing-adjacent/customer-facing static work
- Auto-review: ON
- Include IDE context: ON
- Network: OFF unless explicitly needed

Goal Mode rule:
- OFF by default.
- ON only for exploratory unknowns like CI failure diagnosis, unknown bugs, root-cause discovery, broad audits.

Plan Mode rule:
- Plan Mode ON means plan-only.
- Do not say “Plan Mode ON briefly, then implement.”
- If implementation is allowed, use Plan Mode OFF and say “State a brief plan first, then implement only if scope stays narrow.”

## 4. Project Context

Repo:
- C:\Repos\Bay-Delivery-Quote-Copilot
- GitHub: olsen1995/Bay-Delivery-Quote-Copilot

Live app:
- Homepage: https://bay-delivery-quote-copilot.onrender.com/
- Quote page: https://bay-delivery-quote-copilot.onrender.com/quote
- Admin desktop: https://bay-delivery-quote-copilot.onrender.com/admin
- Admin mobile: https://bay-delivery-quote-copilot.onrender.com/admin/mobile
- Health: https://bay-delivery-quote-copilot.onrender.com/health

Core files:
- app/quote_engine.py = only authoritative pricing engine
- app/main.py = FastAPI routes/app construction
- app/storage.py = SQLite persistence
- static/index.html + static/site.css = homepage
- static/quote.* = public quote flow
- static/admin.* = desktop admin
- static/admin_mobile.* = mobile admin
- docs/gpt/* and dist/gpt_grounding_pack/* = GPT grounding/source/export surfaces
- docs/roadmaps/* = roadmap/planning docs

## 5. Hard Rules / Invariants

Preserve unless explicitly scoped:
- One pricing engine only: app/quote_engine.py.
- Do not create duplicate pricing logic.
- Do not change pricing unless explicitly scoped.
- Do not casually touch app/quote_engine.py.
- Backend is source of truth.
- SQLite is source of truth.
- Google Calendar is mirror/convenience only.
- Admin is operations-only.
- GPT/internal assistant is internal-only and recommendation-first.
- Customers use public quote flow, not internal GPT paths.
- Do not leak internal risk, margin, owner-review, pricing caution, recommended trailer, operating-cost gap, or admin-only data to public/customer pages.
- Do not add customer-facing GPT behavior.
- Do not add GPT price override.
- Do not auto-schedule or auto-approve via GPT.
- Cash has no HST.
- EMT/e-transfer adds 13% HST.
- Do not mutate production data unless explicitly requested.
- Do not submit live quote forms, create bookings, send notifications, run cleanup tools, or alter admin data on live Render unless explicitly requested.
- Do not merge automatically.
- Stop after opening/updating a PR unless Austin explicitly asks to merge.

## 6. Current Verified State

CURRENT VERIFIED STATE:
- Current main is verified through PR #326.
- Latest verified main commit: d2b0d1f create admin csp style compliance hardening (#326).
- Live Render /health is healthy and serving commit d2b0d1f30697.
- Current version: 0.12.0.
- Version parity passed.
- GPT grounding parity passed: 9 files match manifest and sources.
- tests/test_static_assets.py passed: 41 passed.
- tests/test_launch_smoke_playwright.py passed: 4 passed.
- tests/test_admin_quote_risk_visibility.py passed: 16 passed.
- tests/test_admin_ops_queue.py passed: 15 passed.
- tests/test_admin_job_costing.py passed: 27 passed.
- tests/test_smoke_script_contract.py passed: 18 passed.
- Full pytest passed: 728 passed.
- Protected no-go diff for PR #326 passed with no output.
- Live /admin clean-session CSP verification passed.
- Live /admin pre-auth gating passed in clean desktop session.
- No inline-style CSP violation observed.
- No authenticated admin API data loaded before login.
- app/quote_engine.py remains the only pricing authority.

## 7. Completed Work In This Chat

### PR #322 — Homepage logo replacement
- Replaced homepage logo with optimized `static/images/bay-delivery-logo.png`.
- Final optimized size: 256x250, under 100 KB.
- Verified and merged earlier.
- Post-merge live health passed.

### PR #323 — Desktop admin collapsible section polish
- Converted desktop admin sections to collapsible `details/summary`.
- Recent Estimates, Booking Requests, and Jobs default open.
- Follow-Up Message Helper and Completed Job Profit Review default collapsed.
- Added focus helper behavior for shortcuts.
- Merged and verified.
- Live health after merge passed.

### Skills / workflow discussion
Useful Bay Delivery skills/checklists narrowed:
1. receiving-code-review
2. bay-delivery-pr-safety-review
3. verification-before-completion

Other skills should trigger only when relevant:
- superpowers:test-driven-development for pricing, public quote, GPT/admin-boundary, storage/read-model, and customer-facing behavior changes
- browser/Playwright verification for static/UI/public-page changes, with `/`, `/quote`, `/admin`, and `/admin/mobile` checked at desktop and mobile widths
- codex-security:security-diff-scan for admin, auth, CSP, public-exposure, docs exposure, headers, origin/CORS/CSP, and customer-path boundary changes
- small-PR evidence discipline is already default

### PR #324 — Current-state refresh for visual polish
- Initially got merge call too early.
- Codex later found P2 docs issues:
  - stale roadmap date wording
  - short SHA used where full SHA label was present
  - skipped PR #319/#320/#321 baseline entries
  - PR #323/cSpell commit provenance confusion
- Fixed with follow-up commits.
- Final state:
  - PR #323 correctly identified as `create desktop admin collapsible section polish`
  - `15b9d7b` correctly identified as follow-up cSpell commit
  - full SHA used where needed
  - roadmap date corrected to May 29
  - static-assets count corrected
- Merged and verified.
- Important rule learned: docs/current-state PRs need thorough traceability review.

### Full repo / Render / security / visual audit
- Ran a read-only full audit.
- No P1 findings.
- Main P2 findings:
  1. Production Live-Safe Smoke needed for current main.
  2. Production `/docs` and `/openapi.json` exposure.
  3. Admin CSP inline-style warning.
  4. Public `/quote` importing admin.css.
  5. Docs/current-state refresh after hardening changes eventually needed.
- Some things were not fully checked in initial audit:
  - authenticated admin post-auth screens
  - Render logs/metrics
  - full mutation paths
  - browser visual was partially limited until later checks

### Production Live-Safe Smoke after PR #324
- Run ID: 26671383404
- Workflow: production_live_safe_smoke.yml
- Result: success
- Head SHA: 1a3bda81802c18c74e48a93eab253e0f4322dd33
- Live /health remained ok true, version 0.12.0, commit 1a3bda81802c.

### PR #325 — Production API docs exposure hardening
- Disabled `/docs`, `/redoc`, and `/openapi.json` on Render production using existing Render env markers:
  - RENDER
  - RENDER_SERVICE_ID
  - RENDER_EXTERNAL_HOSTNAME
- Preserved local/test docs behavior.
- Tests added for all three markers and /health availability.
- Merged and verified.
- Live results:
  - /docs -> 404
  - /redoc -> 404
  - /openapi.json -> 404
  - /health ok true, commit 328b1094af16
- Full pytest: 728 passed.

### PR #326 — Admin CSP style compliance hardening
- Removed inline `style="display:none"` from desktop admin protected dashboard.
- Replaced `.style.display` usage with `hidden` and `aria-hidden`.
- Converted schedule modal visibility to hidden/ARIA with `.modal[hidden]`.
- app/main.py and CSP header were not changed.
- Mobile admin untouched.
- Merged and verified locally:
  - static tests: 41 passed
  - launch smoke: 4 passed
  - admin quote risk: 16 passed
  - admin ops queue: 15 passed
  - admin job costing: 27 passed
  - smoke script contract: 18 passed
  - full pytest: 728 passed
  - live /health commit d2b0d1f30697
- Live clean-session browser verification:
  - /admin loaded
  - pre-auth login UI visible
  - protected dashboard hidden
  - no "Admin data loaded successfully"
  - no authenticated admin API calls before login
  - no console errors/warnings
  - no inline-style CSP violation
- Final PR #326 status: fully cleared.

### Prompt template update
Austin requested the prompt template be updated with:
- best-final-prompt-first rule
- Goal Mode rule
- Plan Mode rule
- validation dirt safeguards
- live visual/security verification
- browser/cache clean session
- stronger PR review standard
- stronger final report expectations
- current verified baseline through PR #326

Recommended repo path:
- docs/templates/Bay_Delivery_Prompt_Template.md

### Homepage/mobile visual review
Austin shared mobile homepage screenshots. Observations:
- overall site looks much more professional and trustworthy
- truck image, logo, CTA buttons, service cards look legit
- top mobile button layout feels crowded
- section headings sometimes feel jammed under browser/status UI while scrolling
- footer/CTA spacing could use light cleanup
- homepage is customer first impression, so visual polish is worth doing
- should not mix homepage polish into quote stylesheet cleanup

Austin also shared the desired full image and noted the homepage should use that full image, not the cut-off/cropped version.

## 8. Current Open / Next Tasks

### Next best task
Do this first:

`create homepage full hero mobile polish`

Purpose:
- Replace the cut-off homepage hero/supporting image with the full user-provided image.
- Improve mobile top button layout.
- Add better section heading spacing.
- Maybe lightly improve footer/CTA spacing.
- Keep homepage-only scope.
- Do not touch /quote, admin, backend, GPT, workflows, dependencies, or version.

Important:
- Save the full image before running Codex:
  - C:\Repos\Bay-Delivery-Quote-Copilot\working_assets\homepage-hero-full.jpg
  - or C:\Repos\Bay-Delivery-Quote-Copilot\working_assets\homepage-hero-full.png

Use Codex:
- Goal Mode OFF
- Plan Mode OFF
- Reasoning High
- Branch from latest main YES
- State brief plan first, then implement only if scope stays narrow

### After that
Second task:

`create quote stylesheet boundary cleanup`

Purpose:
- Remove `/static/admin.css` import from `static/quote.html`.
- Move only required public-safe generic styling into `static/quote.css`.
- Preserve quote layout, field IDs, option values, payload shape, quote.js behavior, mobile layout.
- Do not touch admin/backend/GPT/workflows/version.
- This task already has a reviewed plan.
- Use Codex Plan Mode OFF after homepage PR is done.
- Reasoning High because customer-facing.

### Later / deferred
1. Post-merge visual verification for homepage desktop/mobile after image/mobile polish PR.
2. Post-merge verification for quote stylesheet cleanup.
3. Read-only live quote page visual check.
4. Docs/current-state refresh after the visual/static hardening PRs are complete.
5. Dependency/security audit report if Austin wants higher confidence.
6. Completed-job/manual calibration entry habit.
7. Future demolition calibration cases only after enough real job data exists.
8. Demolition pricing safeguards only after evidence supports it.

## 9. Important Unimplemented / Discussed Items To Remember

### Homepage mobile polish
Still needs implementation:
- top mobile button layout
- section heading spacing
- maybe footer/CTA spacing
- full hero image replacement

### Quote stylesheet boundary cleanup
Still needs implementation:
- remove `admin.css` from quote page
- copy only needed public-safe base rules into quote.css
- static tests to prevent re-import
- Playwright/static/full tests
- post-merge live quote visual check

### Current-state/docs refresh
Do not do it immediately after every small docs/static PR unless necessary.
Better to bundle after the next visual hardening/static PRs.

### Completed-job calibration
Most important non-code habit:
- enter completed jobs/manual calibration entries after jobs
- demolition pricing changes must wait for real evidence
- future shed/tear-down pricing anchors should be captured with actual hours, crew, disposal, access, density, notes

Known calibration anchor from prior memory:
- old shed removal quoted/completed at $1,200 CAD, 2 workers, about 3 hours, profitable, supports demolition as premium work.
- 16x10 shed teardown discussion should likely be priced as premium demolition/haul-away, not basic dump run.

### Automations
Optional reminders discussed:
- weekly repo health reminder
- daily/evening completed-job calibration reminder after job days
- monthly dependency/security review reminder
No automation was created in this chat.

### Skills/checklists
Do not activate every possible skill.
Use only when triggered:
- docs/current-state traceability audit
- internal-only boundary review
- SQLite mutation-safety review
- protected-surface frontend contract review
- small-PR evidence discipline is default
Core three useful skills:
- receiving-code-review
- bay-delivery-pr-safety-review
- verification-before-completion

## 10. Validation / Commands / Checks

Standard verification:

```powershell
cd C:\Repos\Bay-Delivery-Quote-Copilot

git status --short --branch
git diff --check
.\.venv\Scripts\python.exe tools\check_version_parity.py
.\.venv\Scripts\python.exe tools\check_gpt_grounding_pack_parity.py
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m compileall app tools scripts tests
.\.venv\Scripts\python.exe -m pytest -q tests/test_static_assets.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_launch_smoke_playwright.py
.\.venv\Scripts\python.exe -m pytest -q
```

For quote page work also run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_quote_structured_intake_fields.py
```

For admin/security work also run focused admin/security tests as relevant:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_env_and_dependencies.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_abuse_controls.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_admin_quote_risk_visibility.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_admin_ops_queue.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_admin_job_costing.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_smoke_script_contract.py
```

Live health:

```powershell
Invoke-RestMethod https://bay-delivery-quote-copilot.onrender.com/health
```

Production Live-Safe Smoke:

```powershell
gh workflow run production_live_safe_smoke.yml --ref main
gh run list --workflow production_live_safe_smoke.yml --limit 5
gh run watch RUN_ID --exit-status
```

## 11. Risks / Watchouts

- Do not mix homepage image/mobile polish with quote stylesheet cleanup.
- Do not touch quote page in homepage PR.
- Do not touch homepage in quote stylesheet cleanup unless explicitly scoped.
- Do not change `app/main.py` after PR #325/#326 unless a new backend/security task requires it.
- Do not change CSP to add `unsafe-inline`.
- Do not call browser/admin pre-auth checks passed unless clean session was used.
- Do not trust “mergeable” alone. Always inspect comments/threads/diff.
- Do not call docs/current-state PRs safe without checking dates, PR titles, PR numbers, full SHAs, and generated pack parity.
- Do not run broad cleanup commands.
- Do not commit browser screenshots/artifacts.
- Do not use `git add .` casually.
- Do not submit live quote/admin forms during QA.
- Do not touch `app/quote_engine.py` without explicit pricing task and evidence.

## 12. Copy-Paste Prompt For Next Tool

Use this next with Codex after saving the full image to `working_assets`.

```text
CODEX SETTINGS:
New Codex task/chat: YES
Repo: C:\Repos\Bay-Delivery-Quote-Copilot
Branch from latest main: YES
Goal mode / Pursue goal: OFF
Plan Mode: OFF
Reasoning: High
Auto-review: ON
Include IDE context: ON
Network: OFF unless explicitly needed

PLUGINS:
Use:
- GitHub
- Superpowers

Do not use unless task clearly requires it:
- Browser
- Chrome
- Render
- Codex Security
- OpenAI Developers
- Google Calendar
- Gmail
- Canva
- Spreadsheets
- Documents
- Presentations
- Supabase
- HubSpot
- Build Web Apps
- Build Web Data Visualization

PLUGIN / MEMORY ACCESS:
If local skill/memory reads are needed and Windows sandbox blocks them, use read-only sandbox grants only:
/sandbox-add-read-dir C:\Users\austi\.codex\plugins
/sandbox-add-read-dir C:\Users\austi\.codex\memories

Do not add writable roots for those folders.
Do not use danger-full-access.
Do not read unrelated user folders.
Do not change .codex/config.toml.

MODE:
Narrow homepage static implementation PR.
State a brief plan first, then implement only if the plan stays inside scope.
Do not merge.
Do not deploy.
Do not mutate production data.

TASK:
Create a narrow homepage full hero image and mobile polish PR.

REPO:
C:\Repos\Bay-Delivery-Quote-Copilot

SOURCE IMAGE:
Use this exact locally provided full image as the replacement source if present:
C:\Repos\Bay-Delivery-Quote-Copilot\working_assets\homepage-hero-full.jpg

Fallback if needed:
C:\Repos\Bay-Delivery-Quote-Copilot\working_assets\homepage-hero-full.png

Stop if neither source file exists.

CURRENT VERIFIED BASELINE:
- Current main is verified through PR #326.
- Latest verified main commit: d2b0d1f create admin csp style compliance hardening (#326).
- Live Render /health is healthy and serving commit d2b0d1f30697.
- Current version: 0.12.0.
- Version parity passed.
- GPT grounding parity passed: 9 files match manifest and sources.
- tests/test_static_assets.py passed: 41 passed.
- tests/test_launch_smoke_playwright.py passed: 4 passed.
- tests/test_admin_quote_risk_visibility.py passed: 16 passed.
- tests/test_admin_ops_queue.py passed: 15 passed.
- tests/test_admin_job_costing.py passed: 27 passed.
- tests/test_smoke_script_contract.py passed: 18 passed.
- Full pytest passed: 728 passed.
- Protected no-go diff for PR #326 passed with no output.
- Live /admin clean-session CSP verification passed.
- Live /admin pre-auth gating passed in clean desktop session.
- No inline-style CSP violation observed.
- No authenticated admin API data loaded before login.
- app/quote_engine.py remains the only pricing authority.

USER VISUAL FINDINGS:
Austin reviewed the live mobile homepage and wants:
1. The homepage image should use the full provided hero image, not the cut-off/cropped version.
2. Mobile top button layout should be improved.
3. Section heading spacing should be improved so headings do not feel jammed under mobile browser/status UI while scrolling.
4. Footer/CTA spacing may be lightly improved if needed.

PRIMARY GOAL:
Replace the current cut-off/cropped homepage hero/supporting image with the full user-provided image and make a narrow mobile homepage polish pass.

SCOPE:
Homepage static visual correction only.

FILES ALLOWED:
- static/index.html
- static/site.css
- static/images/*
- tests/test_static_assets.py
- tests/test_launch_smoke_playwright.py only if a very narrow non-brittle homepage assertion update is clearly needed

PREFER TO CHANGE AS FEW FILES AS POSSIBLE.

STRICT DO NOT CHANGE:
- app/quote_engine.py
- app/main.py
- app/storage.py
- app/services/*
- app/gcalendar.py
- static/quote.html
- static/quote.js
- static/quote.css
- static/admin.html
- static/admin.js
- static/admin.css
- static/admin_mobile.html
- static/admin_mobile.js
- static/admin_mobile.css
- docs/gpt/*
- dist/gpt_grounding_pack/*
- render.yaml
- .github/workflows/*
- requirements.txt
- requirements.lock.txt
- VERSION
- canon_versions.txt
- .codex/config.toml
- pricing logic
- quote behavior
- admin behavior
- mobile admin behavior
- GPT behavior
- schema/storage
- dependencies
- workflows
- version files

IMPORTANT BOUNDARIES:
- This is not a homepage redesign.
- This is not a quote page change.
- This is not a branding rewrite.
- Do not change customer quote flow.
- Do not change pricing.
- Do not change backend/runtime.
- Do not change admin.
- Do not change GPT docs/grounding.
- Do not introduce new dependencies.
- Preserve current homepage copy and CTA behavior unless a tiny spacing/layout change is required.

IMPLEMENTATION REQUIREMENTS:
1. Inspect how the homepage currently uses the hero/supporting image asset.
2. Identify the current cropped/cut-off asset and where it is referenced.
3. Replace it with the provided full image.
4. Optimize the final shipped image to a reasonable web-friendly size without visibly damaging quality.
5. Preserve the homepage logo, CTA links, phone links, Facebook/Google links, and customer-facing copy.
6. Ensure desktop displays the full image intentionally and does not crop off key left-side content.
7. Ensure mobile displays the full image cleanly and does not look accidentally cropped.
8. Improve mobile top button layout so primary CTAs do not feel crowded.
9. Prefer top mobile CTA priority:
   - Get a Quote
   - Call 705-303-4409
   - Facebook / Google Profile can be secondary if needed.
10. Improve section heading spacing on mobile so headings have more breathing room when scrolling.
11. Lightly improve footer/CTA spacing only if needed and only within homepage CSS.
12. Preserve no horizontal overflow.
13. Preserve homepage CTA visibility.
14. Keep changes quote/admin/backend-safe.
15. Do not touch /quote stylesheet boundary cleanup in this PR.
16. Do not touch static/quote.html, static/quote.css, or static/quote.js.
17. Do not touch admin or mobile admin.
18. Do not do unrelated cleanup.

TEST REQUIREMENTS:
Update/add tests in tests/test_static_assets.py to protect:
1. homepage references the intended full hero image asset
2. new image asset exists and is non-empty
3. image dimensions/filesize are reasonable if practical
4. homepage logo still exists
5. homepage Get a Quote CTA still exists and points to the quote flow
6. homepage call CTA still exists
7. homepage social/contact links remain present if currently tested
8. homepage does not reference the old cropped/cut-off image if it is being replaced

If a very narrow Playwright assertion is helpful and non-brittle, update tests/test_launch_smoke_playwright.py minimally.
Do not make Playwright depend on exact copy/pixel layout.

VALIDATION:
Run:
git status --short --branch
git checkout main
git pull origin main
git status --short --branch
git log --oneline -8
git diff --check
.\.venv\Scripts\python.exe tools\check_version_parity.py
.\.venv\Scripts\python.exe tools\check_gpt_grounding_pack_parity.py
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m compileall app tools scripts tests
.\.venv\Scripts\python.exe -m pytest -q tests/test_static_assets.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_launch_smoke_playwright.py
.\.venv\Scripts\python.exe -m pytest -q

PROTECTED NO-GO DIFF:
Run:
git diff main...HEAD -- app/quote_engine.py app/main.py app/storage.py app/services app/gcalendar.py static/quote.html static/quote.js static/quote.css static/admin.html static/admin.js static/admin.css static/admin_mobile.html static/admin_mobile.js static/admin_mobile.css docs/gpt dist/gpt_grounding_pack render.yaml .github/workflows requirements.txt requirements.lock.txt VERSION canon_versions.txt .codex/config.toml

Expected protected no-go diff:
No output.

PRE-COMMIT SELF-REVIEW GATE:
Before committing:
1. Run validation.
2. Run protected no-go diff.
3. Inspect the actual diff.
4. Confirm only allowed files changed.
5. Review your own diff as if you are the PR reviewer.
6. Report P1/P2/P3 self-review findings.
7. Fix any P1/P2 before committing.
8. Commit and push only after P1/P2 are clear.

BRANCH:
create/homepage-full-hero-mobile-polish

COMMIT:
Headline:
create homepage full hero mobile polish

Description:
Replace the cut-off homepage hero image with the full user-provided image and make a narrow mobile homepage spacing/CTA polish pass while preserving protected quote, admin, backend, GPT, workflow, dependency, and version surfaces.

PR:
Title:
create homepage full hero mobile polish

Open the PR and stop.
Do not merge.

PR BODY REQUIREMENTS:
Include:
1. Brief plan
2. Implementation summary
3. Files changed
4. Old cropped/cut-off asset/reference replaced
5. New image details:
   - filename
   - dimensions
   - filesize
   - whether optimized/resized
6. Mobile polish summary:
   - top button layout
   - section heading spacing
   - footer/CTA spacing if changed
7. Validation results
8. Protected no-go diff result
9. Confirmation no pricing/backend/quote/admin/mobile admin/GPT/workflow/dependency/version changes
10. P1/P2/P3 self-review
11. Post-merge verification note:
   - visually verify homepage desktop/mobile
   - confirm no awkward crop
   - confirm CTA visibility
   - confirm no horizontal overflow

FINAL REPORT:
Return:
1. Brief plan
2. Implementation summary
3. Files changed
4. Old asset/reference replaced
5. New asset details:
   - filename
   - dimensions
   - filesize
6. Mobile polish details
7. Validation commands/results
8. Protected no-go diff result
9. Commit hash
10. PR link
11. P1/P2/P3 self-review
12. Confirmation no forbidden files changed
13. Plugins used
14. Confirmation Codex stopped after opening PR

STOP CONDITIONS:
Stop and report instead of guessing if:
- repo is dirty before starting
- local main is not current with origin/main
- the source image file is missing
- replacing the asset would require changes outside homepage/static scope
- homepage structure would need a broad redesign
- quote page changes appear necessary
- admin/mobile admin changes appear necessary
- backend/runtime/pricing/storage/GPT/workflow/dependency/version changes appear necessary
- validation fails for unclear reasons
- protected no-go diff is non-empty
- scope expands beyond homepage full hero image and mobile polish
```

## 13. First Message To Paste Into A New Chat

```text
Please ingest this Bay Delivery Quote Copilot handoff and continue from the current verified baseline.

I want you to act as my Bay Delivery repo/project co-pilot. Continue the same working style:
- recommendation first
- thorough P1/P2/P3 reviews
- best possible Codex/VS Code prompts
- protect pricing and app/quote_engine.py
- keep PRs narrow and auditable
- do not call PRs merge-ready without checking diff, comments/threads, scope, validation, and protected surfaces
- use Canadian/North Bay practical business context

Current verified baseline:
- Current main is verified through PR #326.
- Latest verified main commit: d2b0d1f create admin csp style compliance hardening (#326).
- Live Render /health is healthy and serving commit d2b0d1f30697.
- Current version: 0.12.0.
- Full pytest passed: 728 passed.
- Live /admin clean-session CSP verification passed.
- app/quote_engine.py remains the only pricing authority.

Next recommended task:
Create a Codex prompt or review the PR for `create homepage full hero mobile polish`.

Important:
Do homepage full hero image + mobile polish first.
Then do `create quote stylesheet boundary cleanup`.
Do not mix the quote stylesheet cleanup into the homepage PR.
