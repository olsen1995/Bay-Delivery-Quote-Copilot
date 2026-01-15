# 02 — Daily Check-In Template (Life OS)

Purpose: a simple, repeatable daily check-in that creates clarity and momentum without overwhelm.  
Use Canadian context for costs/logistics when relevant.

This template provides:

- 60-second check-in (Low energy/time)
- 5-minute check-in (Normal)
- 15-minute check-in (Deep, optional)

Guiding rules:

- Keep it practical and user-led.
- Prefer least-risk, reversible actions.
- Ask 1–3 questions max, only if it materially changes outcome or safety.
- If a topic is high-risk (vehicles, electricity, chemicals, food safety, baby safety, large $$), apply STOP/CHECK/OPTIONS/ESCALATE discipline.

---

## 60-Second Check-In (Quick / Low)

### 1) Today’s status (pick one)

- Energy: Low / Medium / High
- Time available: 5 min / 30 min / 2+ hrs
- Stress: Low / Medium / High

### 2) One win (yesterday or today)

- Win: _______________________

### 3) Top 1 priority (must move today)

Write it in “verb + object” form:

- Priority: _______________________

### 4) Next safe step (2–10 minutes)

Choose the smallest step that creates motion:

- Next step: _______________________

### 5) One constraint (what could derail this)

- Constraint: _______________________

### 6) Lock it in (micro-commitment)

- When (time): _______________________
- Where: _____________________________

**Output expectation (assistant):**

- Return a 3-step micro-plan (max).
- Include a “If you stall, do this” fallback.
- Do not add extra goals.

---

## 5-Minute Check-In (Normal)

### 1) Reality check (fast scan)

- Sleep: Poor / OK / Good
- Food/water: Behind / OK / On point
- Body: Sore / OK / Good
- Mood: Low / OK / Good

### 2) Today’s outcomes (choose 1–3)

- Outcome A: _______________________
- Outcome B: _______________________
- Outcome C: _______________________

### 3) Risks & safety (only if relevant)

If anything involves a high-risk domain, list it here:

- Risk domain(s): _______________________
- What’s unknown: _______________________

### 4) Plan the day (simple)

- First task (10–30 min): _______________________
- Second task (30–60 min): _______________________
- “Maintenance task” (5–15 min): ________________

### 5) Money & logistics (optional, if relevant)

Canadian context:

- Expected spend today (CAD): $__________
- Bills due / deadlines: _______________________
- Travel / pickup / drop-off: ___________________

### 6) Accountability (tight)

- What would “done” look like by tonight? _______________________
- One thing you’re NOT doing today (boundary): ________________

**Output expectation (assistant):**

- Provide a prioritized 1–3 item plan with time estimates.
- Offer a Conservative option if the user’s energy/time is low.
- If a safety domain is involved: include STOP/CHECK and a clear escalation point.

---

## 15-Minute Check-In (Deep / High)

### 1) What’s the actual problem?

- Problem statement (one sentence): _______________________
- Why it matters (one sentence): _______________________

### 2) Constraints & resources

- Constraints (time, money, people, tools): _______________________
- Resources you have: _______________________

### 3) Options (least-risk first)

List 2–3 options:

- Option 1 (reversible): _______________________
- Option 2 (moderate): _______________________
- Option 3 (irreversible / high effort): _______________________

### 4) Decision (pick one)

- Chosen option: _______________________
- Reason: _______________________

### 5) Next actions (sequenced)

- Step 1: _______________________
- Step 2: _______________________
- Step 3: _______________________

### 6) Failure modes & fallback

- Likely failure mode: _______________________
- Fallback plan: _______________________

**Output expectation (assistant):**

- Return a clean decision + 3–7 step plan.
- Clearly separate known vs assumed if confidence <80%.
- Keep questions minimal and only if they change the decision.

---

## Prompt you can paste into the GPT (Daily Check-In)

Copy/paste this when you want a check-in:

> “Daily check-in. Energy = [   ]. Time = [   ]. Stress = [   ]  
> My top priority is: [   ]  
> Constraints: [   ]  
> If money/logistics matters today: [   ]  
> Give me the smallest safe plan to make progress.”

---

## Notes for maintainers (repo)

- If you later add “reminders,” keep them as a planning spec first (`docs/automation/`).
- Keep this template stable; update only with version bumps and changelog entries.
