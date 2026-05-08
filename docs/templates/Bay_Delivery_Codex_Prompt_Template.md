# Bay Delivery Codex Prompt Template

Use this template for Bay Delivery repo tasks.

Default workflow:

```text
Plan -> Implement -> Validate -> Branch -> PR -> Summarize -> STOP
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

Note: dist/gpt_grounding_pack/ is a generated export artifact (not committed to the repo).
Do not list it as a protected committed path or include it in protected-diff commands.

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
- Commit hash
- PR link
- Whether safe to merge

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

```
