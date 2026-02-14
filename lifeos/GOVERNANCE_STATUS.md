# Governance Status — Bay Delivery Quote Copilot

**Status:** Operational Mode  
**Last Updated:** MANUAL  
**Authority:** Human Operators  
**Enforcement:** None (Read-Only Visibility)

---

## 1. Freeze Status

**Freeze Active:** false  
**Freeze Scope:** none  

**Source of Truth:**  
- `Bay Delivery Quote Copilot/FREEZE.json`

Notes:
- When a freeze is active, this document MUST be updated manually.
- This file does NOT enforce freezes. It only reflects declared state.

---

## 2. Canon State

**Canon Version:** declared in Canon release metadata  
**Canon Schema Version:** declared in Canon schemas  

**Determinism Expectations:**
- Canon ordering is deterministic
- Canon content is immutable unless released
- Canon access is governed by read-gate rules

This document does not compute or validate Canon state.

---

## 3. Snapshot Integrity

**Latest Snapshot Digest:** declared (if present)  
**Snapshot ↔ Canon Match:** expected by governance rules  

Notes:
- Snapshot generation and validation are enforced elsewhere
- This section is descriptive only

---

## 4. Runtime Compatibility (Declared)

**Runtime Declared Canon Compatibility:**  
- Declared statically in runtime source (if present)

Notes:
- Absence of a declaration is allowed during bootstrap
- Presence of a declaration implies intentional compatibility

This document does not validate compatibility.

---

## 5. Operational Expectations (Steady State)

In normal operation:

- CI is green
- Canon is immutable unless released
- Runtime only consumes declared Canon versions
- Freezes are explicit and auditable
- Overrides require documentation

---

## 6. Exceptional States

Exceptional conditions include:

- Active incident response
- Active system freeze
- Emergency override in effect
- Canon promotion or release window

These states MUST be reflected explicitly when active.

---

## 7. Authority & Change Control

This file is:
- Human-maintained
- Read-only with respect to enforcement
- Intended for visibility and audit clarity

Any changes to this file are intentional declarations, not automation.

---
