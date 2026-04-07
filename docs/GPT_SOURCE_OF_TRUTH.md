# GPT Source of Truth

> Compatibility note: the focused grounding pack now lives under `docs/gpt/`.
>
> Start with `docs/gpt/GPT_SOURCE_OF_TRUTH.md`, then use the companion files in that folder for business rules, system boundaries, workflow rules, and current state.

This document defines how GPT assistance should ground to the current repository state.

## Purpose

Use this file to avoid stale chat-memory assumptions and broad, noisy repo scanning. GPT guidance should prioritize the authoritative files listed below.

## Primary Truth Files (in order)

1. `PROJECT_RULES.md` for architecture, security, pricing-change constraints, and scope guardrails.
2. `docs/CURRENT_STATE.md` for current phase, operating boundaries, and active priorities.
3. `README.md` for operator-facing usage, route-level behavior notes, and practical run context.
4. `DEPLOYMENT_NOTES.md` for deployment/runtime parity, env handling, and production verification.

If there is a conflict, follow this precedence order unless maintainers explicitly approve an exception.

## Current Project Phase

The project is stable and production-usable, in refinement and launch-readiness mode, with drift prevention and operational reliability prioritized over feature sprawl.

## Required Grounding Rules for GPT

### One pricing engine rule

Treat `app/quote_engine.py` as the pricing authority. Do not propose or imply a second pricing engine.

### Admin vs customer boundaries

- Customer quoting is the public flow (`/` and `/quote`).
- Admin surfaces (`/admin`, `/admin/mobile`, `/admin/uploads`) are internal operations tools.
- GPT should not conflate admin operations with customer quote intake.

### Screenshot assistant boundary

Screenshot assistant behavior is recommendation-only guidance for internal admin review. It is not autonomous quote truth and does not override pricing authority.

### Jobs as operational anchor

Operational lifecycle should remain job-centered (approvals, scheduling, execution state), with database-first persistence and external mirrors following repo state.

## What GPT Should Not Assume

- Do not assume archived handoff or audit docs represent current main behavior.
- Do not assume broad refactors are desired when narrow fixes satisfy the goal.
- Do not assume deployment behavior from memory; verify against current docs and code paths.
- Do not assume customer-facing AI exposure or AI-only pricing workflows.

## Changes Requiring Explicit Approval

Require explicit maintainer approval before proposing or implementing:

- pricing policy shifts or broad repricing
- schema-tightening or compatibility-breaking API changes
- auth/token/security model changes
- workflow changes that alter customer/admin boundaries
- deployment-impacting config and environment behavior
- large refactors that exceed narrow, task-scoped edits

## Recommended Workflow

1. Plan first: read authoritative docs, confirm scope, and state the minimal change path.
2. Implement second: make narrow edits aligned to the approved plan.
3. Validate: confirm internal doc consistency and behavior-scope boundaries.

## Maintenance Rule

When project direction materially changes, update `docs/CURRENT_STATE.md` first, then update this grounding file if precedence, boundaries, or guardrails changed.
