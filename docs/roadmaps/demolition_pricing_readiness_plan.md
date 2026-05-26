# Demolition Pricing Readiness Plan

Prepared: May 26, 2026

## Purpose

This is a readiness plan, not a pricing implementation.

Demolition and rip-out work is one of the clearest underpricing risks for Bay Delivery, but this plan does not change quote totals, service minimums, customer flow, admin behavior, storage, GPT behavior, or deployment configuration.

Authoritative pricing remains in `app/quote_engine.py`. There must be one pricing engine only.

Completed-job records, manual calibration entries, operator notes, and mock calibration cases are advisory evidence until a scoped future pricing PR deliberately changes pricing logic and validates the change.

## Current Conclusion

Demolition/rip-out should be the first service category reviewed for future pricing safeguards.

No pricing code change is justified yet. The latest readiness review found no P1 blockers, but it also found that more real completed-job and manual calibration data is needed before changing quote logic.

Readiness-review notes to carry forward:

- Local completed-job evidence was empty at review time: `total_completed_jobs=0`.
- The manual calibration table was empty at review time: count `0`.
- The old $16/hr helper anchor remains active and can understate labour economics for jobs that need extra hands. This is a pricing-readiness concern, not a change in this plan.

Current known anchors are useful but directional only:

- $1,200 old shed removal, teardown, and haul-away.
- $600 backyard tarp, fence teardown, and cleanup.

Those anchors show that real demolition work can land far above the historical demolition minimum, but two directional examples are not enough to rewrite pricing safely.

## Why Demolition/Rip-Out Is First

Demolition/rip-out should be reviewed first because it combines several risks that can turn a simple-looking quote into a margin problem:

- High underpricing risk compared with the current historical demolition minimum.
- Mock and calibration signal showing demolition can lose margin when treated like basic haul-away.
- Directional shed and backyard teardown anchors that are much higher than a basic minimum.
- Dense debris and disposal uncertainty.
- Labour and time overrun risk.
- Access, trailer, tool, and cleanup risk.
- Liability, property-damage, and customer-expectation risk.
- More frequent need for manual review when photos or job details are unclear.

The goal is not to win every demolition job. The goal is to avoid accepting work that is too cheap for the time, load, disposal, access, and risk involved.

## What Counts As Demolition/Rip-Out

For this plan, demolition/rip-out includes jobs where Bay Delivery is not only moving items, but also taking something apart, tearing something out, breaking down material, cleaning up after removal, or hauling away debris created by tear-out work.

Examples include:

- Shed teardown and removal.
- Fence, tarp, or backyard teardown.
- Flooring rip-out.
- Drywall or fixture removal.
- Deck or small structure tear-down.
- Construction debris cleanup after tear-out.
- Mixed teardown plus haul-away.

## Jobs That Should Stay Manual-Review/Premium

The following jobs should stay manual-review or premium-priced until Bay Delivery has enough evidence to support specific pricing safeguards:

- Full shed or structure teardown.
- Unknown material or hidden debris.
- Dense or heavy debris.
- Concrete, brick, tile, or dirt.
- Basement, inside, or long-carry demolition.
- Stairs, elevator, apartment, or tight-access constraints.
- Possible hazardous or regulated material.
- Permit-sensitive or liability-sensitive work.
- Jobs with high customer-expectation or property-damage risk.
- Any job where photos are missing, unclear, or do not show the full scope.

When the scope is unclear, the safer operating move is manual review, not a low automatic price.

## Evidence To Collect Before Pricing Code Changes

Before any demolition pricing PR, collect enough real job evidence to explain what changed and why.

For each demolition/rip-out or closely related job, capture:

- Quoted amount.
- Collected amount.
- Payment method.
- Service type.
- Crew size.
- Actual hours.
- Helper cost.
- Disposal or tipping cost.
- Fuel and travel distance.
- Trailer or load size.
- Whether the material was dense or heavy.
- Access difficulty.
- Stairs, inside work, or long carry.
- Tool or disassembly time.
- Cleanup or sweeping time.
- Before and after photos, if available.
- Whether the job was underpriced.
- What made the job easier than expected.
- What made the job harder than expected.
- Operator notes.

The notes matter. A price that looks high or low on paper can make sense once access, disposal, tool time, or cleanup is understood.

## Minimum Evidence Threshold

This is a practical owner/operator threshold, not a legal or scientific rule.

Before changing demolition pricing, Bay Delivery should have roughly:

- At least 5 to 10 real demolition/rip-out or closely related completed/manual calibration entries.
- At least 2 examples of premium teardown jobs.
- At least 2 examples of smaller teardown or cleanup jobs.
- Actual hours known for most entries.
- Disposal and fuel costs known for most entries.
- Crew size and helper cost known when helpers were used.
- At least one dense/heavy debris or difficult-access example if that logic will be changed.
- Enough operator notes to explain why the new safeguard would protect margin without overfitting to one unusual job.

If the evidence is still thin, the right next step is more calibration entry, not pricing code.

## Future Pricing PR Options

A future pricing PR could consider one or more of these options, but only if the evidence supports the change:

- Raise the demolition minimum.
- Add manual-review or premium floors for teardown signals.
- Add dense/heavy debris safeguards.
- Add crew/time floors for inside, long-carry, stairs, or tool-heavy work.
- Add internal quote-output or admin advisory wording, only if it stays internal.
- Use before/after calibration mocks before any quote engine pricing change.

Each option should be scoped narrowly. A demolition pricing PR should not silently change dump run, small move, scrap pickup, or other category pricing unless that is explicitly approved.

## Tests Required For Any Later Pricing PR

Any later demolition pricing PR should include tests for:

- Cash pricing has no HST.
- EMT/e-transfer pricing adds 13% HST.
- Rounding behavior.
- Demolition minimum and floor cases.
- Small teardown compared with premium teardown cases.
- Dense debris cases.
- Missing photos or manual-review advisory cases.
- Quote response contract stability.
- No customer-facing internal-risk, margin, or advisory language leakage.
- No changes to unrelated service categories unless explicitly scoped.
- Full pytest.

The tests should prove both the new demolition behavior and the absence of unrelated pricing drift.

## Protected Boundaries For Future Pricing PRs

Any future demolition pricing PR must protect these boundaries:

- `app/quote_engine.py` remains the sole pricing authority.
- No second pricing engine.
- No customer-facing GPT pricing path.
- No automatic GPT price override.
- No auto-scheduling or auto-approval.
- No customer-facing risk, margin, or internal advisory terms.
- SQLite remains the source of truth for persisted data.
- Google Calendar remains a mirror and convenience layer only.
- Completed-job/manual calibration evidence remains advisory until a reviewed pricing PR changes quote logic.

If a proposed change needs a second pricing path or customer-facing internal language, it is the wrong change.

## Recommended Next Operating Step

Start entering demolition/rip-out completed-job or manual calibration entries after each relevant job.

Do not change pricing until enough evidence exists. After enough entries exist, review the calibration data again and decide whether the next PR should create calibration cases, pricing safeguards, or no code change at all.

## Future PR Sequence

Recommended sequence:

1. Create demolition pricing readiness plan.
2. Collect demolition calibration entries.
3. Create demolition calibration cases.
4. Create demolition pricing safeguards, only if evidence supports it.
5. Create GPT/current-state refresh if needed after pricing changes.

This order keeps the system boring, auditable, and margin-protective.
