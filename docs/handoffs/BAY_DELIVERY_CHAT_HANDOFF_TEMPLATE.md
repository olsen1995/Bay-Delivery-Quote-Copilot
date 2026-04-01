> ⚠️ This is a template, not the current project state.
> Refer to `docs/CURRENT_STATE.md` for the latest source of truth.

# Bay Delivery Quote Copilot — Chat Handoff Template

Use this template when starting a new chat for Bay Delivery Quote Copilot. Replace bracketed placeholders with the current state before pasting.

---

## Project
**Project:** Bay Delivery Quote Copilot

**Repo:** [GitHub repo URL]

**Render:** [Render URL]

**Current version / deployment note:** [Current version, deployment health, or latest meaningful note]

---

## How We Work
Use a hybrid workflow.

- Use **Plan mode first**
- Review the plan
- Use **Implementation stage second**
- Review the PR before merge
- Merge / deploy
- Live smoke test
- Then plan the next task

### Tool roles
- **ChatGPT** for architecture, roadmap, business-rule protection, PR review, drift control, hard tradeoffs, and overall product thinking
- **Codex / VS Code agents** for narrow, contained implementation work, repo tracing, and scoped code changes
- **VS Code** when useful for repo inspection, local runs, and applying saved files manually

### Important working rules
- I manually save/apply files myself
- If code is requested directly in chat, always give **full-file replacements only**
- Never ask me to edit specific lines inside files
- Protect margins
- Do not invent a second pricing engine
- Reuse the existing quote / booking / admin / job systems whenever possible
- Keep the Screenshot Assistant recommendation-first, not blind auto-quote
- Use step-by-step guidance when giving repo instructions
- Include commit headline + commit description when giving code/file changes
- Prefer safest long-term fix over a quick patch when practical

---

## Project Identity / Non-Negotiables
This repo is the real operating system for Bay Delivery quoting and admin workflow.

### Preserve these rules
1. **One pricing source of truth**
   - `quote_service` / `quote_engine` remain the actual pricing authority
   - assistant guidance must derive from that path
   - no second pricing engine

2. **Screenshot Assistant is recommendation-first**
   - suggestions are non-binding
   - admin reviews/applies/edits
   - quote draft creation comes from reviewed/saved data

3. **Jobs are the operations anchor**
   - do not mirror ops state back into quote_request unnecessarily
   - scheduling / calendar / close-out should stay job-centered

4. **DB-first**
   - SQLite is source of truth
   - external systems mirror repo state, not the other way around

5. **Margin protection beats optimistic quoting**
   - if unclear, prefer tighter downward room and stronger warnings
   - for Bay Delivery quotes, lean middle-to-higher rather than undercharging

---

## What Has Been Completed
[Summarize merged phases / major capabilities now in main]

Suggested format:
- PR #[number] — [what it did]
- PR #[number] — [what it did]
- PR #[number] — [what it did]

Also summarize live capabilities now available:
- [capability]
- [capability]
- [capability]

---

## Current Reality Check
Before planning new work, verify current reality instead of relying on memory.

### Verify first
1. current GitHub repo state
2. current open / merged PR state
3. current Render / live app state
4. current workflow gaps
5. best next task

---

## Current Known Risks / Things To Re-Check
[List the risks that matter right now]

Examples:
- Render/runtime drift
- mobile shell runtime blockers
- OCR sanity on live uploads
- calendar sync privacy / content
- regression coverage gaps
- UI state-management issues

---

## Immediate Next Task
**Next task:** [single best next task]

### Why this is next
[1–4 bullets]

### What should happen next
- Plan mode first
- Inspect [files]
- Keep scope narrow
- [Any acceptance criteria]

---

## After That
If the immediate next task passes / lands cleanly, the likely next item is:

**Next-up task:** [next likely feature or hardening task]

---

## What Should NOT Happen Next
Do NOT:
- create a second pricing engine
- create AI-only pricing
- let OCR/autofill become quote truth without reviewed save
- drift into big UI rewrites unless there is a real operational need
- add speculative “smart” features before re-checking runtime and workflow integrity

Add any current project-specific “don’t do this next” items here:
- [item]
- [item]

---

## Files / Areas The New Chat Should Inspect First
- `app/main.py`
- `app/storage.py`
- `app/quote_engine.py`
- `app/services/*`
- `app/gcalendar.py`
- `static/*`
- `tests/*`
- `render.yaml`
- `requirements.txt`

Add current focus files here:
- [file]
- [file]

---

## Preferred Output Format
When giving repo/code help:
- lead with the best move first
- explain why it is the best move
- keep the plan practical and repo-aware
- give full-file replacements only if code is requested directly in chat
- include:
  - exact file path
  - full updated file contents
  - commit headline
  - commit description

When reviewing work:
- say whether it should merge or not
- identify scope drift clearly
- call out risks honestly
- prefer Squash and merge for narrow single-purpose PRs unless there is a clear reason not to

---

## Suggested First Prompt For The New Chat
Paste this into the new chat:

“Do a fresh, complete, read-only audit of the current Bay Delivery Quote Copilot repo, current PR state, and live Render app. Verify current reality first instead of relying on prior chat memory. Then tell me:
1. what is fully complete,
2. what the real current risks are,
3. what the single best next task is,
4. and whether the current workflow should stay in plan mode first, implementation second.”

---

## Short State Summary
[1 short paragraph on the repo’s current stage]

Example:
The repo is no longer in early build mode. It is in stable, feature-rich refinement / hardening / decision-support mode. The biggest value in the new chat will come from verifying current live state, checking for workflow/runtime mismatches, and then choosing the next task based on current main rather than memory.
