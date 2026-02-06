# Draft Promotion Pipeline (Development → Canon → Runtime)

## Status

**DRAFT ONLY**

This document describes a shared human understanding of how changes
*conceptually* move through the system.

It does NOT:
- automate promotion
- enforce gates
- block commits
- modify CI behavior
- imply active machinery

This is documentation only.

---

## Purpose

The promotion pipeline exists to ensure that:

- Canon remains authoritative and stable
- Runtime upgrades are intentional
- Humans share a clear mental model of responsibility
- Nothing promotes “by accident”

---

## Promotion Stages

### 1) DEVELOPMENT

**Purpose**
- Free exploration and iteration
- Learning, prototyping, refactoring

**Allowed actions**
- Rapid edits
- Incomplete tests
- Experimental Canon drafts
- Runtime experimentation

**Human responsibility**
- Individual contributor
- No assumption of stability
- No downstream guarantees

**Common failure modes**
- Assuming development state is production-ready
- Forgetting Canon is not yet authoritative

---

### 2) CANON CANDIDATE

**Purpose**
- Explicit intent to promote changes into Canon

**Allowed actions**
- Review of Canon structure
- Snapshot awareness
- Governance checks
- Freeze awareness

**Human responsibility**
- Reviewer(s) acknowledge intent
- Canon integrity is consciously evaluated
- Determinism and structure are verified

**Common failure modes**
- Skipping review
- Promoting during a freeze
- Treating Canon as mutable

---

### 3) CANON APPROVED

**Purpose**
- Establish an authoritative, deterministic Canon state

**Allowed actions**
- Read-only consumption
- Snapshot reference
- Versioned acknowledgment

**Human responsibility**
- Ensure Canon is immutable unless released
- Confirm governance invariants hold
- Treat Canon as a source of truth

**Common failure modes**
- Silent edits to approved Canon
- Assuming approval implies runtime upgrade

---

### 4) RUNTIME CONSUMPTION

**Purpose**
- Safe usage of Canon guarantees by runtime systems

**Allowed actions**
- Read-only access
- Version-aware consumption
- Compatibility declaration

**Human responsibility**
- Runtime explicitly acknowledges Canon version
- No mutation or reinterpretation
- Upgrade decisions are deliberate

**Common failure modes**
- Runtime consuming newer Canon implicitly
- Ignoring version compatibility
- Treating Canon as dynamic configuration

---

## Explicit Non-Goals

This pipeline does NOT:
- implement gates
- trigger CI behavior
- auto-promote Canon
- auto-upgrade runtime
- replace human judgment

All transitions are intentional and human-driven.

---

## Summary

Promotion is a **human decision process**, not a technical shortcut.

Canon is stable by choice.
Runtime upgrades are deliberate.
Nothing moves without intent.