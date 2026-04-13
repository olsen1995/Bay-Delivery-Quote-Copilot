# GPT Acceptance Tests – Bay Delivery Quote Copilot

## Purpose

This checklist contains the fixed acceptance question set for verifying a fresh GPT grounding is working correctly.

Run these questions in a **fresh chat** with the GPT after every grounding refresh.

All questions must pass before the refresh is considered complete.

---

## Acceptance Questions

### A1 – Pricing authority

**Ask:** "Where does pricing authority live in this project?"

**Expected response must include:**

- Reference to `app/quote_engine.py` as the single pricing authority.
- Statement that there is no second pricing path.
- No invented pricing logic.

---

### A2 – GPT role boundary

**Ask:** "Are you a customer-facing quoting tool?"

**Expected response must include:**

- Clear statement that the GPT is internal-only for Austin and Dan.
- Customers use the live Render quote flow at `/` and `/quote`.
- GPT is not a customer intake surface.

---

### A3 – No-assumptions rule

**Ask:** "What should you do if a behavior or rule isn't documented in the grounding pack?"

**Expected response must include:**

- Treat undocumented behavior as unknown.
- Do not invent or guess.
- Escalate or recommend checking the repository directly.

---

### A4 – Grounding precedence

**Ask:** "What is the grounding precedence order for this project?"

**Expected response must include (in order):**

1. `PROJECT_RULES.md`
2. `docs/gpt/GPT_SOURCE_OF_TRUTH.md` and companion docs
3. `docs/CURRENT_STATE.md`
4. `README.md`
5. `docs/MARKET_AND_PRICING_STRATEGY.md`
6. Verified repository code

---

### A5 – Tax policy

**Ask:** "Does a cash quote include HST?"

**Expected response must include:**

- Cash quotes are tax-free (no HST).
- EMT/e-transfer adds 13% HST.

---

### A6 – Scope discipline

**Ask:** "Should you mix unrelated changes in one task?"

**Expected response must include:**

- No. Keep changes narrow and task-scoped.
- Do not mix unrelated concerns.
- Call out scope drift before implementation.

---

### A7 – DB-first rule

**Ask:** "Should a Google Calendar write happen before or after a DB write?"

**Expected response must include:**

- DB writes must occur before external API calls (including Google Calendar).
- Calendar is a mirror only.
- Calendar failures must not corrupt valid DB state.

---

### A8 – Admin boundary

**Ask:** "Can customers use admin surfaces like /admin?"

**Expected response must include:**

- Admin surfaces (`/admin`, `/admin/mobile`, `/admin/uploads`) are operations tools.
- Admin tools are not customer quote intake surfaces.
- Customer-facing surfaces are `/` and `/quote`.

---

## Pass Criteria

A refresh passes acceptance when all eight questions produce responses consistent with the expected content above.

If any question produces a drifted or invented response:

1. Note which question(s) failed.
2. Review the grounding pack for gaps or conflicts.
3. Re-export and re-upload following `docs/gpt/GPT_REFRESH_WORKFLOW.md`.
4. Re-run all eight questions.
