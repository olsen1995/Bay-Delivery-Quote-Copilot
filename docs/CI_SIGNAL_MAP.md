# CI Signal Simplification Map (Human Clarity Layer)

**Status:** Documentation Only  
**Audience:** Human operators and maintainers  
**Purpose:** Reduce noise, clarify priority, guide attention

---

## Why This Document Exists

CI surfaces many signals, but not all signals are equal.

This document explains:
- Which CI failures actually block progress
- Which failures demand immediate attention
- Which failures are advisory or contextual
- How humans should prioritize response

This document does NOT:
- enforce behavior
- block commits
- automate decisions
- change CI logic

It is an interpretive guide only.

---

## Signal Categories

### 1️⃣ BLOCKING SIGNALS

**What this means**
- A core governance or trust boundary was violated
- Progress should stop until resolved

**Typical causes**
- Canon freeze violations
- Integrity contract failures
- Canon provenance or drift guard failures

**Recommended human action**
- Stop and assess intent
- Confirm whether change was authorized
- Revert or explicitly override if justified

These failures indicate **system-level risk**.

---

### 2️⃣ HIGH-PRIORITY SIGNALS

**What this means**
- A declared contract or boundary is stressed
- Likely requires correction, but not always systemic

**Typical causes**
- OpenAPI drift
- Canon structural invariant failures
- Import boundary violations

**Recommended human action**
- Investigate promptly
- Decide whether to update the contract or fix the change
- Avoid ignoring repeated occurrences

These failures indicate **design or interface misalignment**.

---

### 3️⃣ INFORMATIONAL SIGNALS

**What this means**
- Something is incomplete or worth noting
- No immediate risk to system integrity

**Typical causes**
- Coverage gaps
- Advisory or non-governing tests
- Documentation mismatches

**Recommended human action**
- Acknowledge
- Address when appropriate
- Track if recurring

These failures indicate **quality or completeness gaps**, not danger.

---

### 4️⃣ IGNORABLE / CONTEXTUAL SIGNALS

**What this means**
- Experimental, draft, or context-specific indicators
- Not relevant to most decision-making

**Typical causes**
- Draft-only checks
- Temporary diagnostics
- Local experimentation signals

**Recommended human action**
- Ignore unless actively working in that area
- Remove if they become confusing or obsolete

These signals should **never block progress**.

---

## How to Use This Map

When CI fails:
1. Identify which category the failure belongs to
2. Respond according to the recommended action
3. Avoid overreacting to low-signal noise
4. Treat blocking signals as intentional guardrails

---

## Non-Goals (Explicit)

This map does NOT:
- replace CI output
- define enforcement rules
- encode escalation paths
- automate prioritization

Human judgment remains central.

---

## Summary

CI is a signal amplifier, not a decision-maker.

This map exists so humans can:
- stay calm
- focus attention correctly
- act deliberately
