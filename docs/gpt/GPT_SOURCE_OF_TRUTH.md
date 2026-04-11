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

## Grounding Precedence

1. `PROJECT_RULES.md`
2. `docs/gpt/GPT_SOURCE_OF_TRUTH.md` and companion docs in `docs/gpt/`
3. `docs/CURRENT_STATE.md`
4. `README.md`
5. `docs/MARKET_AND_PRICING_STRATEGY.md`
6. Verified repository code (`app/main.py`, `app/quote_engine.py`, `app/storage.py`, `app/services/*`, `app/storage/*`)

## Required GPT Behavior

- Keep recommendations narrow, reversible, and repo-aligned.
- Preserve customer/admin boundary separation.
- Preserve DB-first operational truth.
- Preserve one-pricing-engine policy.
- Escalate ambiguity rather than guessing.

## Grounding Workflow Artifacts

The following documents operationalize the grounding refresh cycle:

| Document | Purpose |
|----------|---------|
| `docs/gpt/GPT_KNOWLEDGE_PACK.md` | Canonical upload-set reference — defines exactly which files to upload to GPT Builder |
| `docs/gpt/GPT_BUILDER_INSTRUCTIONS.md` | Copy-paste Builder instruction block |
| `docs/gpt/GPT_REFRESH_WORKFLOW.md` | Manual-on-release refresh runbook |
| `docs/gpt/GPT_ACCEPTANCE_TESTS.md` | Fixed acceptance question set for verifying a fresh grounding |
| `tools/export_gpt_grounding_pack.py` | Export script — generates the local upload pack with manifest |

Refresh grounding on every release that changes `PROJECT_RULES.md`, any file in `docs/gpt/`, `docs/CURRENT_STATE.md`, or pricing rules in `app/quote_engine.py` / `config/business_profile.json`.
