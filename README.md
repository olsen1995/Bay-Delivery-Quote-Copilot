# Bay Delivery – Quote Copilot

Local quote/estimate tool for Bay Delivery (North Bay, Ontario).

This project provides:

- Customer-facing quote UI (served at `/`)
- Quote API (`POST /quote/calculate`)
- Booking decision workflow + admin approval
- SQLite storage for ops review

---

## Required customer info (prevents no-info estimates)

All quotes require:

- `customer_name`
- `customer_phone`
- `job_address`
- `description` (must include item/job details)

For `small_move` and `item_delivery`, also required:

- `pickup_address`
- `dropoff_address`

---

## Pricing rules (canonical)

### Tax policy

- **Cash:** no HST
- **EMT / e-transfer:** add **13% HST** to the total

### Service types

- **Junk Removal / Haul Away** (Junk + Dump are the same service)
  - Disposal may be included in the **total**
  - Disposal is **NOT itemized** as a customer fee line/toggle
  - Mattress/box spring is **note-only**

- **Scrap Pickup**
  - Curbside/outside: **$0**
  - Inside removal: **$30 flat**
  - Scrap bypasses labour/travel/disposal logic completely

---

## Booking decision workflow (customer → admin approval)

1) Customer generates an estimate on `/`
2) Customer uses the decision endpoint to **Accept** or **Decline** the quote
3) System stores/updates the `quote_requests` row with status:
   - `customer_accepted_pending_admin` when accepted
   - `customer_declined` when declined
4) Admin reviews accepted requests in `/admin` and either:
   - Approves → status `admin_approved`
   - Rejects → status `rejected`

---

## Admin access protection (recommended for Render)

If your deployment is public, set an admin token:

- Environment variable: `BAYDELIVERY_ADMIN_TOKEN`

Admin APIs require:

- Header: `X-Admin-Token: <token>` for all `/admin/api/*` routes.
- Optional convenience bootstrap: open `/admin?token=<token>` (or `/admin/uploads?token=<token>`) once; frontend stores it in `sessionStorage`, strips it from URL, and uses the header afterwards.

Admin pages:

- `/admin`
- `/admin/uploads`

Note: the HTML pages are intentionally viewable without admin auth so refresh/direct navigation never lock out. Protected actions remain on `/admin/api/*`.

---

## Running locally (Windows PowerShell)

### Create/activate venv (recommended: Python 3.11)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open:

- Home: `http://127.0.0.1:8000/`
- Quote page: `http://127.0.0.1:8000/quote`
- Admin page: `http://127.0.0.1:8000/admin`

---

## Environment variables

### Admin auth

- `BAYDELIVERY_ADMIN_TOKEN` (recommended for Render/public deploys)
- OR `ADMIN_USERNAME` + `ADMIN_PASSWORD` for HTTP Basic auth

### Google Drive (optional)

- `GDRIVE_FOLDER_ID`
- `GDRIVE_SA_KEY_B64`
- `GDRIVE_BACKUP_KEEP` (optional)
- `GDRIVE_AUTO_SNAPSHOT=1` (optional)

### CORS (optional)

- `BAYDELIVERY_CORS_ORIGINS` (comma-separated origins, e.g. `https://your-render-domain.onrender.com`)
- If not set, CORS middleware is not enabled (same-origin only).

### Versioning

- `VERSION` is the source of truth for app version metadata (`/health` uses this).
- Releases are Python-first (no Node tooling): run the **Release** GitHub Action and choose a bump type (`patch`/`minor`/`major`).
- The release workflow updates `VERSION`, creates a `vX.Y.Z` tag, and publishes a GitHub Release.

---

## Smoke test

With the server running locally:

```powershell
python scripts/smoke_test.py
```
