---
name: bay-delivery-github-render-readiness-audit
description: Use for read-only Bay Delivery GitHub and Render readiness audits before or after important merges, deployments, smoke checks, and launch-readiness reviews. This skill reports readiness status, protected-surface risk, and exact next steps without making fixes or production changes.
---

# Bay Delivery GitHub + Render Readiness Audit Skill

Use this skill for read-only readiness audits in the Bay Delivery Quote Copilot repository.

This skill is report-only. It does not implement fixes, mutate production, or change repository state.

## Purpose

This is a read-only readiness audit skill for Bay Delivery GitHub + Render operation.

Use it to assess whether the current GitHub, workflow, and deployment state is ready for merge, launch, smoke review, or follow-up.

## When to Use

Use this skill when Austin asks:
- is this safe to launch?
- check GitHub/Render readiness
- post-merge verify
- deployment readiness check
- deploy drift check
- production smoke review
- before/after important merge
- are checks healthy?
- is Render aligned with GitHub?

## When Not to Use

Do not use this skill for:
- implementing fixes
- pricing changes
- `app/quote_engine.py` changes
- storage/schema changes
- Render setting changes
- workflow edits
- dependency upgrades
- live admin/quote mutation
- production cleanup
- broad architecture changes

## Hard Read-Only Rules

During audit use, forbid:
- file edits
- branch creation
- commits
- pushes
- PR creation
- merging
- resolving review threads
- workflow dispatch unless Austin separately approves it
- Render setting changes
- Render deploys
- production mutations
- quote submissions
- admin mutations
- SQLite or `app/data` writes
- dependency installs
- config edits
- live endpoint calls unless Austin explicitly approves live-safe GET-only checks

If the audit reveals problems, report them. Do not fix them automatically.

## Standard Audit Checklist

Use this checklist unless Austin narrows scope:
- `git status --short --branch`
- `git log --oneline -10`
- `gh pr status`
- `gh pr list`
- review recent merged PRs relevant to the current readiness question
- `gh run list --limit 10`
- review failed or pending checks
- inspect `.github/workflows` inventory
- inspect `render.yaml` read-only
- inspect deployment docs read-only
- inspect `production_live_safe_smoke.yml` status if present
- review protected surfaces for unexpected changes or drift
- only if Austin explicitly approves live-safe GETs, check `/health` version and commit parity

## Protected Surfaces

Treat these as protected during readiness audits:
- `app/quote_engine.py`
- `app/storage.py`
- `app/services/`
- `app/data`
- `render.yaml`
- `.github/workflows`
- `requirements.txt`
- `requirements.lock.txt`
- `VERSION`
- `docs/gpt`
- `dist/gpt_grounding_pack`
- static customer and admin assets
- `.codex/config.toml`

If these changed unexpectedly, report the exact path and treat it as a readiness concern.

## Approved Live-Safe Checks

Live GET checks are optional and require explicit Austin approval first.

Allowed only if approved:
- `GET /health`
- `GET /`
- `GET /quote`
- `GET /admin` pre-auth shell only
- `GET /admin/mobile` pre-auth shell only

Forbid:
- POST requests
- quote submissions
- admin mutations
- shared-secret login attempts
- Render deploy triggers
- workflow dispatch unless separately approved

Without explicit approval, do not call live production endpoints.

## Output Format

Start every audit report with:

`Recommendation: Ready / Not ready / Needs follow-up`

Then include:
- Current setup observed
- GitHub status
- Render/deployment status
- Workflow/check status
- Smoke/live-safe status if approved
- Protected-surface review
- P1 blockers
- P2 risks
- P3 notes
- Exact next step

## P1/P2/P3 Definitions

- P1 = must fix before launch, merge, or deploy.
- P2 = should fix before launch, merge, or deploy unless explicitly accepted.
- P3 = non-blocking note or improvement.

## Stop Conditions

Stop and report instead of stretching the audit if:
- the worktree is dirty with unrelated active work
- the branch is unexpected
- GitHub context is unavailable
- Render context would require mutation
- a live endpoint check was not explicitly approved
- checks are failing or pending and Austin asked for a ready/not-ready call
- protected files changed unexpectedly
- production mutation would be needed
- the fix would require code changes
- the audit cannot distinguish local state from deployed state
