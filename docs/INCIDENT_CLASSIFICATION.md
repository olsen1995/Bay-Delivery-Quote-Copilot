# Incident Classification & Response Levels

## Purpose

This document defines a shared, human-facing taxonomy for incidents
affecting the Life-OS system.

It provides:
- A common language for severity
- Clear expectations for human response
- Governance-focused examples

This document is **declarative only**.
It does NOT enforce behavior, trigger automation, or alter runtime or CI execution.

---

## Incident Severity Levels

### LEVEL 0 — Informational

**Description**
- Normal, expected observations
- No risk to system integrity or trust

**Examples**
- Canon documentation updates
- Governance notes or clarifications
- Non-functional refactors already approved

**Expected Human Response**
- No action required
- Optional logging or annotation

---

### LEVEL 1 — Advisory

**Description**
- Potential inconsistency or early signal
- No immediate risk, but worth awareness

**Examples**
- Near-miss governance checks
- Early signs of schema drift
- Unused Canon artifacts detected

**Expected Human Response**
- Monitor
- Optional review
- No freeze required

---

### LEVEL 2 — Warning

**Description**
- Governance boundary under stress
- Risk exists if left unaddressed

**Examples**
- Canon changes without release metadata
- Snapshot version ambiguity
- Runtime compatibility declarations missing or outdated

**Expected Human Response**
- Human review REQUIRED
- Mitigation plan documented
- Freeze may be considered

---

### LEVEL 3 — Critical

**Description**
- Canon integrity or trust boundary at risk
- High likelihood of incorrect behavior if ignored

**Examples**
- Canon drift detected post-release
- Snapshot digest mismatch
- Runtime consuming Canon outside declared compatibility

**Expected Human Response**
- Immediate human intervention
- Freeze strongly recommended
- Rollback or corrective action planned

---

### LEVEL 4 — Emergency

**Description**
- Active corruption or security risk
- System trust compromised

**Examples**
- Canon data tampering
- Unauthorized override of governance controls
- Loss of Canon immutability guarantees

**Expected Human Response**
- Full system freeze
- Incident response initiated
- Audit and recovery required before resumption

---

## Notes

- Incident levels describe **severity**, not blame
- Classification does not imply automation
- Human judgment remains authoritative

This taxonomy exists to improve clarity, coordination, and trust.