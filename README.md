# Bay Delivery – Quote Copilot

Local quote/estimate tool for Bay Delivery (North Bay, Ontario).

Current stable milestone: `0.10.0`.

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
   - `customer_accepted` when accepted
   - `customer_declined` when declined
4) Admin reviews accepted requests in `/admin` and either:
   - Approves → status `admin_approved`
   - Rejects → status `rejected`

---

## quote_request status lifecycle (server-enforced)

Canonical statuses:

- `customer_pending`
- `customer_accepted`
- `customer_declined`
- `admin_approved`
- `rejected`

Allowed transitions:

- `customer_pending` -> `customer_accepted`
- `customer_pending` -> `customer_declined`
- `customer_accepted` -> `admin_approved`
- `customer_accepted` -> `rejected`

Terminal statuses (no outgoing transitions):

- `customer_declined`
- `admin_approved`
- `rejected`

---

## Admin access protection (recommended for Render)

If your deployment is public, set admin Basic Auth credentials:

- Environment variables: `ADMIN_USERNAME` and `ADMIN_PASSWORD`

Admin pages:

- `/admin`
- `/admin/uploads`

Note: the HTML pages are intentionally viewable without admin auth so refresh/direct navigation never lock out. Protected actions remain on `/admin/api/*`.

---

## Security behavior (current)

- Security headers are always set in API responses, including CSP (`default-src 'self'; frame-ancestors 'none'; base-uri 'self'`).
- Admin API endpoints require HTTP Basic auth (`ADMIN_USERNAME` / `ADMIN_PASSWORD`).
- Brute-force protection is enabled for admin auth attempts (lockout after repeated failures).
- Request size limits and rate limits are enabled for quote/admin POST paths.

---

## Running locally (Windows PowerShell)

### Create/activate venv (recommended: Python 3.11)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
