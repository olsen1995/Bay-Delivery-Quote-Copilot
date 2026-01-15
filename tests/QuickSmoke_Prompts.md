# QuickSmoke Prompts — Manual Behaviour Check (Life OS)

This is a quick manual checklist to validate the Custom GPT’s behaviour after instruction changes.

This is separate from the automated repo QuickSmoke script.

## 1) Day Plan

**Prompt:** Create a simple day plan with morning, afternoon, and evening blocks.  

**Pass criteria:**

- Includes three time blocks with clear labels.
- Includes 3 anchors: MUST-DO / PROGRESS / CARE.
- Includes a friction scan + 1 prep step.
- Ends with a win condition.

## 2) Decision Check

**Prompt:** Help me decide whether to attend a 1-hour optional meeting today.  

**Pass criteria:**

- Uses Option A / Option B / Option C structure.
- Each option includes: tradeoffs, main risk, reversibility, and next step.
- Ends with a default recommendation.

## 3) Soft Brakes

**Prompt:** My stress is spiking—give me a soft brakes response to slow down.  

**Pass criteria:**

- Calm, empathetic tone.
- Suggests one immediate grounding step.
- Reduces scope to one next action.
- Keeps the response under 6 sentences.

## 4) Upload Analysis Gate

**Prompt:** Analyze the uploaded document for key takeaways and risks.  

**Pass criteria:**

- Uses the full 6-step Upload Analysis Gate.
- Includes a risk label: Safe / Risky / Do-Not-Touch.
- Includes missing-data check and confidence statement.
- If confidence is not High and changes could be risky, STOPs and asks for missing info before advising changes.

## 5) Daily Horoscope Freshness

**Prompt:** Give me today’s horoscope in a fresh, non-generic style.  

**Pass criteria:**

- Includes: theme, action bias, watch-out, practical anchor.
- Avoids clichés like “today is your day.”
- Keeps it under 120 words.
