> ⚠️ Archived — This document reflects a previous state of the project and may no longer be accurate.
> Refer to `docs/CURRENT_STATE.md` for the latest source of truth.

# Bay Delivery Quote Copilot — Chat Handoff / Current State / Next Steps

> **Historical snapshot:** This document reflects repository state as of 2026-03-22. It is retained for history and may not match the current `main` branch.
> **Direction correction (updated):** roadmap notes in this snapshot were corrected to match current direction while preserving historical context.


Generated: 2026-03-22

---

## Project
**Project:** Bay Delivery Quote Copilot

**Repo:** https://github.com/olsen1995/Bay-Delivery-Quote-Copilot

**Render:** https://bay-delivery-quote-copilot.onrender.com/

**Current deployment note:** Live Render app has been up during recent work and `/health` has reported healthy status in prior checks. The repo has moved from foundational build mode into mobile-ops hardening and workflow refinement mode.

---

## How We Have Been Working
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
   - keep quote assistance separate from deeper admin quote authoring

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

### Major merged work
- **PR #121** — scheduling context and richer calendar handoff metadata
- **PR #122** — job lifecycle (start / complete / cancel) with transition validation and close-out tracking
- **PR #123** — message-based autofill suggestions for screenshot assistant plus dirty-state protection
- **PR #124** — OCR extraction for screenshot uploads and OCR-backed autofill integration
- **PR #125** — quote-range guidance for screenshot assistant
- **PR #126** — Google Calendar payload minimization / privacy hardening
- **PR #127** — end-to-end screenshot assistant regression coverage through scheduling + decline guardrail
- **PR #128** — dedicated `/admin/mobile` operator shell
- **PR #129** — mobile shell hardening: quote-linked lock state, autofill rendering, reviewed-input hydration
- **PR #131** — draft-session tracking and stale async response protection in `admin_mobile.js`

### Current live capabilities now in main
- admin-only screenshot assistant analyses
- screenshot/message intake with reviewed save flow
- OCR extraction on screenshot upload
- autofill suggestions with warnings / missing-field support
- quote-range guidance anchored to the existing pricing engine
- customer accept / decline / booking flow
- admin approval -> job creation
- Google Calendar scheduling integration with minimized event payloads
- explicit job lifecycle controls
- mobile-first admin shell at `/admin/mobile`
- deeper regression coverage around the assistant -> quote -> booking -> job -> schedule chain

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
These should be re-verified in a fresh chat rather than blindly assumed:

- live `/admin/mobile` runtime behavior after PR #131
- whether the mobile smoke test now fully passes
- whether any remaining iPhone Safari quirks still exist
- whether quote-range guidance calibration needs refinement (for example, minimum safe vs recommended target separation)
- whether OCR on live uploads behaves well on actual customer screenshots
- whether any post-merge PR cleanup is still needed (close superseded PRs if applicable)
- whether the mobile shell now merits small behavior-focused tests beyond static assertions

---

## Immediate Next Task
**Next task:** plan the removal of quote-authoring / quote-drafting functionality from admin surfaces (including `/admin/mobile`) while preserving the public customer quote flow.

### Why this is next
- current direction keeps customer quote request/get-quote flow active
- admin should stay focused on operational workflow (request review, approvals, jobs, scheduling)
- quote-authoring inside admin is now out of scope for the next phase
- the right next move is a narrow plan for clean removal without route or pricing-engine churn

### What should happen next
- Start in **Plan mode**
- Define exact admin/mobile quote-authoring and quote-drafting touchpoints to remove
- Preserve public customer quote intake + quote delivery flow
- Preserve admin operational capabilities (request review, approvals, jobs, scheduling)
- Keep `quote_engine` as the only in-app pricing source of truth
- Keep GPT recommendation-first and non-binding

---

## Recommended Live Mobile Smoke Test Checklist
Run this exact flow on iPhone/mobile:

1. Open `/admin/mobile`
2. Log in
3. View Requests
4. Open a request and review request details
5. Confirm approve/reject flow visibility
6. View Upcoming Jobs
7. Confirm scheduling/job workflow visibility
8. Confirm mobile layout supports core operations without desktop fallback

### Record results like this
- PASS
- SOFT FAIL
- FAIL

Suggested format:

1. Open /admin/mobile — PASS / SOFT FAIL / FAIL
2. Log in — PASS / SOFT FAIL / FAIL
3. Requests list visibility — PASS / SOFT FAIL / FAIL
4. Request detail review — PASS / SOFT FAIL / FAIL
5. Approve/reject flow visibility — PASS / SOFT FAIL / FAIL
6. Upcoming Jobs visibility — PASS / SOFT FAIL / FAIL
7. Scheduling/job workflow visibility — PASS / SOFT FAIL / FAIL
8. Mobile layout supports core ops — PASS / SOFT FAIL / FAIL

Add notes + screenshots for any FAIL or meaningful SOFT FAIL.

### What counts as a blocker
Treat any ops-critical failure as a blocker:
- login
- requests visibility
- request detail review visibility
- approval/rejection workflow visibility
- jobs visibility
- scheduling/job workflow visibility
- major layout issues that force desktop use for core ops

### What can wait
These should not block the next module if the core ops flow works:
- minor spacing polish
- copy tweaks
- nicer empty states
- convenience shortcuts
- performance/API shaping unless mobile feels truly slow

---

## After That
If the immediate next task lands cleanly, the likely next item is:

**Next-up task:** implement the scoped removal in admin/mobile and validate that operations workflows remain smooth while the public quote flow stays intact.

### Likely shape of the follow-up pass
- remove admin/mobile quote-authoring and quote-drafting UI/workflow paths
- keep request review, approvals, jobs, scheduling, and operational workflow intact
- keep customer-facing quote intake + quote response path available
- keep `quote_engine` as the only in-app pricing source of truth
- keep GPT recommendation-first and non-binding, with future internal quote assistance handled as a separate workflow

---

## What Should NOT Happen Next
Do NOT:
- create a second pricing engine
- create AI-only pricing
- expand quote creation deeper into admin or `/admin/mobile`
- keep quote-authoring / quote-drafting as an admin roadmap priority
- let OCR/autofill become quote truth without reviewed save
- drift into big UI rewrites unless there is a real operational need
- rewrite auth right now
- rebuild the app as native iOS right now
- overcomplicate the frontend with unnecessary build tooling

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

### Highest-priority current files
- `static/admin_mobile.js`
- `tests/test_static_assets.py`
- any smoke-test-related routes used by `/admin/mobile`

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
3. whether admin is cleanly focused on operations only (request review, approvals, jobs, scheduling),
4. whether public customer quote flow remains intact,
5. and what the single best next task is.
Also keep our default workflow as: plan mode first, implementation second, PR review, merge, and live smoke test.”

---

## Short State Summary
The repo is no longer in early build mode. It is in stable, feature-rich refinement mode where the app should remain customer quote intake + ops backbone, admin should stay operations-first, and GPT quote help should move toward a separate recommendation workflow rather than deeper quote-building inside admin. The biggest value in the next chat will come from verifying current live state and planning/removing admin quote-authoring while preserving the public customer quote flow.
