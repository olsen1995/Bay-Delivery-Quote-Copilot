# GPT Knowledge Pack

## Purpose

This document defines the exact upload set for the Bay Delivery internal advisor GPT.

This pack is intentionally small, text-heavy, and release-approved.

## Canonical Upload Set

Upload these files to the custom GPT Knowledge panel:

1. `docs/gpt/GPT_SOURCE_OF_TRUTH.md`
2. `docs/gpt/GPT_SYSTEM_BOUNDARIES.md`
3. `docs/gpt/GPT_BUSINESS_RULES.md`
4. `docs/gpt/GPT_WORKFLOW_RULES.md`
5. `docs/gpt/GPT_CURRENT_STATE.md`
6. `PROJECT_RULES.md`
7. `docs/CURRENT_STATE.md`
8. `README.md`

## Pack Rules

- Keep the pack small and curated.
- Prefer stable text docs over raw code or screenshots.
- Treat `docs/gpt/` as the primary memory layer for the advisor GPT.
- Use `PROJECT_RULES.md`, `docs/CURRENT_STATE.md`, and `README.md` as supporting canonical repo docs.
- Re-upload changed files after meaningful rule or release updates.

## Do Not Upload As Primary GPT Knowledge

- The whole repo
- Tests
- Static/frontend assets
- Database files
- Temporary planning notes
- Random code snapshots
- Generated exports or scratch files

## Builder Workflow

1. Update the canonical repo docs first.
2. Verify repo truth against implementation when needed.
3. Upload this exact file set in GPT Builder.
4. Run the acceptance question set in `docs/gpt/GPT_ACCEPTANCE_TESTS.md`.
5. Treat the GPT as current only after the upload and verification steps are complete.
