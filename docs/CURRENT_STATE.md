# Current State

This document is the authoritative current system status summary referenced by `README.md`.

Last reviewed: 2026-04-16

For GPT grounding precedence and companion detail, use `docs/gpt/GPT_SOURCE_OF_TRUTH.md` and the maintained grounding pack in `docs/gpt/`.

## Project Status

- Bay Delivery Quote Copilot is stable and production-usable.
- Current work is focused on hardening, controlled expansion, operational clarity, reliability, and narrow, auditable refinements rather than broad feature expansion.
- When system state is unclear, verify against `PROJECT_RULES.md`, `docs/gpt/`, `README.md`, and current repository code instead of relying on memory or undocumented assumptions.

## Current Operating Phase

- The project is production-usable and stable, in hardening / controlled-expansion / operational-confidence mode.
- The goal is to preserve alignment between repository truth, current documented workflow, and maintained GPT grounding.
- Documentation should describe current documented system state conservatively and should not present unverified live behavior as guaranteed fact.

## Locked Business Rules

- There is one pricing engine only: `app/quote_engine.py`.
- GPT may describe repo-approved rules and workflows, but it must not invent, override, or bypass pricing behavior.
- Cash quotes are tax-free.
- EMT / e-transfer quotes add 13% HST.
- A universal $60 CAD minimum floor is enforced in pricing authority.

## Customer-Facing Reality

- Customers continue to use the live Render customer quote flow at `/` and `/quote`.
- Customer-facing quote behavior remains the live quote flow, not GPT.
- Admin surfaces support operations and review; they are not customer quote intake surfaces.

## Architecture Boundaries

- SQLite is the source of truth.
- Google Calendar is a mirror only.
- Customers use `/` and `/quote`.
- Admin surfaces (`/admin`, `/admin/mobile`, `/admin/uploads`) are operations tools, not customer quote intake surfaces.
- Route handlers must remain thin orchestration layers.
- Business logic belongs in `app/services/`, SQL and persistence logic belong in `app/storage/`, and external API wrappers belong in `app/integrations/`.

## Internal GPT Boundary

- The Bay Delivery GPT is internal-only for Austin + Dan.
- GPT grounding exists to keep outputs aligned to repository truth, project rules, and current operating boundaries.
- GPT may explain, summarize, and guide process, but it must not override repo pricing logic, workflow state, auth, token, or persistence rules.

## Recent Completed Hardening

- C1.5a internal quote risk scoring is complete.
- Internal quote artifacts now include `confidence_level` and `risk_flags`.
- The assessment is internal-only, artifact-pipeline-only, and is not customer-facing or persisted.
- Haul-away risk scoring only counts supported `bag_type` and `trailer_fill_estimate` values; unsupported raw strings are ignored so they do not inflate confidence.
- `python-multipart` is now pinned to `0.0.26`, closing the related CI/security unblock that shipped with PR #197.

## Workflow Expectations

- Plan first.
- Implementation second.
- Review PR before merge.
- Merge, deploy, and smoke-verify.
- Documentation tasks stay documentation-only unless tiny link or index cleanup is clearly necessary.
- Keep changes narrow, reversible, and task-scoped.

## What Is Complete

- Live customer quote flow is established on Render (`/` and `/quote`).
- Single pricing authority is established in `app/quote_engine.py` with config-backed service rules.
- Admin operations surfaces exist with protected admin actions.
- Quote-request and job lifecycle foundations are implemented and persisted in SQLite.
- Security, abuse controls, and deployment notes are documented and in active use.
- Internal quote risk scoring is implemented in the artifact pipeline without changing pricing, API, UI, DB, or booking behavior.

## Active Docs Map

- `PROJECT_RULES.md`: architecture invariants, security rules, pricing and business guardrails, and change-scope rules
- `docs/gpt/GPT_SOURCE_OF_TRUTH.md`: GPT grounding precedence
- `docs/gpt/GPT_CURRENT_STATE.md`: GPT-oriented current-state summary
- `docs/gpt/GPT_BUSINESS_RULES.md`: maintained business-rule grounding
- `docs/gpt/GPT_SYSTEM_BOUNDARIES.md`: system-boundary grounding
- `docs/gpt/GPT_WORKFLOW_RULES.md`: repo-safe GPT working method
- `README.md`: operator-facing overview, release markers, and canonical reference links

## Current Priorities

- Keep repository behavior aligned with docs and deployment reality.
- Prevent memory drift and undocumented assumptions.
- Make narrow, auditable refinements only.
- Preserve one-pricing-engine discipline.
- Maintain clear customer/admin operational boundaries.

## Drift-Control Rules

- When current state is ambiguous, verify against `PROJECT_RULES.md`, `docs/gpt/`, `README.md`, and current repository code instead of guessing.
- Do not create a parallel GPT grounding source outside `docs/gpt/`.
- Do not invent undocumented assumptions or undocumented capabilities.
- Keep documentation aligned to current documented workflow and repo-approved behavior.

## What Should Not Happen Next

- No second pricing engine.
- No customer-facing GPT pricing path.
- No broad speculative architecture work.
- No unnecessary flow rewrites in stable areas.
- No mixing unrelated runtime changes into documentation work.
