# Bay Delivery Quote Copilot Operational Mode

## Status
**OPERATIONAL MODE: ACTIVE**

This repository is no longer in build or experimental mode.
All governance systems are assumed active and authoritative.

---

## 1. Definition of Normal Operation

Normal operation means:

- CI is green
- Canon is immutable unless explicitly released
- Runtime only consumes declared, compatible Canon versions
- Governance gates (freeze, promotion, snapshot rules) are active
- No emergency conditions are present

Normal operation is the DEFAULT state.

---

## 2. Exceptional States

The following states are considered exceptional and must be explicit:

### 🔴 Incident Mode
Triggered by:
- Production incident
- Data integrity risk
- Security concern

May justify a system freeze.

---

### ❄️ Freeze Mode
Triggered by:
- Active incident
- Release stabilization window
- Manual operator decision

Effects:
- Canon and/or Runtime become immutable
- CI enforces freeze boundaries
- Changes require explicit emergency override with audit trail

---

### 🚨 Emergency Override
Emergency overrides are allowed ONLY when:
- Explicit override metadata is declared
- Reason is documented
- Actor is identified
- Timestamp is recorded

Overrides are auditable and never implicit.

---

## 3. Operator Responsibilities

### Authorized Operators May:
- Declare a system freeze
- Lift a system freeze
- Issue an emergency override (with full audit metadata)
- Promote Canon releases
- Acknowledge Runtime ↔ Canon compatibility

### Operators MUST:
- Preserve auditability
- Avoid silent changes
- Keep governance metadata accurate
- Treat Canon as authoritative

---

## 4. Steady-State Expectations

In operational mode, the system assumes:

- CI failures are actionable and blocking
- Canon drift is not tolerated
- Runtime upgrades are intentional
- Snapshot versions are respected
- Promotion gates are enforced

Any deviation must be explicit.

---

## 5. Governance Posture

Governance systems are:
- Enabled
- Enforced
- Non-optional

This document declares posture only.
It introduces **no enforcement logic**.

---

## 6. Change Control

Any change that affects:
- Canon structure
- Snapshot semantics
- Runtime compatibility
- Governance rules

Must be intentional, reviewed, and traceable.

---

**Operational Mode is the baseline.**
Anything else is an exception.
