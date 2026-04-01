# Bay Delivery Quote Copilot — Current State

## Purpose / Authority
This document is the single authoritative current-state source of truth for Bay Delivery Quote Copilot.

## Project Status
- Stable and production-usable
- In refinement / cleanup / launch-readiness mode
- Focused on drift prevention, cleanup, validation, and margin protection
- Not in feature-sprawl mode

## Customer-Facing Reality
- Customers use the Render homepage and quote flow only
- `/` = homepage
- `/quote` = structured quote + accept/decline + booking flow
- `/admin` = internal admin only

## Internal GPT Boundary
- Bay Delivery Assistant GPT is internal-only
- For Austin and Dan only
- Not customer-facing
- GPT does not override pricing logic

## Non-Negotiable Rules
- One pricing source of truth only (`quote_engine.py`)
- No second pricing engine
- Screenshot assistant is recommendation-only
- Jobs are the operations anchor
- DB-first
- Margin protection beats optimistic quoting
- No Facebook-post workflow inside customer quote flow

## Current Priorities
- Docs drift prevention
- Repo/Render alignment
- Real-world validation
- Narrow cleanup only

## What We Are Not Doing
- No second pricing engine
- No AI-only pricing
- No exposing GPT to customers
- No large speculative UI rewrites
- No unnecessary feature expansion

## Development Workflow
- Plan mode first
- Review
- Implementation
- PR review
- Merge
- Live smoke

## Active Docs Map
- `README.md` = entry point
- `docs/CURRENT_STATE.md` = canonical state doc
- `docs/MARKET_AND_PRICING_STRATEGY.md` = pricing/strategy guardrails
- `docs/DEMO_CHECKLIST.md` = operational validation checklist
- `docs/handoffs/BAY_DELIVERY_CHAT_HANDOFF_TEMPLATE.md` = reusable template, not source of truth
- `docs/archive/*` = historical only

## Drift-Control Rules
- Update `docs/CURRENT_STATE.md` when project direction materially changes
- Archive dated handoffs/audits instead of deleting
- Keep README pointer short; keep detailed truth in `docs/CURRENT_STATE.md`

## Last Reviewed
2026-04-01
