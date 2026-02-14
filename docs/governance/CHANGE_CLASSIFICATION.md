# Change Classification (Safe / Risky / Forbidden)

## Purpose

This document defines a shared, system-wide language for classifying changes **before** they are executed.

It is a **decision framework** for humans.

It does NOT:
- enforce restrictions
- block commits
- modify CI behavior
- add automation, scripts, guards, or gates

---

## The Three Change Classes

### 1) SAFE CHANGE

**Definition**
A change that has **no behavioral impact** and does not alter any system execution surface.

**Examples**
- Documentation-only updates (README, docs, runbooks)
- Comments only
- Formatting only (no logic edits)
- Static typing improvements (type narrowing / annotations) with identical runtime behavior
- Lint-only fixes that do not alter code execution
- Test additions that do not change runtime logic (tests only)

**Required human actions**
- Normal review
- Standard commit message
- No freeze awareness required unless changing a frozen documentation scope

**Escalation expectations**
- If there is *any* doubt about behavior impact → classify as **RISKY CHANGE**

---

### 2) RISKY CHANGE

**Definition**
A change that could plausibly have **behavioral impact** or touches areas adjacent to runtime, CI, Canon governance, or integrity boundaries.

**Examples**
- Runtime-adjacent changes (routes, services, storage, mode routing)
- CI workflow changes
- Canon governance enforcement changes (tests, read-gates, invariants)
- Snapshot logic / digest logic adjustments
- Dependency changes (requirements, Python version, tooling)
- Refactors that might change execution order, imports, or initialization

**Required human actions**
- Human review is REQUIRED
- Diff must be inspected carefully
- If a freeze exists, freeze scope must be checked before proceeding
- If change touches governance boundaries, confirm it remains deterministic

**Escalation expectations**
- If a change would violate an active freeze or breaks governance invariants → classify as **FORBIDDEN CHANGE**

---

### 3) FORBIDDEN CHANGE

**Definition**
A change that violates governance rules or requires authority beyond normal operation.

A change is forbidden when it:
- breaks Canon immutability expectations
- bypasses declared read-gates / integrity rules
- modifies frozen scopes without explicit override authority + audit trail

**Examples**
- Modifying Canon while a Canon freeze is active
- Introducing unauthorized Canon access paths (direct filesystem reads that bypass read-gate)
- Disabling or bypassing integrity contract enforcement
- Silent drift introduced into Canon schemas/trees/strategies
- CI changes that introduce implicit overrides or non-deterministic behavior
- Any attempt to encode enforcement while claiming it is “visibility only”

**Required human actions**
- STOP
- Requires override authority + documented incident metadata
- Requires explicit intent, reason, and timestamp (audit trail)
- Requires a follow-up incident record and post-change review

**Escalation expectations**
- Treat as Level 3/4 incident depending on severity
- Full freeze may be required before proceeding

---

## Classification Rules of Thumb

If you are uncertain:
- Choose the higher-risk classification
- SAFE only when you can confidently prove “no behavior impact”

The goal is not bureaucracy — it’s preventing silent drift.

---

## Notes

This classification framework is descriptive and human-facing.
It does not trigger any automation or enforcement by itself.
