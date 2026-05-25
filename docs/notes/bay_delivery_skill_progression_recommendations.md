# Bay Delivery Skill Progression Recommendations

**Purpose:** Capture evidence-backed repo/workflow skills worth deepening for Bay Delivery Quote Copilot.

**Recommended status:** Save as a strategic note, not an active rule set yet.

**Suggested repo path:**

```text
docs/notes/bay_delivery_skill_progression_recommendations.md
```

## Best Use

This is not a task list. It is a future skill-hardening map.

Use it when a pattern repeats enough that it deserves a checklist, agent skill, or PR review standard.

---

## Ranked Priority

| Rank | Skill                                                               | Recommendation                                                                  |
| ---: | ------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
|    1 | Small-PR evidence discipline                                        | Most useful immediately. Keep using this in every PR review.                    |
|    2 | Protected-surface frontend contract review                          | Very useful for quote-page/customer-facing polish.                              |
|    3 | Docs and current-state traceability audit                           | Useful for version, SHA, roadmap, and grounding-pack accuracy.                  |
|    4 | Internal-only boundary review for admin, GPT, and notification work | Important before future GPT/admin/notification expansion.                       |
|    5 | SQLite mutation-safety review for operator tools                    | Use when touching data cleanup, backup/import/export, or persisted admin tools. |

---

## 1. Protected-Surface Frontend Contract Review

Deepen a review skill specifically for public quote-page polish where behavior must not move.

The repeated pattern in PR #298, PR #312, and PR #315 is not simply “make the UI nicer.” It is:

```text
Change copy/layout while proving IDs, names, enum values, selectors, data-step values, payload shape, and backend behavior stayed fixed.
```

### What the skill should enforce

- Confirm field IDs are unchanged.
- Confirm field names are unchanged.
- Confirm enum values are unchanged.
- Confirm selectors are unchanged.
- Confirm `data-step` values are unchanged.
- Confirm payload keys/shape are unchanged.
- Confirm backend behavior is unchanged.
- Check collapsible-field regressions.
- Check mobile overflow.
- Check step-label clarity.
- Require focused Playwright/static assertions when UI behavior changes.

### Trigger this skill when

- Public quote page copy/layout changes.
- Optional detail sections are collapsed/expanded/hidden.
- Service-specific fields are shown/hidden.
- Mobile quote UX changes.
- Any frontend quote behavior could affect estimate submission.

### Done criteria

- Protected no-go diff clean.
- Focused static tests pass.
- Structured intake tests pass.
- Playwright quote flow smoke passes.
- Full suite passes if practical.
- PR body explicitly states unchanged payload/ID/selector surfaces.

---

## 2. Docs and Current-State Traceability Audit

Deepen a docs-review skill that treats version markers, commit SHAs, roadmap state, and grounding-pack parity as audit-critical, not editorial.

The clearest example is the P2 review on PR #313, where an incorrect full SHA broke verified-baseline traceability. Similar current-state and grounding refresh patterns appeared around PR #307, PR #308, PR #310, and PR #313.

### What the skill should enforce

- Exact full SHA verification when a document says “full SHA.”
- Current version matches `VERSION`, README/version markers, and relevant docs.
- Roadmap “current state” is not stale.
- Source/generated-pack mapping is explicit.
- Grounding-pack regeneration is identified when required.
- Generated files are updated only through the existing export/parity workflow.
- PR body states what was regenerated and why.

### Trigger this skill when

- Updating `PROJECT_RULES.md`.
- Updating `PROJECT_VISION.md`.
- Updating roadmap/current-state docs.
- Updating GPT docs or grounding-pack sources.
- Updating agent/project instruction files that reference current repo state.

### Done criteria

- Version parity passes.
- GPT grounding parity passes if touched/affected.
- Commit SHAs resolve correctly.
- Source and generated files are both accounted for.
- Docs are not updated beyond scope.
- No runtime/deploy/version files drift unexpectedly.

---

## 3. Internal-Only Boundary Review for Admin, GPT, and Notification Work

Deepen a review skill that checks whether internal features stayed internal in both data shape and operator UX.

PR #299 and PR #311 centered on exposing useful status without leaking recipients or raw failure detail. PR #306 marked a GPT write action as consequential and kept it admin-only.

### What the skill should enforce

- No customer-surface leakage of internal/admin data.
- No raw notification recipient exposure.
- No raw failure/exception/SMTP detail exposure.
- Sanitized operator-facing errors.
- Read-only visibility is clearly separated from mutating actions.
- GPT write actions remain bounded and explicitly allowed.
- No accidental new pricing path.
- No internal risk/margin/admin-only fields exposed publicly.

### Trigger this skill when

- Adding admin visibility.
- Adding notification status/error handling.
- Adding GPT/admin-note behavior.
- Exposing new fields in admin read models.
- Changing public/customer response shapes.

### Done criteria

- Public/customer routes do not expose internal fields.
- Admin-only fields remain behind auth.
- Notification errors are sanitized.
- GPT actions cannot mutate operations outside approved bounds.
- Tests cover customer/admin boundary where practical.

---

## 4. SQLite Mutation-Safety Review for Operator Tools

Deepen a skill for narrow admin/data tools that can touch persisted records but must stay reversible and bounded.

PR #297 is the best example: allowlist-only cleanup, dry-run by default, `--apply` plus backup confirmation, single transaction, and explicit preserved tables. PR #296 adds the complementary pattern of separate tables and admin-only endpoints instead of overloading lifecycle data.

### What the skill should enforce

- Lineage mapping before data mutation.
- Preserved-surface enumeration.
- Dry-run by default.
- Explicit `--apply` or confirmation gate for destructive work.
- Backup confirmation before mutation.
- Single transaction for grouped updates/deletes.
- Allowlist-only table/record targeting.
- No broad delete path.
- Rollback posture documented.

### Trigger this skill when

- Adding cleanup scripts.
- Adding import/export/restore logic.
- Adding admin tools that mutate jobs/quotes/requests.
- Adding calibration/manual job tables.
- Touching persisted lifecycle records.

### Done criteria

- Dry-run mode exists where relevant.
- Backup/export path is clear.
- Transaction boundaries are explicit.
- Preserved tables/surfaces are enumerated.
- Tests prove no broad/accidental deletion path.
- Admin/audit logging exists for sensitive operations.

---

## 5. Small-PR Evidence Discipline

Deepen a meta-skill that standardizes how narrow PRs prove safety.

Recent Bay Delivery PRs repeat the same healthy pattern:

- protected no-go diff
- focused tests
- full suite when appropriate
- explicit unchanged surfaces
- P1/P2/P3 risk framing
- clean post-merge verification

That repetition is a signal that this is now a core repo competency worth preserving.

### What the skill should enforce

- Clear scope statement.
- Explicit files changed.
- Explicit files/surfaces not changed.
- Validation commands/results included.
- Protected no-go diff included.
- P1/P2/P3 self-review before commit when sensitive.
- Stop conditions respected.
- PR stops before merge.
- Post-merge verification follows merge.

### Trigger this skill when

- Any PR is opened.
- Any agent reports implementation complete.
- Any Codex/VS Code agent task touches repo files.
- Any docs/static/admin/backend change needs review.

### Done criteria

- PR has a narrow title and branch.
- Changed files match scope.
- Validation is appropriate for the change.
- Protected surfaces are checked.
- CI is green before merge.
- Post-merge verification passes.

---

## Practical Adoption Plan

Do not create all five skills immediately.

Use this progression:

1. Keep this note as reference.
2. Apply the relevant section manually during reviews.
3. If the same skill is used repeatedly, turn it into a lightweight checklist.
4. Only after repeated successful use, promote it into an agent skill or project instruction.

## Recommended Immediate Action

Do not turn this into active rules yet.

Save this file under:

```text
docs/notes/bay_delivery_skill_progression_recommendations.md
```

Then continue normal workflow. Use the sections above when the matching PR type appears.

## Final Principle

Bay Delivery Quote Copilot is strongest when each PR proves what changed and, just as importantly, what did not change.

The goal is not more process for its own sake. The goal is fewer surprise regressions, cleaner operator confidence, and safer production changes.
