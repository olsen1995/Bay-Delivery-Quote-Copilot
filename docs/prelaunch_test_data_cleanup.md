# Prelaunch Test Data Cleanup

This runbook documents the one-time operator workflow for removing explicitly allowlisted pre-launch test quote lineage from the live Bay Delivery SQLite database.

## Exact Live Execution Method

Run the cleanup from the Render web service shell, or an equivalent production shell that has direct access to the live SQLite database path exposed by `BAYDELIVERY_DB_PATH`.

Current verified production contract:

- `render.yaml` mounts the persistent disk at `/var/data`
- `render.yaml` sets `BAYDELIVERY_DB_PATH=/var/data/bay_delivery.sqlite3`
- `app/storage.py` resolves `BAYDELIVERY_DB_PATH` as the active database path

If Render Shell or an equivalent safe production shell is not available, stop. Do not improvise with a local copy, a permanent admin delete control, or a broad DB import/export reset.

## Backup-First Requirement

Before any destructive apply step:

1. Capture a fresh admin DB export using the existing backup flow.
2. Optionally capture a Drive snapshot if the operator wants an additional out-of-band rollback point.
3. Record the exact quote IDs being allowlisted for cleanup.

The cleanup script requires `--backup-confirmed` together with `--apply` so the destructive step cannot run without an explicit operator acknowledgement.

## Dry Run

From the production shell:

```bash
python scripts/create_prelaunch_test_data_cleanup.py \
  --quote-id quote_test_1 \
  --quote-id quote_test_2
```

Dry run is the default. It prints:

- the resolved database path
- the explicit requested quote IDs
- any missing quote IDs
- exact counts for quotes, quote requests, jobs, and attachments
- the exact records that would be deleted from those four tables

Dry run does not delete any rows.

## Apply

After reviewing the dry-run output and confirming the backup/export:

```bash
python scripts/create_prelaunch_test_data_cleanup.py \
  --quote-id quote_test_1 \
  --quote-id quote_test_2 \
  --apply \
  --backup-confirmed
```

Apply behavior:

- deletes only the allowlisted quote lineage
- resolves related `quote_requests` by `quote_id`
- resolves related `jobs` by `quote_id` or `request_id`
- resolves related `attachments` by `quote_id`, `request_id`, or `job_id`
- runs DB deletion inside a single SQLite transaction
- prints the exact IDs and counts deleted

## Explicitly Preserved Data

This tool does not delete or modify:

- `completed_job_calibration_entries`
- `admin_audit_log`
- GPT observability/history tables
- pricing logic or pricing configuration
- customer quote payload behavior
- mobile admin assets
- Render config, workflows, requirements, or version markers

## Scope Boundary

This tooling PR does not perform live cleanup on its own. It only adds the operator-run dry-run/apply script, storage helpers, focused tests, and this runbook.