# Bay Delivery Agent Template Usefulness Notes

Updated: 2026-05-24

## Purpose

This note records which automation/template suggestions are useful for Bay Delivery Quote Copilot and when to use them.

Bay Delivery Quote Copilot is production infrastructure. Use these templates only when they support safe, narrow, practical repo work. Do not let generic templates distract from the current verified workflow.

---

## Most useful templates

### 1. Scan outdated dependencies; propose safe upgrades with minimal changes

**Use when:**
- Planning a dependency/security review.
- Checking `requirements.txt` and `requirements.lock.txt`.
- Reviewing `pip-audit` results.
- Considering safe package upgrade candidates.

**Priority:** P2 later.

**Tool recommendation:** Codex preferred, because dependency changes can affect CI, Render, and runtime behavior.

**Important rule:** Start as read-only planning. Do not immediately upgrade packages unless the plan is clear and scoped.

---

### 2. Summarize CI failures and flaky tests from the last CI window

**Use when:**
- GitHub Actions fails.
- CI has flaky tests.
- We need a quick root-cause summary before writing a fix prompt.

**Priority:** Use only when CI fails.

**Tool recommendation:** VS Code or GitHub Actions view first. Use Codex only if the failure is complex or implementation-sensitive.

---

### 3. Check CI failures; group by likely root cause and suggest minimal fixes

**Use when:**
- CI fails and we need a practical action plan.
- Multiple tests fail and the cause is not obvious.

**Priority:** Use only when CI fails.

**Tool recommendation:** VS Code first for triage; Codex for deeper code fixes.

---

### 4. Audit performance regressions and propose highest-leverage fixes

**Use when:**
- The live app feels slow.
- Admin pages become heavy.
- Real traffic or database size creates noticeable latency.

**Priority:** P3 later.

**Tool recommendation:** Plan/audit first. Do not optimize without evidence.

**Important rule:** Avoid speculative performance work until there is real-world slowness or measurable data.

---

### 5. Before tagging, verify changelog, migrations, feature flags, and tests

**Use when:**
- Preparing a formal release/tag.
- Verifying a launch milestone.
- Checking that changelog/release notes, migrations, feature flags, and tests are aligned.

**Priority:** Later, when release tagging becomes part of the workflow.

**Tool recommendation:** VS Code Agent for read-only verification; Codex only if issues require code fixes.

---

## Maybe useful, but not urgent

### Draft weekly release notes from merged PRs

**Use when:**
- Creating a weekly project summary.
- Preparing a handoff.
- Recording what changed for business/ops history.

**Priority:** Optional.

---

### Synthesize this week’s PRs, rollouts, incidents, and reviews into a weekly update

**Use when:**
- Creating a weekly operational update.
- Summarizing progress for future handoffs.

**Priority:** Optional.

---

### Update AGENTS.md with newly discovered workflows and commands

**Use when:**
- `AGENTS.md` is confirmed active and stale.
- A workflow discovery should be preserved for future agents.

**Priority:** Only after an audit proves it is needed.

**Important rule:** PR #313 already refreshed the active project/agent instruction files, so do not chase this unless `AGENTS.md` is actively used.

---

### Identify untested paths from recent changes; add focused tests

**Use when:**
- A PR touched behavior and coverage feels thin.
- Review comments suggest missing tests.
- A bug reveals an untested edge case.

**Priority:** Useful, but can become a rabbit hole.

**Important rule:** Use only when there is a specific coverage concern. Avoid broad “test everything” prompts.

---

## Not useful for Bay Delivery right now

These are generic templates and should not be used unless a very specific need appears:

- Create a small classic game with minimal scope.
- From recent PRs and reviews, suggest next skills to deepen.
- Summarize yesterday’s git activity for standup.
- Compare recent changes to benchmarks or traces.
- Triage new issues; suggest owner, priority, and labels.

These are not bad templates; they are just not aligned with current Bay Delivery priorities.

---

## Practical use order

| Situation | Useful template |
|---|---|
| CI fails | Summarize CI failures / Check CI failures |
| Dependency/security review | Scan outdated dependencies |
| Before version tag or release | Before tagging, verify changelog/migrations/flags/tests |
| Weekly handoff/update | Draft weekly release notes / Synthesize weekly update |
| Coverage concern after PR | Identify untested paths |

---

## Current priority reminder

Do not use these templates during the current narrow security hardening task unless needed.

Current task in motion:

```text
create admin post origin fail closed hardening
```

After that PR is reviewed, merged, and verified, the next most useful template is likely:

```text
Scan outdated dependencies; propose safe upgrades with minimal changes.
```

Use it as a read-only plan first, not as an immediate upgrade PR.

---

## Bay Delivery rule of thumb

Use templates only when they reduce risk, clarify scope, or improve launch-readiness. Avoid generic automation rabbit holes. Bay Delivery needs boring, reliable, margin-protective infrastructure.
