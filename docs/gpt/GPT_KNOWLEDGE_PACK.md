# GPT Knowledge Pack – Bay Delivery Quote Copilot

## Purpose

This document defines the canonical upload set for the Bay Delivery internal advisor GPT grounding workflow.

When refreshing GPT Builder knowledge, upload exactly the files listed in the **Upload Set** below — no more, no less.

---

## Upload Set

The following files form the complete grounding pack for a GPT Builder refresh:

| File                                   | Purpose                                                           |
| -------------------------------------- | ----------------------------------------------------------------- |
| `docs/gpt/GPT_SOURCE_OF_TRUTH.md`      | Authority rules, grounding precedence, pricing authority rule     |
| `docs/gpt/GPT_BUSINESS_RULES.md`       | Pricing, tax, travel, labour, and disposal rules                  |
| `docs/gpt/GPT_CURRENT_STATE.md`        | Current system status, what is complete, and what must not happen |
| `docs/gpt/GPT_SYSTEM_BOUNDARIES.md`    | Architectural and operational boundaries                          |
| `docs/gpt/GPT_WORKFLOW_RULES.md`       | Expected working method, scope control, change-type rules         |
| `docs/gpt/GPT_BUILDER_INSTRUCTIONS.md` | Builder-ready system instruction block                            |
| `docs/gpt/GPT_ACCEPTANCE_TESTS.md`     | Fixed acceptance question set for verifying a fresh grounding     |
| `PROJECT_RULES.md`                     | Core repo rules (structural changes, pricing, admin, booking)     |
| `docs/CURRENT_STATE.md`                | Live authoritative system status                                  |

> **Upload only** the exported `.md` files from `dist/gpt_grounding_pack/`. Do **not** upload `tools/export_gpt_grounding_pack.py` or `manifest.json` — those are local helpers only.

---

## Export Script

Use `tools/export_gpt_grounding_pack.py` to generate a local copy of the upload set with a manifest:

```bash
python tools/export_gpt_grounding_pack.py --output-dir dist/gpt_grounding_pack
```

The script copies the exact files listed above into the output directory and writes `manifest.json` with SHA-256 hashes for auditability.

---

## Refresh Trigger

Refresh GPT grounding on every release that changes any of the following:

- `PROJECT_RULES.md`
- Any file in `docs/gpt/`
- `docs/CURRENT_STATE.md`
- Pricing rules in `app/quote_engine.py` or `config/business_profile.json`

See `docs/gpt/GPT_REFRESH_WORKFLOW.md` for the full refresh runbook.

---

## Scope Rule

This grounding pack grounds an **internal advisor GPT only**.

- The GPT is internal-only for Austin + Dan.
- Customers continue to use the live Render quote flow (`/` and `/quote`).
- The GPT must not act as a second pricing engine.
- Pricing authority remains in `app/quote_engine.py`.
