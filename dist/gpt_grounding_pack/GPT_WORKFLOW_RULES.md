# GPT Workflow Rules

This file defines the expected working method for repo-safe GPT-assisted work.

## Working Sequence

1. Plan first.
2. Implementation second.
3. Review PR before merge.
4. Merge, deploy, and smoke-verify.

## Scope Control

- Keep changes narrow, reversible, and task-scoped.
- Prefer minimal diffs.
- Do not mix unrelated concerns in one pass.
- Stop and call out scope drift before implementation.

## Change-Type Rules

- Documentation tasks stay documentation-only unless tiny link/index cleanup is clearly necessary.
- Runtime, pricing, auth, schema, and workflow behavior changes require explicit approval and separate scope.

## Edit Mechanics Rule

- In chat-driven implementation mode, full-file replacements are acceptable when code is explicitly requested in chat.
- Do not depend on brittle specific-line edit instructions as the primary workflow contract.

## Guardrails to Preserve

- One pricing engine only.
- Admin/customer boundary separation.
- DB-first operational truth.
- Security and token protections fail closed.

## PR Discipline

- Keep commits focused.
- Use clear PR summaries: what changed, what did not change, and risk check.
- Confirm behavior scope is unchanged when work is docs-only.
