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

## Scrap Rules

- Scrap pickup is hard-locked flat-rate behavior.
- Curbside scrap is free.
- Inside scrap pickup is a flat charge.
- Scrap bypasses labour, travel, and disposal logic.

## Access and Awkwardness

- Access difficulty adders protect margin for difficult/extreme conditions.
- Tiny awkward haul-away jobs use access-aware floor protection where configured.

## Trailer and Load Rules

- Haul-away supports bag-type anchors and trailer-fill floor anchors.
- Class-specific trailer fill anchors apply where configured.
- Small move/item delivery use enclosed trailer adders where configured.
- Optional haul-away `space_fill` mode applies bounded discount logic with class floors.

## Item Delivery Guardrail

- Item delivery enforces a protected pre-access floor before access adjustments.
- Item delivery remains within the single pricing engine path.

## Margin-Protection Philosophy

- Bay Delivery is not tuned to be the cheapest option.
- Convenience, awkwardness, density, access, disposal risk, and real labour must affect price.
- Large/awkward jobs must not be flattened unrealistically.
- Pricing changes must stay narrow, auditable, and explicitly approved.

## GPT Constraint

The GPT may describe these rules and help maintain documentation/process alignment.

The GPT may not invent, override, or bypass pricing behavior implemented in `app/quote_engine.py` and repo-approved config.
