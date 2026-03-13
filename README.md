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
  - Optional haul-away inputs currently supported:
    - `bag_type` (`light`, `heavy_mixed`, `construction_debris`) applies a per-bag floor
    - `trailer_fill_estimate` (`under_quarter`, `quarter`, `half`, `three_quarter`, `full`) applies a trailer-fill floor
    - `trailer_class` (`single_axle_open_aluminum`, `double_axle_open_aluminum`, `older_enclosed`, `newer_enclosed`) selects lane-specific fill anchors **only when** a `trailer_fill_estimate` is also provided; by itself, `trailer_class` is accepted as metadata but does **not** change pricing
  - Current trailer-class behavior (all conditional on `trailer_fill_estimate` being set):
    - `single_axle_open_aluminum` has a class-specific `quarter` floor
    - `double_axle_open_aluminum` currently falls back to default fill anchors
    - enclosed classes are accepted but currently use default fill anchors (no additional enclosed-class pricing impact yet)
    - if `trailer_fill_estimate` is **not** provided, trailer-class fill floors are treated as 0 and `trailer_class` has no effect on the quote total

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
```

---

## Smoke test usage

Smoke script: `scripts/smoke_test.py`

- `live-safe` mode (default): read-only validation for health/admin/auth surfaces; no quote workflow records are intentionally created.
- `stateful` mode: exercises quote workflow routes and creates quote records (`POST /quote/calculate`), and may create quote-request state when decision routes are available.

Examples:

```powershell
python scripts/smoke_test.py --mode live-safe
python scripts/smoke_test.py --mode stateful
```

Common deploy target env var:

```powershell
$env:BASE_URL = "https://your-render-service.onrender.com"
python scripts/smoke_test.py --mode live-safe
```

---

## Maintainer manual Render verification checklist

- Homepage loads at `/`
- Quote page loads at `/quote`
- Haul-away detail fields (`bag_type`, `trailer_fill_estimate`) appear only when `service_type=haul_away`
- Haul-away quote request payload includes `bag_type` and `trailer_fill_estimate`
- Admin page loads normally at `/admin`
