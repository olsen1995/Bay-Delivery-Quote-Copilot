# Instruction Hierarchy

Use this when Bay Delivery repo instructions, templates, skills, memory notes, or current-state docs appear to conflict.

## Authority Order

1. Current explicit user task instructions for the active PR or audit.
2. Repo safety rules in `AGENTS.md`, `PROJECT_RULES.md`, and this hierarchy file.
3. Verified source code and source-of-truth runtime boundaries.
4. Current-state and roadmap docs in `docs/`.
5. Agent templates, repo skills, prior memory, and archived notes.

## Source-Of-Truth Boundaries

- Pricing authority is `app/quote_engine.py` only.
- Persisted operational data authority is SQLite through the app storage layer.
- Backend behavior is the source of truth for public quote and admin runtime behavior.
- Google Calendar is a mirror/convenience layer only.
- GPT/internal assistant behavior is advisory, internal-only, and never customer-facing pricing authority.

## Conflict Rules

- If a template, skill, memory note, or archived prompt conflicts with current repo rules or verified code, treat it as stale guidance.
- If docs disagree with verified runtime behavior, do not invent behavior; stop and report the exact conflict.
- If a cleanup requires runtime, pricing, auth, schema/storage, workflow, Render, dependency, or public/admin behavior changes, stop and get explicit scope approval first.
- Generated grounding-pack output should match its source docs when those source docs are intentionally changed.
