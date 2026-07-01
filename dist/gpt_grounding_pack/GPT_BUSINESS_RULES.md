# GPT Business Rules

This file documents current Bay Delivery business and pricing rules as grounded in repository docs, config, and pricing engine behavior.

## Tax and Payment

- Cash quotes are tax-free.
- EMT/e-transfer quotes add 13% HST.

## Travel Minimums and Zone Protection

- Travel baseline is gas + wear minimums from `config/business_profile.json`.
- Travel-zone adders are applied for `in_town`, `surrounding`, and `out_of_town`.
- Travel is part of the pre-access subtotal and margin protection.

## Service Minimums

- Service-level minimum hours and minimum totals are enforced by service configuration.
- Quote outputs respect service minimums before final cash rounding.
- A universal global minimum floor of $60 CAD is enforced in pricing authority for all quote outputs.
- When service-level minimums are below $60, the final price is raised to $60.

## Labour Rules

- Small move enforces a 4-hour minimum and minimum crew expectations.
- Small move has labour-floor protection (`min_labor_per_crew_hour`, with long-job uplift for extended jobs).
- Haul-away can auto-escalate crew when bag count/density indicates single-operator assumptions are unrealistic.
- Dense-material haul-away labour uses a multiplier to protect against underpricing heavy loads.

## Disposal Rules

- Haul-away disposal is included in the total, not itemized as a separate customer fee line.
- Disposal allowance follows configured tier anchors by bag count.
- Small-load protection applies to tiny light loads so disposal scales proportionally.
- Dense-material scenarios preserve stronger disposal protection via config-backed multipliers.
- Mattress/box-spring disposal impacts total and remains note-based for customer presentation.
- Current customer charge calibration is $60 per mattress and $60 per box spring.
- North Bay dump/disposal jobs may use the internal local default of approximately 50 km / 48 minutes round trip only when no better route or time data is supplied.
- The dump-route default must not be applied to ordinary small moves, item deliveries, demolition jobs, scrap pickup, or generic non-disposal work.
- Internal landfill assumptions include: $10 for 6 bags or less; $25 for 7+ bags / half-ton truck or trailer; $35 for vehicle + trailer double load; $118/tonne for dual-axle weighed trailer with $25 minimum; $236/tonne for mixed/contaminated load; $30 each mattress/box spring landfill cost; $25 each refrigerant appliance; $25 wood/tree brush; and free clean separated grass/leaves/concrete without rebar/bricks/tires.
- GPT must not expose landfill cost, margin, owner-review wording, or internal disposal calibration as customer-facing quote line items.

## Scrap Rules

- Curbside scrap pickup uses a dedicated scrap path in `app/quote_engine.py` and follows the normal scrap/minimum behavior.
- Inside scrap removal adds $30 CAD above the normal scrap/minimum behavior.
- If curbside scrap is $60 CAD cash, inside scrap is $90 CAD cash before EMT/HST.
- GPT must not describe current scrap quote outcomes as "free curbside" or as only "$30 inside"; inside is the normal scrap/minimum amount plus the inside removal charge.
- Scrap does not run through the haul-away labour, travel-zone, or disposal ladders.

## Access and Awkwardness

- Access difficulty adders protect margin for difficult/extreme conditions.
- Tiny awkward haul-away jobs use access-aware floor protection where configured.

## Trailer and Load Rules

- Haul-away supports bag-type anchors and trailer-fill floor anchors.
- Class-specific trailer fill anchors apply where configured.
- Small move/item delivery use enclosed trailer adders where configured.
- Optional haul-away `space_fill` mode applies bounded discount logic with class floors.
- High-care appliance/moving jobs with 4 workers and 6+ hours should trigger internal owner review when item/property risk or extra-care handling is present; this advisory has no pricing effect and is not customer-visible.

## Item Delivery Guardrail

- Item delivery enforces a protected pre-access floor before access adjustments.
- Item delivery remains within the single pricing engine path.

## Demolition Safeguards

- Demolition pricing safeguards live only in `app/quote_engine.py`.
- Controlled/light demolition has a protected runtime floor.
- Normal demolition, mixed demolition materials, unknown/hidden material wording, apartment/elevator/access wording, structure teardown wording, heavy material wording, and heavy-plus-access combinations use higher runtime floor protection to avoid undercharging.
- Soil, concrete, brick, stone, masonry, rubble, tile, shingles, fireplace/chimney, and similar heavy demolition material wording must stay margin-protective.
- Structure teardown wording such as sheds, decks, fences, gazebos, structures, outbuildings, teardown, tear down, or dismantle must stay owner-review eligible.
- Unknown or hidden demolition material scope must stay owner-review eligible.
- GPT may explain the safeguards and flag owner-review concerns, but it must not calculate demolition pricing outside `app/quote_engine.py`.

## Margin-Protection Philosophy

- Bay Delivery is not tuned to be the cheapest option.
- Convenience, awkwardness, density, access, disposal risk, and real labour must affect price.
- Large/awkward jobs must not be flattened unrealistically.
- Pricing changes must stay narrow, auditable, and explicitly approved.

## GPT Constraint

The GPT may describe these rules and help maintain documentation/process alignment.

The GPT may not invent, override, or bypass pricing behavior implemented in `app/quote_engine.py` and repo-approved config.
