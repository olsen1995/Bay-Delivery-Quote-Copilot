# Bay Delivery Quote Engine — Calibration Rules

## Purpose

This file translates the business strategy in `docs/MARKET_AND_PRICING_STRATEGY.md`
into practical, enforceable calibration rules for future pricing PRs.

Anyone proposing a pricing change should read both files before opening a PR.

---

## Calibration Priorities (Current Order)

1. **haul-away optional-input floor calibration by trailer lane** — the foundation is shipped; verify floor anchors by lane before broader re-tuning
2. **small_move pricing** — remains high-importance selective work and must stay worth doing
3. **high-volume haul-away scaling and fringe cleanup** — keep 16+ progression healthy while refining 5–8 bag edge cases

Do not mix multiple priority areas in a single PR.

---

## Current Haul-Away Floor Mechanics (Shipped)

For `haul_away`, optional inputs currently affect pricing through floors (not additive surcharges):

- `bag_type` applies a per-bag floor using `bag_type_anchors_cad_per_bag`
- `trailer_fill_estimate` applies a fill floor using `trailer_fill_floor_anchors_cad`
- `trailer_class` can select class-specific fill anchors via `trailer_class_fill_floor_anchors_cad`

Current precedence/order in the quote engine:

1. Compute base haul-away cash from travel + labour + disposal + mattress/boxspring + access
2. Apply service minimum total floor
3. Compute `bag_type` floor
4. Compute trailer-fill floor by trailer lane
5. Use the highest floor/base value before rounding

In engine terms, this behaves as `max(raw_cash, minimum_total, bag_type_floor, trailer_fill_floor)` before cash rounding.

Current trailer lane behavior:

- `single_axle_open_aluminum`: class-specific trailer-fill table is active where configured
- `double_axle_open_aluminum`: accepted and currently falls back to default trailer-fill anchors unless class rows are added
- `older_enclosed` and `newer_enclosed`: accepted but intentionally use default trailer-fill anchors right now

Current scope limit:

- enclosed trailer classes are accepted inputs but have no additional enclosed-class pricing impact yet

---

## What Counts as a Good Pricing Change

A pricing change is good if it:

- is driven by calibration data from the dataset in `analysis/`
- moves a specific scenario closer to a market-credible range
- does not cause a different scenario to move outside an acceptable range
- passes all tests without modification to test expectations unless the test itself was wrong
- is reviewed against this rules file before merge

---

## What Counts as a Bad Pricing Change

A pricing change is bad if it:

- is made without calibration evidence (guesswork)
- makes Bay Delivery more likely to undercharge on work it already dislikes
- makes tiny junk jobs look unrealistic versus visible local minimums
- flattens large cleanout pricing so that disposal volume loses progressive value
- removes pricing value from convenience, labour, difficult access, or dense materials
- mixes multiple behaviour changes into a single PR

---

## Rules for Tiny Junk Jobs

- Single-item or very small junk pickups should stay in a believable local band.
- Local visible minimums in North Bay are approximately $100–$125 + HST.
- Bay Delivery should not produce quote outputs that look wildly overpriced against those minimums.
- Bay Delivery should also not price tiny jobs so low that dispatching them is financially pointless.
- Easy curbside pickup should not earn the same quote as an awkward basement carry.

---

## Rules for `small_move`

- `small_move` is **selective, higher-hassle, premium-ish work**.
- Pricing should be calibrated so accepted jobs are worth doing, not to win every move lead.
- Losing some move leads to cheaper competitors is acceptable.
- Being slightly expensive versus a bargain mover is acceptable.
- Being cheaper than a full premium mover can still be enough.
- Do not tune `small_move` to chase volume.
- Do not reduce `small_move` rates to "look competitive."
- Any PR that lowers `small_move` rates needs strong calibration evidence.

---

## Rules for High-Volume Haul-Away Jobs

- Large cleanout scenarios must continue to scale progressively.
- Do not let per-bag or per-load pricing flatten too early.
- Estate cleanouts, garage cleanouts, and 16+ bag jobs should produce quotes that match
  real disposal + labour work, not just incremental per-item pricing.
- Do not pass theoretical dump-run efficiency savings back to customers automatically.
- Bin rental and dumpster alternatives already support strong pricing expectations
  for larger jobs — Bay Delivery pricing should reflect this.

---

## Rules for Difficult Access / Dense Materials

- Stairs, basement access, long carries, and awkward loading are labour-intensive.
- Dense or hazardous materials require extra handling.
- These should not produce quotes equivalent to easy curbside pickup.
- Convenience, awkwardness, and access difficulty are part of the service value and must
  be reflected in pricing.

---

## Decision Checklist Before Merging a Pricing PR

Before merging any change to `app/pricing_engine.py`, `app/quote_engine.py`,
or related service/config files, confirm all of the following:

- [ ] The change is backed by calibration data from `analysis/`
- [ ] The target scenario moves closer to the expected range
- [ ] No other scenarios regress outside an acceptable range
- [ ] `small_move` rates are not reduced without strong evidence
- [ ] Tiny junk output is still believable against local visible minimums
- [ ] Large cleanout scaling still progresses and does not flatten
- [ ] Difficult access and dense materials are still priced higher than easy pickup
- [ ] Only one pricing behaviour changed in this PR
- [ ] `python -m compileall app tests` passes
- [ ] `pytest -q` passes without changing test expectations

---

## Recommended Order of Future Pricing Refinement Work

1. **small_move calibration** — tighten 3–5 hour move outputs so they are consistently
   in a worthwhile range, not just occasionally correct
2. **large cleanout / high-volume scaling** — verify the progressive scaling curve is
   steep enough for 16+ bag / estate cleanout scenarios
3. **difficult access premium** — verify that stairs/basement/dense-material modifiers
   are producing meaningfully different outputs versus easy access scenarios
4. **small-to-mid junk fringe cases** — review 5–8 bag non-dense scenarios where
   outputs may still overshoot slightly relative to local visible competitors
5. **combo/hybrid job calibration** — junk + demo, delivery + removal, and mixed service
   jobs should reflect the full labour value of handling multiple service types

Each step should be its own PR with its own calibration evidence.
