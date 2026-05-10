# Completed Job Calibration JSON Integration Plan

## Purpose

Completed-job calibration JSON is local analysis evidence for operator review, admin reporting, internal GPT summaries, and future internal tooling.

It is not pricing authority. Production pricing remains owned by `app/quote_engine.py`, and completed-job calibration output must not create a second pricing engine, override quote totals, or change customer-facing quote behavior.

The analyzer is read-only and analysis-only. Its output is generated on demand, written to stdout, and should be treated as advisory evidence about completed-job profitability, missing cost data, and owner-review risk patterns.

## Current JSON Producer

The current producer is `scripts/analyze_completed_job_calibration.py`.

Run JSON output from the repo root with:

```powershell
.\.venv\Scripts\python.exe scripts\analyze_completed_job_calibration.py --format json
```

The analyzer reads completed jobs from the local SQLite database resolved by the existing storage path. It opens SQLite with `mode=ro`, applies `PRAGMA query_only = ON`, analyzes completed-job rows, and writes the JSON payload to stdout only.

The analyzer does not write files, mutate jobs, mutate quotes, create quote requests, call the pricing engine, or persist calibration findings.

## Operator Workflow

1. Complete jobs in admin through the normal operations workflow.
2. Enter the final collected amount and actual labor, disposal, fuel, and other job costs.
3. Run:

```powershell
.\.venv\Scripts\python.exe scripts\analyze_completed_job_calibration.py --format json
```

4. Review the margin, missing-data, owner-review, and risk-flag findings.
5. Treat the findings as advisory evidence only.
6. Do not automatically change quote pricing from analyzer output.

## Approved Later Consumers

Approved future consumers are limited to internal, non-customer-facing use:

- Human operator review by Austin and Dan.
- Admin reporting that helps review completed-job profitability.
- Internal GPT summaries that explain calibration findings as advisory evidence.
- A future protected internal endpoint, if needed, that exposes a summary without mutating production data.
- Future CSV, export, or dashboard views only if they remain internal and read-only.

Any consumer must preserve the rule that completed-job calibration output is evidence, not pricing authority.

## Explicit Non-Goals

This integration plan does not approve:

- Pricing overrides.
- Customer-facing calibration exposure.
- Automatic quote changes.
- GPT-created pricing totals.
- Mutating jobs, quotes, quote requests, or completed-job costing records.
- Treating incomplete costing data as final profitability truth.
- A second pricing engine or duplicate pricing logic.

## GPT Interpretation Rules

GPT may summarize completed-job calibration findings for Austin and Dan.

GPT may:

- Flag under-margin patterns.
- Recommend human review.
- Identify jobs or categories with missing costing data.
- Explain risk flags and category patterns in operational language.
- Suggest what data is missing before a profitability conclusion can be trusted.

GPT must:

- Label calibration findings as advisory.
- Treat analyzer output as evidence, not pricing authority.
- Never override `app/quote_engine.py`.
- Never invent or create customer-facing pricing totals from analyzer output.
- Never turn calibration findings into customer-facing promises.
- Never imply it changed a quote, job, request, payment status, or pricing rule.

If a future GPT workflow needs authoritative quote totals, it must continue to use the existing approved quote authority path rather than deriving totals from completed-job calibration data.

## Admin And Reporting Integration Rules

Future admin reporting may show completed-job margin metrics, risk flags, missing-cost indicators, owner-review counts, and category summaries.

Admin/reporting views should:

- Clearly separate payment collection status from profitability.
- Clearly mark missing or incomplete cost data.
- Show risk flags as review prompts, not automatic decisions.
- Preserve SQLite as the source of truth for persisted job and costing data.
- Keep completed-job calibration data internal to operations.

Admin/reporting views must not:

- Auto-change quote pricing.
- Auto-update jobs, quotes, requests, payment state, or pricing rules.
- Present calibration findings as final truth when costing fields are missing.
- Expose completed-job calibration data to customers.

## Future Internal Endpoint Proposal

A possible future internal route is:

```http
GET /api/gpt/calibration/completed-jobs/summary
```

This route should be added only in a separate implementation PR if there is a clear internal need.

If implemented, it must be:

- Internal-only.
- Token-gated.
- Read-only.
- Non-mutating.
- Hidden from public OpenAPI if consistent with the existing internal GPT endpoint pattern.
- Built from existing storage and analyzer behavior without duplicating pricing logic.
- Explicitly not customer-facing.

The endpoint must never mutate the database and must never expose a customer-facing calibration endpoint.

## JSON Contract Summary

The current JSON payload is intended for internal summary and review tooling. Future consumers should treat it as a reporting contract, not as pricing input.

Key payload areas:

- `metadata`: generation time, `analysis_mode`, database existence, and no-data reason.
- Summary metrics: total completed jobs, average collected, average known cost, average known profit, average known margin, below-margin count, missing-cost count, and owner-review count.
- `jobs`: per-job collected amount, known cost, known profit, known margin, operating-cost target floor/gap, payment status, job profit status, missing fields, risk flags, and owner-review marker.
- `category_summary`: service-type summaries for completed-job counts, average collected, average known profit, average known margin, and owner-review count.
- `highest_risk_jobs`: top owner-review examples sorted by risk.
- `risk_flags`: advisory flags such as below-margin, missing-cost, disposal-heavy, labor-underpriced, payment-not-fully-collected, and operator-marked-underpriced conditions.
- No-data payloads: `metadata.no_data_reason` may indicate missing database or no completed jobs.

Consumers must tolerate missing or `null` values and must not treat missing-cost records as complete profitability evidence.

## Risk Controls

Safe integration depends on these controls:

- Missing data must be visible and not hidden inside averages.
- Stale data must not be assumed current without a fresh analyzer run.
- Analyzer output must not mutate production records.
- Analyzer output must not become a second pricing engine.
- Analyzer output must not be exposed to customers.
- GPT and admin surfaces must keep findings advisory until a human reviews the underlying completed-job data.

## Recommended Next Implementation Order

1. Add structured quote risk fields with no pricing effect.
2. Add a GPT calibration interpretation guide.
3. Add an internal GPT calibration summary endpoint only if needed.
4. Add admin/reporting display for completed-job margin and risk review.
5. Add quote-engine protections one category at a time, only through explicit pricing-engine PRs with tests.

Each step should be a separate narrow PR. Pricing changes, endpoint work, admin UI, GPT grounding updates, and analyzer contract changes should not be mixed into one change.
