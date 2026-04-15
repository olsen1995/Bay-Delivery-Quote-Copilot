# Future Upgrades — Margin Protection & Input Accuracy

## Purpose

This document captures approved future upgrade ideas for reducing customer guessing, protecting Bay Delivery margins, and improving quote accuracy without weakening conversion.

These are **not implemented yet** unless explicitly stated elsewhere in the repo.

This file exists so the ideas are not lost and can be executed later in controlled phases.

---

## Current Problem

The quote flow is now much clearer and easier to use, but a real-world risk still remains:

- customers often guess low on bag count, volume, weight, or access difficulty
- some customers do not understand terms like dense materials or trailer fill
- some customers skip photos even when photos would materially improve quote accuracy
- this can lead to underestimated jobs and margin leakage

The goal is **not** to remove customer inputs.

The goal is to:

- guide customer inputs better
- interpret risky inputs more safely
- protect margins without scaring customers away

---

## Guiding Principle

Customer inputs should be treated as:

> **useful signals, not perfect truth**

Future improvements should move the system toward:

> **customer estimate + system interpretation + margin protection**

---

## 1. Safe UX Improvements (Frontend Guidance)

These are low-risk improvements that can reduce customer guessing without changing pricing logic.

## 1.1 Garbage Bag Guidance

Add plain-English helper text:

- "A full kitchen garbage bag = 1. If unsure, estimate slightly higher."

Goal:

- reduce undercounting
- improve consistency

---

## 1.2 Dense Materials Guidance

Add clearer examples:

- "Examples: drywall, tile, concrete, shingles, soil. These are heavier and cost more."

Goal:

- improve heavy-material detection
- reduce underpricing on construction-type loads

---

## 1.3 Access Difficulty Guidance

Use more practical examples:

- Easy = curbside / garage
- Medium = short walk / a few stairs
- Hard = basement / long carry / tight access

Goal:

- reduce customer confusion
- improve labour/access pricing accuracy

---

## 1.4 Uncertainty Guidance

Add a small reassurance line near risky inputs:

- "Not sure? Give your best estimate — we’ll confirm details before finalizing the job."

Goal:

- improve completion rate
- encourage honest best-guess input

---

## 1.5 Photo Messaging Upgrade

Strengthen the photo-upload prompt.

Before estimate:

- "You can add photos after your estimate to help confirm accuracy."

After estimate:

- "Adding photos now helps lock in your price and avoid changes later."

Goal:

- increase photo uploads
- reduce surprises
- protect margins

---

## 1.6 Soft Low-Input Nudges

If a customer enters a very low value in a risky field, show a soft suggestion without blocking submission.

Example:

- if garbage_bag_count <= 3, show:
  - "Most jobs are 5–10 bags. Adjust if needed."

Rules:

- no hard block
- no forced changes
- guidance only

Goal:

- reduce accidental underreporting
- protect conversion while nudging accuracy

---

## 2. Future Margin Protection Layer (Backend Interpretation)

These are future backend upgrades and should be implemented carefully in their own phase.

## 2.1 Confidence Level

Add an internal quote confidence layer:

- `high`
- `medium`
- `low`

This should be based on:

- completeness of inputs
- presence/absence of photos
- dense materials flag
- access difficulty
- volume signals
- mismatch patterns in the inputs

Goal:

- identify risky quotes
- improve internal decision quality

---

## 2.2 Risk Flags

Add internal risk flags such as:

- `low_input_signal`
- `likely_underestimated_volume`
- `dense_material_risk`
- `access_volume_risk`
- `no_photo_risk`

Goal:

- expose why a quote is risky
- allow future admin visibility or logic adjustments

---

## 2.3 Post-Calculation Margin Protection

Important rule:

Do **not** replace or bypass `app/quote_engine.py`.

Instead:

- run the standard pricing engine first
- then apply carefully controlled post-calculation protection only when confidence is low or risk flags indicate likely underestimation

Examples of future protected adjustments:

- slight low-confidence uplift
- stricter minimum floor
- moderate access/volume safeguard
- mixed bulky-item safeguard

Goal:

- protect margin without inventing a second pricing engine

---

## 2.4 No Pricing Override Rule

Future margin protection must follow this rule:

- `app/quote_engine.py` remains the only pricing authority
- future protection logic may only wrap or adjust the final result in a controlled, documented way
- no duplicate engine
- no silent repricing without rule-based explanation

---

## 3. Suggested Future Rollout Order

## Phase MP1 — UX Input Guidance

Safe frontend-only improvements:

- bag guidance
- dense materials examples
- access examples
- uncertainty wording
- better photo messaging
- soft low-input nudges

Risk:

- low

---

## Phase MP2 — Internal Confidence & Risk Flags

Backend/internal only:

- confidence level
- risk flags
- no visible customer behavior change yet

Risk:

- medium

---

## Phase MP3 — Controlled Margin Protection Adjustments

Backend:

- post-calculation safeguards
- small low-confidence uplift
- stronger floor protection on risky quotes

Risk:

- medium to high

---

## Phase MP4 — Admin Visibility (Optional Later)

Admin-facing:

- show confidence level
- show risk flags
- help operators identify underreported jobs faster

Risk:

- medium

---

## 4. Non-Negotiable Rules

Future work from this document must preserve:

- one pricing engine only
- backend as source of truth
- no customer self-scheduling
- no weakening of margin protection
- no hidden second pricing path
- no broad redesign unless explicitly approved

---

## 5. Recommended Next Step

The safest next implementation from this document is:

## **Phase MP1 — UX Input Guidance**

That means:

- frontend-only
- no pricing logic changes
- no API changes
- no schema changes
- no booking/approval/calendar changes

This is the best first move for reducing customer guessing while keeping risk low.

---

## 6. Status

Current status:

- documented only
- not implemented unless separately merged in a dedicated PR

Future implementation should be done in narrow, reviewable PRs.
