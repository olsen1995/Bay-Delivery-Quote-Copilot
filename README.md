# Bay Delivery – Quote Copilot

Local quote/estimate tool for Bay Delivery (North Bay, Ontario).

This project provides:

- Customer-facing quote UI (served at `/`)
- Quote API (`POST /quote/calculate`)
- Booking request workflow + admin approval
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

## Booking request workflow (customer → admin approval)

1) Customer generates an estimate on `/`
2) Customer clicks **Request Booking** and submits date/time window
3) System stores a `quote_requests` row with status `customer_requested`
4) Admin reviews in `/admin` and either:
   - Approves → status `admin_approved`
   - Rejects → status `rejected`

---

## Admin access protection (recommended for Render)

If your deployment is public, set an admin token:

- Environment variable: `BAYDELIVERY_ADMIN_TOKEN`

Admin endpoints require:

- Header: `X-Admin-Token: <token>` OR query param `?token=<token>`

Admin page:

- `/admin`

---

## Running locally (Windows PowerShell)

### Create/activate venv (recommended: Python 3.11)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
