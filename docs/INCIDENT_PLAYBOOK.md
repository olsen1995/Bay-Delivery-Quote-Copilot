# Incident Playbook — “What Can Go Wrong”

**Status:** Guidance Only  
**Audience:** Human operators and maintainers  
**Purpose:** Calm, deliberate response under stress

---

## Why This Playbook Exists

This playbook exists to support **human judgment during incidents**.

It answers:
- What kinds of failures are realistic in this system?
- How should a human respond without panic?
- What actions are safe vs risky during uncertainty?
- When should freezes or overrides be *considered*?

This document:
- DOES NOT enforce behavior
- DOES NOT automate responses
- DOES NOT change CI or runtime behavior

It is a calm reference, not a rulebook.

---

## 1️⃣ CI Fails Unexpectedly

### Symptoms
- CI turns red without obvious cause
- Multiple workflows fail at once
- Failure messages seem unfamiliar

### Likely causes
- Governance guard triggered
- Drift or invariant violation
- Environmental or ordering issue
- Human misinterpretation of CI output

### Safe actions
- Identify which CI layer failed first (governance vs tests)
- Read the failure message fully
- Check recent changes for scope and intent
- Compare against CI Signal Map

### What NOT to do immediately
- Do not panic-revert blindly
- Do not disable checks
- Do not assume CI is “broken”

### Escalation notes
- If failures indicate governance or Canon integrity risk,
  consider pausing further changes until clarified

---

## 2️⃣ Canon Drift or Structural Invariant Failure

### Symptoms
- Canon drift guard fails
- Structural invariant tests fail
- CI reports unexpected Canon changes

### Likely causes
- Canon modified unintentionally
- Deterministic ordering changed
- Schema or contract mismatch

### Safe actions
- Confirm which Canon files changed
- Determine whether change was intentional
- Review related governance documentation
- Decide whether change should be reverted or formalized

### When a freeze is appropriate
- If Canon authority or trust is unclear
- If multiple Canon-adjacent failures occur
- If human intent is uncertain

---

## 3️⃣ OpenAPI or Contract Mismatch

### Symptoms
- OpenAPI drift guard fails
- Contract validation errors appear
- Runtime vs schema disagreement

### Likely causes
- API behavior changed without schema update
- Schema updated ahead of implementation
- Version or ordering mismatch

### Safe actions
- Validate whether behavior or contract is the source of truth
- Decide whether to fix forward or roll back
- Keep Canon and runtime alignment intentional

### Escalation notes
- Repeated contract mismatches indicate process gaps,
  not just local mistakes

---

## 4️⃣ Human Error (Bad Commit, Misread Signal)

### Symptoms
- Wrong file edited
- Incorrect assumption about CI failure
- Accidental scope expansion

### Likely causes
- Fatigue
- Ambiguous signals
- Incomplete mental model

### Safe actions
- Pause and reassess
- Re-read governance or stability docs
- Revert or amend calmly
- Document what was learned

### Documentation hygiene
- Update docs if confusion was reasonable
- Reduce ambiguity for the next human

---

## General Guidance During Any Incident

- Slower is safer than faster
- Clarity beats heroics
- Governance exists to help, not punish
- Freezes and overrides are tools, not failures

---

## Non-Goals of This Playbook

This playbook does NOT:
- replace governance rules
- authorize overrides
- define enforcement
- act as incident automation

Human judgment remains central.

---

## Summary

Most failures are recoverable.
Most mistakes are understandable.
The goal is **trust, not blame**.

Stay calm.
Read the signal.
Act deliberately.
