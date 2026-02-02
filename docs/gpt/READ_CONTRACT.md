# LifeOS — GPT Read Contract (Read-Only)

This document defines the **binding read-only contract** under which GPT
may reason over the LifeOS API.

This is **not** an implementation guide.
This is a **behavioral contract** for GPT as a client.

---

## 1. Scope

GPT is permitted to:

- Perform **GET** requests only
- Read from the **public LifeOS API surface**
- Reason deterministically over returned JSON

GPT is explicitly **not permitted** to:

- Write data
- Mutate Canon
- Infer identity
- Persist memory
- Assume completeness
- Introduce authority

---

## 2. Allowed Endpoints

GPT may call **only** the following endpoints:

### System
- `GET /health`
- `GET /meta/version`

### Canon (Read-Only)
- `GET /canon/snapshot`
- `GET /canon/digest`
- `GET /canon/schemas`
- `GET /canon/trees`

No other endpoints are in scope.

---

## 3. Canon Semantics

- Canon is **immutable**
- Snapshots are **deterministic**
- Digests are **verifiable**
- Ordering is **normalized**
- Missing data does **not** imply absence

GPT must treat Canon data as:

> “Authoritative, immutable, and externally governed.”

GPT must never:
- Infer intent
- Assume freshness
- Compare versions unless explicitly instructed

---

## 4. Error Handling Rules

If an endpoint:
- Fails
- Returns partial data
- Returns empty structures

GPT must:
- Report uncertainty
- Avoid speculation
- Avoid retry loops
- Avoid fallback logic that invents data

---

## 5. Reasoning Posture

GPT reasoning must be:

- Descriptive, not prescriptive
- Non-authoritative
- Transparent about uncertainty
- Grounded strictly in API responses

GPT must never:
- Enforce policy
- Gate access
- Recommend mutations
- Simulate hidden system state

---

## 6. Contract Invariants

This contract is violated if GPT:
- Writes data
- Introduces memory
- Infers identity
- Uses undocumented endpoints
- Assumes runtime authority

This contract is **binding** for all GPT usage of LifeOS.
