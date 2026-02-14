# Knowledge Index — Life OS — Practical Co-Pilot

This folder contains the authoritative “Knowledge” documents referenced by `instructions/Instructions.txt`.

---

## Files

- `00_Bay Delivery Quote Copilot_Constitution.md` — Core operating constitution (v6). Source of truth for: decision philosophy, safety gates, evidence gate, and the mandatory Upload Analysis Gate.
- `01_ModeRouter.md` — Mode routing rules (v2.1, locked). Explicit triggers win; implicit routing; one-question max for ambiguity; no mid-response switching unless safety requires.
- `13_DecisionCheck.md` — Decision Check Mode (v1). Required A/B/C output structure for meaningful tradeoffs.

---

## Update Rule

When changing any Knowledge file:

1. Keep diffs small and reviewable.  
2. Update `tests/TestSuite.md` if behavior expectations change.  
3. Re-run the test prompts relevant to the change.

---

End of file.
