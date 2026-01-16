# Mode Router Cases — Manual Validation

**Purpose:** Validate mode routing rules from `knowledge/01_ModeRouter.md`.

**How to Use:** Paste each prompt into the Custom GPT and confirm the expected mode behavior occurs.  
**Rule:** Explicit triggers win. Ambiguity → ask 1 question max or choose safest likely mode.

---

## Day Planner (Explicit)

1. **Prompt:** "plan my day"  
   **Expected:** Day Planner

2. **Prompt:** "plan my day, I have low energy and only 2 hours"  
   **Expected:** Day Planner (Energy/Time adaptation)

3. **Prompt:** "help me map my day, morning/afternoon/evening"  
   **Expected:** Day Planner

---

## Life Coach (Emotional Clarity)

1. **Prompt:** "I feel overwhelmed and stuck. Help me get clarity."  
   **Expected:** Life Coach

2. **Prompt:** "I keep spiraling on the same thought loop—what do I do?"  
   **Expected:** Life Coach

---

## Fix-It Diagnostic (Broken/Malfunction)

1. **Prompt:** "My truck is making a grinding noise when I brake."  
   **Expected:** Fix-It Diagnostic (Stop/Check safety framing)

2. **Prompt:** "My laptop is overheating and shutting off."  
   **Expected:** Device Optimization **or** Fix-It (but must follow safety and diagnostics flow)

---

## Cleaning

1. **Prompt:** "How do I clean yellow smoke stains off walls?"  
   **Expected:** Cleaning

2. **Prompt:** "Best way to clean a litter box after dumping it?"  
   **Expected:** Cleaning

---

## Laundry

1. **Prompt:** "How do I get poop stains out of a baby onesie?"  
    **Expected:** Laundry

2. **Prompt:** "Can I wash couch cushion covers on warm?"  
    **Expected:** Laundry

---

## Kitchen

1. **Prompt:** "What can I cook with ground beef and rice in 30 minutes?"  
    **Expected:** Kitchen

2. **Prompt:** "How long should I bake chicken thighs at 400?"  
    **Expected:** Kitchen + food safety notes

---

## Skincare

1. **Prompt:** "Build me a simple AM/PM skincare routine using my products."  
    **Expected:** Skincare

2. **Prompt:** "My face is irritated after retinol—what now?"  
    **Expected:** Skincare (barrier repair rules)

---

## Device Optimization

1. **Prompt:** "My PC is slow—what should I check first?"  
    **Expected:** Device Optimization

2. **Prompt:** "Help me reduce startup apps safely on Windows."  
    **Expected:** Device Optimization

---

## RC Car

1. **Prompt:** "My Hyper Go H16BM ESC keeps dying on 3S. What upgrades make sense?"  
    **Expected:** RC Car mode + LiPo safety reminders

---

## Daily Horoscope (Explicit)

1. **Prompt:** "daily horoscope"  
    **Expected:** Daily Horoscope

2. **Prompt:** "Leo horoscope for today"  
    **Expected:** Daily Horoscope

---

## Decision Check (Explicit)

1. **Prompt:** "decision check: should I buy a used snowblower for $600?"  
    **Expected:** Decision Check (options + risk + reversibility)

---

## Ambiguity Cases (Must Ask 1 Question Max or Choose Safest Likely Mode)

1. **Prompt:** "I need help with my schedule and I feel stressed."  
    **Expected:** Day Planner **or** Life Coach. Must choose one safely or ask 1 question max

2. **Prompt:** "My phone battery sucks and I'm annoyed."  
    **Expected:** Device Optimization. If unclear device/OS, ask 1 question max

3. **Prompt:** "Can you help me with this?"  
    **Expected:** Ask 1 clarifying question max OR propose safest likely mode based on minimal assumptions

---

## Pass Criteria

- ✅ Correct mode chosen for explicit triggers  
- ✅ For safety domains (vehicles, electricity, food, large money), uses Stop/Check approach  
- ✅ For ambiguous prompts, asks ≤ 1 clarifying question or proceeds with safest likely mode  
- ✅ No internal labels exposed to user
