---
name: bay-delivery-storage-invariant-review
description: Use when reviewing or changing Bay Delivery SQLite writes, constraints, save/update/upsert paths, imports, restores, backups, migrations, duplicate handling, startup integrity, or storage persistence behavior.
---

# Bay Delivery Storage Invariant Review

Use this skill with `bay-delivery-pr-safety-review` for storage-sensitive Bay Delivery work.

The core rule is fail closed without destroying valid persisted state. Review the complete persistence surface, not only the helper named in the task.

## Storage Surface Inventory

Before implementation or merge, identify every relevant:

- table, primary key, unique index, business key, and foreign or logical relationship
- insert, save, direct update, and explicit upsert path
- startup initialization and integrity-check path
- seed and compatibility path
- import, restore, backup/export, and dry-run/preview path

Record which invariant each path must preserve. Stop if the table or mutation-path inventory is incomplete.

## Duplicate, Missing, And Legacy Matrix

Review each applicable state deliberately:

| State | Required review |
| --- | --- |
| Valid unique record | Normal behavior preserves all protected fields and relationships. |
| Duplicate primary or business key | Fail before mutation unless an explicit, field-level upsert contract exists. |
| Duplicate `quote_id` or request linkage | Distinguish the duplicate from a missing record and fail closed across every caller. |
| Missing record | Return or raise the documented missing-record result without creating a replacement implicitly. |
| Legacy duplicates | Preserve records non-destructively while blocking ambiguous reads and unsafe writes. |
| Unique index absent | Keep application-level guards active for both legacy keys and otherwise clean new keys. |
| `NULL` or blank unique values | Define and test each value separately; do not assume SQLite treats them equivalently. |
| Stale duplicate payload | Prove protected state cannot be erased, regenerated, or rolled back. |
| Partial update in legacy state | Apply the same duplicate guard as create/save paths before any update. |

Do not collapse duplicate and missing outcomes into one generic `None`, falsey value, or not-found response unless every caller is proven to fail closed.

## Mutation And Transaction Safety

Require evidence that:

- input validation, confirmation checks, and duplicate checks happen before mutation
- failed operations preserve existing rows and do not partially update related records
- multi-step integrity work uses an explicit transaction
- commit and rollback behavior is clear for every failure branch
- concurrent writes remain safe when a database-level unique index is unavailable
- external API failures cannot corrupt valid SQLite state

When a transaction opens before a guard, ensure every early return or exception closes it through commit, rollback, and connection cleanup as appropriate.

## `INSERT OR REPLACE` And Upsert Review

Treat `INSERT OR REPLACE` as high risk because SQLite replacement can delete and recreate a row. Do not use it for operational records unless replacement semantics are explicitly required and every protected field is proven safe.

Review whether replacement or conflict handling could erase, regenerate, or stale:

- accept and booking tokens or token timestamps
- admin, lifecycle, follow-up, deposit, and payment state
- quote IDs, request IDs, service type, request JSON, and customer totals
- scheduling and Google Calendar IDs, sync state, and errors
- costing, collection, closeout, profit, and receipt fields
- creation, acceptance, approval, start, completion, cancellation, and refund timestamps

For `ON CONFLICT DO UPDATE`, classify each field as immutable, preserved operational state, or intentionally refreshable descriptive data. Use the existing database row explicitly for protected fields; do not rely on stale caller payloads or broad `COALESCE` behavior.

## Backup, Preview, Import, And Restore Parity

Build one table-by-table contract showing whether each known table is:

- exported
- represented in the payload when empty or omitted
- shown in dry-run/preview output
- cleared or retained by the real operation
- restored
- verified after restore

The preview must represent the real mutation scope. If the real restore clears an omitted table, the preview must show that table with a zero count or an explicit destructive warning.

Also verify token rotation, duplicate invariants, failure behavior, transaction boundaries, and rollback behavior. Restore counts must describe rows actually retained, not attempted inserts that replacement or constraints discarded.

## Isolated Round-Trip Verification

For backup/import/restore work, use temporary SQLite databases and fixtures:

1. Seed representative records, including protected fields and applicable legacy duplicates.
2. Export or construct the backup payload.
3. Preview the operation and compare it with the real table mutation inventory.
4. Restore or import into an isolated temporary database.
5. Verify every known table, relationship, protected field, and expected token rotation.
6. Verify duplicate handling and unique-index present/absent behavior.
7. Verify no unexpected records disappear.
8. Verify invalid input fails before mutation and rolls back completely.

## Safe Logging And Privacy

Storage errors, duplicate reports, and import/restore previews may expose only controlled identifiers, bounded counts, safe table metadata, and short non-sensitive summaries.

Never log or return:

- accept or booking tokens
- customer names, phone numbers, addresses, or descriptions
- complete backup payloads or raw customer records
- payment-sensitive data

Review both application logs and HTTP/admin responses because safe internal exceptions can still leak through callers.

## Data Protection

During repository implementation and testing:

- do not mutate production databases
- do not run destructive live import or restore tests
- do not mutate local app/data unless Austin explicitly approves it
- do not treat local app/data as production calibration truth
- do not delete or rewrite data merely to make a test pass
- use isolated temporary SQLite databases and fixtures

## Required Review Evidence

The final report must include:

- affected tables and indexes
- every mutation path reviewed
- duplicate/missing/legacy matrix results
- transaction, commit, and rollback review
- protected fields reviewed
- round-trip results when applicable
- safe-log and privacy review
- tests run and results
- protected no-go diff result
- remaining P1/P2/P3 findings

## Manual Pressure Cases

Use these recurring patterns to test whether the review is complete:

1. A preview reports fewer known tables than the real restore clears.
2. Legacy duplicate `quote_requests.quote_id` rows prevent creation of the unique index.
3. A direct partial update bypasses the guard used by create/save paths.
4. A stale duplicate job payload carries conflicting lifecycle, totals, payment, costing, and calendar state.

Each case must route to an explicit rule above and produce a fail-closed, non-destructive outcome.

## Stop Conditions

Stop and report instead of broadening scope when:

- the table or mutation-path inventory is incomplete
- preview and real mutation scope disagree
- a required invariant cannot be expressed within the approved files
- production or unapproved local app/data mutation would be required
- protected operational fields cannot be classified safely
- tests fail for unclear reasons
- the fix requires unrelated pricing, UI, workflow, Render, dependency, or schema redesign
