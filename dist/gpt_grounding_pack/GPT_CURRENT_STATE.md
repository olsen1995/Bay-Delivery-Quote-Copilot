# GPT Current State

## Status Snapshot

Bay Delivery Quote Copilot is stable and production-usable.

The project is in a hardening / controlled-expansion phase focused on drift prevention, operational clarity, and reliability rather than broad feature expansion.

## What Is Already Complete

- Live customer quote flow is established on Render (`/` + `/quote`).
- Single pricing authority is established in `app/quote_engine.py` with config-backed service rules.
- Pricing authority enforces a universal $60 CAD minimum floor on final quote outputs.
- Admin operations surfaces exist (`/admin`, `/admin/mobile`, `/admin/uploads`) with protected admin actions.
- Desktop admin now includes a read-only Daily Ops Queue backed by `GET /admin/api/ops-queue`.
- Quote-request and job lifecycle foundations are implemented and persisted in SQLite.
- Security, abuse controls, and deployment notes are documented and in active use.
- Internal quote risk scoring now exists in the quote artifact pipeline and exposes internal `confidence_level` / `risk_flags` metadata while feeding a narrow pricing-engine margin-protection layer that preserves the customer-facing response shape.

## Current Priorities

- Keep repo behavior aligned with docs and deployment reality.
- Prevent memory drift and undocumented assumptions.
- Make narrow, auditable refinements only.
- Preserve margin-protection direction and one-pricing-engine discipline.
- Maintain clear customer/admin operational boundaries.
- Keep internal risk assessment downstream to pricing authority and limited to narrow repo-approved margin protection inside `app/quote_engine.py`.
- Treat Daily Ops Queue items as admin attention flags only; use existing admin surfaces for any manual follow-up.

## What Should Not Happen Next

- No second pricing engine.
- No customer-facing GPT pricing path.
- No broad speculative architecture work.
- No unnecessary flow rewrites in stable areas.
- No mixing unrelated runtime changes into documentation tasks.
- No GPT or Daily Ops Queue actions that approve, reject, expire, schedule, contact, price, message, or mutate records.

## GPT Grounding Goal

GPT grounding is an internal alignment goal for Austin + Dan.

It is not a customer-facing product behavior change.

The purpose is to improve consistency and reduce drift while preserving existing production flows.

Pricing authority remains unchanged in `app/quote_engine.py`.

An internal-only `POST /api/gpt/quote` endpoint now exists as a non-persistent interface into that pricing authority.

When the endpoint is available, GPT should use its returned totals rather than inventing totals or generating independent pricing.

This internal endpoint does not replace the customer quote flow, booking flow, or live Render customer path, and it is not a customer-facing quote route.

## Daily Ops Queue Grounding

The desktop admin Daily Ops Queue is a read-only operations attention list.

- Endpoint: `GET /admin/api/ops-queue`.
- Access: admin-auth required.
- Surface: desktop `/admin` only; it is not part of mobile admin.
- Loading: best-effort frontend loading so core admin data remains usable if the queue fails.
- Data source: targeted read-only SQLite queries through the existing `app/storage.py` implementation path.
- Sections: accepted requests needing approval, follow-up marked / needs attention, completed jobs missing costing, jobs missing schedule, jobs missing booking preferences, and stale pending estimates.

For "What should I do today?" style questions, GPT should tell Austin/Dan to check the Daily Ops Queue first, then use the existing admin sections for manual review and follow-up.

The queue does not approve, reject, expire, schedule, contact, price, message, send, or mutate records. It only shows attention flags from existing admin data.

## Conservative Truth Rule

When current state is ambiguous, use conservative wording and verify against repository truth instead of guessing.
