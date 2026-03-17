# Demo Checklist

Use this quick list to run a lean end-to-end demo in staging/production.

## 1) Health

- Open `GET /health`.
- Confirm:
  - `ok: true`
  - app version is returned
  - note whether `drive_configured` is true/false.

## 2) Quote flow

- Open `/quote` and submit a quote.
- Confirm a `quote_id` is returned and totals are displayed.

## 3) Upload photos

- From the quote page, upload 1–2 sample photos.
- Confirm upload returns success (`ok: true`).

## 4) Customer accept / decline

- If the quote UI provides **Accept/Decline** buttons, use those for the demo.
- If calling API directly, try `POST /quote/{quote_id}/decision` with:
  - `{"action":"accept"}` (primary demo)
  - `{"action":"decline"}` (optional alternate)

## 5) Admin approve

- Open `/admin` and sign in.
- In **Booking Requests**, approve an accepted request.
- Confirm a job record is created.
- Admin decision endpoint remains available (admin auth required):
  - `POST /admin/api/quote-requests/{request_id}/decision`

## 6) Drive snapshot + list backups

- Call `POST /admin/api/drive/snapshot`
- Call `GET /admin/api/drive/backups`

## 7) Restore backup

### Post-PR Live Smoke-Test Checklist

Use this checklist after merging a PR to verify live-safe behavior on production.

- Homepage loads successfully
- Homepage "Get a Quote" CTAs route to `/quote`
- `/quote` page loads successfully
- Haul-away quote: form submission succeeds and a quote result appears
- Moving quote: form submission succeeds and a quote result appears
- Item-delivery quote: form submission succeeds and a quote result appears
- Unauthenticated access to `/admin` is blocked by Basic Auth
- No major visible UI issues during these checks
