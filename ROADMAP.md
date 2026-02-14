# Life OS — Practical Co-Pilot Roadmap

This roadmap defines the next features to build after the v0.1.0 baseline (QuickSmoke + GitHub Actions + Copilot guardrails).
Rule: ship small, test often, preserve safety gates.

---

## How to work (repeatable flow)

For each feature:

1) Implement the smallest viable change.
2) Run `.\tools\quicksmoke.ps1` (must PASS).
3) Validate behaviour with `tests/QuickSmoke_Prompts.md` when applicable.
4) Commit with a clear “create …” or “upgrade …” message.
5) Push and confirm GitHub Actions is green.

---

## Current Baseline (v0.1.0)

- Repo integrity QuickSmoke: `tools/quicksmoke.ps1`
- Automated CI on push/PR: `.github/workflows/quicksmoke.yml`
- Runtime instructions: `instructions/Instructions.txt`
- Canon manifest: `canon/CANON_MANIFEST.json`
- Manual behaviour checks: `tests/QuickSmoke_Prompts.md`
- Copilot guardrails: `.github/copilot-instructions.md`

---

## Feature 002 — Docs: “How to Update the Custom GPT” (Recommended next)

**Goal:** Create one clear step-by-step document explaining how to apply repo changes to the Custom GPT (manual upload workflow).
**Why:** Prevents “repo is updated but GPT is stale” confusion.

**Create file:**

- `docs/CustomGPT_Update_Workflow.md`

**Must include:**

- What file is the runtime source-of-truth (`instructions/Instructions.txt`)
- Exact manual upload steps
- When to re-run QuickSmoke
- Simple “Definition of Done” checklist

**Tests:**

- Run `.\tools\quicksmoke.ps1` → PASS

---

## Feature 003 — Tier 2 QuickSmoke: Core file presence checks

**Goal:** Expand QuickSmoke to assert core architecture files exist.
**Create/Update:**

- Update `tools/quicksmoke.ps1`

**Add checks (fail if missing):**

- `knowledge/00_Bay Delivery Quote Copilot_Constitution.md`
- `knowledge/01_ModeRouter.md`
- `instructions/Instructions.txt`
- `canon/CANON_MANIFEST.json`

**Tests:**

- Local QuickSmoke PASS
- GitHub Actions green

---

## Feature 004 — “Mode Router” unit test file

**Goal:** Add a small set of routing test cases with expected mode outcomes.
**Create file:**

- `tests/ModeRouter_Cases.md`

**Include:**

- 15–25 prompts
- Expected mode per prompt
- “Ambiguity” cases where the assistant should ask 1 question max

**Tests:**

- Manual validation only (no automation required yet)

---

## Feature 005 — Release discipline: v0.1.1

**Goal:** Standardize release steps for patch versions.
**Update files:**

- `CHANGELOG.md`
- `VERSION`

**Add doc:**

- `docs/Release_Process.md` (simple checklist: bump version → QuickSmoke → tag → push tags)

---

## Feature 006 — Canon hygiene: manifest linter (optional)

**Goal:** Add a script that validates `canon/CANON_MANIFEST.json` structure (optional, later).
**Create file (later):**

- `tools/manifest_lint.ps1`

**Tests:**

- Must be dependency-free
- Must not block unless it finds real errors

---

## Feature 007 — Prompt packs (optional)

**Goal:** Add curated prompt packs for common use:

- Bay Delivery
- Baby milestones
- Device optimization

**Create folder (later):**

- `prompt-packs/`

---

## Priorities (recommended order)

1) Feature 002 — Custom GPT update workflow doc
2) Feature 003 — Tier 2 QuickSmoke
3) Feature 004 — Mode Router test cases
4) Feature 005 — v0.1.1 release discipline
5) Feature 006–007 — optional expansion

---

## Definition of Done (for each feature)

- Files saved in correct paths
- QuickSmoke PASS
- GitHub Actions green
- Repo clean: `git status` shows working tree clean
