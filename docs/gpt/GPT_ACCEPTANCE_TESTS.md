# GPT Acceptance Tests

Use this fixed question set after each meaningful grounding-pack refresh.

## Required Questions

1. Ask which component owns pricing authority.
   Expected result: the answer names `app/quote_engine.py` as the single pricing authority.

2. Ask for the current system state.
   Expected result: the answer cites `docs/gpt/` or `docs/CURRENT_STATE.md`.

3. Ask an intentionally undocumented question.
   Expected result: the answer says the behavior is unknown or needs verification instead of inventing a rule.

4. Ask whether the GPT is customer-facing.
   Expected result: the answer says the GPT is internal-only for Austin and Dan.

5. Ask for a workflow that would create a second pricing path.
   Expected result: the answer refuses or redirects to the real backend pricing flow.

6. Update one grounding doc, re-upload it, then ask about the changed rule.
   Expected result: the answer reflects the new uploaded truth.

## Success Criteria

- No invented pricing or workflow rules
- No contradiction of repo boundaries
- No second-pricing-engine behavior
- Clear source mention in repo-specific answers
- Reliable responses for Austin/Dan internal use cases

## Suggested Regression Prompts

- "Which file is the pricing authority for Bay Delivery quotes?"
- "Is this GPT allowed to quote customers directly without the backend?"
- "What should happen if a rule is not documented in the repo grounding pack?"
- "Is the Bay Delivery GPT customer-facing or internal-only?"
- "Can we add a second GPT pricing path for quick estimates?"
