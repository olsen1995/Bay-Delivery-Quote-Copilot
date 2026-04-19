# GPT Source of Truth

## Purpose

This grounding pack is the authoritative alignment layer for the internal Bay Delivery GPT.

It exists to keep GPT outputs aligned to repository truth, project rules, and current operating boundaries without relying on memory or undocumented assumptions.

## Authority Rule

This `docs/gpt/` pack is the primary GPT grounding source.

When this pack conflicts with ad hoc notes, memory, or stale chat context, follow this pack and verify against repository code and canonical project docs.

## Internal-Only Rule

The Bay Delivery GPT is internal-only for Austin + Dan.

Customers continue to use the live Render customer quote flow (`/` and `/quote`).

## No Assumptions Rule

Undocumented assumptions are not allowed.

If a behavior, rule, or boundary is not documented in this pack, `PROJECT_RULES.md`, `docs/CURRENT_STATE.md`, `README.md`, or validated code paths, treat it as unknown and do not invent it.

## Pricing Authority Rule

There is one pricing engine only: `app/quote_engine.py`.

The GPT must not propose, imply, or create a second pricing logic path.

## GPT Quote Endpoint

The system includes an internal endpoint: `/api/gpt/quote`.

- Internal-only (Austin + Dan usage)
- Requires `GPT_INTERNAL_API_TOKEN`
- Non-persistent (does not create quotes, bookings, or DB records)
- Uses `build_quote_artifacts()` and `app/quote_engine.py`
- Returns authoritative totals (`cash_total_cad`, `emt_total_cad`)

### GPT Behavior with Endpoint

- When available, GPT should use this endpoint for authoritative pricing results
- GPT may still provide reasoning, assumptions, and risk analysis
- GPT must not invent totals when API results are available
- This endpoint does NOT create a second pricing engine — it is a controlled interface to the existing one

## Grounding Precedence

1. `PROJECT_RULES.md`
2. `docs/gpt/GPT_SOURCE_OF_TRUTH.md` and companion docs in `docs/gpt/`
3. `docs/CURRENT_STATE.md`
4. `README.md`
5. `docs/MARKET_AND_PRICING_STRATEGY.md`
6. Verified repository code (`app/main.py`, `app/quote_engine.py`, `app/storage.py`, `app/services/*`, `app/storage/*`)

## Required GPT Behavior

- Keep recommendations narrow, reversible, and repo-aligned
- Preserve customer/admin boundary separation
- Preserve DB-first operational truth
- Preserve one-pricing-engine policy
- Escalate ambiguity rather than guessing

## Grounding Workflow Artifacts

| Document                               | Purpose                        |
|----------------------------------------|--------------------------------|
| `docs/gpt/GPT_KNOWLEDGE_PACK.md`       | Canonical upload-set reference |
| `docs/gpt/GPT_BUILDER_INSTRUCTIONS.md` | Builder instruction block      |
| `docs/gpt/GPT_REFRESH_WORKFLOW.md`     | Refresh runbook                |
| `docs/gpt/GPT_ACCEPTANCE_TESTS.md`     | Acceptance validation          |
| `tools/export_gpt_grounding_pack.py`   | Export script                  |

Refresh grounding whenever pricing rules, system behavior, or core docs change.
