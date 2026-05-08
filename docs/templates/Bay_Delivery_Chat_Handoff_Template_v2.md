# Bay Delivery Quote Copilot — Chat Handoff Template v2

**Updated:** 2026-05-08
**Project:** Bay Delivery Quote Copilot
**User:** Austin / Bay Delivery
**Primary repo path:** `C:\Repos\Bay-Delivery-Quote-Copilot`

---

## 0. Start Here — Instructions for the New Chat

You are continuing the **Bay Delivery Quote Copilot** project.

This is a real production operations and quoting system for Bay Delivery in North Bay, Ontario. It is not LifeOS, not Canon, and not a governance experiment.

**First response should confirm:**

- Current project baseline understood.
- Latest merged PR / commit: `[PR # / commit / title]`.
- Current version: `[version]`.
- Next safest task: `[task]`.
- Whether repo/live verification is needed before implementation.

**Default behaviour:**

- Answer first, then explain.
- Use Canadian dollars.
- Protect margin over winning bad jobs.
- Keep changes narrow, reversible, and test-backed.
- Provide copy/paste-ready Codex prompts when repo work is needed.
- Do not suggest pricing changes without considering market price, operating cost, risk, and current quote-engine behaviour.

---

## 1. Project Overview

**Project name:** Bay Delivery Quote Copilot
**Repo:** `https://github.com/olsen1995/Bay-Delivery-Quote-Copilot`
**Render App:** `https://bay-delivery-quote-copilot.onrender.com`
**Home:** `https://bay-delivery-quote-copilot.onrender.com/`
**Quote page:** `https://bay-delivery-quote-copilot.onrender.com/quote`
**Admin:** `https://bay-delivery-quote-copilot.onrender.com/admin`
**Mobile Admin:** `https://bay-delivery-quote-copilot.onrender.com/admin/mobile`
**Health:** `https://bay-delivery-quote-copilot.onrender.com/health`
**Current version:** `[inspect repo: Get-Content VERSION]`

**Purpose:**

- Prevent undercharging.
- Protect Bay Delivery margin.
- Support real customer quote/job workflows.
- Keep admin operational and internal.
- Keep customer quote flow simple and trustworthy.
- Keep GPT internal-only and recommendation-only.

**Stack:**

- FastAPI
- Python 3.11
- SQLite
- Uvicorn
- Static HTML/CSS/JS frontend
- Render deployment
- No React
- No complex frontend build system

---

## 2. Required Live / Repo Verification

Before implementation, verify as needed:

```powershell
cd C:\Repos\Bay-Delivery-Quote-Copilot

git checkout main
git pull --ff-only
git status -sb
git log --oneline -8
```

Standard validation:

```powershell
.\.venv\Scripts\python.exe tools\check_version_parity.py
.\.venv\Scripts\python.exe -m compileall app tools scripts tests
.\.venv\Scripts\python.exe -m pytest -q
```

Conditional checks (only when relevant to the task):

```powershell
# GPT grounding parity — run the export script first, then check parity:
#   .\.venv\Scripts\python.exe tools\export_gpt_grounding_pack.py --output-dir dist\gpt_grounding_pack
#   .\.venv\Scripts\python.exe tools\check_gpt_grounding_pack_parity.py

# Dependency audit — pip-audit is CI-only; not installed locally by default.
# If needed locally, install first:
#   .\.venv\Scripts\python.exe -m pip install pip-audit==2.10.0
#   pip-audit -r requirements.lock.txt
# CI runs this automatically. See .github/workflows/ci.yml.
```

Post-deploy live smoke, only when relevant:

```powershell
$env:BASE_URL='https://bay-delivery-quote-copilot.onrender.com'
.\.venv\Scripts\python.exe scripts\smoke_test.py --mode post-deploy
```

---

## 3. Current System State

**Latest merged PR:** `[PR # / title]`
**Latest main commit:** `[commit sha / title]`
**Current phase:** `[stable refinement / pricing calibration / admin hardening / etc.]`
**Production state:** `[healthy / needs verification / unknown]`
**Local validation state:** `[tests passed / pending]`

**Important current baseline:**

- Pricing authority remains `app/quote_engine.py` only.
- Public customer quote flow remains active.
- Admin is internal operations only.
- SQLite is source of truth.
- Google Calendar is mirror/convenience only.
- GPT is internal-only/recommendation-only and must not override pricing.

---

## 4. Core Business Rules — Do Not Change Without Discussion

**Pricing authority:** `app/quote_engine.py`

**Locked rules:**

- One pricing engine only.
- No duplicate pricing logic.
- Cash quotes do not include HST.
- EMT/e-transfer quotes add 13% HST.
- Currency is CAD.
- Travel minimum: $20 gas + $20 wear = $40 minimum.
- Dump run minimum: $50.
- Small move minimum: $60.
- Demolition minimum: $75.
- Other minimum: $50.
- Mattress disposal: $50 per mattress.
- Box spring disposal: $50 per box spring.
- Scrap curbside can be free only when pure/easy/route-compatible.
- Inside/basement/heavy scrap should be treated with higher labour/access risk.

**Internal labour cost anchors:**

- Operator/Austin internal anchor: $20/hr.
- Helper internal anchor: $16/hr.

**Critical distinction:** internal labour cost is not the customer-facing labour rate. Customer-facing labour should usually be much higher, often around $50-$100+/hr depending on service type, crew size, equipment, access, damage risk, and job risk.

---

## 5. Bay Delivery Operating Modes

Model two versions of Bay Delivery:

### Mode A — Current Lean Owner/Operator

Bay Delivery is currently closer to a lean “guy with truck + trailer” operation.

- Lower fixed overhead.
- More flexible pricing.
- Still must cover fuel, wear, disposal, helper pay, tools, time, risk, and profit.
- Still must consider legal, tax, insurance, safety, and liability risks.
- Still should not race casual underpriced haulers to the bottom.

### Mode B — Future Formal Business

Future formal model may include:

- Business registration/licensing verification.
- Commercial auto/business insurance.
- General liability insurance.
- Cargo/customer-belongings coverage.
- WSIB considerations if applicable.
- Bookkeeping/accounting.
- Software/admin systems.
- Advertising/marketing.
- Written cancellation/damage policies.
- PPE/safety procedures.
- Higher risk reserve.
- Stronger professional pricing floor.

---

## 6. Vehicles and Trailer Inventory

### Vehicles

1. **2015 Dodge Ram 1500 5.7L HEMI**
   - Work/hauling truck.
   - Used for dump runs, trailer hauling, scrap pickup, junk removal, deliveries, and general Bay Delivery work.

2. **2019 Dodge Ram 1500 Classic Warlock Edition 5.7L HEMI crew cab / 4 full-size doors**
   - Used or available as work/hauling truck.
   - Important for fuel, wear, towing cost, payload/trailer usage, maintenance, and depreciation assumptions.

### Trailers

1. **single_axle_aluminum**
   - Most dump runs.
   - Light household junk.
   - Normal garbage.
   - Lighter materials.
   - Default open trailer for ordinary dump runs and smaller/light loads.

2. **double_axle_aluminum**
   - Heavy loads.
   - Wood.
   - Construction materials.
   - Bricks.
   - Dense demo debris.
   - Big scrap loads.
   - Full/heavy dump runs.
   - Jobs where single axle is full/insufficient.

3. **older_enclosed**
   - Random rough stuff.
   - Scrap storage/hauling.
   - Mattresses.
   - Box springs.
   - Dirty enclosed loads.
   - Enclosed hauling where item is not a high-value/nice moving job.

4. **newer_enclosed**
   - Moving jobs.
   - Furniture delivery.
   - Appliance delivery.
   - Nice customer-owned items.
   - Rain/snow/weather-sensitive jobs.
   - Damage/weather protection.

---

## 7. Tool Usage Strategy

> Canonical tool-selection rules are in `AGENTS.md`. This section summarises the intent.

**ChatGPT role:**

- Planning.
- Research interpretation.
- Architecture judgment.
- Prompt creation.
- Review and risk analysis.
- Pricing/business logic reasoning.

**Codex role:**

- Narrow implementation.
- Tests.
- Branch/commit/PR creation.
- Validation.
- Final implementation report.
- Audit/planning tasks.

**VS Code Agent role:**

- Read-only post-merge verification (default).
- Read-only audits, repo mapping, and test coverage mapping.
- Audit/planning tasks and codebase exploration (read-only).
- No file edits, commits, or PRs unless explicitly requested.

See `AGENTS.md` for the full authoritative tool-selection and scope-boundary rules.

---

## 8. Workflow

Default workflow:

```text
Plan -> Implement -> Validate -> Branch/Commit -> PR -> Review -> Merge -> Post-merge verification -> STOP
```

No shotgun PRs. One business concept per PR when pricing is involved.

---

## 9. Recent Completed Work

**Do not hard-code PR history here.** Look up current state before filling this in:

```powershell
git log --oneline -10
```

For each handoff, fill in:

- PR number and title.
- Status: merged/open/reviewed/blocked.
- Files changed.
- Validation result.
- Whether production/runtime changed.

---

## 10. Current Pricing Calibration State

The calibration harness is:

```powershell
.\.venv\Scripts\python.exe scripts\run_price_calibration_mocks.py
```

It currently reports:

- Current quote-engine price.
- EMT/e-transfer price.
- Mock labour/disposal/fuel/other/scrap values.
- Profit.
- Margin.
- Profit risk flag.
- Market target cash floor.
- Market target range.
- Gap to target floor.
- Market flag.
- Equipment type.
- Trailer type.
- Recommended trailer.
- Load weight class.
- Disposal mode.
- Owner-review scenarios.

Current strongest pricing risks:

1. Demolition: urgent; losing money and under market.
2. Moving: can be profitable but under market; true moving jobs often need $500+.
3. Heavy/dense/double-axle disposal: needs safeguards.
4. Delivery: longer distance/weather/protection/access needs escalation.
5. Scrap: curbside easy is fine; basement/awkward/heavy is risky.
6. Mattress/refrigerant/disposal-heavy jobs need stronger structured handling.

---

## 11. Next Step

**Do not hard-code the next step here.** Current priorities drift quickly; always read the authoritative sources before planning work:

1. Read `docs/gpt/GPT_CURRENT_STATE.md` — authoritative current phase, priorities, and what should not happen next.
2. Read `AGENTS.md` — canonical workflow and scope-boundary rules.
3. Read `README.md` — current stable milestone and pointers to key docs.
4. Run `git log --oneline -8` to confirm the latest merged work.

Only after reviewing those should a next-step recommendation be formed.

---

## 12. What Not To Do Yet

Do not:

- Change `app/quote_engine.py` without research + plan.
- Add a second pricing engine.
- Let GPT override pricing.
- Add broad admin redesign.
- Add mobile admin costing expansion.
- Add reporting dashboards before real costing data exists.
- Auto-price hazardous/suspicious demolition.
- Auto-price dense demo/construction debris by volume only.
- Race casual cheap haulers to the bottom.

---

## 13. Final Note

Bay Delivery should be competitive, but not cheap for the sake of being cheap. The system should protect Austin from undercharging, protect the trucks/trailers, account for real labour and risk, and help choose the right job at the right price.
