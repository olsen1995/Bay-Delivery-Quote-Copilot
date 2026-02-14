# GitHub Copilot Instructions – Life OS — Practical Co-Pilot

## Mandatory Guardrails

Copilot must follow these rules when assisting in this repo.

### Precedence (if conflict):

**Wrapper > Instructions.txt > Knowledge > Copilot instructions**

---

## DO NOT:

- Modify `instructions/Instructions.txt` unless explicitly asked.
- Invent new modes, routing logic, safety systems, or “philosophies.”
- Bypass upload handling or high-risk rules.
- Expose internal system labels (e.g., “router”, “CI”, “manifest”, file paths).
- Assume repo auto-syncs to GPT. All pastes/uploads are manual.
- Optimize, refactor, rename, restructure, or add automation/scripts unless requested.

## ALWAYS:

- Treat `instructions/Instructions.txt` as canonical.
- Preserve existing structure unless user directs otherwise.
- Prefer reversible, low-risk actions.
- Stay scoped to the user’s request. No “while we're here…” edits.
- Assume commits are done in **VS Code Source Control UI**, not terminal.

---

## Required Testing (if `tools/quicksmoke.ps1` exists)

Instruct user to run it if:
- `instructions/`, `canon/`, `knowledge/` are modified
- Instruction or routing logic is changed

If not present: ask user what test to run or refer to `tests/QuickSmoke_Prompts.md` (if it exists).

---

## GPT Runtime Notes

- The Custom GPT textbox allows ~8000 characters.
- Never recommend pasting full Instructions.txt.
- Use the wrapper at `docs/CustomGPT_Instructions_Wrapper.md` + any needed Knowledge uploads.
- Knowledge uploads are **manual**.

---

## Output Discipline

### Standard structure (default):

1. **STOP** — Only if immediate harm/risk
2. **Steps** — Numbered (3–8), least-risk first
3. **Quick check** — Optional; only if info is missing and safety is impacted

### Formatting rules:

- No emojis or decorative headings
- No add-ons, templates, variants unless user asked
- Never say “Would you like…”

### Memory:

- Never claim memory unless user asks and proper mechanism is used

### Evidence:

- Prefer live authoritative sources for high-stakes or time-sensitive answers
- Else, use conservative guidance; don’t name authorities

### Canadian Context:

- Use CAD and Canada-based context when money/logistics are involved

---

## Preferred Workflow (Copilot view)

1. Edit `instructions/`, `knowledge/`, `canon/`, or `tests/`
2. Run `tools/quicksmoke.ps1` if those files change
3. Manually verify using `tests/QuickSmoke_Prompts.md` (if exists)
4. Commit via VS Code Source Control (no terminal)
5. Manually update GPT instructions + knowledge

---

## Key Files

- `instructions/Instructions.txt` — Canonical runtime spec
- `docs/CustomGPT_Instructions_Wrapper.md` — 8000-char GPT wrapper
- `knowledge/00_Bay Delivery Quote Copilot_Constitution.md` — Core constraints
- `knowledge/01_ModeRouter.md` — Routing rules
- `canon/CANON_MANIFEST.json` — Canon manifest
- `tests/QuickSmoke_Prompts.md` — Manual test prompts
- `tools/quicksmoke.ps1` — Smoke test
