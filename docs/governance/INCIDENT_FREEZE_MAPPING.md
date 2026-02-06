# Incident → Freeze Mapping

## Purpose

This document defines the **expected relationship** between
incident severity levels and system freeze actions.

It provides:
- Shared operator expectations
- Consistent decision-making guidance
- Clear separation between classification and enforcement

This document is **declarative only**.
It does NOT trigger freezes or automate responses.

---

## Mapping Overview

| Incident Level | Freeze Expectation | Notes |
|---------------|------------------|-------|
| Level 0 — Informational | No freeze | Normal system operation |
| Level 1 — Advisory | No freeze | Monitoring only |
| Level 2 — Warning | Freeze optional | Human judgment required |
| Level 3 — Critical | Freeze recommended | Governance trust at risk |
| Level 4 — Emergency | Freeze required | System trust compromised |

---

## Level-by-Level Guidance

### LEVEL 0 — Informational
- Freeze: **Not applicable**
- Rationale: No risk to Canon or runtime trust
- Action: None

---

### LEVEL 1 — Advisory
- Freeze: **Not recommended**
- Rationale: Early signal only
- Action: Monitor and document

---

### LEVEL 2 — Warning
- Freeze: **Optional**
- Rationale: Boundary stress detected
- Action:
  - Human review
  - Freeze considered if risk escalates

---

### LEVEL 3 — Critical
- Freeze: **Strongly recommended**
- Rationale: Canon integrity or compatibility at risk
- Action:
  - Immediate assessment
  - Freeze likely required to prevent drift

---

### LEVEL 4 — Emergency
- Freeze: **Mandatory**
- Rationale: Active corruption or loss of trust
- Action:
  - Full system freeze
  - Incident response initiated
  - Audit before resume

---

## Notes

- Freeze decisions remain **human-authoritative**
- Mapping is guidance, not enforcement
- Overrides must follow documented freeze override policy

This document exists to support clarity, not automation.