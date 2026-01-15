# Custom GPT Update Workflow — Life OS Practical Co-Pilot

This document defines the only supported process for updating the Custom GPT after making repository changes.

GitHub does NOT auto-sync to Custom GPTs. Updates are always manual.

## Source of Truth

- Runtime instructions: `instructions/Instructions.txt`
- GPT textbox wrapper: `docs/CustomGPT_Instructions_Wrapper.md`
- Canonical structure: `canon/CANON_MANIFEST.json`
- Knowledge files: `knowledge/`
- Safety & routing rules: enforced silently via instructions and knowledge

If these files are not uploaded, the GPT is stale.

## When You MUST Update the Custom GPT

You MUST re-upload files to the Custom GPT if you change:

- `docs/CustomGPT_Instructions_Wrapper.md`
- `instructions/Instructions.txt`
- Any file in `knowledge/`
- `canon/CANON_MANIFEST.json`
- Any core behavior rule explicitly referenced by runtime instructions

You do NOT need to update the GPT for:

- README changes
- ROADMAP changes
- Tests-only changes (unless they correspond to instruction/knowledge/canon changes)

## Required Pre-Checks

Before updating the Custom GPT:

- Confirm you are on the intended branch (default: main)
- Confirm all intended changes are committed and pushed
- If instructions, knowledge, or canon changed, run the repo smoke test if present

## Step-by-Step Update Process (Required)

### Step 1 — Make repo changes

Edit files as needed.

### Step 2 — Run QuickSmoke (if present)

From repo root, run:

```
.\tools\quicksmoke.ps1
```

If `tools/quicksmoke.ps1` does not exist, run the relevant manual prompts from `tests/QuickSmoke_Prompts.md` (if present).

### Step 3 — Identify files that must be uploaded

Upload is required for ALL changed files in these categories:

- **Wrapper**: `docs/CustomGPT_Instructions_Wrapper.md`
- **Runtime instructions**: `instructions/Instructions.txt`
- **Knowledge**: Any modified file(s) under `knowledge/`
- **Canon / manifest**: `canon/CANON_MANIFEST.json` (only if changed)

If unsure, upload the full knowledge set to avoid drift.

### Step 4 — Update the Custom GPT (Manual)

In the Custom GPT editor:

- Paste the wrapper into the Instructions textbox  
  Source: `docs/CustomGPT_Instructions_Wrapper.md`  
  Do NOT paste `instructions/Instructions.txt` into the textbox
- Upload the canonical runtime file  
  Upload: `instructions/Instructions.txt`
- Upload knowledge files  
  Upload: all relevant files under `knowledge/`
- Upload canon manifest if applicable  
  Upload: `canon/CANON_MANIFEST.json`

### Step 5 — Post-Update Verification (Required)

Immediately after updating the GPT, verify:

- **Response shape**  
  - Defaults to numbered steps  
  - Uses STOP only when immediate risk exists  
  - Asks no more than 1–2 questions when required
- **Upload handling**  
  - References to missing uploads prompt for upload  
  - No guessing or assumptions
- **High-risk behavior**  
  - Least-risk steps first  
  - Clear constraints embedded in steps  
  - Escalation guidance when appropriate

### Step 6 — Record the update (Recommended)

If behavior changed materially:

- Update `CHANGELOG.md`
- Bump `VERSION`
- Tag a release if appropriate
