# GPT Current State

## Status Snapshot

Bay Delivery Quote Copilot is stable and production-usable.

The project is in a hardening / controlled-expansion phase focused on drift prevention, operational clarity, and reliability.

## What Is Already Complete

- Live customer quote flow exists (`/` and `/quote`)
- Single pricing authority exists in `app/quote_engine.py`
- Universal $60 CAD minimum enforced
- Admin surfaces implemented (`/admin`, `/admin/mobile`, `/admin/uploads`)
- Quote lifecycle persists in SQLite
- Security and abuse controls active
- Risk scoring integrated into quote artifacts

## GPT Quote Endpoint (NEW)

- Internal endpoint: `/api/gpt/quote`
- Token-protected (`GPT_INTERNAL_API_TOKEN`)
- Non-persistent (does NOT create quotes or DB entries)
- Uses `build_quote_artifacts()` and pricing engine
- Returns authoritative totals

### Purpose

- Allow GPT to access real pricing engine safely
- Avoid creating a second pricing system
- Keep GPT aligned with repo truth

### Behavior

- GPT should use endpoint for pricing when available
- GPT still provides reasoning and risk analysis
- GPT does NOT replace booking or quote flows

## Current Priorities

- Maintain repo and docs alignment
- Prevent GPT drift
- Keep one pricing engine
- Maintain margin protection
- Keep customer/admin separation clean

## What Should Not Happen

- No second pricing engine
- No customer-facing GPT pricing
- No persistence from GPT endpoint
- No workflow overrides
- No speculative architecture

## GPT Grounding Goal

GPT is an internal advisor layer.

- It improves consistency
- It reduces drift
- It does NOT replace backend logic

## Conservative Truth Rule

When uncertain:

- Verify against repo
- Do not guess
- Use conservative wording
