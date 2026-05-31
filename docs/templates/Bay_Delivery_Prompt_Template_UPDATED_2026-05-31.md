# Bay Delivery Prompt Template

Use this as the default structure for Codex, VS Code Agent, live browser checks, and ChatGPT PR reviews for Bay Delivery Quote Copilot.

Updated: 2026-05-31

Purpose:
Keep Bay Delivery repo work narrow, safe, copy-paste friendly, production-aware, and easy to review.

Bay Delivery Quote Copilot is production infrastructure for Bay Delivery in North Bay, Ontario. It is not a sandbox. Every prompt should protect pricing, customer trust, admin safety, production data, and repo stability.

---

# 1. Austin Add-ons / Current Prompt Rules

Use these rules whenever creating Codex, VS Code Agent, Browser/Chrome, or ChatGPT PR-review prompts for Bay Delivery Quote Copilot.

## Prompt quality rule

When Austin asks for a prompt, give the best final version immediately.

Do not give a mostly-good prompt and then list extra things to add afterward unless Austin specifically asks for review/iteration. Bake the safety checks, validation, stop conditions, and current lessons directly into the prompt.

## Goal Mode rule

Default:

Goal mode / Pursue goal: OFF

Use Goal Mode ON only for exploratory investigation where Codex needs to own an outcome, such as unknown CI failures, unknown bugs, broad read-only audits, flaky test investigation, or performance/root-cause discovery.

Do not use Goal Mode ON for narrow implementation PRs, pricing changes, storage/schema changes, auth/security changes, GPT behavior, workflows, or customer/admin UI changes unless explicitly approved.

## Plan Mode rule

Plan Mode ON means plan-only.

Do not write “Plan Mode ON briefly, then implement.” If implementation is allowed, use Plan Mode OFF and say:

State a brief plan first, then implement only if the plan stays inside scope.

Use Plan Mode ON for:
- pricing
- schema/storage/import/export
- auth/security
- workflows/Render/deployment
- GPT Action schema design
- architecture-sensitive work
- broad/unclear scope
- final audits/read-only audits

Use Plan Mode OFF for:
- narrow known implementation PRs
- docs-only syncs with known facts
- version bumps
- tiny static/copy fixes
- post-merge verification
- simple static checks
- approved narrow static UI implementation after plan review

## Validation dirt rule

Prefer validation commands that reduce repo dirt.

For compile checks, use:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m compileall app tools scripts tests
```

For pytest, `-B` is also acceptable when dirt risk matters:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q
```

If artifacts are created, list them clearly and do not commit them.

Do not run `git clean`, `git reset --hard`, or broad cleanup commands unless Austin explicitly approves.

## Pre-commit self-review gate

For production-sensitive Codex PRs, require:

Before committing:
1. Run validation.
2. Run protected no-go diff.
3. Inspect actual diff.
4. Confirm only allowed files changed.
5. Review your own diff as if you are the PR reviewer.
6. Report P1/P2/P3 self-review findings.
7. Fix any P1/P2 before committing.
8. Commit and push only after P1/P2 are clear.

## PR review standard

For every PR review, start with:

Merge recommendation:
- Merge
- Do not merge yet
- Needs re-review
- Fix-forward acceptable

Then always include:
- GitHub mergeable: yes/no/unknown
- Bay Delivery merge-ready: yes/no/unknown
- P1 blockers
- P2 blockers
- P3 notes
- Validation assessment
- Scope/protected-surface assessment
- Review comments/thread status
- Final next step

Do not treat green CI or GitHub mergeable status as enough. Inspect the diff, review comments/threads, scope, protected files, and validation evidence.

## Live visual/security verification rule

For UI/security fixes, include post-merge live verification when relevant.

Examples:
- For CSP/browser-console work: verify console errors/warnings are gone.
- For auth/pre-auth pages: use clean/incognito session if cached state could affect the result.
- For public visual changes: verify desktop and mobile viewports.
- For production route hardening: verify live routes directly.
- For image/asset changes: verify the live page does not awkwardly crop, overflow, or break CTA visibility.

Do not claim “fully verified” unless the relevant browser/live check actually ran. If not checked, say “not checked” and why.

## Browser/cache rule

When checking admin pre-auth/auth boundaries, require a clean session:

- fresh incognito/private context, or
- new isolated browser context with no storage state, or
- cleared cookies, localStorage, sessionStorage, and cached auth state.

Do not reuse an authenticated browser session and call it pre-auth verification.

## Protected-surface rule

Every implementation prompt must clearly list:
- files allowed
- strict do-not-change files
- protected no-go diff
- expected protected no-go diff result

For customer quote/public UI changes, explicitly protect:
- field IDs
- field names
- enum/option values
- selectors
- data-step values
- payload shape
- backend behavior
- internal/admin/risk/margin language boundaries

## Final report rule

Every Codex implementation report must include:
1. Brief plan
2. Implementation summary
3. Files changed
4. Tests added/updated
5. Validation commands/results
6. Protected no-go diff result
7. Commit hash
8. PR link
9. P1/P2/P3 self-review
10. Confirmation no forbidden files changed
11. Plugins used
12. Confirmation Codex stopped after opening/updating PR

## Default stop conditions

Stop and report instead of guessing if:
- repo is dirty before starting
- local main is not current with origin/main
- scope expands beyond the prompt
- protected files need changes
- validation fails for unclear reasons
- protected no-go diff is non-empty
- runtime/pricing/storage/customer/admin/GPT/deploy/dependency/version files need changes outside scope
- browser/live verification would require production mutation
- credentials/auth are needed but not explicitly provided

---

# 2. Codex Prompt Template

Use this for production-sensitive implementation, review, audit, and planning work.

## Codex default settings

```text
CODEX SETTINGS:
New Codex task/chat: YES
Repo: C:\Repos\Bay-Delivery-Quote-Copilot
Branch from latest main: YES
Goal mode / Pursue goal: OFF unless explicitly requested
Plan Mode: [ON/OFF]
Reasoning: [Medium/High]
Auto-review: ON
Include IDE context: ON
Network: OFF unless explicitly needed
```

## Codex plugin block

```text
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
```

## Codex plugin / memory access block

```text
PLUGIN / MEMORY ACCESS:
If local skill/memory reads are needed and Windows sandbox blocks them, use read-only sandbox grants only:
/sandbox-add-read-dir C:\Users\austi\.codex\plugins
/sandbox-add-read-dir C:\Users\austi\.codex\memories

Do not add writable roots for those folders.
Do not use danger-full-access.
Do not read unrelated user folders.
Do not change .codex/config.toml unless explicitly scoped.
```

## Codex narrow implementation prompt structure

```text
CODEX SETTINGS:
New Codex task/chat: YES
Repo: C:\Repos\Bay-Delivery-Quote-Copilot
Branch from latest main: YES
Goal mode / Pursue goal: OFF
Plan Mode: OFF
Reasoning: [Medium/High]
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
Do not change .codex/config.toml unless explicitly scoped.

MODE:
Narrow implementation PR.
State a brief plan first, then implement only if the plan stays inside scope.
Do not merge.
Do not deploy.
Do not mutate production data.

TASK:
[One clear sentence describing the task.]

REPO:
C:\Repos\Bay-Delivery-Quote-Copilot

CURRENT VERIFIED STATE:
- Current main is verified through PR #[NUMBER].
- Latest verified main commit: [SHORT_SHA] [COMMIT_TITLE].
- Current version: [VERSION].
- Version parity passed.
- GPT grounding parity passed.
- Full pytest passed: [RESULT].
- Protected no-go diff passed with no output.
- Live /health if relevant: [RESULT].
- app/quote_engine.py remains the only pricing authority.

SCOPE:
[Describe exactly what Codex should do.]

FILES ALLOWED:
- [path/to/file_or_folder]
- [path/to/file_or_folder]

STRICT DO NOT CHANGE:
- app/quote_engine.py
- pricing logic
- app/main.py unless explicitly scoped
- app/storage.py
- app/services/* unless explicitly scoped
- app/gcalendar.py unless explicitly scoped
- config/business_profile.json
- storage/schema/migrations
- customer quote flow unless explicitly scoped
- static/quote.html unless explicitly scoped
- static/quote.js unless explicitly scoped
- static/quote.css unless explicitly scoped
- static/admin.html unless explicitly scoped
- static/admin.js unless explicitly scoped
- static/admin.css unless explicitly scoped
- static/admin_mobile.html unless explicitly scoped
- static/admin_mobile.js unless explicitly scoped
- static/admin_mobile.css unless explicitly scoped
- docs/gpt/*
- dist/gpt_grounding_pack/*
- render.yaml
- .github/workflows/*
- requirements.txt
- requirements.lock.txt
- VERSION
- canon_versions.txt
- .codex/config.toml

IMPORTANT BOUNDARIES:
- One pricing engine only: app/quote_engine.py.
- Do not create a second pricing path.
- GPT is internal-only and recommendation-first.
- Do not add customer-facing GPT behavior.
- Do not leak internal risk, margin, owner-review, pricing caution, recommended trailer, operating-cost gap, or admin-only data to customer pages.
- Do not broaden scope.
- Do not do unrelated cleanup.
- Do not mutate production data.

IMPLEMENTATION REQUIREMENTS:
1. Keep the PR narrow.
2. Make only the scoped changes.
3. Preserve existing contracts and behavior outside the scoped change.
4. Add or update focused tests if behavior changes.
5. Do not do unrelated cleanup.
6. Do not touch protected files unless explicitly scoped.

VALIDATION:
Run:
git status --short --branch
git diff --check
.\.venv\Scripts\python.exe tools\check_version_parity.py
.\.venv\Scripts\python.exe tools\check_gpt_grounding_pack_parity.py
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m compileall app tools scripts tests
.\.venv\Scripts\python.exe -m pytest -q tests/test_static_assets.py
.\.venv\Scripts\python.exe -m pytest -q [ADD_FOCUSED_TESTS_IF_NEEDED]
.\.venv\Scripts\python.exe -m pytest -q

If full pytest is impractical, stop and report why. Do not call incomplete validation a pass.

PROTECTED NO-GO DIFF:
Run:
git diff main...HEAD -- app/quote_engine.py app/main.py app/storage.py app/services config/business_profile.json render.yaml .github/workflows docs/gpt dist/gpt_grounding_pack requirements.txt requirements.lock.txt VERSION canon_versions.txt static/quote.html static/quote.js static/quote.css static/admin.html static/admin.js static/admin.css static/admin_mobile.html static/admin_mobile.js static/admin_mobile.css .codex/config.toml

Expected:
No output unless the task explicitly scoped one of those files.

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
create/[short-task-name]

COMMIT:
Headline:
create [short task name]

Description:
[One or two sentences explaining what changed and confirming protected surfaces stayed unchanged.]

PR:
Title:
create [short task name]

Open the PR and stop.
Do not merge.

PR BODY REQUIREMENTS:
Include:
1. Plan summary
2. Implementation summary
3. Files changed
4. Validation results
5. Protected no-go diff result
6. P1/P2/P3 self-review
7. Confirmation no forbidden changes
8. Confirmation Codex stopped after opening PR

FINAL REPORT:
Return:
1. Brief plan
2. Implementation summary
3. Files changed
4. Tests added/updated
5. Validation commands/results
6. Protected no-go diff result
7. Commit hash
8. PR link
9. P1/P2/P3 self-review
10. Confirmation no forbidden files changed
11. Plugins used
12. Confirmation Codex stopped after opening PR

STOP CONDITIONS:
Stop and report instead of guessing if:
- repo is dirty before starting
- local main is not current with origin/main
- scope expands beyond this prompt
- protected files need changes
- validation fails for unclear reasons
- protected no-go diff is non-empty
- runtime/pricing/storage/customer/admin/GPT/deploy/dependency/version files need changes outside scope
```

---

# 3. Codex Read-Only Audit / Plan-Only Template

Use this when you want Codex to inspect and report only.

Examples:
- pricing readiness review
- final launch-grade audit
- security audit
- dependency audit
- architecture review
- schema/storage planning
- Render/deployment-sensitive review

Plan Mode should usually be ON here.

```text
CODEX SETTINGS:
New Codex task/chat: YES
Repo: C:\Repos\Bay-Delivery-Quote-Copilot
Branch from latest main: NO
Goal mode / Pursue goal: OFF unless explicitly requested
Plan Mode: ON
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
Read-only audit / plan-only.
Do not modify files.
Do not create a branch.
Do not commit.
Do not push.
Do not open a PR.
Do not merge.
Do not mutate local or production data.

TASK:
[One clear sentence describing the audit.]

REPO:
C:\Repos\Bay-Delivery-Quote-Copilot

CURRENT VERIFIED STATE:
- Current main is verified through PR #[NUMBER].
- Latest verified main commit: [SHORT_SHA] [COMMIT_TITLE].
- Current version: [VERSION].
- Version parity passed.
- GPT grounding parity passed.
- Full pytest passed: [RESULT].
- Protected no-go diff passed with no output.
- Production smoke: [RESULT OR NOT REQUIRED].
- app/quote_engine.py remains the only pricing authority.

PRIMARY GOAL:
[Explain the audit question Codex must answer.]

AUDIT SCOPE:
Review:
1. [area]
2. [area]
3. [area]
4. [area]

CORE GUARDRAILS:
- One pricing engine only: app/quote_engine.py.
- Do not create or recommend a second pricing path.
- Do not recommend pricing code changes without enough completed-job/manual calibration evidence.
- Cash has no HST.
- EMT/e-transfer adds 13% HST.
- Backend is source of truth.
- SQLite is source of truth.
- Google Calendar is mirror/convenience only.
- GPT is internal-only and recommendation-first.
- Customer quote flow must stay simple and must not expose internal risk/margin/admin data.
- No production mutations.
- No file changes.

COMMANDS TO RUN:
cd C:\Repos\Bay-Delivery-Quote-Copilot

$env:GIT_PAGER = "cat"

git status --short --branch
git log --oneline -10
git diff --check
.\.venv\Scripts\python.exe tools\check_version_parity.py
.\.venv\Scripts\python.exe tools\check_gpt_grounding_pack_parity.py
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m compileall app tools scripts tests
.\.venv\Scripts\python.exe -m pytest -q tests/test_static_assets.py
.\.venv\Scripts\python.exe -m pytest -q [ADD_FOCUSED_TESTS_IF_RELEVANT]
.\.venv\Scripts\python.exe -m pytest -q

SEARCHES TO RUN:
rg -n "TODO|FIXME|SECURITY|HACK|temporary|unsafe|debug" app static tests scripts tools docs .github
rg -n "manual review required|owner_review|profit|margin|pricing engine|underpriced" README.md PROJECT_RULES.md PROJECT_VISION.md docs static app tests tools scripts .github .agents
rg -n "innerHTML|outerHTML|insertAdjacentHTML|eval\(|Function\(|document\.cookie|localStorage|sessionStorage" static app tests
rg -n "@app\.(get|post|put|delete|patch)\(" app/main.py

OPTIONAL LIVE CHECK:
Only if explicitly approved in this task, check:
- https://bay-delivery-quote-copilot.onrender.com/health

Confirm:
- ok true
- version matches repo VERSION
- commit matches current main HEAD

Do not submit forms or mutate live data.

OUTPUT FORMAT:
Return:
1. Executive verdict:
   - Green / Yellow / Red
   - score out of 100
   - score out of 10
   - one-sentence reason
2. Current verified baseline
3. P1 blockers
4. P2 issues
5. P3 notes
6. Detailed findings by area
7. Recommended next tasks ranked 1-5
8. Final recommendation
9. Commands run and results
10. Stop confirmation:
   - no files changed
   - no branch
   - no commit
   - no push
   - no PR
   - no production mutations

STRICT STOP CONDITIONS:
Stop and report instead of guessing if:
- repo is dirty before starting
- commands would mutate local or production data
- protected files would need editing to answer the audit
- validation fails for unclear reasons
- live verification would require mutation
- network is needed but not approved

FINAL RULE:
Do not implement anything. This is a read-only audit only.
```

---

# 4. VS Code Agent Prompt Template

Use VS Code Agent for lower-risk, mechanical, docs/version/verification work.

Do not include a reasoning level in VS Code Agent prompts.

```text
MODE:
[Read-only post-merge verification / Narrow VS Code Agent task]
Do not modify files unless explicitly scoped.
Do not create branches unless explicitly scoped.
Do not commit unless explicitly scoped.
Do not push unless explicitly scoped.
Do not open a PR unless explicitly scoped.
Do not merge.

TASK:
[One clear sentence describing the task.]

REPO:
C:\Repos\Bay-Delivery-Quote-Copilot

CURRENT VERIFIED STATE:
- Current main is verified through PR #[NUMBER].
- Latest verified main commit: [SHORT_SHA] [COMMIT_TITLE].
- Current version: [VERSION].
- Version parity passed.
- GPT grounding parity passed.
- Full pytest passed: [RESULT].
- Protected no-go diff passed with no output.

SCOPE:
[Docs-only / version bump / read-only verification / simple cleanup]

FILES LIKELY ALLOWED:
- [file/folder]
- [file/folder]

STRICT DO NOT CHANGE:
- app runtime code
- app/quote_engine.py
- pricing logic
- app/storage.py
- storage/schema
- customer quote flow
- admin UI
- mobile admin
- GPT endpoint behavior
- docs/gpt/* unless explicitly scoped
- dist/gpt_grounding_pack/* unless explicitly scoped
- Render config
- workflows
- requirements
- VERSION unless version bump task
- .codex/config.toml

VALIDATION:
Run:
git status --short --branch
git diff --check
.\.venv\Scripts\python.exe tools\check_version_parity.py
.\.venv\Scripts\python.exe tools\check_gpt_grounding_pack_parity.py
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m compileall app tools scripts tests
.\.venv\Scripts\python.exe -m pytest -q tests/test_static_assets.py
.\.venv\Scripts\python.exe -m pytest -q [ADD_FOCUSED_TESTS_IF_RELEVANT]
.\.venv\Scripts\python.exe -m pytest -q

PROTECTED NO-GO DIFF:
Run:
git diff main...HEAD -- app static tests tools scripts render.yaml .github/workflows requirements.txt requirements.lock.txt .codex/config.toml

Expected:
No output unless explicitly scoped.

BRANCH:
[branch/name if creating PR]

COMMIT:
Headline:
[commit headline]

Description:
[commit description]

PR:
Title:
[PR title]

FINAL REPORT:
Return:
1. Files changed
2. Validation results
3. Protected no-go diff result
4. Commit hash if applicable
5. PR link if applicable
6. P1/P2/P3 risk review
7. Confirmation no forbidden changes
8. Confirmation VS Code Agent stopped after opening PR or completing verification

STOP CONDITIONS:
Stop and report instead of guessing if:
- repo is dirty before starting
- protected files need changes
- validation fails for unclear reasons
- protected no-go diff is non-empty
- task becomes broader than prompt
```

---

# 5. VS Code Agent Read-Only Post-Merge Verification Template

Use this after merging a PR, especially for docs/static/lower-risk work.

```text
MODE:
Read-only post-merge verification.
Do not modify files.
Do not create branches.
Do not commit.
Do not push.
Do not open a PR.
Do not merge.

TASK:
Post-merge verify PR #[NUMBER] on main.

REPO:
C:\Repos\Bay-Delivery-Quote-Copilot

CURRENT MERGE:
PR #[NUMBER] [PR_TITLE]
Merge commit:
[FULL_MERGE_SHA]

EXPECTED BASELINE:
- Current version: [VERSION].
- Expected changed files:
  - [file]
  - [file]
- No pricing changes unless explicitly scoped.
- No storage/schema changes unless explicitly scoped.
- No customer/admin/GPT/deploy/dependency/version changes unless explicitly scoped.

COMMANDS:
cd C:\Repos\Bay-Delivery-Quote-Copilot

$env:GIT_PAGER = "cat"

git checkout main
git pull origin main

git status --short --branch
git log --oneline -8

git diff --name-only [MERGE_SHA]^1 [MERGE_SHA]

.\.venv\Scripts\python.exe tools\check_version_parity.py
.\.venv\Scripts\python.exe tools\check_gpt_grounding_pack_parity.py
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m compileall app tools scripts tests

.\.venv\Scripts\python.exe -m pytest -q tests/test_static_assets.py
.\.venv\Scripts\python.exe -m pytest -q [ADD_FOCUSED_TESTS_IF_RELEVANT]
.\.venv\Scripts\python.exe -m pytest -q

PROTECTED NO-GO DIFF:
git diff [MERGE_SHA]^1 [MERGE_SHA] -- app/quote_engine.py app/main.py app/storage.py app/services config/business_profile.json render.yaml .github/workflows docs/gpt dist/gpt_grounding_pack requirements.txt requirements.lock.txt VERSION canon_versions.txt static/quote.html static/quote.js static/quote.css static/admin.html static/admin.js static/admin.css static/admin_mobile.html static/admin_mobile.js static/admin_mobile.css .codex/config.toml

EXPECTED:
- main is current with origin/main.
- PR #[NUMBER] merge commit is present.
- Changed files match expected scope.
- Version parity passes.
- GPT grounding parity passes.
- compileall passes.
- focused tests pass.
- full pytest passes.
- protected no-go diff has no output.

FINAL REPORT:
Return:
1. PASS/FAIL
2. Current branch/status
3. Latest main commit and PR #[NUMBER] merge evidence
4. Files changed by PR #[NUMBER]
5. Version parity result
6. GPT grounding parity result
7. compileall result
8. Focused test results
9. Full pytest result
10. Protected no-go diff result
11. P1/P2/P3 risk review
12. Final call: PR #[NUMBER] post-merge verified or not verified
13. Exact next recommended step
```

---

# 6. Live Browser / Visual Verification Template

Use this for read-only production page checks.

```text
MODE:
Read-only live visual/console verification.
No file changes.
No branch.
No commit.
No PR.
No production mutation.
No admin login unless explicitly requested.
No form submissions.
No workflow reruns.

TASK:
[Describe exact live page check.]

REPO:
C:\Repos\Bay-Delivery-Quote-Copilot

CURRENT VERIFIED BASELINE:
- Current main is verified through PR #[NUMBER].
- Latest verified main commit: [SHORT_SHA] [COMMIT_TITLE].
- Live Render /health is healthy and serving commit [COMMIT_PREFIX].
- Current version: [VERSION].
- Full pytest passed: [RESULT].
- Protected no-go diff passed with no output.
- app/quote_engine.py remains the only pricing authority.

LIVE PAGES:
- https://bay-delivery-quote-copilot.onrender.com/health
- https://bay-delivery-quote-copilot.onrender.com/[PAGE]

VIEWPORTS:
Check:
- Desktop: about 1366x900
- Mobile/narrow: about 390x844

READ-ONLY CHECKS:
1. Open /health and confirm:
   - ok true
   - version matches repo VERSION
   - commit matches current deployed main commit prefix.
2. Open the scoped live page.
3. Confirm page loads.
4. Check browser console errors/warnings exactly.
5. Check network panel for failed page-critical requests.
6. Capture screenshots if supported.
7. Verify the specific acceptance criteria for this task.
8. Do not submit forms.
9. Do not mutate production data.

CLEAN-SESSION REQUIREMENT:
If checking admin pre-auth/auth boundaries, use:
- fresh incognito/private context, or
- new isolated browser context with no storage state, or
- cleared cookies, localStorage, sessionStorage, and cached auth state.

EXPECTED:
- /health healthy and matching current live commit.
- Scoped page loads.
- No page-critical network failures.
- No unexpected console errors/warnings.
- Acceptance criteria pass.
- Repo remains unchanged.

IF BROWSER/CHROME FAILS:
Do not guess.
Report:
- exact tool failure/error
- what was checked instead, if anything
- whether browser/live verification remains NOT CHECKED

FINAL REPORT:
Return:
1. PASS/FAIL/INCONCLUSIVE verdict
2. Pages checked
3. Viewports checked
4. /health result
5. Page load result
6. Console errors/warnings, exact text if present
7. Network failures, exact URLs/statuses if present
8. Visual result
9. Screenshot paths if captured
10. Any local artifacts created
11. P1/P2/P3 findings
12. Final recommendation

STOP CONDITIONS:
Stop and report instead of guessing if:
- /health is unhealthy
- /health commit does not match current deployed main
- scoped page does not load
- browser tooling fails before required inspection
- inspection requires login or production mutation not explicitly approved
- any step would modify repo files or production data
```

---

# 7. ChatGPT PR Review Request Template

Use this when Codex or VS Code opens a PR and Austin wants ChatGPT to review whether it is safe to merge.

```text
Please review this Bay Delivery Quote Copilot PR.

PR:
[PASTE PR LINK OR NUMBER]

Codex/Agent final report:
[PASTE FINAL REPORT]

Review it using my preferred format:
1. Merge recommendation first:
   - Merge
   - Do not merge yet
   - Needs re-review
   - Fix-forward acceptable
2. P1 blockers
3. P2 blockers
4. P3 notes
5. Validation assessment
6. Scope/protected-surface assessment
7. Final next step

Bay Delivery constraints:
- app/quote_engine.py is the only pricing authority.
- Do not accept duplicate pricing logic.
- Do not accept pricing changes unless explicitly scoped.
- Do not leak internal/admin/risk/margin data to customer pages.
- Customer quote, admin desktop, admin mobile, GPT, Render/workflows, storage/schema, requirements, VERSION, docs/gpt, and dist/gpt_grounding_pack are protected unless explicitly scoped.
- Prefer narrow, reversible, auditable PRs.
- If there is uncertainty, say exactly what must be verified before merge.
```

---

# 8. ChatGPT Create A Codex Prompt Request Template

Use this when asking ChatGPT to make the next Codex prompt.

```text
Give me the best possible Codex prompt for the next Bay Delivery task.

Task:
[DESCRIBE TASK]

Current verified state:
[PASTE LATEST MAIN COMMIT, VERSION, TEST RESULTS, PR CONTEXT]

Requirements:
- One clean copy-paste prompt.
- Give the best final version immediately.
- Include recommended reasoning level.
- Include Plan Mode ON or OFF and explain why before the prompt.
- Include Goal Mode ON or OFF and explain why before the prompt.
- Include plugins and memory access block.
- Include current verified state.
- Include scope.
- Include files allowed.
- Include strict do-not-change list.
- Include validation.
- Include protected no-go diff.
- Include pre-commit self-review gate when appropriate.
- Include branch name.
- Include commit headline and commit description.
- Include PR title.
- Include final report requirements.
- Include stop conditions.
- Keep it narrow.
- Do not use nested markdown fences inside the prompt.
- Protect app/quote_engine.py and pricing authority unless explicitly scoped.
```

---

# 9. ChatGPT Create A New-Chat Handoff Request Template

Use this when ending a long ChatGPT chat and starting fresh.

```text
Please create a full Bay Delivery Quote Copilot new-chat handoff.

The goal is to let me start a fresh ChatGPT chat without losing important project context.

The handoff must include:
- What we were trying to accomplish
- What PR/task we were on
- What has already been completed
- What has already been merged or verified
- What still needs to happen next
- Current repo/live app assumptions
- Any PR numbers, commit SHAs, workflow runs, links, version numbers, or validation results mentioned
- Files changed or files that must not be changed
- Tests/commands that passed or still need to be run
- Known blockers, risks, drift, or things to verify
- My formatting/workflow preferences
- My Codex / VS Code Agent preferences
- My Bay Delivery pricing/business rules
- Any “do not do this” rules
- The exact next prompt I should paste into Codex, VS Code Agent, or ChatGPT if applicable

Use this structure:

# Bay Delivery Quote Copilot — New Chat Handoff

## 1. Handoff Purpose
## 2. User Working Preferences
## 3. Project Context
## 4. Hard Rules / Invariants
## 5. Current State
## 6. Completed Work
## 7. Current Open Task
## 8. Recommended Next Step
## 9. Validation / Commands / Checks
## 10. Risks / Watchouts
## 11. Copy-Paste Prompt for the Next Tool
## 12. First Message to Paste Into the New Chat

Be detailed, practical, and continuation-ready. Do not summarize too aggressively. Preserve anything needed to avoid re-explaining the work.
```

---

# 10. Quick Rules For Choosing The Template

| Situation | Use Template |
|---|---|
| Need Codex to make a narrow PR | Codex Narrow Implementation PR |
| Need Codex to inspect/score/plan only | Codex Read-Only Audit / Plan-Only |
| PR just merged | VS Code Agent Post-Merge Verification |
| Need a live visual/browser check | Live Browser / Visual Verification |
| Need ChatGPT to review a PR | ChatGPT PR Review Request |
| Need ChatGPT to make a Codex prompt | ChatGPT Create Codex Prompt Request |
| Need to start a fresh ChatGPT chat | New-Chat Handoff Request |

---

# 11. Reminder About Plan Mode

Use Plan Mode ON for:

- pricing
- schema/storage/import/export
- auth/security
- workflows/Render/deployment
- GPT Action schema design
- architecture-sensitive changes
- broad/unclear scope
- final audits/read-only audits

Use Plan Mode OFF for:

- narrow docs PRs
- known small implementation PRs
- version bumps
- tiny static/copy changes
- tasks where the plan is already approved

When Plan Mode is OFF but you still want care, say:

State a brief plan first, then implement only if the plan stays inside scope.

Do not say “Plan Mode ON briefly, then implement.” Codex treats Plan Mode ON as hard plan-only.

---

# 12. Current Bay Delivery Baseline To Paste Into Any Prompt

Update this block whenever a newer verified baseline replaces it.

```text
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
```

---

# 13. Bay Delivery Guardrails Reminder

| Guardrail | Reminder |
|---|---|
| Pricing authority | Only `app/quote_engine.py`. Do not create a second pricing engine. |
| Cash/EMT | Cash no HST. EMT/e-transfer +13% HST. |
| Admin | Internal operations only. |
| GPT | Internal-only, recommendation-first. |
| Customer quote flow | Public customer flow stays simple and safe. |
| Storage | SQLite is source of truth. |
| Calendar | Google Calendar is mirror/convenience only. |
| PR style | Narrow, reversible, auditable. |
| Verification | Parity checks + focused tests + protected diff. |
| Merge rule | Review first. Do not auto-merge. |
