# Bay Delivery Market & Pricing Strategy

## Purpose

This note exists to keep Bay Delivery quote calibration aligned with:

- the real North Bay market
- the kinds of jobs Bay Delivery actually wants
- margin protection
- practical service positioning

This is not a public marketing document.
This is an internal strategy note for pricing decisions, quote-engine tuning, and business judgment.

---

## Core Business Position

Bay Delivery is best positioned as:

**fast, local, hands-on help for annoying small-to-mid jobs that are too much for DIY but too small, awkward, or mixed-up for larger competitors to handle efficiently.**

Bay Delivery is **not** trying to be:

- the cheapest mover
- the cheapest junk hauler
- a full-scale premium moving company
- a bin rental substitute for every large cleanup
- everything to everyone

The business should compete hardest where:

- speed matters
- labour matters
- convenience matters
- awkwardness matters
- mixed service jobs matter

Examples:

- junk removal with loading
- dump runs
- awkward basement or garage jobs
- light demo + cleanup
- delivery + removal combo jobs
- smaller property cleanups
- selective moving jobs at worthwhile pricing

---

## Local Market Anchors

The local market matters because quote outputs are judged against what customers can already find.

### Junk Removal Anchors

Visible competitors in or around North Bay have public minimums and volume-pricing signals in roughly this range:

- **705 Junk**: publicly signals a **$100 minimum charge**
- **J.O. Junk**: publicly signals **$125 + HST minimum pickup fee**
- higher volume jobs scale up into several-hundred-dollar ranges

### What this means

For Bay Delivery:

- very small junk jobs should stay in a **believable local band**
- tiny/easy jobs should not look wildly overpriced versus visible local competitors
- tiny/easy jobs should also not be priced so low that dispatching them becomes stupid financially

The goal is not “match everyone.”
The goal is “be credible, competitive enough, and still worth doing.”

---

## Moving Market Position

Moving is a valid service lane, but it is **not a favourite Bay Delivery service**.

That matters.

### Bay Delivery move philosophy

Bay Delivery should treat moving as:

**selective, higher-hassle, premium-ish work that must be worth doing to accept.**

This means Bay Delivery should **not** optimize small_move pricing around:

- winning every move lead
- being the cheapest mover
- chasing low-budget moving customers

Instead, move pricing should:

- protect margin
- reflect hassle/risk
- filter out bad-fit move jobs
- remain competitive only where the price is still worthwhile

### Practical rule

If a move quote feels merely “cheap enough to win,” it may still be too low.

If a move quote feels “a bit expensive but still below a premium mover,” that may be the correct zone.

---

## Competitor Positioning Summary

### 1. Small junk competitors

These competitors tend to win:

- single bulky items
- easy curbside jobs
- simple junk calls
- customers shopping obvious minimum prices

### 2. Convenience-first junk competitors

These competitors tend to win:

- customers who want polished booking
- customers who value fast quoting and easy scheduling
- full-service junk jobs where labour is part of the convenience

### 3. Bin / dumpster / higher-volume cleanup competitors

These competitors tend to win:

- larger cleanouts
- renovation debris
- estate cleanouts
- jobs where volume is obvious and several-hundred-dollar pricing feels normal

### 4. Full-service movers

These competitors tend to win:

- serious residential moves
- commercial/office moves
- higher-trust move jobs
- customers expecting a full moving-company experience

### Bay Delivery implication

Bay Delivery should focus on the overlap zone where:

- the job is annoying
- the customer wants hands-on help
- the scope is too mixed or awkward for a simple bin solution
- the customer is not necessarily trying to hire a premium mover

---

## Services to Chase Hard

These are the jobs Bay Delivery should feel good about pursuing aggressively.

### A. Small-to-mid junk jobs with labour

Examples:

- furniture haul-away
- appliance removal
- garage junk
- basement junk
- local cleanup jobs with loading included

### B. Hybrid labour jobs

Examples:

- junk + demo
- delivery + removal
- cleanup + haul-away
- small mixed property cleanup jobs

### C. Awkward / annoying jobs

Examples:

- difficult access
- dirty or unpleasant loads
- “I just need this gone” jobs
- jobs where the labour/convenience is the real product

---

## Services to Quote Selectively

These are jobs Bay Delivery can still do, but the quote should reflect caution and margin protection.

### A. Moving jobs

Especially:

- 4–5 hour small moves
- apartment moves with stairs
- commercial/light business moves
- heavier or more awkward furniture moves

### B. High-volume haul-away jobs

Especially:

- estate cleanouts
- garage cleanouts
- 16+ bag jobs
- jobs where disposal volume starts to resemble a mini-cleanout rather than a simple pickup

---

## Services That Must Not Be Priced Too Softly

### 1. Moves

Because:

- they are least favourite work
- they carry more hassle/risk
- they are already underquoting in calibration
- the local moving market supports higher pricing than your current engine is sometimes producing

### 2. Large cleanouts

Because:

- customers already understand bigger cleanup jobs cost real money
- local competitors and bin alternatives support stronger pricing expectations
- flattening disposal too much can quietly destroy margin

### 3. Awkward access jobs

Because:

- stairs, basement access, long carries, and awkward loading are labour-intensive
- convenience and labour are part of the value
- these are not “just hauling” jobs

---

## Quote Engine Calibration Principles

These principles should guide future pricing changes.

### Principle 1: Protect margin over “cheap-looking” estimates

A quote that looks friendly but loses money is not a good quote.

### Principle 2: Tiny junk jobs should stay believable vs local minimums

For very small/easy junk jobs:

- do not overshoot the local market badly
- do not underprice below a sensible dispatch-worth-doing level

### Principle 3: Moves are selective premium work

Do not tune small_move to chase volume.
Tune it so accepted jobs are worth doing.

### Principle 4: Large cleanouts need progressive scaling

Do not let high-volume haul-away flatten unrealistically.
Bigger jobs should continue scaling in a way that protects margin.

### Principle 5: Convenience is part of the product

Fast, local, hands-on, “we’ll deal with it” service has value.
Do not strip that value out of the quote.

### Principle 6: Awkwardness deserves pricing

Difficult access, dense materials, ugly handling, and mixed labour should not be treated like easy curbside jobs.

---

## Current Strategy Implications for the Quote System

### Current haul-away implementation state (post rollout)

Haul-away pricing now supports optional inputs that act as floors:

- `bag_type` (`light`, `heavy_mixed`, `construction_debris`) applies a per-bag floor
- `trailer_fill_estimate` (`under_quarter`, `quarter`, `half`, `three_quarter`, `full`) applies a fill floor
- `trailer_class` (`single_axle_open_aluminum`, `double_axle_open_aluminum`, `older_enclosed`, `newer_enclosed`) selects class-specific fill anchors when configured

Current quote-engine ordering for haul-away:

1. Build base cash from travel + labour + disposal + mattress/boxspring + access
2. Apply service minimum floor
3. Apply optional haul-away floors and keep the highest value before rounding

Current trailer-lane behavior:

- `single_axle_open_aluminum` has class-specific fill anchors configured
- `double_axle_open_aluminum` is accepted and currently uses default fill anchors
- enclosed classes are accepted and currently use default fill anchors

Current scope limit:

- enclosed trailer classes are supported inputs, but there is no additional enclosed-class pricing impact yet

### Highest current pricing priority

**haul-away optional-input lane calibration**

Reason:

- foundation is now in place (`bag_type`, `trailer_fill_estimate`, `trailer_class`)
- lane-specific anchors now need evidence-based refinement, not structural rewrites
- this can be tuned with narrow config-level changes

### Likely next priority after that

**small_move calibration**

Reason:

- remains selective, higher-hassle work
- quotes should continue filtering bad-fit move jobs and preserving margin

### Lower priority than those

**high-volume haul-away scaling + 5-8 bag cleanup**

Reason:

- 16+ progression and 5-8 bag edge handling still matter
- but both now sit behind lane-floor validation and small_move protection

---

## Practical Bay Delivery Pricing Posture

### Junk jobs

- stay believable
- stay worth dispatching
- do not race to the bottom
- labour/convenience should still be reflected

### Moves

- quote high enough that the job is worth the hassle
- losing some move leads is acceptable
- being cheaper than premium movers can still be enough

### Bigger cleanouts

- quote like real disposal + labour work
- do not underprice simply because one trailer can hold multiple jobs operationally
- do not pass theoretical dump-efficiency savings back to customers automatically

---

## What Future PRs Should Respect

Any pricing PR should be checked against this note.

Before merging a pricing change, ask:

1. Does this make Bay Delivery more likely to undercharge on work we already dislike?
2. Does this make tiny junk jobs look unrealistic against local visible minimums?
3. Does this flatten larger cleanout pricing too much?
4. Does this remove value from convenience/labour/access?
5. Are we tuning to win every lead, or to win the right leads?

If the change helps win bad-fit jobs cheaply, it is probably the wrong change.

---

## Decision Rule Summary

### Bay Delivery should

- chase small-to-mid labour-heavy junk jobs
- price moves selectively and strongly
- scale larger cleanouts more aggressively than tiny pickups
- treat convenience and awkward labour as premium value

### Bay Delivery should not

- act like a bargain mover
- underprice large haul-away jobs
- optimize quotes only to “look nice”
- assume every competitor should be matched on price

---

## Bottom Line

Bay Delivery should be calibrated to win the **right** jobs, not the **most** jobs.

That means:

- believable tiny junk pricing
- stronger move pricing
- stronger large-cleanout scaling
- no apology for labour, awkwardness, or convenience premiums
