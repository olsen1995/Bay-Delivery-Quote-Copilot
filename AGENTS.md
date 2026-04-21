# Bay Delivery Quote Copilot - Codex Operating Rules

## Purpose / Source of Truth

- Plan first, then implement.
- Inspect repo truth before changing anything.
- Verify against `PROJECT_RULES.md`, `docs/gpt/GPT_CURRENT_STATE.md`, `docs/gpt/`, `README.md`, verified repo code, and CI logs when docs are ambiguous.
- Do not guess or invent business rules, workflow rules, or undocumented behavior.

## Workflow

- Keep changes narrow, task-focused, and reversible.
- Prefer the smallest correct fix over broad cleanup or refactors.
- Reuse existing helpers, patterns, and source-of-truth logic instead of duplicating behavior.
- Diagnose root cause before fixing issues; if CI fails, inspect the logs before applying any fix.
- Documentation tasks stay documentation-only unless a tiny consistency tweak is clearly required.

## Scope Boundaries

- There is one pricing engine only: `app/quote_engine.py`.
- Admin surfaces (`/admin`, `/admin/mobile`, `/admin/uploads`) are ops-only, not customer quote intake.
- GPT is internal-only for Austin + Dan; it is not a customer-facing pricing path.
- Do not change pricing logic, auth, quote behavior, customer-facing flows, or architecture unless explicitly requested.
- Do not mix unrelated pricing, runtime, UI, schema, dependency, or workflow changes into a narrow task.

## Validation

- Run validation after changes.
- Default validation for repo tasks:
  - `python tools/check_version_parity.py`
  - `pytest -q`
- If validation fails, separate failures caused by your change from pre-existing environment or unrelated issues.

## PR / Reporting

- Keep PRs narrow and auditable.
- Report exact changed files and validation results.
- State clearly when runtime behavior is unchanged for docs-only work.
- Create the PR and stop.
