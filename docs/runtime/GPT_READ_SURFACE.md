# GPT Runtime Read Surface (Authoritative)

## Purpose

This document defines the **only sanctioned runtime surface** that a
Custom GPT may read from the Bay Delivery Quote Copilot backend.

The intent is to provide **visibility without authority**.

No other runtime endpoints are approved for GPT consumption unless this
document is explicitly amended.

---

## Approved Endpoint

### `GET /meta`

This endpoint exposes **read-only governance and system status signals**.

It is safe for GPT consumption because:

- It is read-only
- It mutates no state
- It tolerates missing data
- It enforces no behavior
- It exposes no sensitive runtime internals

---

## Response Fields (Non-Exhaustive)

The `/meta` endpoint may include the following fields:

- `operational_mode`  
  Human-readable system posture (e.g., "Day-2 (Operational)")

- `canon_version`  
  Canon system identity version, if available

- `canon_digest_loaded`  
  Boolean indicating whether a Canon snapshot digest is present

- `freeze_active`  
  Boolean indicating whether a Canon freeze is currently active

Fields are optional and may be `null` or omitted.

---

## Explicit Non-Authorization

The Custom GPT is **NOT authorized** to:

- Write to any runtime endpoint
- Mutate Canon
- Infer permissions from `/meta`
- Treat `/meta` as enforcement or instruction
- Assume presence of any field

This surface is **informational only**.

---

## Change Control

Any expansion of GPT-readable runtime surfaces requires:

1. A new documented contract
2. Explicit governance review
3. A versioned amendment to this file

Absent that, `/meta` is the **sole approved surface**.
