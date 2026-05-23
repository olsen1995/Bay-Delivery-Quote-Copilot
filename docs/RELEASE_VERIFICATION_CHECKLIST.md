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
   - Response should include `ok`, `version`, `drive_configured`, and nullable `commit`.

Reference: `README.md`, `DEPLOYMENT_NOTES.md`.

---

## 3) Deployment-Sensitive Render Env Checks

Before concluding verification, confirm expected Render env assumptions are still true:

- `LOCAL_TIMEZONE` is set (expected documented value: `America/Toronto`).
- `BAYDELIVERY_CORS_ORIGINS` is set to exact production origin(s), no wildcard, no trailing slash.
- DB path expectation is consistent with documented Render disk usage (`BAYDELIVERY_DB_PATH=/var/data/bay_delivery.sqlite3`).
- If GPT grounding refresh was required/performed, `GPT_GROUNDING_REVISION` is set to the current refresh record value
  (for example `vX.Y.Z+<manifest-hash-prefix>` from `docs/gpt/GPT_REFRESH_WORKFLOW.md` step 8).

If behavior looks wrong, check env/config first before proposing code changes.

Reference: `render.yaml`, `DEPLOYMENT_NOTES.md`.

---

## 4) Live-Safe Smoke Verification

Manual post-deploy route smoke:

```bash
BASE_URL=https://bay-delivery-quote-copilot.onrender.com python scripts/smoke_test.py --mode post-deploy
```

This mode needs network access but no admin credentials. It checks `/health` status and JSON markers (`ok`, `version`, `commit`), public customer pages, and the pre-auth desktop/mobile admin shells. A pass means the deployed app is reachable and the basic customer/admin entry points are serving the expected protected shell HTML. It intentionally does not check quote calculation, uploads, booking submission, accepted quote flow, admin APIs, backups, imports, exports, restores, or any destructive/admin mutation.

Run live-safe smoke when:

- a production release just completed, or
- a deployment-sensitive environment change was made, or
- a production incident/fix touched live reliability assumptions.

Preferred path:

- Trigger GitHub Actions workflow: `.github/workflows/production_live_safe_smoke.yml`
  - This path runs the existing GPT observability live-safe assertion, uses `scripts/smoke_test.py --check-health-version` to verify deployed `/health.version` matches the checked-out repo `VERSION`, and uses `--check-health-commit` to compare `/health.commit` against the first 12 characters of the checked-out `HEAD` SHA when the deployed commit fingerprint is available.
  - Treat exact deploy proof as confirmed only when `/health.commit` is present and matched. If the field is absent/null, the workflow remains a deployed `VERSION` alignment check only.

Manual path:

```bash
python scripts/smoke_test.py --mode live-safe --check-health-version --check-health-commit
```

Practical pass/fail interpretation:

- **Pass**: `/health`, admin markers, auth-protected checks, configured Drive-backed checks, deployed `VERSION` alignment, and deployed commit alignment when `/health.commit` is present all succeed.
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

After any grounding refresh, run the full A1-A19 acceptance set in a **fresh chat**:

- `docs/gpt/GPT_ACCEPTANCE_TESTS.md`

Record outcome as:

- Pass: all A1-A19 aligned with expected responses.
- Fail: record failed IDs, fix grounding gap, refresh again, then rerun all A1-A19.

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
  - GPT acceptance A1-A19 (if refresh performed)
- Final status: PASS / FAIL
- Follow-up issue/ticket link if anything failed

Do not mark a release fully verified until required checks above are complete and recorded.
