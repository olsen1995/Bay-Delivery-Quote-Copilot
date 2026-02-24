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
- Call `POST /quote/{quote_id}/decision` with:
  - `{"action":"accept"}` (primary demo)
  - `{"action":"decline"}` (optional alternate)
- Confirm response includes `ok: true` and a `request_id`.

## 5) Admin approve
- Open `/admin` and sign in.
- In **Booking Requests**, approve an accepted request.
- Confirm a job record is created.

## 6) Drive snapshot + list backups
- If Drive is configured:
  - Call `POST /admin/api/drive/snapshot`
  - Call `GET /admin/api/drive/backups`
- Confirm snapshot returns `ok: true` and list returns backup items.

## 7) Restore backup
- From backup list, pick a backup `file_id`.
- Call `POST /admin/api/drive/restore` with `{"file_id":"..."}`.
- Confirm restore reports restored table counts.
