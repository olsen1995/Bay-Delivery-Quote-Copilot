# GitHub Copilot Instructions for Life OS — Practical Co-Pilot

## Copilot Guardrails (Mandatory)

When assisting in this repository, GitHub Copilot MUST follow these rules:

### DO NOT
- Do NOT modify `instructions/Instructions.txt` unless the user explicitly asks.
- Do NOT invent new modes, safety gates, routing logic, or philosophies.
- Do NOT bypass the Upload Analysis Gate or Risk Gate under any circumstance.
- Do NOT reference internal system labels (e.g., “Mode Router”, “ARP Gate”, “Upload Analysis Gate”) in user-facing outputs.
- Do NOT assume files auto-sync to the Custom GPT (manual upload is always required).
- Do NOT optimize, refactor, or “clean up” architecture unless explicitly requested.

### ALWAYS
- ALWAYS treat `instructions/Instructions.txt` as the runtime source of truth.
- ALWAYS treat `canon/CANON_MANIFEST.json` as the authoritative canonical manifest.
- ALWAYS preserve existing architecture unless the user explicitly requests a change.
- ALWAYS instruct the user to run `.\tools\quicksmoke.ps1` after:
  - modifying instructions
  - modifying canon or routing files
  - adding or removing knowledge files
- ALWAYS prefer reversible, least-risk actions over irreversible ones.
- ALWAYS follow output hygiene rules silently (no internal labels in responses).

Failure to follow these rules is considered incorrect assistance.

---

## Project Overview

This repository is the source of truth for **Life OS — Practical Co-Pilot**, a Custom GPT assistant for grounded, real-world decision-making and life management.

The system routes user requests to specialized modes (e.g., Day Planner, Life Coach) and enforces mandatory safety gates such as the Upload Analysis Gate for any uploaded content.

---

## Architecture

### Modes
- Domain-specific playbooks live in `knowledge/`
  - Examples: `02_DayPlanner.md`, `04_LifeCoach.md`
- Each mode defines:
  - Scope of responsibility
  - Required response structure
  - Safety constraints

### Routing
- Governed by `knowledge/01_ModeRouter.md`
- Rules:
  - Explicit user requests override implicit routing
  - Ambiguous requests are routed conservatively
  - Mid-response mode switching is forbidden unless safety requires it

### Safety Gates
- **Upload Analysis Gate** (mandatory for uploads):
  1. Ingest & classify upload
  2. Full scan of contents
  3. Consistency and logic check
  4. Risk label: Safe / Risky / Do-Not-Touch
  5. Missing-data check
  6. Confidence statement
- **Risk Gate**:
  - For health, vehicles, electricity, chemicals, food safety, or significant money
  - Enforce Stop/Check behavior and escalation guidance

### Adaptive Response Protocol (ARP)
Responses adapt based on:
- **Energy**: Low → simplify
- **Time**: Quick → summary only
- **Confidence**: <80% → separate known vs assumed
- **Risk**: Apply safety gates before advising

---

## Developer Workflow

### Making Changes
- Edit:
  - `instructions/Instructions.txt`
  - files in `knowledge/`
  - files in `tests/`
- Commit changes to GitHub
- Manually upload updated instruction content to the Custom GPT  
  (GitHub does NOT auto-sync to the GPT runtime)

### Testing (Mandatory)
- **Automated**:
  - Run `.\tools\quicksmoke.ps1`
  - Must PASS before changes are considered safe
- **Manual**:
  - Validate behavior using `tests/QuickSmoke_Prompts.md`

### Versioning
- Update `VERSION` and `CHANGELOG.md` when applicable
- Tag releases (e.g., `v0.1.0`, `v1.0.0`)

### Repo Sync Discipline (for GPT context)
- Conservative fetch order:
  1. `VERSION`
  2. `canon/CANON_MANIFEST.json`
  3. Files listed in manifest runtime load order
- Newly fetched content overrides stale internal GPT context

---

## Conventions

### Output Hygiene
- Never expose internal system concepts or labels
- Follow constitutional rules silently

### Memory Discipline
- Never claim to store or remember information unless the user explicitly asks

### Evidence Discipline
- For high-stakes or time-sensitive topics:
  - Browse authoritative sources
  - Cite sources
  - Do not name authorities without browsing

### Question Restraint
- Ask no more than 1–3 questions
- Only ask questions that materially affect outcome or safety

### Decision Philosophy
- Prefer least-risk and reversible actions
- Choose lowest-regret paths when options are similar

### Non-Repetition
- Avoid repeating advice unless required for clarity or safety

---

## Examples

### Upload Handling
User uploads a CSV log:
- Classify as “device log”
- Scan for errors and outliers
- Risk-label as “Risky” if anomalies are present
- State “Medium confidence” if applicable
- Ask for clarification before advising changes if harm is possible

### Routing
User asks “plan my day”:
- Route to Day Planner mode per `01_ModeRouter.md`

### Response Adaptation
Low-energy user:
- Provide the simplest safe steps
- Avoid optimization or overload

---

## Key Files

- `knowledge/00_LifeOS_Constitution.md` — Core constitution and philosophy
- `knowledge/01_ModeRouter.md` — Routing rules
- `instructions/Instructions.txt` — Runtime instructions (source of truth)
- `canon/CANON_MANIFEST.json` — Canonical content manifest
- `tests/QuickSmoke_Prompts.md` — Manual behavior validation checklist
- `tools/quicksmoke.ps1` — Automated repo integrity smoke test
