# Bay Delivery Codex Prompt Template

Use this template for Bay Delivery repo tasks.

Default workflow:

```text
Plan -> Implement -> Validate -> Branch -> PR -> Summarize -> STOP
```

Default Bay Delivery implementation overlays:

```text
Active defaults:
- superpowers:receiving-code-review
  - comment-by-comment P1/P2/P3 triage
  - targeted regression test for each accepted behavior-changing review fix
  - short gap-closed note before push
- bay-delivery-pr-safety-review
  - main Bay-specific safety gate
  - embedded pricing red-team pass for quote-engine and business-rule work
  - embedded docs/GPT publication pass for `docs/gpt`, `dist/gpt_grounding_pack`, and manifest parity as one unit
- verification-before-completion
  - clean working tree
  - targeted tests plus relevant full validation
  - protected no-go diff
  - final what changed / what did not change report

Trigger-only overlays:
- superpowers:test-driven-development for pricing, public quote, GPT/admin-boundary, storage/read-model, and customer-facing behavior changes only
- browser/Playwright verification for static/UI/public-page changes only
  - verify `/`, `/quote`, `/admin`, and `/admin/mobile` at desktop and mobile widths
  - fail on overflow, weak CTA visibility, internal-language leakage, broken responsive layout, or oversized assets
  - do not assume Vercel deployment behavior; Bay Delivery deploys on Render
- codex-security:security-diff-scan for admin, auth, CSP, public-exposure, docs exposure, headers, origin/CORS/CSP, and customer-path boundary changes only
```

---

## Copy/Paste Codex Prompt

```text
Reasoning: [Low / Medium / High / Very High]

Task:
[One-sentence task title]

Repo:
C:\Repos\Bay-Delivery-Quote-Copilot

Context:
[Explain current baseline, latest merged PR, and why this task exists.]

Primary repo safety skill:
- .agents/skills/bay-delivery-pr-safety-review/SKILL.md is the main Bay Delivery source of truth.
- Keep this prompt concise and follow the skill for protected surfaces, stop conditions, and report discipline.

Goal:
[Define the exact desired outcome.]

Current baseline:
- Current version: [inspect repo: Get-Content VERSION or cat VERSION]
- Latest merged PR: [inspect repo: git log --oneline -5]
- Latest main commit: [inspect repo: git log --oneline -1]
- Production impact expected: [none / local-only / admin-only / customer flow / Render]

Business rules:
- One pricing engine only: app/quote_engine.py.
- Do not create duplicate pricing logic.
- Cash quotes do not include HST.
- EMT/e-transfer quotes add 13% HST.
- Currency is CAD.
- GPT is recommendation-only and must not override pricing.
- SQLite is source of truth.
- Google Calendar is mirror/convenience only.
- Admin is internal operations only.
- Keep scope narrow and reversible.
- Protect margin over winning bad jobs.

Scope rules:
- Plan first.
- Implement only if the plan stays inside this prompt.
- Do not make unrelated edits.
- Do not change pricing logic unless this task explicitly says to.
- Do not change quote payload behaviour unless required and explained.
- Do not touch production data.
- Stop and report if protected files must be touched unexpectedly.

Codex Fix Button guardrails:
- Review context/Fix button is allowed to load reviewer feedback.
- It is not permission to auto-commit or auto-push.
- Pre-commit reviewer simulation is still required before commit.
- Pricing-sensitive fixes still require pricing red-team review before commit.
- Do not broaden scope just because review comments mention deferred follow-up areas.

Expected files to change:
- [file 1]
- [file 2]

Protected no-go files unless explicitly required:
- app/quote_engine.py
- app/services/quote_service.py
- app/storage.py
- config/business_profile.json
- render.yaml
- .github/workflows/
- docs/gpt/
- requirements.txt
- requirements.lock.txt
- static/admin_mobile.html
- static/admin_mobile.js

Note: `dist/gpt_grounding_pack/` is a generated export artifact and is tracked when intentionally refreshed for GPT Builder upload parity.
For PRs that edit `docs/gpt/*` or another grounding-pack source, regenerate and stage the matching `dist/gpt_grounding_pack/` output. For unrelated PRs, leave it untouched unless explicitly scoped.

Implementation requirements:
1. Inspect relevant files first.
2. State the implementation plan.
3. Implement the smallest safe change.
4. Add or update focused tests.
5. Preserve existing behaviours unless this task explicitly changes them.
6. Keep output/user experience readable and practical.

Validation:
Default local checks (always run):

cd C:\Repos\Bay-Delivery-Quote-Copilot

git status -sb
git diff --check
.\.venv\Scripts\python.exe tools\check_version_parity.py
.\.venv\Scripts\python.exe -m compileall app tools scripts tests
.\.venv\Scripts\python.exe -m pytest -q

Conditional checks (run only when relevant to this task):

# GPT grounding parity — only meaningful after exporting the grounding pack first:
#   .\.venv\Scripts\python.exe tools\export_gpt_grounding_pack.py --output-dir dist\gpt_grounding_pack
#   .\.venv\Scripts\python.exe tools\check_gpt_grounding_pack_parity.py

# Dependency audit — pip-audit is CI-only; not installed locally by default.
# If needed locally, install first:
#   .\.venv\Scripts\python.exe -m pip install pip-audit==2.10.0
#   pip-audit -r requirements.lock.txt
# CI runs this automatically on every push/PR via .github/workflows/ci.yml.

Additional focused validation:
[Add task-specific commands here, e.g., a specific test module or calibration script.]

Pre-commit reviewer simulation:
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
- add/update focused tests if applicable
- rerun validation
- rerun protected no-go diff

Pricing red-team review before commit:
Required when touching:
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
- access/location wording that must not become target
- plural/singular variants
- verb variants
- substring traps
- old acceptance examples
- non-demolition baseline
- customer-facing response shape
- cash/EMT/HST totals

Near-miss examples:
- deck access is not deck demolition
- fence access is not fence demolition
- wall-to-wall carpet is not wall demolition
- drywall is not wall
- waterproofing/proofing is not roofing
- wall panel is not electrical panel
- utility room is not utility-line risk
- yard cleanup alone is not heavy mixed debris

Protected no-go diff:
git diff main...HEAD -- app/quote_engine.py app/services/quote_service.py config/business_profile.json render.yaml .github/workflows docs/gpt requirements.txt requirements.lock.txt static/admin_mobile.html static/admin_mobile.js

Branch:
[branch/name]

Commit headline:
[imperative short title]

Commit description:
[Explain what changed, why, and what was intentionally not changed.]

PR title:
[create/fix/update task title]

PR description should include:
- Summary
- Why
- Scope
- Files changed
- Validation
- Risk
- What was not changed

Final report must include:
- Plan summary
- Files changed
- Exact commands run
- Validation results
- Protected no-go diff result
- Pre-commit reviewer simulation results
- Pricing red-team review results when applicable
- P1/P2/P3 self-review
- Commit hash
- PR link
- Confirmation PR opened but not merged unless explicitly requested

STOP after opening/updating the PR and providing the final report.
```

---

## Reasoning Level Guide

- **Low:** tiny read-only checks.
- **Medium:** narrow docs, tests, static UI, non-risky config, local scripts.
- **High:** pricing-adjacent analysis, schema/storage, auth/security, workflows, Render, GPT grounding, complex bugs.
- **Very High:** actual pricing engine changes, production emergency, major architecture, repeated failures.

---

## Common Branch Naming

```text
codex/<task-name>
fix/<bug-name>
docs/<docs-task>
```

For Bay Delivery, prefer:

```text
codex/<specific-task-name>
```

---

## Commit Headline Examples

```text
create price calibration market equipment targets
fix seed script direct execution import path
create local simulated job costing data
update admin job costing usability
```

---

## PR Review Checklist

Before merge, confirm:

- Only expected files changed.
- Protected files untouched unless explicitly approved.
- Tests pass.
- Version parity passes.
- GPT grounding parity passes.
- No pricing drift unless this is a pricing PR.
- No second pricing path.
- No production data mutation.
- Customer flow unchanged unless intended.
- Admin/mobile unaffected unless intended.
- README/docs match actual commands.
- Pre-commit reviewer simulation was run on the actual diff.
- Pricing red-team review was run before commit when pricing-sensitive.

```
