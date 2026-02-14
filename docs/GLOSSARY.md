# Governance Glossary
(Authoritative Language Reference)

## Purpose

This document defines the **authoritative meanings** of governance-critical terms
used throughout the Life-OS repository.

Its goals are to:
- Eliminate ambiguity
- Prevent terminology drift
- Serve as the single reference point for future writing

This glossary defines **language only**.
It does NOT introduce rules, enforcement, automation, or authority.

---

## Canon

**Meaning**  
The Canon is the authoritative, structured source of truth for the system.

It represents information that is:
- Deliberately curated
- Deterministically structured
- Treated as immutable unless explicitly released

**What it is NOT**
- A runtime cache
- A mutable configuration store
- An automatically updated dataset

**Common misunderstandings**
- “Canon updates automatically when code changes” ❌  
- “Canon can be patched ad-hoc” ❌

---

## Freeze

**Meaning**  
A Freeze is a declared governance state indicating heightened caution and review.

A freeze signals that:
- Changes should be treated as higher risk
- Human attention is required
- Promotion or mutation should be deliberate

**What it is NOT**
- An automatic block
- A runtime halt
- A CI failure by default

**Common misunderstandings**
- “Freeze means nothing can change” ❌  
- “Freeze enforces itself automatically” ❌

---

## Promotion

**Meaning**  
Promotion is a **human decision** to elevate Canon or behavior into a more authoritative or relied-upon state.

Promotion always implies:
- Explicit intent
- Review
- Traceability

**What it is NOT**
- Automatic
- Time-based
- Triggered by passing tests alone

**Common misunderstandings**
- “CI success equals promotion” ❌  
- “Promotion happens implicitly” ❌

---

## Canon Candidate

**Meaning**  
A Canon Candidate is a proposed Canon state under review.

It signals:
- Intent to promote
- Review readiness
- Sensitivity to freezes

**What it is NOT**
- Approved Canon
- Immutable
- Guaranteed stable

**Common misunderstandings**
- “Candidate means production-ready” ❌

---

## Canon Approved

**Meaning**  
Canon Approved refers to a Canon state that has been explicitly accepted as authoritative.

It implies:
- Determinism
- Stability
- Eligibility for runtime consumption

**What it is NOT**
- Automatically consumed
- Mutable without a new release

**Common misunderstandings**
- “Approved means runtime must upgrade immediately” ❌

---

## Operational Mode

**Meaning**  
Operational Mode is the system’s normal, steady-state posture.

In Operational Mode:
- Governance systems are assumed active
- Canon is authoritative
- No incident or emergency is implied

**What it is NOT**
- A deployment mode
- A performance mode
- A special override state

**Common misunderstandings**
- “Operational Mode means no changes allowed” ❌

---

## Governance

**Meaning**  
Governance is the collection of **human-centered agreements** that define:
- Authority boundaries
- Responsibility
- Decision flow

Governance prioritizes clarity over control.

**What it is NOT**
- Automation
- Enforcement logic
- Centralized command

**Common misunderstandings**
- “Governance equals restriction” ❌

---

## Drift

**Meaning**  
Drift is the unintentional divergence between declared truth and actual state.

Drift may occur in:
- Canon vs snapshot
- Documentation vs behavior
- Declared intent vs outcome

**What it is NOT**
- Always a failure
- Always malicious

**Common misunderstandings**
- “Drift implies blame” ❌

---

## Invariant

**Meaning**  
An invariant is a condition expected to remain true within a defined scope.

Invariants express **assumptions**, not enforcement by default.

**What it is NOT**
- A guarantee
- A runtime assertion unless explicitly enforced elsewhere

**Common misunderstandings**
- “Invariant violations always crash systems” ❌

---

## Snapshot

**Meaning**  
A snapshot is a deterministic capture of Canon state at a point in time.

Snapshots support:
- Auditability
- Reproducibility
- Historical reference

**What it is NOT**
- A live view
- A mutable artifact

**Common misunderstandings**
- “Snapshots update themselves” ❌

---

## Enforcement

**Meaning**  
Enforcement refers to explicit mechanisms that block, fail, or prevent actions.

**By default, enforcement is NONE** unless explicitly declared elsewhere.

**What it is NOT**
- Documentation
- Tests that describe expectations
- Visibility or observability

**Common misunderstandings**
- “Any rule implies enforcement” ❌

---

## Final Note

If a term appears elsewhere with a conflicting meaning:
→ This glossary is authoritative.

If a new term is introduced:
→ It should be added here before widespread use.
