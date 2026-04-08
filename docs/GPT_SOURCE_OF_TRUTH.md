# GPT Source of Truth

This document defines the authoritative grounding layer for the Bay Delivery Quote Assistant.

## Authority Order

1. quote_engine (repo pricing logic)
2. Approved grounding docs
3. Workflow rules
4. Everything else

If conflict exists:

- repo pricing wins
- GPT must NOT override pricing logic

## Non-Negotiables

- One pricing engine only
- No second pricing system
- No undocumented assumptions
- GPT is internal only
