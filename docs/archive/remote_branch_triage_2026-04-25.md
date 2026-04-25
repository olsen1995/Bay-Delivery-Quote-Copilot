# Remote Branch Triage - 2026-04-25

Context: after PR #222 merged and stale merged branches were cleaned up, the remaining old remote branches were triaged before deletion.

Future tasks to preserve:
- Quote duplicate-submit guard: `feature/prevent-duplicate-quote-submissions` shows a still-useful idea. Implement from current `main`, not by reviving the branch. Keep scope frontend-only: prevent duplicate `/quote/calculate` submits while a quote calculation is in flight, with focused static/browser coverage.
- Optional admin mobile smoke resilience: `chore/post-157-audit-hardening` suggests making mobile admin smoke assertions less brittle. Only revisit if copy churn causes false failures, and preserve the current ops-only/no quote-authoring boundary.

Covered or stale branches safe to delete:
- Abuse/rate-limit branches are superseded by current `app/abuse_controls.py`, tests, and unicode guard tooling.
- GPT grounding workflow branch is superseded by current `docs/gpt/` and `tools/export_gpt_grounding_pack.py`.
- Security headers branch is superseded by current `SecurityHeadersMiddleware`.
- Strict quote_request status branch is superseded by current 409/detail transition handling.
- Mobile new-draft branch is stale because current mobile admin is ops-only and should not regain quote authoring.
