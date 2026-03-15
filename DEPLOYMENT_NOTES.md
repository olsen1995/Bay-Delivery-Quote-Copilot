# Bay Delivery Quote Copilot — Deployment Notes

This file documents production deployment expectations that are operationally important but should not be rediscovered during incidents.

---

## Production Hosting

Current production origin:

- <https://bay-delivery-quote-copilot.onrender.com>

If a custom production domain is added later, update this file and include that domain in the CORS allowlist.

---

## CORS

Production CORS must be explicitly configured.

Use this environment variable in Render:

- BAYDELIVERY_CORS_ORIGINS

Current expected production value:
BAYDELIVERY_CORS_ORIGINS=<https://bay-delivery-quote-copilot.onrender.com>

Rules:

- use exact origins only
- use https
- no wildcard
- no trailing slash
- no localhost entries in production

Do not leave production dependent on localhost fallback defaults.

If a custom production domain is added, include both origins as a comma-separated list.

Example:
BAYDELIVERY_CORS_ORIGINS=<https://bay-delivery-quote-copilot.onrender.com,https://www.example.com>

---

## Deployment-Sensitive Environment Areas

Before changing code for production incidents, inspect whether the issue is actually env-only in one of these areas:

- CORS allowlist
- trusted proxy and forwarded IP handling
- admin credentials
- storage backend selection
- Google integration settings

Prefer env-only fixes when the application code already supports the intended behavior.

---

## Live Verification for CORS

After a production CORS change, verify both a denied and allowed preflight.

Denied localhost preflight command:
curl -i -X OPTIONS <https://bay-delivery-quote-copilot.onrender.com/quote/calculate> -H "Origin: <http://localhost:3000>" -H "Access-Control-Request-Method: POST"

Expected:

- HTTP 400
- disallowed CORS origin
- no matching Access-Control-Allow-Origin for localhost

Allowed production preflight command:
curl -i -X OPTIONS <https://bay-delivery-quote-copilot.onrender.com/quote/calculate> -H "Origin: <https://bay-delivery-quote-copilot.onrender.com>" -H "Access-Control-Request-Method: POST"

Expected:

- HTTP 200
- Access-Control-Allow-Origin: <https://bay-delivery-quote-copilot.onrender.com>
- Access-Control-Allow-Credentials: true

---

## Live-Safe Smoke Verification

After deployment-sensitive fixes, run the live-safe smoke test with real admin credentials.

PowerShell example:
$env:BASE_URL="https://bay-delivery-quote-copilot.onrender.com"
$env:ADMIN_USERNAME="`real admin username`"
$env:ADMIN_PASSWORD="`real admin password`"
python scripts/smoke_test.py --mode live-safe

Expected:

- /health passes
- admin page markers pass
- authenticated admin endpoints pass
- Drive-backed admin endpoint checks pass when Drive is configured

Do not paste real credentials into chat, docs, screenshots, or commit history.

---

## Operational Scope Rules

Do not mix deployment hardening with:

- pricing changes
- schema tightening
- frontend polish
- broad refactors

For deployment and security incidents:

1. inspect first
2. confirm root cause
3. prefer the smallest safe fix
4. verify live behavior
5. document the operational result

---

## Current Known Good Outcome

As of the latest verified pass:

- production CORS allows the production origin
- localhost origin is denied
- authenticated live-safe smoke passes
- Drive-backed admin checks pass
- the CORS remediation was an env-only Render fix, not a repo code change
