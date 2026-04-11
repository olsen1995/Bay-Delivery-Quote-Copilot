# GPT Refresh Workflow – Bay Delivery Quote Copilot

## Purpose

This runbook documents the manual-on-release GPT grounding refresh process.

Follow this runbook whenever a release changes content that the grounding pack depends on.

---

## When to Refresh

Refresh GPT grounding on every release that changes any of the following:

- `PROJECT_RULES.md`
- Any file in `docs/gpt/`
- `docs/CURRENT_STATE.md`
- Pricing rules in `app/quote_engine.py` or `config/business_profile.json`

If none of the above files changed in a release, grounding refresh is optional.

---

## Refresh Steps

### 1. Pull the latest release

```bash
git pull origin main
```

Confirm the release version in `VERSION` matches what was deployed to Render.

### 2. Export the grounding pack

```bash
python tools/export_gpt_grounding_pack.py --output-dir dist/gpt_grounding_pack
```

Review the generated `dist/gpt_grounding_pack/manifest.json` to confirm the expected files are included and the SHA-256 hashes reflect the latest content.

### 3. Open GPT Builder

Navigate to [https://chat.openai.com](https://chat.openai.com) and open the Bay Delivery internal advisor GPT in GPT Builder (Edit GPT).

### 4. Replace the knowledge files

In the **Knowledge** section:

- Remove all previously uploaded grounding files.
- Upload exactly the files listed in `docs/gpt/GPT_KNOWLEDGE_PACK.md` — use the local copies from `dist/gpt_grounding_pack/`.

Upload only the `.md` files from `dist/gpt_grounding_pack/`. Do not upload `tools/export_gpt_grounding_pack.py` or `manifest.json`.

### 5. Update Builder instructions if needed

If `docs/gpt/GPT_BUILDER_INSTRUCTIONS.md` changed in this release:

- Open the **Instructions** field in GPT Builder.
- Replace the existing block with the updated block from `docs/gpt/GPT_BUILDER_INSTRUCTIONS.md`.

### 6. Save and publish

Save and publish the updated GPT in Builder.

### 7. Run acceptance tests

Open a fresh chat with the GPT and run the acceptance questions from `docs/gpt/GPT_ACCEPTANCE_TESTS.md`.

All questions must pass before the refresh is considered complete.

### 8. Record the refresh

Note the refresh in the release notes or internal ops log:

```
GPT grounding refreshed for vX.Y.Z – files: [list], manifest hash: [hash from manifest.json]
```

---

## Rollback

If a grounding refresh causes the GPT to produce incorrect or drifted output:

1. Re-export from the previous release commit using `tools/export_gpt_grounding_pack.py`.
2. Repeat steps 4–7 with the previous release's files.

---

## What This Workflow Does NOT Cover

- This workflow does not change app runtime behavior.
- This workflow does not change pricing logic.
- This workflow does not change admin or booking workflows.
- The GPT is an internal advisor only. Refreshing it does not affect customer-facing quote behavior.
