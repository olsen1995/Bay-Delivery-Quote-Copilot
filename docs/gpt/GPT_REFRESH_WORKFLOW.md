# GPT Refresh Workflow

## Default Sync Model

Use manual-on-release refresh.

Repo doc changes are not considered GPT-live until the updated file is re-uploaded into the custom GPT Knowledge pack.

## Refresh Triggers

Refresh the Knowledge pack whenever any of these change materially:

- pricing behavior
- workflow boundaries
- current project state or launch stage
- business-rule-sensitive wording
- any file in `docs/gpt/`
- any release that changes how the system should be described internally

## Required Workflow

1. Update the canonical repo docs first.
2. Verify the repo truth against implementation where needed.
3. Re-upload the changed files in GPT Builder.
4. Run the acceptance question set in `docs/gpt/GPT_ACCEPTANCE_TESTS.md`.
5. Only then treat the advisor GPT as updated.

## Staleness Rule

If repo truth changed but the upload step has not happened yet, the GPT must be treated as stale.

## Future Scope Boundary

If live backend reads or tightly bounded actions are needed later, use a separate internal operator GPT with a narrow action schema.

Do not overload the advisor GPT with broad admin access or live operator duties.
