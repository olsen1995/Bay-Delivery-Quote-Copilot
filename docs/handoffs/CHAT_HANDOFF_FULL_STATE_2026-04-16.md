# 📦 Bay Delivery Quote Copilot — Full Chat Handoff

Generated: 2026-04-16

---

## 🔷 PROJECT OVERVIEW

**Project:** Bay Delivery Quote Copilot
**Purpose:** Real-world quoting + booking-request system for Bay Delivery (North Bay, Ontario)

This is a **live revenue system** — not a sandbox.

Primary goals:

* protect margin
* maintain one pricing engine
* improve customer clarity
* prevent undercharging
* scale safely

---

## 🔗 CORE LINKS

Repo
<https://github.com/olsen1995/Bay-Delivery-Quote-Copilot>

Render App
<https://bay-delivery-quote-copilot.onrender.com/>

Quote Page
<https://bay-delivery-quote-copilot.onrender.com/quote>

Admin
<https://bay-delivery-quote-copilot.onrender.com/admin>

Mobile Admin
<https://bay-delivery-quote-copilot.onrender.com/admin/mobile>

Health
<https://bay-delivery-quote-copilot.onrender.com/health>

Custom GPT (Internal Only)
<https://chatgpt.com/g/g-69c12331d9548191b77eb4b0b78205e5-bay-delivery-quote-assistant>

---

## 🔴 NON-NEGOTIABLE RULES

### Business

* One pricing engine only → app/quote_engine.py
* Protect margin over winning cheap jobs
* No silent underpricing
* Cash vs EMT rules must remain correct

### Architecture

* Backend = source of truth
* SQLite = source of truth
* Google Calendar = mirror-only
* Admin approval required before booking is confirmed
* GPT = recommendation only (never pricing authority)
* No duplicate pricing logic
* No second pricing engine

---

## 🔷 WORKFLOW STANDARD

Always follow:

PLAN → IMPLEMENT → VALIDATE → BRANCH → PR → REVIEW → MERGE

---

## 🔷 CODEX USAGE

Codex handles:

* scoped implementation
* tests
* frontend polish
* storage groundwork

ChatGPT handles:

* architecture
* scope control
* PR review
* system direction

---

## 🔷 CURRENT SYSTEM STATE

Status:

* Stable
* Production-ready
* No pricing drift
* Stress-tested
* UX improved

Phase:
Hardening + margin protection + controlled expansion

---

## 🔷 COMPLETED WORK

* Deployment parity fixes (timezone + CORS)
* Backup integrity improvements
* Quote UX (Phase A)
* Booking flow polish (Phase B)
* Payment groundwork (Phase C1)
* Stress-test harness
* Quote UX copy improvements
* Input guidance + margin hints
* C1.5a internal quote risk scoring

---

## 🔷 CURRENT GAP

Main risk:
Customer input underestimation → margin loss

---

## 🔷 NEXT TASK

Next immediate step:

* docs/state cleanup + sanity verification after PR #197

Next likely candidate:

* C1.5d — admin visibility for internal quote risk assessment

---

## 🔷 C1.5a DESIGN

Status:
Completed in PR #197.

Confidence:

* high
* medium
* low

Risk flags:

* low_input_signal
* missing_structured_scope
* dense_material_risk
* access_volume_risk
* mixed_bulky_load_risk
* likely_underestimated_volume

Placement:
quote_service.build_quote_artifacts()
(after calculate_quote)

Rules:

* never modify pricing
* never recalculate totals
* only read normalized input + engine output
* unsupported raw `bag_type` / `trailer_fill_estimate` strings must not count as structured scope signals

Example (internal only):

{
"confidence_level": "medium",
"risk_flags": ["low_input_signal"]
}

---

## 🔷 FUTURE PHASES

C1.5b → optional persistence
C1.5c → margin protection adjustments
C1.5d → admin visibility

---

## 🔷 DO NOT DO YET

* payments
* Stripe/webhooks
* repricing
* admin redesign

---

## 🔷 TEST COMMANDS

pytest -q tests/test_quote_stress_harness.py tests/test_quote_request_transitions.py

pytest -q tests/test_static_assets.py
pytest -q tests/test_launch_smoke_playwright.py -k quote

python tools/check_version_parity.py

---

## 🔷 CODEX REASONING

Low → tiny edits
Medium → frontend / small work
High → architecture / pricing

C1.5a = High

---

## 🔷 FINAL NOTE

System is stable.

Next step is docs/state cleanup + sanity verification,
then the likely candidate is C1.5d admin visibility.

---

## 🏁 END
