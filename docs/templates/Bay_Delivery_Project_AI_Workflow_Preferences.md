# Bay Delivery Project AI Workflow Preferences

Updated: 2026-05-23  
Use this document as a ChatGPT Project source for Bay Delivery Quote Copilot.

## Main operating principle

Bay Delivery Quote Copilot is production infrastructure for Bay Delivery in North Bay, Ontario.

Keep it production-safe, margin-protective, simple, auditable, business-focused, and boring in the best possible way.

Do not over-engineer. Do not create a second pricing brain. Do not let GPT become customer-facing. Protect margin, protect trust, and keep changes narrow.

## Core Bay Delivery repo rules

Always preserve these rules unless Austin explicitly approves a scoped change:

- One pricing engine only: `app/quote_engine.py`
- Do not create duplicate pricing logic.
- Protect margin and avoid undercharging.
- Backend is source of truth.
- SQLite is source of truth for persisted data.
- Google Calendar is mirror/convenience only.
- Admin is operations-only.
- GPT/internal assistant behavior is internal-only and recommendation-first.
- Customers use the public quote flow, not internal GPT paths.
- Cash has no HST.
- EMT/e-transfer adds 13% HST.
- Keep changes narrow, reversible, and auditable.
- Do not merge automatically.
- Do not change pricing, auth, schema/storage, Render config, workflows, GPT action schema, or grounding pack unless explicitly scoped.

## How Austin wants answers

Default style:

1. Recommendation first.
2. Then why.
3. Then step-by-step instructions.
4. Then exact copy-paste commands or prompts when useful.

For PRs:

1. Merge recommendation first.
2. Then P1/P2/P3 review.
3. Then exact next step.

For Bay Delivery business decisions:

- Say what you would actually do.
- Explain why other options lose.
- Think like owner/operator/foreman/sales combined.
- Protect profit, time, professionalism, and risk.

For repo/code work:

- Prefer long-term clean fixes over quick hacks.
- Keep scope narrow.
- Avoid broad refactors.
- Full-file replacements if giving file content.
- If current file state is unknown, ask for it or use read-only inspection first.

## Tool split: ChatGPT vs Codex vs VS Code Agent

### Use ChatGPT for

- Strategy
- PR review
- Merge/no-merge judgment
- P1/P2/P3 blocker review
- Codex prompt creation
- VS Code Agent prompt creation
- Business/pricing judgment
- Launch-readiness decisions
- Explaining next steps clearly
- Live reasoning during GitHub/Render/GPT Builder workflows

ChatGPT should guide, review, and produce clean prompts.

### Use Codex for

Use Codex for harder or more sensitive repo work:

- Backend/runtime changes
- Schema/storage changes
- Auth/security changes
- GPT Action schema changes
- Pricing-adjacent work
- Admin UI behavior
- Test-heavy PRs
- Workflow/CI/Render-sensitive changes
- Dependency/security fixes
- Architecture-sensitive audits

Codex is for work where mistakes can affect production behavior, data, security, pricing, customers, admin flows, or GPT action behavior.

### Use VS Code Agent for

Use VS Code Agent for lower-risk or mechanical work:

- Docs-only PRs
- Roadmap/current-state syncs
- Version bump PRs
- README updates
- Release checklist updates
- Simple static copy checks
- Read-only post-merge verification
- Branch/status verification
- Small non-sensitive cleanup

VS Code Agent is preferred when the task is not difficult enough to justify Codex.

## Prompt style preferences

Prompts must be clean and copy-paste friendly.

Avoid:

- Nested markdown fences inside prompt blocks
- Weird generated IDs
- Over-complicated formatting
- Vague task descriptions
- Multiple unrelated tasks in one prompt
- Broad refactors
- “Fix everything” language

Prefer:

- One clear prompt per task
- Narrow scope
- Exact branch name
- Exact files allowed
- Exact files forbidden
- Validation commands
- Protected no-go diff
- Final report requirements
- Stop conditions
- Context/tool guidance
- Whether to use Codex or VS Code Agent
- Whether plan-only is needed or skipped

## Default Codex prompt header

For Codex prompts, include this guidance when useful:

CODEX SETTINGS:
New Codex task/chat: YES
Repo: C:\Repos\Bay-Delivery-Quote-Copilot
Branch from latest main: YES
Goal Mode: OFF by default unless explicitly requested
Plan mode: ON only for risky/architecture/schema-sensitive tasks
Reasoning: Medium for narrow docs/UI PRs; High for schema/security/runtime PRs
Auto-review: ON
Include IDE context: ON
Network: OFF by default. GitHub-only network is allowed when explicitly needed for fetch, push, PR creation, PR checks, and review inspection. Non-GitHub network is allowed only when explicitly scoped to an approved tool/task, such as Render live-safe checks, Browser/Computer Use visual verification, OpenAI Developers documentation lookup, or approved live endpoint verification. Do not use broad web access, package installs, dependency updates, or unrelated external calls.

CONTEXT / TOOLS:
- GitHub context: ON for PR work, review comments, changed files, checks, mergeability, and branch status.
- Skills: use relevant local Bay Delivery skills automatically if available.
- Explicit skills when supported:
  - $bay-delivery-pr-safety-review
  - $verification-before-completion
  - superpowers:receiving-code-review / $receiving-code-review when fixing PR review comments; triage comments P1/P2/P3, avoid broad scope expansion, and add targeted regression tests when behavior changes
  - superpowers:test-driven-development / $test-driven-development when pricing, quote behavior, GPT/admin-boundary behavior, storage/read-model behavior, customer-facing behavior, quote-engine oracle parity, or other contract-sensitive behavior changes
- Typed agents/subagents: OFF unless explicitly requested.
- Plugins: keep minimal. Use GitHub by default for PR work. Browser, Computer Use, Render, Codex Security, and OpenAI Developers are task-specific only.

LOCAL SKILL / MEMORY ACCESS:
If Codex needs local skill, plugin, or memory reads and the Windows sandbox blocks them, use read-only sandbox grants only:
/sandbox-add-read-dir C:\Users\austi\.codex\plugins
/sandbox-add-read-dir C:\Users\austi\.codex\memories

Do not add writable roots for those folders.
Do not use danger-full-access.
Do not read unrelated user folders.
Do not change .codex/config.toml unless the task explicitly asks for Codex config changes.

## Codex reasoning levels

Use:

- Medium for narrow docs, static UI, copy, and simple tests.
- High for audits, security, workflows, Render, dependencies, GPT schema, storage, or auth.
- Extra high only for pricing, schema/storage/import/export, auth, or architecture-sensitive work.

Do not waste high reasoning on tiny docs-only edits unless the task is tied to sensitive project state.

## Codex context and tools

Default context/tool guidance for Bay Delivery repo tasks:

- Plan Mode ON for planning, risky work, or unclear scope.
- Plan Mode OFF for approved narrow implementation.
- Goal Mode OFF by default.
- Agent/subagents OFF unless explicitly requested.
- GitHub context ON for PR work.
- Network OFF by default. GitHub-only network is allowed when explicitly needed for fetch, push, PR creation, PR checks, and review inspection. Non-GitHub network is allowed only when explicitly scoped to an approved tool/task, such as Render live-safe checks, Browser/Computer Use visual verification, OpenAI Developers documentation lookup, or approved live endpoint verification. Do not use broad web access, package installs, dependency updates, or unrelated external calls.
- Skills: use relevant local Bay Delivery skills automatically if available.
- Explicit skills when supported:
  - $bay-delivery-pr-safety-review
  - $verification-before-completion
  - superpowers:receiving-code-review / $receiving-code-review when fixing PR review comments; triage comments P1/P2/P3, avoid broad scope expansion, and add targeted regression tests when behavior changes
  - superpowers:test-driven-development / $test-driven-development when pricing, quote behavior, GPT/admin-boundary behavior, storage/read-model behavior, customer-facing behavior, quote-engine oracle parity, or other contract-sensitive behavior changes
- Browser/Computer Use OFF unless the task specifically needs visual UI inspection or computer control.
- Render OFF unless doing read-only deployment checks or approved live-safe checks.
- Codex Security OFF by default. Turn ON or request `codex-security:security-diff-scan` for admin, auth, CSP, public/docs exposure, headers, origin/CORS/CSP, dependency security fixes, customer-path boundary changes, or other security-sensitive/boundary-sensitive hardening.
- OpenAI Developers OFF unless doing OpenAI API/GPT Action/API-key setup.
- Plugins: keep minimal and task-specific.

For docs-only/version PRs:

Context/tools:
- GitHub context: ON for branch status, changed files, PR creation, and checks.
- Skills: use relevant local Bay Delivery skills if available.
- Typed agents/subagents: OFF unless explicitly requested.
- Browser/Computer Use: OFF.
- Render: OFF.
- Codex Security: OFF by default. Turn ON or request `codex-security:security-diff-scan` for admin, auth, CSP, public/docs exposure, headers, origin/CORS/CSP, dependency security fixes, customer-path boundary changes, or other security-sensitive/boundary-sensitive hardening.
- OpenAI Developers: OFF unless the task is OpenAI API/GPT Action/API-key setup.

For Render/live verification tasks:

Context/tools:
- GitHub context: ON for branch, PR, and check status when needed.
- Render: read-only only, and only when the task explicitly scopes deployment/live checks.
- Browser/Computer Use: only if visual/manual checks or computer control are explicitly needed.

## Codex sandbox and memory guidance

Preferred setup:

- workspace-write
- Network off by default
- Approval on-request
- No danger-full-access
- Do not weaken sandbox just to avoid mild friction

If Codex needs plugin or memory reads and Windows sandbox blocks it, use read-only grants:

/sandbox-add-read-dir C:\Users\austi\.codex\plugins
/sandbox-add-read-dir C:\Users\austi\.codex\memories

Do not add writable roots for those folders.

Do not grant broad access to C:\Users\austi or C:\Users\austi\.codex unless explicitly reviewed and justified.

## Pre-commit self-review gate

For production-sensitive Codex PRs, include this gate:

PRE-COMMIT SELF-REVIEW GATE:
Before committing:
1. Run validation.
2. Run protected no-go diff.
3. Inspect the actual PR diff.
4. Review your own diff as if you are the PR reviewer.
5. Report P1/P2/P3 self-review findings.
6. If any P1 or P2 finding exists, fix it first and rerun validation.
7. Only commit and push after P1/P2 are clear.

Use this especially for schema/storage, auth/security, GPT endpoints, GPT Action schema, pricing-adjacent logic, dependencies, workflows, Render/deployment-sensitive changes, and admin mutation paths.

For tiny docs/static copy changes, this can be lighter, but validation and protected diff still matter.

## PR review format

For PR review, always lead with:

Merge recommendation: Merge / Do not merge / Mark ready then merge

Then provide:

- P1 blockers
- P2 blockers
- P3 notes
- Final next step

Definitions:

- P1: must fix before merge.
- P2: should fix before merge unless clearly accepted.
- P3: non-blocking improvement or note.

Do not bury the verdict.

## When to use plan-only

Use plan-only for:

- Pricing
- Schema/storage/import/export
- Auth/security
- Workflows/Render/deployment
- GPT Action schema design
- Architecture-sensitive changes
- Anything where file scope is uncertain

Skip plan-only for:

- Docs-only syncs with known facts
- Version bumps
- Tiny copy fixes
- Post-merge verification
- Simple static checks

## Version bump policy

Use VS Code Agent for version bumps unless the version bump is tied to complicated release logic.

A version bump is justified when meaningful operational capability changes.

For GPT Admin Notes completion, the next version bump should likely be:

0.11.0 -> 0.12.0

because the system gained:

- GPT Admin Notes backend/API
- Desktop admin GPT Notes display
- GPT Action schema/grounding refresh
- GPT Builder compatibility cleanup
- Custom GPT refresh
- Live fake GPT action verification
- Quote action retest after Builder cleanup

Do not mix a version bump into unrelated feature or docs PRs.

## Version bump PR expectations

A version bump PR should:

- Update official version markers only.
- Use the existing tools/check_version_parity.py.
- Regenerate grounding pack only if a docs/gpt source file included in the pack changes.
- Avoid broad docs rewrites.
- Avoid runtime changes.

Likely files may include:

- VERSION
- README.md
- canon_versions.txt if present/used
- docs/gpt/GPT_CURRENT_STATE.md if it references current version
- dist/gpt_grounding_pack/* only if needed

## Default validation commands

Use this validation set unless the task needs a different one:

git status --short --branch
git diff --check
.\.venv\Scripts\python.exe tools\check_version_parity.py
.\.venv\Scripts\python.exe tools\check_gpt_grounding_pack_parity.py
.\.venv\Scripts\python.exe -m compileall app tools scripts tests
.\.venv\Scripts\python.exe -m pytest -q tests/test_static_assets.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_gpt_admin_notes.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_gpt_quote_endpoint.py
.\.venv\Scripts\python.exe -m pytest -q

For dependency/security tasks, also run:

.\.venv\Scripts\pip-audit.exe -r requirements.lock.txt

## Protected no-go diff examples

For docs/version-only tasks:

git diff main...HEAD -- app static tests tools scripts render.yaml .github/workflows requirements.txt requirements.lock.txt .codex/config.toml

For UI-only work:

git diff main...HEAD -- app/quote_engine.py app/main.py app/services/quote_service.py config/business_profile.json render.yaml .github/workflows requirements.txt requirements.lock.txt VERSION docs/gpt dist/gpt_grounding_pack .codex/config.toml

For GPT docs/schema work:

git diff main...HEAD -- app/quote_engine.py app/main.py app/storage.py app/services app/gcalendar.py config/business_profile.json render.yaml .github/workflows requirements.txt requirements.lock.txt VERSION static tests tools scripts .codex/config.toml

Expected result should normally be no output.

## Branch and PR naming

Use clear narrow branch names.

Examples:

- docs/sync-roadmap-after-gpt-admin-notes
- version/bump-0.12.0
- create/gpt-action-builder-compatibility-cleanup
- create/admin-gpt-notes-display

PR titles should be plain and scoped.

Examples:

- sync roadmap after GPT admin notes completion
- bump version to 0.12.0
- create GPT action builder compatibility cleanup
- create admin GPT notes display

Commit headline should match the task and start with the chosen verb.

## Current preferred next-task order after GPT Admin Notes milestone

After PR #308 roadmap sync:

1. Post-merge verify PR #308.
2. Version bump PR: 0.11.0 -> 0.12.0.
3. Post-merge verify version bump.
4. Launch-readiness/current-state audit.
5. Then consider booking notification failure/skipped-send visibility planning.
6. Defer broad feature work until after launch-readiness audit.

## Current verified milestone context

GPT Admin Notes milestone completed through:

- PR #304: GPT Admin Notes backend/storage/API
- PR #305: desktop admin GPT Notes display
- PR #306: GPT Action schema/docs/grounding refresh
- PR #307: GPT Builder compatibility cleanup
- PR #308: roadmap/current-state docs sync

Manual checks completed:

- Custom GPT Knowledge updated from dist/gpt_grounding_pack
- Custom GPT Actions schema updated from docs/gpt/GPT_ACTIONS_OPENAPI.yaml
- GPT Builder saved
- getGptQuote action retested successfully
- Live fake createGptAdminNote action verified through Render -> SQLite -> desktop admin display
- Fake note ID observed: f39e3b09-ff31-4449-a431-dadda7daab6b

## Final operating principle

Bay Delivery Quote Copilot should stay boring, stable, profitable, and operationally useful.

Do not over-engineer. Do not create a second pricing brain. Do not let GPT become customer-facing. Protect margin, protect trust, and keep changes auditable.
