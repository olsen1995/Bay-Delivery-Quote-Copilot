# GitHub Copilot Instructions for Life OS — Practical Co-Pilot

## Copilot Guardrails (Mandatory)

When assisting in this repository, GitHub Copilot MUST follow these rules.

## Instruction Precedence (conflict resolver)

If instructions conflict, follow this precedence: Wrapper > Canonical instructions > Knowledge > Copilot instructions.

### DO NOT
- Do NOT modify `instructions/Instructions.txt` unless the user explicitly asks.
- Do NOT invent new modes, safety gates, routing logic, philosophies, or “systems.”
- Do NOT bypass required upload-handling or high-risk safety handling behavior under any circumstance.
- Do NOT reference internal system labels or repo mechanics in end-user outputs (e.g., mode/router/gate names, tiers, “playbook”, “reference”, “manifest”, “CI”, file paths, or “according to the repo/knowledge”).
- Do NOT assume files auto-sync to the Custom GPT (manual paste/upload/update is required).
- Do NOT optimize, refactor, restructure, rename folders/files, or “clean up” architecture unless explicitly requested.
- Do NOT introduce new automation, CI changes, scripts, or workflows unless explicitly requested.

### ALWAYS
- ALWAYS treat `instructions/Instructions.txt` as the canonical repo runtime specification.
- ALWAYS preserve existing architecture unless the user explicitly requests a change.
- ALWAYS prefer reversible, least-risk actions over irreversible ones.
- ALWAYS keep changes tightly scoped to the user’s request; no “while we’re here” improvements.
- ALWAYS assume commits are made via **VS Code Source Control UI** unless the user explicitly asks for terminal commands.

### REQUIRED TESTING (when applicable)
- If `tools/quicksmoke.ps1` exists in the repo, instruct the user to run it after:
  - modifying `instructions/Instructions.txt` or other instruction/wrapper documents
  - modifying `canon/` or routing documents
  - adding/removing `knowledge/` documents
- If `tools/quicksmoke.ps1` does NOT exist, do NOT invent it. Ask the user what test they want to run (or point to `tests/QuickSmoke_Prompts.md` if present).

Failure to follow these rules is considered incorrect assistance.

---

## Project Overview

This repository is the source of truth for **Life OS — Practical Co-Pilot**, a Custom GPT assistant for grounded, real-world decision-making and life management.

It maintains:
- Repo runtime instructions (`instructions/Instructions.txt`)
- Knowledge documents (`knowledge/`)
- Canon/manifest files (`canon/`)
- Prompt tests (`tests/`)
- Optional tooling (`tools/`)

---

## Custom GPT Runtime Notes (Critical)

- The Custom GPT “Instructions” textbox has an ~8000 character limit.
- Do NOT recommend pasting the full repo instructions into that textbox.
- Use the wrapper document (`docs/CustomGPT_Instructions_Wrapper.md`) plus Knowledge uploads.
- Knowledge uploads are manual; do not claim anything auto-syncs.

---

## Repo Architecture (Reference)

### Knowledge
- Domain-specific guidance lives in `knowledge/`
- Knowledge documents define scope, constraints, and response expectations.

### Routing (internal reference only)
- Governed by `knowledge/01_ModeRouter.md`
- Rules:
  - Explicit user requests override implicit routing
  - Ambiguous requests are handled conservatively
  - Mid-response switching is avoided unless safety demands it

### Safety Handling
- Upload-related requests must follow the repo’s required upload-handling behavior.
- High-risk domains (health/vehicles/electricity/chemicals/food safety/significant money) require least-risk ordering, clear hazard constraints, and escalation guidance when needed.

---

## Conventions & Output Discipline (End-User Outputs)

### Standard response shape (default)
- Include **STOP** only when immediate danger exists.
- Provide **numbered steps** (typically 3–8), least-risk first.
- Ask an optional **Quick check** (max 1–2 questions) only when missing info materially changes safety/outcome.

### Formatting constraints
- No emojis.
- Avoid decorative headings (“SUMMARY”, “OPTIONAL”, “PLAYBOOK”, etc.) unless they prevent harm or reduce confusion.
- Do not offer extra variants (“Want a low/medium/high-energy version?”) unless the user explicitly asked for customization.

### Evidence discipline
- For time-sensitive or high-stakes topics, prefer browsing authoritative sources and citing them.
- If not browsing, provide conservative best-practice guidance without naming authorities.

### Memory discipline
- Never claim to store/remember anything unless the user explicitly asks to save it and the correct mechanism is used.

### Canadian context
- Use CAD and Canada-relevant context when money/logistics are involved.

---

## Developer Workflow (Preferred)

1) Edit files in `instructions/`, `knowledge/`, `canon/`, or `tests/`
2) If `tools/quicksmoke.ps1` exists and changes touch instructions/canon/routing/knowledge, run it
3) Validate behavior using `tests/QuickSmoke_Prompts.md` (if present)
4) Commit using **VS Code Source Control UI**
5) Manually update the Custom GPT (wrapper/instructions + knowledge uploads)

---

## Key Files

- `instructions/Instructions.txt` — Canonical repo runtime specification
- `docs/CustomGPT_Instructions_Wrapper.md` — Compact GPT textbox wrapper (8000-char safe)
- `knowledge/00_LifeOS_Constitution.md` — Core philosophy/constraints
- `knowledge/01_ModeRouter.md` — Routing rules
- `canon/CANON_MANIFEST.json` — Canonical manifest (when relevant)
- `tests/QuickSmoke_Prompts.md` — Manual behavior validation prompts (if present)
- `tools/quicksmoke.ps1` — Repo integrity smoke test (if present)
