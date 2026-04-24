# Release Verification Checklist (Canonical)

Use this checklist after an important production release or GPT grounding-related change.  
Audience: Austin + Dan (internal operators).

This checklist consolidates existing repo runbooks into one operator sequence. It does **not** replace detailed source docs; it links back to them.

---

## 1) Release / Version Confirmation

1. Confirm the deployed release target and repo release marker match:
   - `VERSION`
   - any parity markers checked by `python tools/check_version_parity.py`
2. Confirm whether this release scope requires GPT grounding refresh:
   - Required if release changed `PROJECT_RULES.md`, anything in `docs/gpt/`, `docs/gpt/GPT_CURRENT_STATE.md`, or pricing rules in `app/quote_engine.py` / `config/business_profile.json`.
   - Optional otherwise.
3. Record the release version you are verifying before continuing.

Reference: `README.md` (Version Alignment), `docs/gpt/GPT_REFRESH_WORKFLOW.md`, `docs/gpt/GPT_KNOWLEDGE_PACK.md`.

---

## 2) Render / Live App Verification

Use the production URL (current: `https://bay-delivery-quote-copilot.onrender.com` unless updated in deployment notes).

Check these pages in order:

1. `/`
   - Page loads and renders normally (no obvious broken layout or server error).
2. `/quote`
   - Quote form loads and is interactive.
3. `/admin`
   - Admin page loads.
   - Protected admin actions are still auth-protected (ops surface, not customer intake).
4. `/admin/mobile`
   - Mobile admin operator surface loads.
5. `/health`
   - Endpoint returns healthy response body/status for the deployed service.

Reference: `README.md`, `DEPLOYMENT_NOTES.md`.

---

## 3) Deployment-Sensitive Render Env Checks

Before concluding verification, confirm expected Render env assumptions are still true:

- `LOCAL_TIMEZONE` is set (expected documented value: `America/Toronto`).
- `BAYDELIVERY_CORS_ORIGINS` is set to exact production origin(s), no wildcard, no trailing slash.
- DB path expectation is consistent with documented Render disk usage (`BAYDELIVERY_DB_PATH=/var/data/bay_delivery.sqlite3`).

If behavior looks wrong, check env/config first before proposing code changes.

Reference: `render.yaml`, `DEPLOYMENT_NOTES.md`.

---

## 4) Live-Safe Smoke Verification

Run live-safe smoke when:

- a production release just completed, or
- a deployment-sensitive environment change was made, or
- a production incident/fix touched live reliability assumptions.

Preferred path:

- Trigger GitHub Actions workflow: `.github/workflows/production_live_safe_smoke.yml`

Manual path:

```bash
python scripts/smoke_test.py --mode live-safe
```

Practical pass/fail interpretation:

- **Pass**: `/health`, admin markers, auth-protected checks, and configured Drive-backed checks succeed.
- **Fail**: treat as a verification failure; log failure area and open follow-up before marking release verified.

Reference: `.github/workflows/production_live_safe_smoke.yml`, `README.md` (Smoke test usage), `DEPLOYMENT_NOTES.md`.

---

## 5) GPT Grounding Refresh (When Required)

Refresh GPT grounding only when release scope meets refresh triggers in existing GPT docs.

Use existing workflow (do not invent a new one):

1. Export grounding pack with `tools/export_gpt_grounding_pack.py`.
2. Upload exact pack files listed in `docs/gpt/GPT_KNOWLEDGE_PACK.md`.
3. Update Builder instructions only if `docs/gpt/GPT_BUILDER_INSTRUCTIONS.md` changed.
4. Save/publish GPT update.

Reference: `docs/gpt/GPT_REFRESH_WORKFLOW.md`, `docs/gpt/GPT_KNOWLEDGE_PACK.md`.

---

## 6) GPT Acceptance Verification (Fresh Chat Required)

After any grounding refresh, run the full A1–A10 acceptance set in a **fresh chat**:

- `docs/gpt/GPT_ACCEPTANCE_TESTS.md`

Record outcome as:

- Pass: all A1–A10 aligned with expected responses.
- Fail: record failed IDs, fix grounding gap, refresh again, then rerun all A1–A10.

---

## 7) Release Recordkeeping (Pass/Fail Log)

Create or update an internal release verification note/log entry with:

- Date
- Release version
- What was verified/refreshed:
  - Render/live checks
  - env/deployment-sensitive checks
  - live-safe smoke
  - GPT refresh (if required)
  - GPT acceptance A1–A10 (if refresh performed)
- Final status: PASS / FAIL
- Follow-up issue/ticket link if anything failed

Do not mark a release fully verified until required checks above are complete and recorded.
